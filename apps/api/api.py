"""The FastAPI application, serving the REST API and the team MCP server. Run with `uvicorn api:app`."""
import sqlite3
from collections.abc import Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from dependencies import Services, get_services
from routers import agents, projects, roles, scopes
from services.errors import ConflictError, NotFoundError
from team_mcp import create_team_mcp

DESCRIPTION = """
Manage teams of Claude agents working on shared projects.

A **project** has a team of **agents**. Each agent has one **role**, which describes its job.
**Resources** (texts, urls, uploaded files) are grouped into **context scopes**: every project and role has one,
and an agent gets the resources in both unless it is pinned to another scope of its project.
Agents message each other along **links**.

Agents work with their team through the MCP server at `/mcp/`.
"""

TAGS = [
    {"name": "projects", "description": "Projects, the roles available in them, and starting their whole team."},
    {"name": "roles", "description": "Reusable job descriptions for agents, shared between projects."},
    {"name": "agents", "description": "Agents, their sessions, the links between them, and messaging."},
    {"name": "resources", "description": "Texts, urls and uploaded files agents can use."},
    {"name": "scopes", "description": "Context scopes: the sets of resources given to agents."},
]


def create_app(services: Callable[[], Services] = get_services) -> FastAPI:
    """Create the app with all routers, the team MCP server at `/mcp/`, and the domain error handlers.

    `services` provides the services to both the routers and the MCP server; tests pass their own.
    """
    mcp_app = create_team_mcp(services).http_app(path="/")
    app = FastAPI(
        title="Agent project team",
        version="0.1.0",
        description=DESCRIPTION,
        openapi_tags=TAGS,
        lifespan=mcp_app.lifespan,
    )
    if services is not get_services:
        app.dependency_overrides[get_services] = services
    for router in (projects.router, roles.router, agents.router, scopes.resource_router, scopes.scope_router):
        app.include_router(router)
    app.mount("/mcp", mcp_app)

    @app.exception_handler(NotFoundError)
    async def not_found(_request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def conflict(_request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})

    @app.exception_handler(sqlite3.IntegrityError)
    async def integrity_error(_request: Request, exc: sqlite3.IntegrityError) -> JSONResponse:
        """Unique and foreign-key violations not caught by the services, e.g. renaming to a taken name."""
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})

    return app


app = create_app()
