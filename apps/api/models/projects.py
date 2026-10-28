"""Projects: a team of agents working towards a shared goal."""
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ProjectRow(BaseModel):
    """Project row model inside the project repo."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    system_prompt: str
    team: list[UUID] = Field(
        description="IDs of the agents inside this project. Each agent is only inside one project."
    )
    main_scope: UUID = Field(
        default_factory=uuid4, description="The main project scope containing all project resources."
    )
    context_scopes: list[UUID] = Field(
        description="All context scopes defined for the agents in this project, including the main scope. "
        "They cannot contain resources missing from the main scope."
    )


class Project(BaseModel):
    """Project model used by services after additional fields are populated."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    system_prompt: str = Field(description="Prepended to the system prompt of every agent in the project.")
    team: list[UUID] = Field(description="IDs of the agents inside this project.")
    roles: list[UUID] = Field(description="IDs of the roles available inside this project.")
    main_scope: UUID = Field(
        default_factory=uuid4, description="The main project scope containing all project resources."
    )
    context_scopes: list[UUID] = Field(
        description="All context scopes defined for the agents in this project, including the main scope."
    )
