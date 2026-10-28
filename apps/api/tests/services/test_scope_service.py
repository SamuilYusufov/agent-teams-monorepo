from uuid import uuid4

import pytest

from services.errors import ConflictError, NotFoundError

pytestmark = pytest.mark.anyio


# Resources

def test_create_in_place_resource(services):
    resource = services.scopes.create_resource("notes", "text", "in_place", content="hello")
    assert services.scopes.get_resource(resource.id) == resource


def test_create_anthropic_managed_resource(services):
    resource = services.scopes.create_resource("spec", "file", "anthropic_managed", anthropic_file_id="file_1")
    assert services.scopes.get_resource(resource.id).anthropic_file_id == "file_1"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"type": "text", "storage": "in_place"},
        {"type": "url", "storage": "anthropic_managed", "anthropic_file_id": "file_1"},
        {"type": "file", "storage": "anthropic_managed"},
    ],
    ids=["in-place-without-content", "managed-non-file", "managed-without-file-id"],
)
def test_create_resource_validation(services, kwargs):
    with pytest.raises(ConflictError):
        services.scopes.create_resource("bad", **kwargs)
    assert services.scopes.list_resources() == []


def test_delete_resource(services):
    resource = services.scopes.create_resource("notes", "text", "in_place", content="x")
    services.scopes.delete_resource(resource.id)
    assert services.scopes.get_resource(resource.id) is None
    with pytest.raises(NotFoundError):
        services.scopes.delete_resource(resource.id)


# Scopes

@pytest.fixture
def notes(services):
    return services.scopes.create_resource("notes", "text", "in_place", content="notes")


@pytest.fixture
def spec(services):
    return services.scopes.create_resource("spec", "file", "anthropic_managed", anthropic_file_id="file_1")


def test_create_scope(services, notes):
    scope = services.scopes.create_scope([notes.id])
    assert services.scopes.get_scope(scope.id).resources == [notes.id]
    assert services.scopes.get_scope_resources(scope.id) == [notes]


def test_create_scope_with_unknown_resource(services):
    with pytest.raises(NotFoundError):
        services.scopes.create_scope([uuid4()])


def test_get_scope_resources_unknown_scope(services):
    with pytest.raises(NotFoundError):
        services.scopes.get_scope_resources(uuid4())


def test_add_resource_to_main_scope(services, project, notes):
    scope = services.scopes.add_resource(project.main_scope, notes.id)
    assert scope.resources == [notes.id]


def test_add_unknown_resource_or_scope(services, project, notes):
    with pytest.raises(NotFoundError):
        services.scopes.add_resource(project.main_scope, uuid4())
    with pytest.raises(NotFoundError):
        services.scopes.add_resource(uuid4(), notes.id)


def test_add_resource_to_role_scope_is_unrestricted(services, role, notes):
    assert services.scopes.add_resource(role.context_scope, notes.id).resources == [notes.id]


def test_secondary_scope_only_takes_main_scope_resources(services, project, notes, spec):
    services.scopes.add_resource(project.main_scope, notes.id)
    secondary = services.scopes.create_project_scope(project.id)
    services.scopes.add_resource(secondary.id, notes.id)
    with pytest.raises(ConflictError):
        services.scopes.add_resource(secondary.id, spec.id)


def test_create_project_scope(services, project, notes):
    services.scopes.add_resource(project.main_scope, notes.id)
    scope = services.scopes.create_project_scope(project.id, [notes.id])
    assert scope.resources == [notes.id]
    assert set(services.projects.get_project(project.id).context_scopes) == {project.main_scope, scope.id}


def test_create_project_scope_rejects_resources_outside_main_scope(services, project, notes):
    with pytest.raises(ConflictError):
        services.scopes.create_project_scope(project.id, [notes.id])
    assert services.projects.get_project(project.id).context_scopes == [project.main_scope]


def test_create_project_scope_unknown_project(services):
    with pytest.raises(NotFoundError):
        services.scopes.create_project_scope(uuid4())


