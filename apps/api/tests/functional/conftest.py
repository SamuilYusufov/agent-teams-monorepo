"""Step definitions for the Gherkin features in `features/`.

Scenarios drive the HTTP API, backed by an in-memory database and a fake Managed Agents client.
Entities are referred to by name in the features; `World` maps the names to what the API returned.
"""
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from pytest_bdd import given, parsers, then, when

from tests.fakes import FakeAnthropic


class World:
    """State shared between the steps of one scenario."""

    def __init__(self, http: TestClient, fake_client: FakeAnthropic):
        self.http = http
        self.fake = fake_client
        self.response: Response | None = None
        self.projects: dict[str, dict[str, Any]] = {}
        self.roles: dict[str, dict[str, Any]] = {}
        self.agents: dict[str, dict[str, Any]] = {}
        self.resources: dict[str, dict[str, Any]] = {}
        self.scopes: dict[str, dict[str, Any]] = {}

    def request(self, method: str, path: str, json: dict[str, Any] | None = None) -> Response:
        """Send a request and remember the response for the `Then` steps."""
        self.response = self.http.request(method, path, json=json)
        return self.response

    def ok(self, method: str, path: str, json: dict[str, Any] | None = None) -> Any:
        """Send a request that must succeed, and return its body."""
        response = self.request(method, path, json)
        assert response.is_success, f"{method} {path} -> {response.status_code}: {response.text}"
        return response.json() if response.content else None

    def project(self, name: str) -> dict[str, Any]:
        """The project as currently stored."""
        return self.ok("GET", f"/api/project/{self.projects[name]['id']}")

    def role_id(self, name: str) -> str:
        """The role's ID, or a random one for roles that were never created."""
        return self.roles[name]["id"] if name in self.roles else "00000000-0000-0000-0000-000000000000"

    def resource_ids(self, datatable: list[list[str]]) -> list[str]:
        return [self.resources[row[0]]["id"] for row in datatable]

    def live_session(self, agent: str):
        sessions = self.fake.live_sessions(self.agents[agent]["anthropic_id"])
        assert len(sessions) == 1, f"{agent} has {len(sessions)} live sessions"
        return sessions[0]

    def texts_received(self, agent: str) -> list[str]:
        anthropic_id = self.agents[agent]["anthropic_id"]
        sessions = [s for s in self.fake.sessions.values() if s.agent_id == anthropic_id]
        return [text for session in sessions for text in self.fake.texts_sent_to(session.id)]


@pytest.fixture
def world(http, fake_client) -> World:
    return World(http, fake_client)


# Roles

@given(parsers.parse('a role "{role}"'))
def given_role(world: World, role: str):
    world.roles[role] = world.ok("POST", "/api/role", {"name": role, "description": f"A {role}."})


@when(parsers.parse('I create the role "{role}" with the resource "{resource}"'))
def create_role_with_resource(world: World, role: str, resource: str):
    body = {"name": role, "description": f"A {role}.", "resource_ids": [world.resources[resource]["id"]]}
    if world.request("POST", "/api/role", body).is_success:
        world.roles[role] = world.response.json()


@when(parsers.parse('I create the role "{role}" with no resources'))
def create_role(world: World, role: str):
    world.request("POST", "/api/role", {"name": role, "description": f"A {role}."})


@when(parsers.parse('I delete the role "{role}"'))
def delete_role(world: World, role: str):
    world.request("DELETE", f"/api/role/{world.roles[role]['id']}")


@then(parsers.parse('the role "{role}" no longer exists'))
def role_is_gone(world: World, role: str):
    assert world.http.get(f"/api/role/{world.roles[role]['id']}").status_code == 404


# Projects

@given(parsers.parse('a project "{project}" with the role "{role}"'))
def given_project(world: World, project: str, role: str):
    body = {"name": project, "description": f"Project {project}.", "system_prompt": "Work together.",
            "role_ids": [world.role_id(role)]}
    world.projects[project] = world.ok("POST", "/api/project", body)


@when(parsers.parse('I create the project "{project}" with the role "{role}"'))
def create_project(world: World, project: str, role: str):
    body = {"name": project, "description": f"Project {project}.", "system_prompt": "Work together.",
            "role_ids": [world.role_id(role)]}
    if world.request("POST", "/api/project", body).is_success:
        world.projects[project] = world.response.json()


@when(parsers.parse('I delete the project "{project}"'))
def delete_project(world: World, project: str):
    world.request("DELETE", f"/api/project/{world.projects[project]['id']}")


@when(parsers.parse('I start the project "{project}"'))
def start_project(world: World, project: str):
    world.ok("POST", f"/api/project/{world.projects[project]['id']}/start")


