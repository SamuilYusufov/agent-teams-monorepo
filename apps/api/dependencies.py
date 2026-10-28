"""Wiring of repositories and services, exposed to the routers as a FastAPI dependency."""
import os
import sqlite3
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

from anthropic import AsyncAnthropic
from fastapi import Depends

from repositories.agent_link_repo import SQLiteAgentLinkRepository
from repositories.agent_repo import SQLiteAgentRepository
from repositories.agent_to_project_repo import SQLiteAgentToProjectRepository
from repositories.agent_to_role_repo import SQLiteAgentToRoleRepository
from repositories.project_repo import SQLiteProjectRepository
from repositories.project_to_role_repo import SQLiteProjectToRoleRepository
from repositories.resource_repo import SQLiteResourceRepository
from repositories.role_repo import SQLiteRoleRepository
from repositories.scope_repo import SQLiteScopeRepository
from repositories.sqlite_base import connect
from services.agent_service import AgentService
from services.mcp_access import McpAccess
from services.project_service import ProjectService
from services.role_service import RoleService
from services.scope_service import ScopeService


@dataclass(frozen=True)
class Services:
    """All services, sharing one database connection."""

    agents: AgentService
    projects: ProjectService
    roles: RoleService
    scopes: ScopeService
    mcp_access: McpAccess | None = None


def build_services(
        conn: sqlite3.Connection,
        environment_id: str,
        client: AsyncAnthropic | None = None,
        mcp_access: McpAccess | None = None,
) -> Services:
    """Wire the SQLite repositories into the services. `client` defaults to a new AsyncAnthropic.

    Without `mcp_access`, agents are created without access to the team MCP server.
    """
    agents = SQLiteAgentRepository(conn)
    projects = SQLiteProjectRepository(conn)
    roles = SQLiteRoleRepository(conn)
    resources = SQLiteResourceRepository(conn)
    scopes = SQLiteScopeRepository(conn)

    scope_service = ScopeService(resources, scopes, projects, roles, agents)
    agent_service = AgentService(
        agents,
        SQLiteAgentToProjectRepository(conn),
        roles,
        SQLiteAgentLinkRepository(conn),
        scope_service,
        environment_id,
        client,
        mcp_access,
    )
    return Services(
        agents=agent_service,
        projects=ProjectService(projects, SQLiteProjectToRoleRepository(conn), roles, scopes, agent_service),
        roles=RoleService(roles, SQLiteAgentToRoleRepository(conn), scopes, resources),
        scopes=scope_service,
        mcp_access=mcp_access,
    )


@lru_cache
def get_services() -> Services:
    """Build the services once per process.

    Configured with:
    - ANTHROPIC_ENVIRONMENT_ID (required): the environment agent sessions run in;
    - AGENTS_DB_PATH: the SQLite database, `agents.db` by default;
    - MCP_PUBLIC_URL and MCP_SECRET: the public URL of the `/mcp/` endpoint and the key used to sign the agents'
      MCP URLs. Without them, agents are created without access to the team MCP server.
    """
    environment_id = os.environ.get("ANTHROPIC_ENVIRONMENT_ID")
    if not environment_id:
        raise RuntimeError("Set ANTHROPIC_ENVIRONMENT_ID to the environment agent sessions should run in")
    mcp_access = None
    if public_url := os.environ.get("MCP_PUBLIC_URL"):
        secret = os.environ.get("MCP_SECRET")
        if not secret:
            raise RuntimeError("Set MCP_SECRET to sign the agents' MCP URLs")
        mcp_access = McpAccess(public_url, secret)
    return build_services(connect(os.environ.get("AGENTS_DB_PATH", "agents.db")), environment_id, mcp_access=mcp_access)


ServicesDep = Annotated[Services, Depends(get_services)]
