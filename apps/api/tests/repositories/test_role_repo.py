import sqlite3
from uuid import uuid4

import pytest

from models.roles import AgentRole


def test_add_and_get_round_trip(repos, seed):
    role = seed.role("dev")
    assert repos.roles.get(role.id) == role


def test_get_missing_returns_none(repos):
    assert repos.roles.get(uuid4()) is None


def test_get_by_name(repos, seed):
    role = seed.role("dev")
    assert repos.roles.get_by_name("dev") == role
    assert repos.roles.get_by_name("nobody") is None


def test_list_orders_by_name(repos, seed):
    b, a = seed.role("b"), seed.role("a")
    assert repos.roles.list() == [a, b]


def test_names_are_unique(seed):
    seed.role("dev")
    with pytest.raises(sqlite3.IntegrityError):
        seed.role("dev")


def test_requires_existing_scope(repos):
    role = AgentRole(name="dev", description="d", task_examples=[], source_examples=[], context_scope=uuid4())
    with pytest.raises(sqlite3.IntegrityError):
        repos.roles.add(role)


def test_update(repos, seed):
    role = seed.role("dev")
    other_scope = seed.scope()
    changed = role.model_copy(
        update={"name": "ops", "task_examples": ["a", "b"], "source_examples": [], "context_scope": other_scope.id}
    )
    assert repos.roles.update(changed) is True
    assert repos.roles.get(role.id) == changed


def test_update_missing_returns_false(repos, seed):
    role = AgentRole(
        name="ghost", description="d", task_examples=[], source_examples=[], context_scope=seed.scope().id
    )
    assert repos.roles.update(role) is False


def test_delete(repos, seed):
    role = seed.role()
    assert repos.roles.delete(role.id) is True
    assert repos.roles.get(role.id) is None
    assert repos.roles.delete(role.id) is False


def test_delete_fails_while_agents_have_role(repos, seed):
    role = seed.role()
    seed.agent(seed.project(), role)
    with pytest.raises(sqlite3.IntegrityError):
        repos.roles.delete(role.id)