@when(parsers.parse('I stop the project "{project}"'))
def stop_project(world: World, project: str):
    world.ok("POST", f"/api/project/{world.projects[project]['id']}/stop")


@then(parsers.parse('the project "{project}" offers the role "{role}"'))
def project_offers_role(world: World, project: str, role: str):
    assert world.project(project)["roles"] == [world.roles[role]["id"]]


@then(parsers.parse('the project "{project}" no longer exists'))
def project_is_gone(world: World, project: str):
    assert world.http.get(f"/api/project/{world.projects[project]['id']}").status_code == 404


@then(parsers.parse('the team of the project "{project}" is:'))
def team_is(world: World, project: str, datatable: list[list[str]]):
    assert world.project(project)["team"] == [world.agents[row[0]]["id"] for row in datatable]


@then(parsers.parse('the team of the project "{project}" is empty'))
def team_is_empty(world: World, project: str):
    assert world.project(project)["team"] == []


# Agents

@given(parsers.parse('an agent "{agent}" with the role "{role}" in the project "{project}"'))
def given_agent(world: World, agent: str, role: str, project: str):
    body = {"name": agent, "role_id": world.role_id(role), "project_id": world.projects[project]["id"]}
    world.agents[agent] = world.ok("POST", "/api/agent", body)


@when(parsers.parse('I create an agent "{agent}" with the role "{role}" in the project "{project}"'))
def create_agent(world: World, agent: str, role: str, project: str):
    body = {"name": agent, "role_id": world.role_id(role), "project_id": world.projects[project]["id"]}
    if world.request("POST", "/api/agent", body).is_success:
        world.agents[agent] = world.response.json()


@when(parsers.parse('I delete the agent "{agent}"'))
def delete_agent(world: World, agent: str):
    world.request("DELETE", f"/api/agent/{world.agents[agent]['id']}")


@given(parsers.parse('the agent "{agent}" is running'))
@when(parsers.parse('I start the agent "{agent}"'))
def start_agent(world: World, agent: str):
    world.ok("POST", f"/api/agent/{world.agents[agent]['id']}/start")


@when(parsers.parse('I stop the agent "{agent}"'))
def stop_agent(world: World, agent: str):
    world.request("POST", f"/api/agent/{world.agents[agent]['id']}/stop")


@then(parsers.parse('the agent "{agent}" is running'))
def agent_is_running(world: World, agent: str):
    world.live_session(agent)


@then(parsers.parse('the agent "{agent}" has exactly one live session'))
def agent_has_one_session(world: World, agent: str):
    world.live_session(agent)
    assert len(world.fake.sessions) == 1


@then(parsers.parse('the agent "{agent}" is not running'))
def agent_is_not_running(world: World, agent: str):
    assert world.fake.live_sessions(world.agents[agent]["anthropic_id"]) == []


# Resources and scopes

@given(parsers.parse('a text resource "{resource}" containing "{content}"'))
def given_text_resource(world: World, resource: str, content: str):
    body = {"name": resource, "type": "text", "storage": "in_place", "content": content}
    world.resources[resource] = world.ok("POST", "/api/resource", body)


@given(parsers.parse('an uploaded file "{resource}" with the file ID "{file_id}"'))
def given_uploaded_file(world: World, resource: str, file_id: str):
    body = {"name": resource, "type": "file", "storage": "anthropic_managed", "anthropic_file_id": file_id}
    world.resources[resource] = world.ok("POST", "/api/resource", body)


@given(parsers.parse('the main scope of the project "{project}" contains:'))
def given_main_scope(world: World, project: str, datatable: list[list[str]]):
    for resource_id in world.resource_ids(datatable):
        world.ok("PUT", f"/api/scope/{world.projects[project]['main_scope']}/resources/{resource_id}")


@given(parsers.parse('the scope of the role "{role}" contains:'))
def given_role_scope(world: World, role: str, datatable: list[list[str]]):
    for resource_id in world.resource_ids(datatable):
        world.ok("PUT", f"/api/scope/{world.roles[role]['context_scope']}/resources/{resource_id}")


@given(parsers.parse('a scope "{scope}" in the project "{project}" containing:'))
def given_project_scope(world: World, scope: str, project: str, datatable: list[list[str]]):
    body = {"resource_ids": world.resource_ids(datatable)}
    world.scopes[scope] = world.ok("POST", f"/api/project/{world.projects[project]['id']}/scopes", body)


@given(parsers.parse('an empty scope "{scope}" in the project "{project}"'))
def given_empty_project_scope(world: World, scope: str, project: str):
    world.scopes[scope] = world.ok("POST", f"/api/project/{world.projects[project]['id']}/scopes", {})


