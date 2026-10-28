import sqlite3
from uuid import uuid4

import pytest

from models.agents import AgentWorker


@pytest.fixture
def project(seed):
    return seed.project()


@pytest.fixture
def role(seed):
    return seed.role()


def test_add_and_get_without_scope(repos, seed, project, role):
    agent = seed.agent(project, role)
    assert repos.agents.get(agent.id) == agent
    assert repos.agents.get(agent.id).context_scope is None


def test_add_and_get_with_scope(repos, seed, project, role):
    agent = seed.agent(project, role, context_scope=project.main_scope)
    assert repos.agents.get(agent.id).context_scope == project.main_scope


def test_get_missing_returns_none(repos):
    assert repos.agents.get(uuid4()) is None


def test_get_by_name(repos, seed, project, role):
    agent = seed.agent(project, role, "alice")
    assert repos.agents.get_by_name("alice") == agent
    assert repos.agents.get_by_name("bob") is None


def test_list_orders_by_name(repos, seed, project, role):
    bob = seed.agent(project, role, "bob")
    alice = seed.agent(project, role, "alice")
    assert repos.agents.list() == [alice, bob]


def test_requires_existing_project_and_role(repos, project, role):
    for project_id, role_id in [(uuid4(), role.id), (project.id, uuid4())]:
        agent = AgentWorker(
            anthropic_id=str(uuid4()), name=str(uuid4()), project=project_id, role=role_id, context_scope=None
        )
        with pytest.raises(sqlite3.IntegrityError):
            repos.agents.add(agent)


def test_names_and_anthropic_ids_are_unique(seed, repos, project, role):
    agent = seed.agent(project, role, "alice")
    for duplicate in (
        agent.model_copy(update={"id": uuid4(), "anthropic_id": "other"}),
        agent.model_copy(update={"id": uuid4(), "name": "other"}),
    ):
        with pytest.raises(sqlite3.IntegrityError):
            repos.agents.add(duplicate)


def test_update(repos, seed, project, role):
    agent = seed.agent(project, role)
    changed = agent.model_copy(update={"name": "renamed", "context_scope": project.main_scope})
    assert repos.agents.update(changed) is True
    assert repos.agents.get(agent.id) == changed


def test_update_can_clear_scope(repos, seed, project, role):
    agent = seed.agent(project, role, context_scope=project.main_scope)
    repos.agents.update(agent.model_copy(update={"context_scope": None}))
    assert repos.agents.get(agent.id).context_scope is None


def test_update_missing_returns_false(repos, project, role):
    agent = AgentWorker(anthropic_id="x", name="ghost", project=project.id, role=role.id, context_scope=None)
    assert repos.agents.update(agent) is False


def test_delete(repos, seed, project, role):
    agent = seed.agent(project, role)
    assert repos.agents.delete(agent.id) is True
    assert repos.agents.get(agent.id) is None
    assert repos.agents.delete(agent.id) is False


def test_deleting_scope_resets_agent_scope(repos, seed, project, role):
    extra = seed.scope()
    repos.projects.update(project.model_copy(update={"context_scopes": [project.main_scope, extra.id]}))
    agent = seed.agent(project, role, context_scope=extra.id)
    repos.scopes.delete(extra.id)
    assert repos.agents.get(agent.id).context_scope is None
