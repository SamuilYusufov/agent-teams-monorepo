"""Endpoints for roles."""
from uuid import UUID

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from dependencies import ServicesDep
from models.roles import AgentRole
from routers.schemas import errors
from services.errors import NotFoundError

router = APIRouter(prefix="/api/role", tags=["roles"])


class RoleCreate(BaseModel):
    name: str = Field(description="Unique role name.")
    description: str
    task_examples: list[str] = Field(default=[], description="Example tasks for agents with this role.")
    source_examples: list[str] = Field(
        default=[], description="Example sources agents should ground their outputs in."
    )
    resource_ids: list[UUID] = Field(default=[], description="Initial resources of the role's context scope.")


class RoleUpdate(BaseModel):
    name: str
    description: str
    task_examples: list[str]
    source_examples: list[str]


@router.post("", status_code=status.HTTP_201_CREATED, responses=errors(404, 409))
async def create_role(body: RoleCreate, services: ServicesDep) -> AgentRole:
    """Create a role together with its default context scope."""
    return services.roles.create_role(
        body.name, body.description, body.task_examples, body.source_examples, body.resource_ids
    )


@router.get("")
async def list_roles(services: ServicesDep) -> list[AgentRole]:
    """List all roles, ordered by name."""
    return services.roles.list_roles()


@router.get("/{role_id}", responses=errors(404))
async def get_role(role_id: UUID, services: ServicesDep) -> AgentRole:
    role = services.roles.get_role(role_id)
    if not role:
        raise NotFoundError(f"Role {role_id} not found")
    return role


@router.put("/{role_id}", responses=errors(404, 409))
async def update_role(role_id: UUID, body: RoleUpdate, services: ServicesDep) -> AgentRole:
    """Update a role. Its context scope's resources are edited through `/api/scope`."""
    role = services.roles.get_role(role_id)
    if not role:
        raise NotFoundError(f"Role {role_id} not found")
    return services.roles.update_role(role.model_copy(update=body.model_dump()))


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT, responses=errors(404, 409))
async def delete_role(role_id: UUID, services: ServicesDep) -> None:
    """Delete a role and its context scope. Fails with 409 while agents have the role."""
    services.roles.delete_role(role_id)
