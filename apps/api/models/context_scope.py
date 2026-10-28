"""Resources and the context scopes that group them."""
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Resource(BaseModel):
    """A piece of context that can be given to agents."""

    # Fields with defaults are always in responses, so document them as required there.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: UUID = Field(default_factory=uuid4)
    name: str
    type: Literal["file", "text", "url"]
    storage: Literal["in_place", "anthropic_managed"] = Field(
        description="`in_place`: the text, url etc. is available in the database. "
        "`anthropic_managed`: the file was uploaded to the Managed Agents backend "
        "and is populated into session resources from there."
    )
    content: str | None = Field(default=None, description="The text or url itself. Required for in-place storage.")
    anthropic_file_id: str | None = Field(
        default=None, description="Files API ID. Required for Anthropic-managed storage."
    )


class ContextScope(BaseModel):
    """A set of resources available to an agent, role or project."""

    # Fields with defaults are always in responses, so document them as required there.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: UUID = Field(default_factory=uuid4)
    resources: list[UUID]