@given(parsers.parse('the agent "{agent}" is pinned to the scope "{scope}"'))
@when(parsers.parse('I pin the agent "{agent}" to the scope "{scope}"'))
def pin_agent(world: World, agent: str, scope: str):
    body = {"context_scope": world.scopes[scope]["id"]}
    world.request("PUT", f"/api/agent/{world.agents[agent]['id']}/scope", body)


@when(parsers.parse('I add the resource "{resource}" to the scope "{scope}"'))
def add_resource_to_scope(world: World, resource: str, scope: str):
    world.request("PUT", f"/api/scope/{world.scopes[scope]['id']}/resources/{world.resources[resource]['id']}")


@when(parsers.parse('I remove the resource "{resource}" from the main scope of the project "{project}"'))
def remove_resource_from_main_scope(world: World, resource: str, project: str):
    main_scope = world.projects[project]["main_scope"]
    world.ok("DELETE", f"/api/scope/{main_scope}/resources/{world.resources[resource]['id']}")


@when(parsers.parse('I delete the scope "{scope}"'))
def delete_scope(world: World, scope: str):
    world.request("DELETE", f"/api/scope/{world.scopes[scope]['id']}")


@when(parsers.parse('I delete the main scope of the project "{project}"'))
def delete_main_scope(world: World, project: str):
    world.request("DELETE", f"/api/scope/{world.projects[project]['main_scope']}")


@then(parsers.parse('the scope of the role "{role}" contains:'))
def role_scope_contains(world: World, role: str, datatable: list[list[str]]):
    scope = world.ok("GET", f"/api/scope/{world.roles[role]['context_scope']}")
    assert set(scope["resources"]) == set(world.resource_ids(datatable))


@then(parsers.parse('the main scope of the project "{project}" contains no resources'))
def main_scope_is_empty(world: World, project: str):
    assert world.ok("GET", f"/api/scope/{world.projects[project]['main_scope']}")["resources"] == []


@then(parsers.parse('the scope "{scope}" contains no resources'))
def scope_is_empty(world: World, scope: str):
    assert world.ok("GET", f"/api/scope/{world.scopes[scope]['id']}")["resources"] == []


@then(parsers.parse('the agent "{agent}" uses the default scope'))
def agent_uses_default_scope(world: World, agent: str):
    assert world.ok("GET", f"/api/agent/{world.agents[agent]['id']}")["context_scope"] is None


@then(parsers.parse('the session of "{agent}" includes "{text}"'))
def session_includes(world: World, agent: str, text: str):
    assert text in world.live_session(agent).params["agent"]["system"]


@then(parsers.parse('the session of "{agent}" does not include "{text}"'))
def session_excludes(world: World, agent: str, text: str):
    assert text not in world.live_session(agent).params["agent"]["system"]


@then(parsers.parse('the session of "{agent}" mounts the file "{file_id}"'))
def session_mounts_file(world: World, agent: str, file_id: str):
    assert file_id in [r["file_id"] for r in world.live_session(agent).params["resources"]]


@then(parsers.parse('the session of "{agent}" mounts no files'))
def session_mounts_no_files(world: World, agent: str):
    assert world.live_session(agent).params["resources"] == []


# Links and messaging

@given(parsers.parse('"{sender}" may send "{type}" messages to "{recipient}"'))
@when(parsers.parse('I allow "{sender}" to send "{type}" messages to "{recipient}"'))
def link_agents(world: World, sender: str, type: str, recipient: str):
    body = {"to_agent": world.agents[recipient]["id"], "type": type}
    world.request("POST", f"/api/agent/{world.agents[sender]['id']}/links", body)


@when(parsers.parse('"{sender}" sends "{recipient}" the "{type}" message "{message}"'))
def send_message(world: World, sender: str, recipient: str, type: str, message: str):
    body = {"from_agent": sender, "to_agent": recipient, "message": message, "type": type}
    world.request("POST", "/api/agent/messages", body)


@then("the message is delivered")
def message_delivered(world: World):
    assert world.response.json()["delivered"] is True


@then("the message is not delivered")
def message_not_delivered(world: World):
    assert world.response.json()["delivered"] is False


@then(parsers.parse('"{agent}" receives a message containing "{text}"'))
def agent_receives(world: World, agent: str, text: str):
    received = world.texts_received(agent)
    assert any(text in message for message in received), received


# Responses

@then("the request succeeds")
def request_succeeds(world: World):
    assert world.response.is_success, f"{world.response.status_code}: {world.response.text}"


@then(parsers.parse("the request fails with status {status:d}"))
def request_fails(world: World, status: int):
    assert world.response.status_code == status, world.response.text


@then(parsers.parse('the error mentions "{text}"'))
def error_mentions(world: World, text: str):
    assert text in world.response.json()["detail"]
