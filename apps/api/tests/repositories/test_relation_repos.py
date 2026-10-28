"""AgentToProject, AgentToRole and ProjectToRole repositories."""
from uuid import uuid4


def test_agent_to_project(repos, seed):
    first, second, role = seed.project("first"), seed.project("second"), seed.role()
    bob = seed.agent(first, role, "bob")
    alice = seed.agent(first, role, "alice")

    assert repos.agent_projects.get_project_id(alice.id) == first.id
    assert repos.agent_projects.get_agent_ids(first.id) == [alice.id, bob.id]

    assert repos.agent_projects.assign(alice.id, second.id) is True
    assert repos.agent_projects.get_project_id(alice.id) == second.id
    assert repos.agent_projects.get_agent_ids(first.id) == [bob.id]


def test_agent_to_project_missing_agent(repos, seed):
    assert repos.agent_projects.assign(uuid4(), seed.project().id) is False
    assert repos.agent_projects.get_project_id(uuid4()) is None


def test_agent_to_role(repos, seed):
    project, dev, ops = seed.project(), seed.role("dev"), seed.role("ops")
    bob = seed.agent(project, dev, "bob")
    alice = seed.agent(project, dev, "alice")

    assert repos.agent_roles.get_role_id(alice.id) == dev.id
    assert repos.agent_roles.get_agent_ids(dev.id) == [alice.id, bob.id]

    assert repos.agent_roles.assign(alice.id, ops.id) is True
    assert repos.agent_roles.get_role_id(alice.id) == ops.id
    assert repos.agent_roles.get_agent_ids(ops.id) == [alice.id]


def test_agent_to_role_missing_agent(repos, seed):
    assert repos.agent_roles.assign(uuid4(), seed.role().id) is False
    assert repos.agent_roles.get_role_id(uuid4()) is None


def test_project_to_role(repos, seed):
    first, second = seed.project("first"), seed.project("second")
    dev, ops = seed.role("dev"), seed.role("ops")

    repos.project_roles.link(first.id, dev.id)
    repos.project_roles.link(first.id, dev.id)  # idempotent
    repos.project_roles.link(first.id, ops.id)
    repos.project_roles.link(second.id, dev.id)

    assert repos.project_roles.is_linked(first.id, dev.id)
    assert set(repos.project_roles.get_role_ids(first.id)) == {dev.id, ops.id}
    assert set(repos.project_roles.get_project_ids(dev.id)) == {first.id, second.id}

    assert repos.project_roles.unlink(first.id, dev.id) is True
    assert repos.project_roles.unlink(first.id, dev.id) is False
    assert not repos.project_roles.is_linked(first.id, dev.id)


def test_project_to_role_cascades(repos, seed):
    project, role = seed.project(), seed.role()
    repos.project_roles.link(project.id, role.id)
    repos.roles.delete(role.id)
    assert repos.project_roles.get_role_ids(project.id) == []
