import sqlite3
from uuid import uuid4

import pytest

from models.context_scope import ContextScope


def test_add_and_get_with_resources(repos, seed):
    a, b = seed.resource("a"), seed.resource("b")
    scope = repos.scopes.add(ContextScope(resources=[a.id, b.id]))
    assert set(repos.scopes.get(scope.id).resources) == {a.id, b.id}


def test_get_missing_returns_none(repos):
    assert repos.scopes.get(uuid4()) is None


def test_add_rejects_unknown_resource(repos):
    with pytest.raises(sqlite3.IntegrityError):
        repos.scopes.add(ContextScope(resources=[uuid4()]))


def test_update_replaces_resources(repos, seed):
    a, b = seed.resource("a"), seed.resource("b")
    scope = seed.scope([a])
    assert repos.scopes.update(ContextScope(id=scope.id, resources=[b.id])) is True
    assert repos.scopes.get(scope.id).resources == [b.id]


def test_update_missing_returns_false(repos):
    assert repos.scopes.update(ContextScope(resources=[])) is False


def test_add_resource_is_idempotent(repos, seed):
    resource = seed.resource()
    scope = seed.scope()
    repos.scopes.add_resource(scope.id, resource.id)
    repos.scopes.add_resource(scope.id, resource.id)
    assert repos.scopes.get(scope.id).resources == [resource.id]


def test_remove_resource(repos, seed):
    resource = seed.resource()
    scope = seed.scope([resource])
    assert repos.scopes.remove_resource(scope.id, resource.id) is True
    assert repos.scopes.remove_resource(scope.id, resource.id) is False
    assert repos.scopes.get(scope.id).resources == []


def test_get_scope_ids(repos, seed):
    resource = seed.resource()
    first, second = seed.scope([resource]), seed.scope([resource])
    seed.scope()
    assert set(repos.scopes.get_scope_ids(resource.id)) == {first.id, second.id}


def test_delete_keeps_resources(repos, seed):
    resource = seed.resource()
    scope = seed.scope([resource])
    assert repos.scopes.delete(scope.id) is True
    assert repos.scopes.get(scope.id) is None
    assert repos.resources.get(resource.id) == resource
    assert repos.scopes.delete(scope.id) is False


def test_delete_fails_while_role_uses_scope(repos, seed):
    role = seed.role()
    with pytest.raises(sqlite3.IntegrityError):
        repos.scopes.delete(role.context_scope)


def test_delete_fails_while_project_main_scope(repos, seed):
    project = seed.project()
    with pytest.raises(sqlite3.IntegrityError):
        repos.scopes.delete(project.main_scope)