def test_removing_from_main_scope_removes_from_secondary_scopes(services, project, notes, spec):
    for resource in (notes, spec):
        services.scopes.add_resource(project.main_scope, resource.id)
    secondary = services.scopes.create_project_scope(project.id, [notes.id, spec.id])

    services.scopes.remove_resource(project.main_scope, notes.id)

    assert services.scopes.get_scope(project.main_scope).resources == [spec.id]
    assert services.scopes.get_scope(secondary.id).resources == [spec.id]


def test_removing_from_secondary_scope_keeps_main_scope(services, project, notes):
    services.scopes.add_resource(project.main_scope, notes.id)
    secondary = services.scopes.create_project_scope(project.id, [notes.id])
    services.scopes.remove_resource(secondary.id, notes.id)
    assert services.scopes.get_scope(secondary.id).resources == []
    assert services.scopes.get_scope(project.main_scope).resources == [notes.id]


def test_remove_resource_unknown_scope(services, notes):
    with pytest.raises(NotFoundError):
        services.scopes.remove_resource(uuid4(), notes.id)


async def test_delete_project_scope_resets_agents(services, project, create_agent):
    secondary = services.scopes.create_project_scope(project.id)
    agent = await create_agent("alice", context_scope=secondary.id)

    services.scopes.delete_project_scope(secondary.id)

    assert services.scopes.get_scope(secondary.id) is None
    assert services.agents.get_agent(agent.id).context_scope is None
    assert services.projects.get_project(project.id).context_scopes == [project.main_scope]


def test_delete_main_scope_is_rejected(services, project):
    with pytest.raises(ConflictError):
        services.scopes.delete_project_scope(project.main_scope)


def test_delete_non_project_scope_is_rejected(services, role):
    with pytest.raises(NotFoundError):
        services.scopes.delete_project_scope(role.context_scope)


# Agents

async def test_set_agent_scope(services, project, create_agent):
    agent = await create_agent("alice")
    secondary = services.scopes.create_project_scope(project.id)

    assert services.scopes.set_agent_scope(agent.id, secondary.id).context_scope == secondary.id
    assert services.agents.get_agent(agent.id).context_scope == secondary.id

    assert services.scopes.set_agent_scope(agent.id, None).context_scope is None
    assert services.agents.get_agent(agent.id).context_scope is None


async def test_set_agent_scope_rejects_foreign_scope(services, role, create_agent):
    agent = await create_agent("alice")
    other_project = services.projects.create_project("other", "d", "s", [role.id])
    for scope_id in (other_project.main_scope, role.context_scope):
        with pytest.raises(ConflictError):
            services.scopes.set_agent_scope(agent.id, scope_id)


def test_set_agent_scope_unknown_agent(services, project):
    with pytest.raises(NotFoundError):
        services.scopes.set_agent_scope(uuid4(), project.main_scope)


async def test_default_agent_resources_are_project_and_role_intersection(
        services, project, role, create_agent, notes, spec
):
    project_only = services.scopes.create_resource("project-only", "text", "in_place", content="p")
    role_only = services.scopes.create_resource("role-only", "text", "in_place", content="r")
    for resource in (notes, spec, project_only):
        services.scopes.add_resource(project.main_scope, resource.id)
    for resource in (notes, spec, role_only):
        services.scopes.add_resource(role.context_scope, resource.id)
    agent = await create_agent("alice")

    assert services.scopes.resolve_agent_resources(agent) == [notes, spec]


async def test_pinned_agent_resources_come_from_its_scope(services, project, role, create_agent, notes, spec):
    for resource in (notes, spec):
        services.scopes.add_resource(project.main_scope, resource.id)
    services.scopes.add_resource(role.context_scope, spec.id)
    secondary = services.scopes.create_project_scope(project.id, [notes.id])
    agent = await create_agent("alice", context_scope=secondary.id)

    assert services.scopes.resolve_agent_resources(agent) == [notes]
