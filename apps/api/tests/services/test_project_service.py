from uuid import uuid4

import pytest

from services.errors import ConflictError, NotFoundError

pytestmark = pytest.mark.anyio


def test_create_project_creates_main_scope(services, role):
    project = services.projects.create_project("p", "d", "s", [role.id])
    assert project.roles == [role.id]
    assert project.team == []
    assert project.context_scopes == [project.main_scope]
    assert services.scopes.get_scope(project.main_scope).resources == []


def test_create_duplicate_project(services, project):
    with pytest.raises(ConflictError):
        services.projects.create_project(project.name, "d", "s")


def test_create_project_with_unknown_role(services, conn):
    with pytest.raises(NotFoundError):
        services.projects.create_project("p", "d", "s", [uuid4()])
    assert conn.execute("SELECT COUNT(*) FROM context_scopes").fetchone()[0] == 0


def test_get_and_list(services, project):
    other = services.projects.create_project("other", "d", "s")
    assert services.projects.get_project(project.id) == project
    assert services.projects.get_project_by_name("other") == other
    assert services.projects.get_project(uuid4()) is None
    assert [p.id for p in services.projects.list_projects()] == [other.id, project.id]


def test_update_project_syncs_roles_and_keeps_scopes(services, project, role):
    secondary = services.scopes.create_project_scope(project.id)
    ops = services.roles.create_role("ops", "d", [], [])
    changed = project.model_copy(
        update={"name": "renamed", "roles": [ops.id], "main_scope": uuid4(), "context_scopes": []}
    )

    updated = services.projects.update_project(changed)

    assert updated.name == "renamed"
    assert updated.roles == [ops.id]
    assert updated.main_scope == project.main_scope
    assert set(updated.context_scopes) == {project.main_scope, secondary.id}


def test_update_unknown_project(services, project):
    with pytest.raises(NotFoundError):
        services.projects.update_project(project.model_copy(update={"id": uuid4()}))


def test_update_project_with_unknown_role(services, project):
    with pytest.raises(NotFoundError):
        services.projects.update_project(project.model_copy(update={"roles": [uuid4()]}))


def test_add_and_remove_role(services, project, role):
    ops = services.roles.create_role("ops", "d", [], [])
    assert set(services.projects.add_role(project.id, ops.id).roles) == {role.id, ops.id}
    assert services.projects.remove_role(project.id, role.id).roles == [ops.id]


def test_add_role_errors(services, project, role):
    with pytest.raises(NotFoundError):
        services.projects.add_role(uuid4(), role.id)
    with pytest.raises(NotFoundError):
        services.projects.add_role(project.id, uuid4())
    with pytest.raises(NotFoundError):
        services.projects.remove_role(uuid4(), role.id)


def test_delete_project_deletes_scopes(services, project):
    secondary = services.scopes.create_project_scope(project.id)
    services.projects.delete_project(project.id)
    assert services.projects.get_project(project.id) is None
    assert services.scopes.get_scope(project.main_scope) is None
    assert services.scopes.get_scope(secondary.id) is None


def test_delete_unknown_project(services):
    with pytest.raises(NotFoundError):
        services.projects.delete_project(uuid4())


async def test_delete_project_with_agents(services, project, create_agent):
    await create_agent("alice")
    with pytest.raises(ConflictError):
        services.projects.delete_project(project.id)


async def test_start_and_stop_whole_team(services, project, create_agent, fake_client):
    alice = await create_agent("alice")
    bob = await create_agent("bob")

    sessions = await services.projects.start(project.id)

    assert {s.agent_id for s in sessions} == {alice.anthropic_id, bob.anthropic_id}
    await services.projects.stop(project.id)
    assert fake_client.live_sessions(alice.anthropic_id) == []
    assert fake_client.live_sessions(bob.anthropic_id) == []


async def test_start_unknown_project(services):
    with pytest.raises(NotFoundError):
        await services.projects.start(uuid4())
    with pytest.raises(NotFoundError):
        await services.projects.stop(uuid4())
