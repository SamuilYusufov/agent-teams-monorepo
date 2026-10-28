"""Endpoints for projects, the roles and scopes inside them, and running their teams."""
from uuid import UUID

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from dependencies import ServicesDep
from models.context_scope import ContextScope
from models.projects import Project
from routers.schemas import SessionInfo, errors
from services.errors import NotFoundError

router = APIRouter(prefix="/api/project", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str = Field(description="Unique project name.")
    description: str
    system_prompt: str = Field(description="Prepended to the system prompt of every agent in the project.")
    role_ids: list[UUID] = Field(default=[], description="Roles available inside the project.")


class ProjectUpdate(BaseModel):
    name: str
    description: str
    system_prompt: str
    roles: list[UUID] = Field(description="Roles available inside the project. Replaces the current list.")


class ProjectScopeCreate(BaseModel):
    resource_ids: list[UUID] = Field(default=[], description="Must all be in the project's main scope.")


# Projects

@router.post("", status_code=status.HTTP_201_CREATED, responses=errors(404, 409))
async def create_project(body: ProjectCreate, services: ServicesDep) -> Project:
    """Create a project together with an empty main scope."""
    return services.projects.create_project(body.name, body.description, body.system_prompt, body.role_ids)


@router.get("")
async def list_projects(services: ServicesDep) -> list[Project]:
    """List all projects, ordered by name."""
    return services.projects.list_projects()


@router.get("/{project_id}", responses=errors(404))
async def get_project(project_id: UUID, services: ServicesDep) -> Project:
    project = services.projects.get_project(project_id)
    if not project:
        raise NotFoundError(f"Project {project_id} not found")
    return project


@router.put("/{project_id}", responses=errors(404, 409))
async def update_project(project_id: UUID, body: ProjectUpdate, services: ServicesDep) -> Project:
    """Update a project and the roles available in it. The team and scopes are managed separately."""
    project = services.projects.get_project(project_id)
    if not project:
        raise NotFoundError(f"Project {project_id} not found")
    return services.projects.update_project(project.model_copy(update=body.model_dump()))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, responses=errors(404, 409))
async def delete_project(project_id: UUID, services: ServicesDep) -> None:
    """Delete a project and its context scopes. Fails with 409 while agents belong to it."""
    services.projects.delete_project(project_id)


# Roles

@router.put("/{project_id}/roles/{role_id}", responses=errors(404))
async def add_role(project_id: UUID, role_id: UUID, services: ServicesDep) -> Project:
    """Make a role available in the project."""
    return services.projects.add_role(project_id, role_id)


@router.delete("/{project_id}/roles/{role_id}", responses=errors(404))
async def remove_role(project_id: UUID, role_id: UUID, services: ServicesDep) -> Project:
    """Remove a role from the project."""
    return services.projects.remove_role(project_id, role_id)


# Scopes

@router.post("/{project_id}/scopes", status_code=status.HTTP_201_CREATED, responses=errors(404, 409))
async def create_project_scope(project_id: UUID, body: ProjectScopeCreate, services: ServicesDep) -> ContextScope:
    """Create an extra context scope in the project, e.g. to pin agents to a subset of its resources."""
    return services.scopes.create_project_scope(project_id, body.resource_ids)


# Sessions

@router.post("/{project_id}/start", responses=errors(404))
async def start_project(project_id: UUID, services: ServicesDep) -> list[SessionInfo]:
    """Start a session for every agent in the project team. Agents that are already running keep their session."""
    return [SessionInfo.from_session(session) for session in await services.projects.start(project_id)]


@router.post("/{project_id}/stop", status_code=status.HTTP_204_NO_CONTENT, responses=errors(404))
async def stop_project(project_id: UUID, services: ServicesDep) -> None:
    """Archive the live sessions of every agent in the project team."""
    await services.projects.stop(project_id)
