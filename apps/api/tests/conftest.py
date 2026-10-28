from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api import create_app
from dependencies import Services, build_services
from models.agents import AgentWorker
from models.context_scope import ContextScope, Resource
from models.projects import ProjectRow
from models.roles import AgentRole
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
from tests.fakes import FakeAnthropic

ENVIRONMENT_ID = "env_test"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def conn():
    conn = connect()
    yield conn
    conn.close()


@pytest.fixture
def repos(conn):
    return SimpleNamespace(
        agents=SQLiteAgentRepository(conn),
        agent_projects=SQLiteAgentToProjectRepository(conn),
        agent_roles=SQLiteAgentToRoleRepository(conn),
        links=SQLiteAgentLinkRepository(conn),
        projects=SQLiteProjectRepository(conn),
        project_roles=SQLiteProjectToRoleRepository(conn),
        resources=SQLiteResourceRepository(conn),
        roles=SQLiteRoleRepository(conn),
        scopes=SQLiteScopeRepository(conn),
    )


class Seed:
    """Insert rows straight through the repositories, bypassing service rules."""

    def __init__(self, repos):
        self._repos = repos

    def resource(self, name="notes", **kwargs) -> Resource:
        kwargs.setdefault("type", "text")
        kwargs.setdefault("storage", "in_place")
        kwargs.setdefault("content", f"{name} content")
        return self._repos.resources.add(Resource(name=name, **kwargs))

    def scope(self, resources=()) -> ContextScope:
        return self._repos.scopes.add(ContextScope(resources=[r.id for r in resources]))

    def role(self, name="dev", scope: ContextScope | None = None) -> AgentRole:
        scope = scope or self.scope()
        return self._repos.roles.add(
            AgentRole(
                name=name,
                description=f"{name} role",
                task_examples=["task"],
                source_examples=["source"],
                context_scope=scope.id,
            )
        )

    def project(self, name="proj", main_scope: ContextScope | None = None) -> ProjectRow:
        main_scope = main_scope or self.scope()
        return self._repos.projects.add(
            ProjectRow(
                name=name,
                description=f"{name} description",
                system_prompt=f"{name} prompt",
                team=[],
                main_scope=main_scope.id,
                context_scopes=[main_scope.id],
            )
        )

    def agent(self, project, role, name="alice", context_scope=None) -> AgentWorker:
        return self._repos.agents.add(
            AgentWorker(
                anthropic_id=f"agent_{name}",
                name=name,
                project=project.id,
                role=role.id,
                context_scope=context_scope,
            )
        )


@pytest.fixture
def seed(repos):
    return Seed(repos)


@pytest.fixture
def fake_client():
    return FakeAnthropic()


@pytest.fixture
def services(conn, fake_client) -> Services:
    return build_services(conn, ENVIRONMENT_ID, fake_client)


@pytest.fixture
def http(services):
    """API client backed by the in-memory `services`."""
    with TestClient(create_app(lambda: services)) as client:
        yield client
