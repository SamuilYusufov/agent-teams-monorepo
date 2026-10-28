from uuid import uuid4

import pytest

from tests.routers.conftest import check


@pytest.fixture
def notes(http):
    body = {"name": "notes", "type": "text", "storage": "in_place", "content": "hello"}
    return check(http.post("/api/resource", json=body), 201)


def test_create_resource(http, notes):
    assert notes["content"] == "hello"
    assert notes["anthropic_file_id"] is None


def test_create_resource_validation(http):
    check(http.post("/api/resource", json={"name": "x", "type": "text", "storage": "in_place"}), 409)
    check(http.post("/api/resource", json={"name": "x", "type": "video", "storage": "in_place", "content": "x"}), 422)


def test_list_get_and_delete_resources(http, notes):
    assert check(http.get("/api/resource")) == [notes]
    assert check(http.get(f"/api/resource/{notes['id']}")) == notes
    check(http.delete(f"/api/resource/{notes['id']}"), 204)
    check(http.get(f"/api/resource/{notes['id']}"), 404)
    check(http.delete(f"/api/resource/{notes['id']}"), 404)


def test_scope_resources(http, project, notes):
    scope_path = f"/api/scope/{project['main_scope']}"

    assert check(http.put(f"{scope_path}/resources/{notes['id']}"))["resources"] == [notes["id"]]
    assert check(http.get(f"{scope_path}/resources")) == [notes]

    assert check(http.delete(f"{scope_path}/resources/{notes['id']}"))["resources"] == []
    check(http.get(f"/api/scope/{uuid4()}"), 404)
    check(http.get(f"/api/scope/{uuid4()}/resources"), 404)
    check(http.put(f"{scope_path}/resources/{uuid4()}"), 404)


def test_secondary_scope_only_takes_main_scope_resources(http, project, notes):
    scope = check(http.post(f"/api/project/{project['id']}/scopes", json={}), 201)
    check(http.put(f"/api/scope/{scope['id']}/resources/{notes['id']}"), 409)


def test_delete_scope(http, project):
    scope = check(http.post(f"/api/project/{project['id']}/scopes", json={}), 201)
    check(http.delete(f"/api/scope/{project['main_scope']}"), 409)
    check(http.delete(f"/api/scope/{scope['id']}"), 204)
    check(http.get(f"/api/scope/{scope['id']}"), 404)
    check(http.delete(f"/api/scope/{scope['id']}"), 404)
