"""Resources, context scopes, and which resources each agent gets."""
from typing import Literal
from uuid import UUID

from models.agents import AgentWorker
from models.context_scope import ContextScope, Resource
from models.projects import ProjectRow
from repositories.agent_repo import AgentRepository
from repositories.project_repo import ProjectRepository
from repositories.resource_repo import ResourceRepository
from repositories.role_repo import RoleRepository
from repositories.scope_repo import ScopeRepository
from services.errors import ConflictError, NotFoundError


class ScopeService:
    """Manages resources and context scopes.

    Invariants:
    - every project context scope only contains resources from that project's main scope;
    - an agent's manual context scope is one of its project's context scopes.
    """

    def __init__(
            self,
            resources: ResourceRepository,
            scopes: ScopeRepository,
            projects: ProjectRepository,
            roles: RoleRepository,
            agents: AgentRepository,
    ):
        self._resources = resources
        self._scopes = scopes
        self._projects = projects
        self._roles = roles
        self._agents = agents

    def _require_scope(self, scope_id: UUID) -> ContextScope:
        scope = self._scopes.get(scope_id)
        if not scope:
            raise NotFoundError(f"Context scope {scope_id} not found")
        return scope

    def _require_resources(self, resource_ids: list[UUID]) -> None:
        found = {resource.id for resource in self._resources.get_many(resource_ids)}
        missing = set(resource_ids) - found
        if missing:
            raise NotFoundError(f"Resources {sorted(map(str, missing))} not found")

    def _require_in_main_scope(self, project: ProjectRow, resource_ids: list[UUID]) -> None:
        outside = set(resource_ids) - set(self._require_scope(project.main_scope).resources)
        if outside:
            raise ConflictError(
                f"Resources {sorted(map(str, outside))} are not in the main scope of project {project.name!r}"
            )

    # Resources

    def create_resource(
            self,
            name: str,
            type: Literal["file", "text", "url"],
            storage: Literal["in_place", "anthropic_managed"],
            content: str | None = None,
            anthropic_file_id: str | None = None,
    ) -> Resource:
        """Create a resource.

        Raises ConflictError if in-place resources lack `content`, or anthropic-managed resources aren't files
        with an `anthropic_file_id`.
        """
        if storage == "in_place" and not content:
            raise ConflictError("In-place resources need `content`")
        if storage == "anthropic_managed":
            if type != "file":
                raise ConflictError("Only file resources can be anthropic-managed")
            if not anthropic_file_id:
                raise ConflictError("Anthropic-managed resources need `anthropic_file_id`")
        return self._resources.add(
            Resource(name=name, type=type, storage=storage, content=content, anthropic_file_id=anthropic_file_id)
        )

    def get_resource(self, resource_id: UUID) -> Resource | None:
        return self._resources.get(resource_id)

    def list_resources(self) -> list[Resource]:
        """All resources, ordered by name."""
        return self._resources.list()

    def delete_resource(self, resource_id: UUID) -> None:
        """Delete the resource and remove it from every scope. Raises NotFoundError if it doesn't exist."""
        if not self._resources.delete(resource_id):
            raise NotFoundError(f"Resource {resource_id} not found")

    # Scopes

    def create_scope(self, resource_ids: list[UUID] | None = None) -> ContextScope:
        """Create a standalone scope. Raises NotFoundError if a resource doesn't exist."""
        resource_ids = resource_ids or []
        self._require_resources(resource_ids)
        return self._scopes.add(ContextScope(resources=resource_ids))

    def create_project_scope(self, project_id: UUID, resource_ids: list[UUID] | None = None) -> ContextScope:
        """Create an extra context scope in a project.

        Raises NotFoundError if the project doesn't exist, ConflictError if a resource isn't in its main scope.
        """
        project = self._projects.get(project_id)
        if not project:
            raise NotFoundError(f"Project {project_id} not found")
        resource_ids = resource_ids or []
        self._require_in_main_scope(project, resource_ids)
        scope = self._scopes.add(ContextScope(resources=resource_ids))
        project.context_scopes.append(scope.id)
        self._projects.update(project)
        return scope

    def get_scope(self, scope_id: UUID) -> ContextScope | None:
        return self._scopes.get(scope_id)

    def get_scope_resources(self, scope_id: UUID) -> list[Resource]:
        """The scope's resources, ordered by name. Raises NotFoundError if the scope doesn't exist."""
        return self._resources.get_many(self._require_scope(scope_id).resources)

    def add_resource(self, scope_id: UUID, resource_id: UUID) -> ContextScope:
        """Add a resource to a scope.

        Raises NotFoundError if either doesn't exist, ConflictError if the scope is a secondary project scope
        and the resource isn't in the project's main scope.
        """
        self._require_scope(scope_id)
        self._require_resources([resource_id])
        project = self._projects.get_by_scope(scope_id)
        if project and project.main_scope != scope_id:
            self._require_in_main_scope(project, [resource_id])
        self._scopes.add_resource(scope_id, resource_id)
        return self._scopes.get(scope_id)

    def remove_resource(self, scope_id: UUID, resource_id: UUID) -> ContextScope:
        """Remove a resource from a scope. Raises NotFoundError if the scope doesn't exist.

        Removing a resource from a project's main scope also removes it from the project's other scopes.
        """
        self._require_scope(scope_id)
        project = self._projects.get_by_scope(scope_id)
        if project and project.main_scope == scope_id:
            for project_scope_id in project.context_scopes:
                self._scopes.remove_resource(project_scope_id, resource_id)
        else:
            self._scopes.remove_resource(scope_id, resource_id)
        return self._scopes.get(scope_id)

    def delete_project_scope(self, scope_id: UUID) -> None:
        """Delete a secondary project scope. Agents using it fall back to their default scope.

        Raises NotFoundError if the scope doesn't belong to a project, ConflictError for a main scope.
        """
        project = self._projects.get_by_scope(scope_id)
        if not project:
            raise NotFoundError(f"Context scope {scope_id} does not belong to a project")
        if project.main_scope == scope_id:
            raise ConflictError("A project's main scope can only be deleted with the project")
        self._scopes.delete(scope_id)

    # Agents

    def set_agent_scope(self, agent_id: UUID, scope_id: UUID | None) -> AgentWorker:
        """Pin the agent to one of its project's scopes, or pass None to use the default scope.

        Raises NotFoundError if the agent doesn't exist, ConflictError if the scope isn't in its project.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            raise NotFoundError(f"Agent {agent_id} not found")
        if scope_id is not None:
            project = self._projects.get(agent.project)
            if scope_id not in project.context_scopes:
                raise ConflictError(f"Context scope {scope_id} is not defined in project {project.name!r}")
        agent.context_scope = scope_id
        self._agents.update(agent)
        return agent

    def resolve_agent_resources(self, agent: AgentWorker) -> list[Resource]:
        """The agent's own scope if set, otherwise the intersection of its project's main scope and role scope."""
        if agent.context_scope is not None:
            return self.get_scope_resources(agent.context_scope)
        project = self._projects.get(agent.project)
        role = self._roles.get(agent.role)
        if not project or not role:
            raise NotFoundError(f"Project or role of agent {agent.name!r} not found")
        project_resources = set(self._require_scope(project.main_scope).resources)
        role_resources = set(self._require_scope(role.context_scope).resources)
        return self._resources.get_many(list(project_resources & role_resources))
