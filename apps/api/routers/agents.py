"""Endpoints for agents, their sessions, links between them, and messaging."""
from uuid import UUID

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from dependencies import ServicesDep
from models.agents import AgentLink, AgentWorker, MessageDelivery, RelationshipType
from routers.schemas import SessionInfo, errors
from services.errors import NotFoundError

router = APIRouter(prefix="/api/agent", tags=["agents"])


class AgentCreate(BaseModel):
    name: str = Field(description="Unique agent name.")
    role_id: UUID = Field(description="Must be available in the project.")
    project_id: UUID
    context_scope: UUID | None = Field(
        default=None,
        description="One of the project's context scopes. Defaults to the intersection of the project's main "
        "scope and the role's scope.",
    )


class AgentScopeUpdate(BaseModel):
    context_scope: UUID | None = Field(description="One of the project's context scopes, or null for the default.")


class LinkCreate(BaseModel):
    to_agent: UUID = Field(description="The agent that will receive messages.")
    type: RelationshipType


class MessageSend(BaseModel):
    from_agent: str = Field(description="Name of the sending agent.")
    to_agent: str = Field(description="Name of the receiving agent.")
    message: str
    type: RelationshipType


# Agents

@router.post("", status_code=status.HTTP_201_CREATED, responses=errors(404, 409))
async def create_agent(body: AgentCreate, services: ServicesDep) -> AgentWorker:
    """Create an agent in a project, both locally and in the Managed Agents API."""
    role = services.roles.get_role(body.role_id)
    if not role:
        raise NotFoundError(f"Role {body.role_id} not found")
    project = services.projects.get_project(body.project_id)
    if not project:
        raise NotFoundError(f"Project {body.project_id} not found")
    return await services.agents.create_agent(body.name, role, project, body.context_scope)


@router.get("")
async def list_agents(services: ServicesDep, project_id: UUID | None = None) -> list[AgentWorker]:
    """List all agents, or only those in `project_id`, ordered by name."""
    return services.agents.list_agents(project_id)


@router.get("/{agent_id}", responses=errors(404))
async def get_agent(agent_id: UUID, services: ServicesDep) -> AgentWorker:
    agent = services.agents.get_agent(agent_id)
    if not agent:
        raise NotFoundError(f"Agent {agent_id} not found")
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT, responses=errors(404))
async def delete_agent(agent_id: UUID, services: ServicesDep) -> None:
    """Stop the agent's sessions, archive it in the Managed Agents API, and delete it."""
    await services.agents.delete_agent(agent_id)


@router.put("/{agent_id}/scope", responses=errors(404, 409))
async def set_agent_scope(agent_id: UUID, body: AgentScopeUpdate, services: ServicesDep) -> AgentWorker:
    """Pin the agent to one of its project's context scopes, or reset it to the default with null."""
    return services.scopes.set_agent_scope(agent_id, body.context_scope)


# Sessions

@router.post("/{agent_id}/start", responses=errors(404))
async def start_agent(agent_id: UUID, services: ServicesDep) -> SessionInfo:
    """Start a session with the agent's context scope, or return the session that is already live."""
    return SessionInfo.from_session(await services.agents.start(agent_id))


@router.post("/{agent_id}/stop", status_code=status.HTTP_204_NO_CONTENT, responses=errors(404))
async def stop_agent(agent_id: UUID, services: ServicesDep) -> None:
    """Archive every live session of the agent."""
    await services.agents.stop(agent_id)


# Links

@router.post("/{agent_id}/links", status_code=status.HTTP_201_CREATED, responses=errors(404, 409))
async def add_link(agent_id: UUID, body: LinkCreate, services: ServicesDep) -> AgentLink:
    """Allow this agent to send messages of `type` to `to_agent`. Both must be in the same project."""
    return services.agents.add_link(agent_id, body.to_agent, body.type)


@router.get("/{agent_id}/links")
async def list_links(agent_id: UUID, services: ServicesDep) -> list[AgentLink]:
    """List the agent's links in both directions."""
    return services.agents.list_links(agent_id)


@router.delete("/{agent_id}/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT, responses=errors(404))
async def remove_link(agent_id: UUID, link_id: UUID, services: ServicesDep) -> None:
    """Delete one of the agent's links, in either direction."""
    if link_id not in {link.id for link in services.agents.list_links(agent_id)}:
        raise NotFoundError(f"Link {link_id} not found for agent {agent_id}")
    services.agents.remove_link(link_id)


# Messaging

@router.post("/messages", responses=errors(404, 409))
async def send_message(body: MessageSend, services: ServicesDep) -> MessageDelivery:
    """Send a message from one agent to another, starting the recipient's session if needed.

    Only delivered along an existing link of the given type. Otherwise the sender's session is told which types
    it may use instead, and the response explains why the message was not delivered.
    """
    return await services.agents.send_message(body.from_agent, body.to_agent, body.message, body.type)
