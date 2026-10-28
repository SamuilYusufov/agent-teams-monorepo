"""Roles: reusable job descriptions for agents."""
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class AgentRole(BaseModel):
    """A role an agent can take on. Roles are shared between projects."""

    # Fields with defaults are always in responses, so document them as required there.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    task_examples: list[str] = Field(description="Example tasks for agents with this role.")
    source_examples: list[str] = Field(description="Example sources agents should ground their outputs in.")
    context_scope: UUID = Field(
        description="Default context scope for this role, unless an agent's scope has been set manually."
    )
