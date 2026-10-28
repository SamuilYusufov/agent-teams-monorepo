from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest

from dependencies import build_services
from services.agent_service import TEAM_MCP_SERVER
from services.mcp_access import McpAccess
from tests.conftest import ENVIRONMENT_ID

pytestmark = pytest.mark.anyio


@pytest.fixture
def access():
    return McpAccess("https://example.com/mcp/", "secret")


def query(url: str) -> dict[str, str]:
    return {key: values[0] for key, values in parse_qs(urlsplit(url).query).items()}


def test_url_for_carries_the_agent_and_a_token(access):
    agent_id = uuid4()
    url = access.url_for(agent_id)
    assert url.startswith("https://example.com/mcp/?")
    assert query(url)["agent"] == str(agent_id)


def test_verify_accepts_issued_tokens(access):
    agent_id = uuid4()
    params = query(access.url_for(agent_id))
    assert access.verify(params["agent"], params["token"]) == agent_id


def test_verify_rejects_forged_or_missing_tokens(access):
    alice, bob = uuid4(), uuid4()
    alice_token = query(access.url_for(alice))["token"]
    assert access.verify(str(bob), alice_token) is None
    assert access.verify(str(alice), "forged") is None
    assert access.verify("not-a-uuid", alice_token) is None
    assert access.verify(None, alice_token) is None
    assert access.verify(str(alice), None) is None


def test_tokens_depend_on_the_secret(access):
    agent_id = uuid4()
    other = McpAccess("https://example.com/mcp/", "another secret")
    params = query(other.url_for(agent_id))
    assert access.verify(params["agent"], params["token"]) is None


async def test_agents_are_created_with_the_team_mcp_server(conn, fake_client, access):
    services = build_services(conn, ENVIRONMENT_ID, fake_client, access)
    role = services.roles.create_role("dev", "d", [], [])
    project = services.projects.create_project("p", "d", "s", [role.id])

    agent = await services.agents.create_agent("alice", role, services.projects.get_project(project.id))

    remote = fake_client.agents[agent.anthropic_id]
    assert remote.mcp_servers == [{"type": "url", "name": TEAM_MCP_SERVER, "url": access.url_for(agent.id)}]
    assert remote.tools == [
        {
            "type": "mcp_toolset",
            "mcp_server_name": TEAM_MCP_SERVER,
            "default_config": {"permission_policy": {"type": "always_allow"}},
        }
    ]


async def test_agents_are_created_without_mcp_when_not_configured(services, fake_client):
    role = services.roles.create_role("dev", "d", [], [])
    project = services.projects.create_project("p", "d", "s", [role.id])

    agent = await services.agents.create_agent("alice", role, services.projects.get_project(project.id))

    assert fake_client.agents[agent.anthropic_id].mcp_servers == []
