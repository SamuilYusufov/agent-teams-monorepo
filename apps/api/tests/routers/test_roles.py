from uuid import uuid4

from tests.routers.conftest import check

NOTES = {"name": "n", "type": "text", "storage": "in_place", "content": "x"}


def test_create_role(http):
    resource = check(http.post("/api/resource", json=NOTES), 201)
    body = {
        "name": "dev",
        "description": "d",
        "task_examples": ["t"],
        "source_examples": ["s"],
        "resource_ids": [resource["id"]],
    }
    role = check(http.post("/api/role", json=body), 201)
    assert role["task_examples"] == ["t"]
    assert check(http.get(f"/api/scope/{role['context_scope']}"))["resources"] == [resource["id"]]


def test_create_duplicate_role_is_409(http, role):
    check(http.post("/api/role", json={"name": role["name"], "description": "d"}), 409)


def test_create_role_with_unknown_resource_is_404(http):
    check(http.post("/api/role", json={"name": "dev", "description": "d", "resource_ids": [str(uuid4())]}), 404)


def test_create_role_validates_body(http):
    check(http.post("/api/role", json={"name": "dev"}), 422)


def test_list_and_get_roles(http, role):
    assert check(http.get("/api/role")) == [role]
    assert check(http.get(f"/api/role/{role['id']}")) == role
    check(http.get(f"/api/role/{uuid4()}"), 404)


def test_update_role(http, role):
    body = {"name": "ops", "description": "new", "task_examples": ["a"], "source_examples": []}
    updated = check(http.put(f"/api/role/{role['id']}", json=body))
    assert updated == {**role, **body}
    check(http.put(f"/api/role/{uuid4()}", json=body), 404)


def test_update_role_to_taken_name_is_409(http, role):
    check(http.post("/api/role", json={"name": "ops", "description": "d"}), 201)
    body = {"name": "ops", "description": "d", "task_examples": [], "source_examples": []}
    check(http.put(f"/api/role/{role['id']}", json=body), 409)


def test_delete_role(http, role):
    check(http.delete(f"/api/role/{role['id']}"), 204)
    check(http.get(f"/api/role/{role['id']}"), 404)
    check(http.delete(f"/api/role/{role['id']}"), 404)


def test_delete_role_in_use_is_409(http, role, create_agent):
    create_agent("alice")
    check(http.delete(f"/api/role/{role['id']}"), 409)
