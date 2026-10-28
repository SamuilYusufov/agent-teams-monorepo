"""Endpoints for resources and context scopes."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from dependencies import ServicesDep
from models.context_scope import ContextScope, Resource
from routers.schemas import errors
from services.errors import NotFoundError

resource_router = APIRouter(prefix="/api/resource", tags=["resources"])
scope_router = APIRouter(prefix="/api/scope", tags=["scopes"])


class ResourceCreate(BaseModel):
    name: str
    type: Literal["file", "text", "url"]
    storage: Literal["in_place", "anthropic_managed"] = Field(
        description="`anthropic_managed` resources must be files uploaded through the Files API."
    )
    content: str | None = Field(default=None, description="The text or url itself. Required for in-place storage.")
    anthropic_file_id: str | None = Field(
        default=None, description="Files API ID. Required for Anthropic-managed storage."
    )


# Resources

@resource_router.post("", status_code=status.HTTP_201_CREATED, responses=errors(409))
async def create_resource(body: ResourceCreate, services: ServicesDep) -> Resource:
    """Create a resource. In-place resources need `content`; Anthropic-managed files need `anthropic_file_id`."""
    return services.scopes.create_resource(**body.model_dump())


@resource_router.get("")
async def list_resources(services: ServicesDep) -> list[Resource]:
    """List all resources, ordered by name."""
    return services.scopes.list_resources()


@resource_router.get("/{resource_id}", responses=errors(404))
async def get_resource(resource_id: UUID, services: ServicesDep) -> Resource:
    resource = services.scopes.get_resource(resource_id)
    if not resource:
        raise NotFoundError(f"Resource {resource_id} not found")
    return resource


@resource_router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT, responses=errors(404))
async def delete_resource(resource_id: UUID, services: ServicesDep) -> None:
    """Delete a resource and remove it from every scope."""
    services.scopes.delete_resource(resource_id)


# Scopes. Project and role scopes are created together with their project or role;
# extra project scopes via POST /api/project/{project_id}/scopes.

@scope_router.get("/{scope_id}", responses=errors(404))
async def get_scope(scope_id: UUID, services: ServicesDep) -> ContextScope:
    scope = services.scopes.get_scope(scope_id)
    if not scope:
        raise NotFoundError(f"Context scope {scope_id} not found")
    return scope


@scope_router.get("/{scope_id}/resources", responses=errors(404))
async def get_scope_resources(scope_id: UUID, services: ServicesDep) -> list[Resource]:
    """List the scope's resources, ordered by name."""
    return services.scopes.get_scope_resources(scope_id)


@scope_router.put("/{scope_id}/resources/{resource_id}", responses=errors(404, 409))
async def add_resource(scope_id: UUID, resource_id: UUID, services: ServicesDep) -> ContextScope:
    """Add a resource to a scope. Extra project scopes only accept resources from the project's main scope."""
    return services.scopes.add_resource(scope_id, resource_id)


@scope_router.delete("/{scope_id}/resources/{resource_id}", responses=errors(404))
async def remove_resource(scope_id: UUID, resource_id: UUID, services: ServicesDep) -> ContextScope:
    """Remove a resource from a scope. Removing it from a project's main scope removes it from all project scopes."""
    return services.scopes.remove_resource(scope_id, resource_id)


@scope_router.delete("/{scope_id}", status_code=status.HTTP_204_NO_CONTENT, responses=errors(404, 409))
async def delete_project_scope(scope_id: UUID, services: ServicesDep) -> None:
    """Delete an extra project scope. Agents using it fall back to their default scope."""
    services.scopes.delete_project_scope(scope_id)
