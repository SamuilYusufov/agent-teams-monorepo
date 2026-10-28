"""Agents and the links that allow them to message each other."""
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# How the sender of a message relates to its recipient.
type RelationshipType = Literal["report", "manager", "peer", "assistant"]


class AgentWorker(BaseModel):
    """An agent working in a project, backed by a Managed Agents agent."""

    id: UUID = Field(default_factory=uuid4)
    anthropic_id: str = Field(description="ID of the agent in the Managed Agents API.")
    name: str = Field(description="Unique name the agent is addressed by.")
    project: UUID = Field(description="The one project the agent works in.")
    role: UUID = Field(description="The one role the agent has.")
    context_scope: UUID | None = Field(
        description="The agent's context scope. When null, the agent uses the intersection of its project's "
        "main scope and its role's scope."
    )


class AgentLink(BaseModel):
    """Permission for `from_agent` to send messages of `type` to `to_agent`."""

    id: UUID = Field(default_factory=uuid4)
    from_agent: UUID = Field(description="The agent allowed to send messages.")
    to_agent: UUID = Field(description="The agent receiving the messages.")
    type: RelationshipType = Field(description="The type of relationship between the agents.")


class MessageDelivery(BaseModel):
    """Outcome of sending a message from one agent to another."""

    delivered: bool
    reason: str | None = Field(default=None, description="Why the message was not delivered.")


class TeamOverview(BaseModel):
    """An agent's view of itself and its team."""

    name: str
    role: str
    role_description: str
    task_examples: list[str]
    source_examples: list[str]
    project: str
    teammates: dict[str, str] = Field(description="Names of the other agents in the project, mapped to their roles.")
    can_message: dict[str, list[RelationshipType]] = Field(
        description="Agents this agent can send messages to, with the allowed message types."
    )
    can_receive_from: dict[str, list[RelationshipType]] = Field(
        description="Agents that can send messages to this agent, with their message types."
    )
