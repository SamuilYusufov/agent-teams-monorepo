"""Agent management, agent sessions, links between agents, and messaging."""
from uuid import UUID, uuid4

from anthropic import AsyncAnthropic
from anthropic.types.beta import BetaManagedAgentsAgent, BetaManagedAgentsSession
from anthropic.types.beta.session_create_params import Resource as SessionResource

from models.agents import AgentLink, AgentWorker, MessageDelivery, RelationshipType, TeamOverview
from models.context_scope import Resource
from models.projects import Project
from models.roles import AgentRole
from repositories.agent_link_repo import AgentLinkRepository
from repositories.agent_repo import AgentRepository
from repositories.agent_to_project_repo import AgentToProjectRepository
from repositories.role_repo import RoleRepository
from services.errors import ConflictError, NotFoundError
from services.mcp_access import McpAccess
from services.scope_service import ScopeService

MODEL = "claude-opus-5-5"
LIVE_SESSION_STATUSES = ["rescheduling", "running", "idle"]
# Name of the team MCP server in the agents' Managed Agents configuration.
TEAM_MCP_SERVER = "team"


class AgentService:
    """Manages agents locally and in the Managed Agents API.

    Each agent runs in at most one live session at a time. With `mcp_access`, agents are created with access to
    the team MCP server, which they use to message each other.
    """

    def __init__(
            self,
            agents: AgentRepository,
            agent_projects: AgentToProjectRepository,
            roles: RoleRepository,
            links: AgentLinkRepository,
            scope_service: ScopeService,
            environment_id: str,
            client: AsyncAnthropic | None = None,
            mcp_access: McpAccess | None = None,
    ):
        self._agents = agents
        self._agent_projects = agent_projects
        self._roles = roles
        self._links = links
        self._scope_service = scope_service
        self._environment_id = environment_id
        self._client = client or AsyncAnthropic()
        self._mcp_access = mcp_access

    # Lookups

    def _require_agent(self, name: str) -> AgentWorker:
        agent = self._agents.get_by_name(name)
        if not agent:
            raise NotFoundError(f"Agent {name!r} not found")
        return agent

    def _team(self, agent_ids: list[UUID]) -> dict[str, str]:
        """Map teammate names to their role names."""
        team = {}
        for agent_id in agent_ids:
            agent = self._agents.get(agent_id)
            if not agent:
                continue
            role = self._roles.get(agent.role)
            team[agent.name] = role.name if role else "unknown"
        return team

    def _allowed_types(self, from_agent: AgentWorker, to_agent: AgentWorker) -> list[RelationshipType]:
        return [link.type for link in self._links.list_between(from_agent.id, to_agent.id)]

    # Prompts and session parameters

    @staticmethod
    def _file_mount_path(resource: Resource) -> str:
        return f"/mnt/session/uploads/{resource.anthropic_file_id}"

    def _build_system_prompt(self, name: str, role: AgentRole, project: Project) -> str:
        team = self._team(project.team)
        return project.system_prompt + f"""
    In this project, you are an agent with the following role: {role.name}.
    You have a unique name: {name}.
    Your brief role description: {role.description}.
    Your project team includes other agents with the following names and roles: {team}.
    Example tasks: {role.task_examples}.
    Example sources to ground your outputs: {role.source_examples}.
    You always stay in the same role.
    """

    def _build_session_system_prompt(
            self,
            agent: BetaManagedAgentsAgent,
            agent_worker: AgentWorker,
            resources: list[Resource],
    ) -> str:
        """Append the agent's messaging links and context scope to its system prompt for this session."""
        prompt = agent.system or ""
        recipients: dict[str, list[RelationshipType]] = {}
        for link in self._links.list_from(agent_worker.id):
            to_agent = self._agents.get(link.to_agent)
            if to_agent:
                recipients.setdefault(to_agent.name, []).append(link.type)
        if recipients:
            prompt += "\n    You can send messages to these agents, with these message types: " + str(recipients)
        if resources:
            lines = []
            for resource in resources:
                if resource.storage == "anthropic_managed":
                    lines.append(f"- {resource.name} (file mounted at {self._file_mount_path(resource)})")
                else:
                    lines.append(f"- {resource.name} ({resource.type}):\n{resource.content}")
            prompt += "\n    Resources in your context scope:\n" + "\n".join(lines)
        return prompt

    def _build_session_resources(self, resources: list[Resource]) -> list[SessionResource]:
        return [
            {"type": "file", "file_id": resource.anthropic_file_id, "mount_path": self._file_mount_path(resource)}
            for resource in resources
            if resource.storage == "anthropic_managed"
        ]

    # Managed Agents API

    async def _live_session(self, anthropic_agent_id: str) -> BetaManagedAgentsSession | None:
        sessions = self._client.beta.sessions.list(
            agent_id=anthropic_agent_id,
            include_archived=False,
            statuses=LIVE_SESSION_STATUSES,
            limit=1,
        )
        async for session in sessions:
            return session
        return None

    async def _send_text(self, session_id: str, text: str) -> None:
        await self._client.beta.sessions.events.send(
            session_id,
            events=[{"type": "user.message", "content": [{"type": "text", "text": text}]}],
        )

    # Agents

    async def create_agent(
            self,
            name: str,
            role: AgentRole,
            project: Project,
            context_scope: UUID | None = None,
    ) -> AgentWorker:
        """Create the agent. Without `context_scope` it uses the intersection of the project and role scopes.

        Raises ConflictError if the name is taken, or the role or scope isn't part of the project.
        """
        if role.id not in project.roles:
            raise ConflictError(f"Role {role.name!r} is not available in project {project.name!r}")
        if context_scope is not None and context_scope not in project.context_scopes:
            raise ConflictError(f"Context scope {context_scope} is not defined in project {project.name!r}")
        if self._agents.get_by_name(name):
            raise ConflictError(f"Agent {name!r} already exists")

        agent_id = uuid4()
        team_mcp = {}
        if self._mcp_access:
            team_mcp = {
                "mcp_servers": [{"type": "url", "name": TEAM_MCP_SERVER, "url": self._mcp_access.url_for(agent_id)}],
                "tools": [
                    {
                        "type": "mcp_toolset",
                        "mcp_server_name": TEAM_MCP_SERVER,
                        # MCP toolsets default to `always_ask`, which pauses the session until a confirmation that
                        # nothing here sends. The team server is first-party and its tools only read the agent's
                        # team and message along links set up through the API, so its calls run unattended.
                        "default_config": {"permission_policy": {"type": "always_allow"}},
                    }
                ],
            }
        agent = await self._client.beta.agents.create(
            name=name,
            model=MODEL,
            system=self._build_system_prompt(name, role, project),
            **team_mcp,
        )

        agent_worker = AgentWorker(
            id=agent_id,
            anthropic_id=agent.id,
            name=agent.name,
            role=role.id,
            project=project.id,
            context_scope=context_scope,
        )

        try:
            # Saving the agent also adds it to the project's team (team is derived from agents.project_id).
            self._agents.add(agent_worker)
        except Exception:
            # Don't leave an orphaned remote agent behind if the local save fails.
            await self._client.beta.agents.archive(agent_id=agent.id)
            raise

        return agent_worker

    def get_agent(self, agent_id: UUID) -> AgentWorker | None:
        return self._agents.get(agent_id)

    def get_agent_by_name(self, name: str) -> AgentWorker | None:
        return self._agents.get_by_name(name)

    async def retrieve_agent(self, agent_id: UUID) -> tuple[AgentWorker, BetaManagedAgentsAgent] | None:
        """The local agent together with its Managed Agents counterpart, or None if it doesn't exist."""
        agent_worker = self._agents.get(agent_id)
        if not agent_worker:
            return None
        agent = await self._client.beta.agents.retrieve(agent_worker.anthropic_id)
        return agent_worker, agent

    def list_agents(self, project_id: UUID | None = None) -> list[AgentWorker]:
        """All agents, or only those in `project_id`, ordered by name."""
        if project_id is None:
            return self._agents.list()
        return [self._agents.get(agent_id) for agent_id in self._agent_projects.get_agent_ids(project_id)]

    def team_overview(self, agent: AgentWorker, project: Project) -> TeamOverview:
        """The agent's role, its teammates, and who it can message and hear from. `project` is the agent's project."""
        role = self._roles.get(agent.role)
        can_message: dict[str, list[RelationshipType]] = {}
        for link in self._links.list_from(agent.id):
            to_agent = self._agents.get(link.to_agent)
            if to_agent:
                can_message.setdefault(to_agent.name, []).append(link.type)
        can_receive_from: dict[str, list[RelationshipType]] = {}
        for link in self._links.list_to(agent.id):
            from_agent = self._agents.get(link.from_agent)
            if from_agent:
                can_receive_from.setdefault(from_agent.name, []).append(link.type)
        teammates = self._team([agent_id for agent_id in project.team if agent_id != agent.id])
        return TeamOverview(
            name=agent.name,
            role=role.name,
            role_description=role.description,
            task_examples=role.task_examples,
            source_examples=role.source_examples,
            project=project.name,
            teammates=teammates,
            can_message=can_message,
            can_receive_from=can_receive_from,
        )

    async def delete_agent(self, agent_id: UUID) -> None:
        """Stop the agent's sessions, archive the remote agent, then remove the local record.

        Raises NotFoundError if the agent doesn't exist.
        """
        agent_worker = self._agents.get(agent_id)
        if not agent_worker:
            raise NotFoundError(f"Agent {agent_id} not found")
        await self.stop(agent_id)
        await self._client.beta.agents.archive(agent_worker.anthropic_id)
        self._agents.delete(agent_id)

    # Sessions

    async def start(self, agent_id: UUID) -> BetaManagedAgentsSession:
        """Start a session with the agent's context scope, or return the session that is already live.

        Raises NotFoundError if the agent doesn't exist.
        """
        retrieve_agent_result = await self.retrieve_agent(agent_id)
        if not retrieve_agent_result:
            raise NotFoundError(f"Agent {agent_id} not found")
        agent_worker, agent = retrieve_agent_result

        live_session = await self._live_session(agent.id)
        if live_session:
            return live_session

        resources = self._scope_service.resolve_agent_resources(agent_worker)
        return await self._client.beta.sessions.create(
            agent={
                "type": "agent_with_overrides",
                "id": agent.id,
                "version": agent.version,
                "system": self._build_session_system_prompt(agent, agent_worker, resources),
            },
            environment_id=self._environment_id,
            resources=self._build_session_resources(resources),
            metadata={"agent_id": str(agent_worker.id), "project_id": str(agent_worker.project)},
            title=f"{agent_worker.name} session",
        )

    async def stop(self, agent_id: UUID) -> None:
        """Archive every live session of the agent. Raises NotFoundError if the agent doesn't exist."""
        agent_worker = self._agents.get(agent_id)
        if not agent_worker:
            raise NotFoundError(f"Agent {agent_id} not found")
        sessions = self._client.beta.sessions.list(
            agent_id=agent_worker.anthropic_id,
            include_archived=False,
            statuses=LIVE_SESSION_STATUSES,
        )
        async for session in sessions:
            await self._client.beta.sessions.archive(session.id)

    # Links

    def add_link(self, from_agent_id: UUID, to_agent_id: UUID, type: RelationshipType) -> AgentLink:
        """Allow `from_agent` to send messages of `type` to `to_agent`. Takes effect in new sessions' prompts.

        Raises NotFoundError if an agent doesn't exist, ConflictError for self-links, links across projects
        and duplicate links.
        """
        from_agent = self._agents.get(from_agent_id)
        to_agent = self._agents.get(to_agent_id)
        if not from_agent or not to_agent:
            raise NotFoundError(f"Agent {from_agent_id if not from_agent else to_agent_id} not found")
        if from_agent.id == to_agent.id:
            raise ConflictError("An agent cannot be linked to itself")
        if from_agent.project != to_agent.project:
            raise ConflictError("Only agents in the same project can be linked")
        if type in self._allowed_types(from_agent, to_agent):
            raise ConflictError(f"{from_agent.name!r} can already send {type!r} messages to {to_agent.name!r}")
        return self._links.add(AgentLink(from_agent=from_agent.id, to_agent=to_agent.id, type=type))

    def list_links(self, agent_id: UUID) -> list[AgentLink]:
        """Links in both directions for the agent."""
        return self._links.list_from(agent_id) + self._links.list_to(agent_id)

    def remove_link(self, link_id: UUID) -> None:
        """Delete the link. Raises NotFoundError if it doesn't exist."""
        if not self._links.delete(link_id):
            raise NotFoundError(f"Link {link_id} not found")

    # Messaging

    async def send_message(
            self,
            from_agent_name: str,
            to_agent_name: str,
            message: str,
            type: RelationshipType,
            notify_sender: bool = True,
    ) -> MessageDelivery:
        """Deliver `message` to the recipient's session, starting one if needed.

        Messages are only delivered along an existing `type` link from the sender to the recipient. Otherwise the
        result says which message types the sender may use for that recipient. With `notify_sender`, the sender's
        session is also sent that reason; callers that return the result to the sender directly can turn it off.
        Raises NotFoundError if an agent doesn't exist, ConflictError if they are in different projects or the
        sender has no live session to notify.
        """
        from_agent = self._require_agent(from_agent_name)
        to_agent = self._require_agent(to_agent_name)
        if from_agent.project != to_agent.project:
            raise ConflictError(f"Agents {from_agent.name!r} and {to_agent.name!r} are in different projects")

        allowed_types = self._allowed_types(from_agent, to_agent)
        if type not in allowed_types:
            if allowed_types:
                reason = (
                    f"Your {type!r} message to {to_agent.name} was not delivered. "
                    f"You can only send them messages of these types: {allowed_types}."
                )
            else:
                reason = f"Your message to {to_agent.name} was not delivered. You are not allowed to message them."
            if notify_sender:
                from_session = await self._live_session(from_agent.anthropic_id)
                if not from_session:
                    raise ConflictError(f"Agent {from_agent.name!r} has no live session to notify")
                await self._send_text(from_session.id, reason)
            return MessageDelivery(delivered=False, reason=reason)

        to_session = await self.start(to_agent.id)
        await self._send_text(to_session.id, f"Message from {from_agent.name} ({type}):\n{message}")
        return MessageDelivery(delivered=True)
