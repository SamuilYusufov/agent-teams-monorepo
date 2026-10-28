from uuid import uuid4

import pytest

from services.errors import ConflictError, NotFoundError

pytestmark = pytest.mark.anyio


def count_scopes(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM context_scopes").fetchone()[0]


def test_create_role_creates_its_scope(services):
    notes = services.scopes.create_resource("notes", "text", "in_place", content="x")
    role = services.roles.create_role("dev", "d", ["task"], ["source"], [notes.id])
    assert services.roles.get_role(role.id) == role
    assert services.scopes.get_scope(role.context_scope).resources == [notes.id]


def test_create_role_without_resources(services):
    role = services.roles.create_role("dev", "d", [], [])
    assert services.scopes.get_scope(role.context_scope).resources == []


def test_create_duplicate_role(services, conn):
    services.roles.create_role("dev", "d", [], [])
    with pytest.raises(ConflictError):
        services.roles.create_role("dev", "d", [], [])
    assert count_scopes(conn) == 1


def test_create_role_with_unknown_resource_leaves_no_scope(services, conn):
    with pytest.raises(NotFoundError):
        services.roles.create_role("dev", "d", [], [], [uuid4()])
    assert count_scopes(conn) == 0


def test_get_and_list(services):
    dev = services.roles.create_role("dev", "d", [], [])
    ops = services.roles.create_role("ops", "d", [], [])
    assert services.roles.get_role_by_name("ops") == ops
    assert services.roles.list_roles() == [dev, ops]


def test_update_role_keeps_scope(services, role):
    changed = role.model_copy(update={"description": "new", "context_scope": uuid4()})
    updated = services.roles.update_role(changed)
    assert updated.description == "new"
    assert updated.context_scope == role.context_scope
    assert services.roles.get_role(role.id) == updated


def test_update_unknown_role(services, role):
    with pytest.raises(NotFoundError):
        services.roles.update_role(role.model_copy(update={"id": uuid4()}))


def test_delete_role_deletes_scope(services, role):
    services.roles.delete_role(role.id)
    assert services.roles.get_role(role.id) is None
    assert services.scopes.get_scope(role.context_scope) is None


def test_delete_unknown_role(services):
    with pytest.raises(NotFoundError):
        services.roles.delete_role(uuid4())


async def test_delete_role_in_use(services, role, create_agent):
    await create_agent("alice")
    with pytest.raises(ConflictError):
        services.roles.delete_role(role.id)
