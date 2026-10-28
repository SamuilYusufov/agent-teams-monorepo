import sqlite3
from uuid import uuid4

import pytest

from models.context_scope import Resource


def test_add_and_get_round_trip(repos):
    resource = Resource(name="spec", type="file", storage="anthropic_managed", anthropic_file_id="file_1")
    repos.resources.add(resource)
    assert repos.resources.get(resource.id) == resource


def test_get_missing_returns_none(repos):
    assert repos.resources.get(uuid4()) is None


def test_get_many_ignores_missing_and_orders_by_name(repos, seed):
    b = seed.resource("b")
    a = seed.resource("a")
    assert repos.resources.get_many([b.id, uuid4(), a.id]) == [a, b]


def test_get_many_empty(repos):
    assert repos.resources.get_many([]) == []


def test_list_orders_by_name(repos, seed):
    b = seed.resource("b")
    a = seed.resource("a")
    assert repos.resources.list() == [a, b]


def test_update(repos, seed):
    resource = seed.resource("notes")
    changed = resource.model_copy(update={"name": "renamed", "content": "new"})
    assert repos.resources.update(changed) is True
    assert repos.resources.get(resource.id) == changed


def test_update_missing_returns_false(repos):
    assert repos.resources.update(Resource(name="x", type="text", storage="in_place", content="x")) is False


def test_delete_removes_resource_from_scopes(repos, seed):
    resource = seed.resource()
    scope = seed.scope([resource])
    assert repos.resources.delete(resource.id) is True
    assert repos.resources.get(resource.id) is None
    assert repos.scopes.get(scope.id).resources == []


def test_delete_missing_returns_false(repos):
    assert repos.resources.delete(uuid4()) is False


def test_schema_rejects_unknown_type(repos):
    invalid = Resource.model_construct(
        id=uuid4(), name="x", type="video", storage="in_place", content="x", anthropic_file_id=None
    )
    with pytest.raises(sqlite3.IntegrityError):
        repos.resources.add(invalid)
