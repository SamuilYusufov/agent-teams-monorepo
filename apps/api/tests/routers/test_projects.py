from uuid import uuid4

from tests.routers.conftest import check

NOTES = {"name": "n", "type": "text", "storage": "in_place", "content": "x"}


def test_create_project(http, role, project):
    assert project["roles"] == [role["id"]]
    assert project["context_scopes"] == [project["main_scope"]]
    assert check(http.get(f"/api/scope/{project['main_scope']}"))["resources"] == []


def test_create_duplicate_project_is_409(http, project):
    check(http.post("/api/project", json={"name": "proj", "description": "d", "system_prompt": "s"}), 409)


def test_create_project_with_unknown_role_is_404(http):
    body = {"name": "p", "description": "d", "system_prompt": "s", "role_ids": [str(uuid4())]}
    check(http.post("/api/project", json=body), 404)


def test_list_and_get_projects(http, project):
    assert check(http.get("/api/project")) == [project]
    assert check(http.get(f"/api/project/{project['id']}")) == project
    check(http.get(f"/api/project/{uuid4()}"), 404)


def test_update_project(http, project):
    body = {"name": "renamed", "description": "new", "system_prompt": "new prompt", "roles": []}
    updated = check(http.put(f"/api/project/{project['id']}", json=body))
    assert updated == {**project, **body}
    check(http.put(f"/api/project/{uuid4()}", json=body), 404)


def test_add_and_remove_role(http, role, project):
    ops = check(http.post("/api/role", json={"name": "ops", "description": "d"}), 201)
    added = check(http.put(f"/api/project/{project['id']}/roles/{ops['id']}"))
    assert set(added["roles"]) == {role["id"], ops["id"]}
    removed = check(http.delete(f"/api/project/{project['id']}/roles/{role['id']}"))
    assert removed["roles"] == [ops["id"]]
    check(http.put(f"/api/project/{project['id']}/roles/{uuid4()}"), 404)


def test_create_project_scope(http, project):
    resource = check(http.post("/api/resource", json=NOTES), 201)
    path = f"/api/project/{project['id']}/scopes"
    check(http.post(path, json={"resource_ids": [resource["id"]]}), 409)

    check(http.put(f"/api/scope/{project['main_scope']}/resources/{resource['id']}"))
    scope = check(http.post(path, json={"resource_ids": [resource["id"]]}), 201)
    assert scope["resources"] == [resource["id"]]
    assert scope["id"] in check(http.get(f"/api/project/{project['id']}"))["context_scopes"]


def test_delete_project(http, project):
    check(http.delete(f"/api/project/{project['id']}"), 204)
    check(http.get(f"/api/project/{project['id']}"), 404)
    check(http.get(f"/api/scope/{project['main_scope']}"), 404)
    check(http.delete(f"/api/project/{project['id']}"), 404)


def test_delete_project_with_agents_is_409(http, project, create_agent):
    create_agent("alice")
    check(http.delete(f"/api/project/{project['id']}"), 409)


def test_start_and_stop_project(http, project, create_agent, fake_client):
    alice = create_agent("alice")
    bob = create_agent("bob")

    sessions = check(http.post(f"/api/project/{project['id']}/start"))

    assert {s["title"] for s in sessions} == {"alice session", "bob session"}
    assert all(s["status"] == "idle" for s in sessions)
    check(http.post(f"/api/project/{project['id']}/stop"), 204)
    assert fake_client.live_sessions(alice["anthropic_id"]) == []
    assert fake_client.live_sessions(bob["anthropic_id"]) == []


def test_start_unknown_project_is_404(http):
    check(http.post(f"/api/project/{uuid4()}/start"), 404)
    check(http.post(f"/api/project/{uuid4()}/stop"), 404)
