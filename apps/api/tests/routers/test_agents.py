from uuid import uuid4

from tests.routers.conftest import check


def test_create_agent(http, project, create_agent, fake_client):
    agent = create_agent("alice")
    assert agent["name"] == "alice"
    assert agent["project"] == project["id"]
    assert agent["context_scope"] is None
    assert agent["anthropic_id"] in fake_client.agents


def test_create_agent_with_scope(http, project, create_agent):
    agent = create_agent("alice", context_scope=project["main_scope"])
    assert agent["context_scope"] == project["main_scope"]


def test_create_agent_errors(http, role, project, create_agent):
    create_agent("alice")
    check(http.post("/api/agent", json={"name": "alice", "role_id": role["id"], "project_id": project["id"]}), 409)
    check(http.post("/api/agent", json={"name": "bob", "role_id": str(uuid4()), "project_id": project["id"]}), 404)
    check(http.post("/api/agent", json={"name": "bob", "role_id": role["id"], "project_id": str(uuid4())}), 404)


def test_list_and_get_agents(http, role, create_agent):
    alice = create_agent("alice")
    other_body = {"name": "other", "description": "d", "system_prompt": "s", "role_ids": [role["id"]]}
    other = check(http.post("/api/project", json=other_body), 201)
    bob = check(http.post("/api/agent", json={"name": "bob", "role_id": role["id"], "project_id": other["id"]}), 201)

    assert check(http.get("/api/agent")) == [alice, bob]
    assert check(http.get("/api/agent", params={"project_id": other["id"]})) == [bob]
    assert check(http.get(f"/api/agent/{alice['id']}")) == alice
    check(http.get(f"/api/agent/{uuid4()}"), 404)
    check(http.get("/api/agent/not-a-uuid"), 422)


def test_delete_agent(http, create_agent, fake_client):
    agent = create_agent("alice")
    check(http.delete(f"/api/agent/{agent['id']}"), 204)
    check(http.get(f"/api/agent/{agent['id']}"), 404)
    assert fake_client.archived_agents == [agent["anthropic_id"]]
    check(http.delete(f"/api/agent/{agent['id']}"), 404)


def test_set_agent_scope(http, project, role, create_agent):
    agent = create_agent("alice")
    path = f"/api/agent/{agent['id']}/scope"
    pinned = check(http.put(path, json={"context_scope": project["main_scope"]}))
    assert pinned["context_scope"] == project["main_scope"]
    assert check(http.put(path, json={"context_scope": None}))["context_scope"] is None
    check(http.put(path, json={"context_scope": role["context_scope"]}), 409)
    check(http.put(f"/api/agent/{uuid4()}/scope", json={"context_scope": None}), 404)


def test_start_and_stop_agent(http, create_agent, fake_client):
    agent = create_agent("alice")

    session = check(http.post(f"/api/agent/{agent['id']}/start"))
    assert session == {"id": session["id"], "status": "idle", "title": "alice session"}
    assert check(http.post(f"/api/agent/{agent['id']}/start"))["id"] == session["id"]

    check(http.post(f"/api/agent/{agent['id']}/stop"), 204)
    assert fake_client.live_sessions(agent["anthropic_id"]) == []
    check(http.post(f"/api/agent/{uuid4()}/start"), 404)


def test_links(http, create_agent):
    alice = create_agent("alice")
    bob = create_agent("bob")
    path = f"/api/agent/{alice['id']}/links"

    link = check(http.post(path, json={"to_agent": bob["id"], "type": "manager"}), 201)
    assert link == {"id": link["id"], "from_agent": alice["id"], "to_agent": bob["id"], "type": "manager"}
    check(http.post(path, json={"to_agent": bob["id"], "type": "manager"}), 409)
    check(http.post(path, json={"to_agent": bob["id"], "type": "boss"}), 422)

    assert check(http.get(path)) == [link]
    assert check(http.get(f"/api/agent/{bob['id']}/links")) == [link]

    carol = create_agent("carol")
    check(http.delete(f"/api/agent/{carol['id']}/links/{link['id']}"), 404)
    check(http.delete(f"{path}/{link['id']}"), 204)
    assert check(http.get(path)) == []


def test_send_message(http, create_agent, fake_client):
    alice = create_agent("alice")
    bob = create_agent("bob")
    check(http.post(f"/api/agent/{alice['id']}/links", json={"to_agent": bob["id"], "type": "manager"}), 201)
    check(http.post(f"/api/agent/{alice['id']}/start"))

    delivered = {"from_agent": "alice", "to_agent": "bob", "message": "Go.", "type": "manager"}
    assert check(http.post("/api/agent/messages", json=delivered)) == {"delivered": True, "reason": None}

    rejected = {**delivered, "type": "peer"}
    assert check(http.post("/api/agent/messages", json=rejected))["delivered"] is False

    check(http.post("/api/agent/messages", json={**delivered, "to_agent": "nobody"}), 404)
