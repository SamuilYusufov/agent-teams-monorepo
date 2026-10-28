"""The team MCP server, called over streamable HTTP through the FastAPI app it is mounted in."""
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx2
import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.exceptions import ToolError

from api import create_app
from dependencies import build_services
from services.mcp_access import McpAccess
from tests.conftest import ENVIRONMENT_ID

pytestmark = pytest.mark.anyio

MCP_URL = "http://testserver/mcp/"


@pytest.fixture
def mcp_access():
    return McpAccess(MCP_URL, "test-secret")


@pytest.fixture
def services(conn, fake_client, mcp_access):
    return build_services(conn, ENVIRONMENT_ID, fake_client, mcp_access)


@pytest.fixture
def app(services):
    return create_app(lambda: services)


@pytest.fixture
async def team(services):
    """Agents alice and bob in one project; alice may send bob `manager` messages."""
    role = services.roles.create_role("developer", "Writes code.", ["Fix bugs"], ["The style guide"])
    project = services.projects.create_project("Apollo", "d", "Work together.", [role.id])
    alice = await services.agents.create_agent("alice", role, services.projects.get_project(project.id))
    bob = await services.agents.create_agent("bob", role, services.projects.get_project(project.id))
    services.agents.add_link(alice.id, bob.id, "manager")
    return alice, bob


@pytest.fixture
def connect(app):
    """Connect to the MCP server with a URL, through the app and its lifespan."""

    def http_client(**kwargs):
        return httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="http://testserver", **kwargs)

    @asynccontextmanager
    async def connect_to(url: str):
        async with app.router.lifespan_context(app):
            transport = StreamableHttpTransport(url, httpx_client_factory=http_client)
            async with Client(transport) as client:
                yield client

    return connect_to


async def test_lists_tools_and_prompts(connect, mcp_access, team):
    alice, _ = team
    async with connect(mcp_access.url_for(alice.id)) as client:
        assert {tool.name for tool in await client.list_tools()} == {"get_team", "send_message"}
        assert {prompt.name for prompt in await client.list_prompts()} == {"assume_identity", "grounding_check"}


async def test_get_team_describes_the_calling_agent(connect, mcp_access, team):
    alice, bob = team

    async with connect(mcp_access.url_for(alice.id)) as client:
        alice_view = (await client.call_tool("get_team")).structured_content
    async with connect(mcp_access.url_for(bob.id)) as client:
        bob_view = (await client.call_tool("get_team")).structured_content

    assert alice_view["name"] == "alice"
    assert alice_view["project"] == "Apollo"
    assert alice_view["teammates"] == {"bob": "developer"}
    assert alice_view["can_message"] == {"bob": ["manager"]}
    assert bob_view["can_receive_from"] == {"alice": ["manager"]}


async def test_send_message_is_delivered_from_the_calling_agent(connect, mcp_access, team, fake_client):
    alice, bob = team

    async with connect(mcp_access.url_for(alice.id)) as client:
        result = await client.call_tool("send_message", {"to_agent": "bob", "message": "Review it.", "type": "manager"})

    assert result.structured_content == {"delivered": True, "reason": None}
    [bob_session] = fake_client.live_sessions(bob.anthropic_id)
    assert fake_client.texts_sent_to(bob_session.id) == ["Message from alice (manager):\nReview it."]


async def test_undelivered_message_reason_is_returned_to_the_caller(connect, mcp_access, team, fake_client):
    _, bob = team

    async with connect(mcp_access.url_for(bob.id)) as client:
        result = await client.call_tool("send_message", {"to_agent": "alice", "message": "Done.", "type": "report"})

    assert result.structured_content["delivered"] is False
    assert "not allowed to message them" in result.structured_content["reason"]
    # The reason is the tool result, so neither agent's session is messaged or started.
    assert fake_client.sent == []
    assert fake_client.sessions == {}


async def test_send_message_to_unknown_agent_is_a_tool_error(connect, mcp_access, team):
    alice, _ = team
    async with connect(mcp_access.url_for(alice.id)) as client:
        with pytest.raises(ToolError, match="not found"):
            await client.call_tool("send_message", {"to_agent": "nobody", "message": "Hi.", "type": "peer"})


@pytest.mark.parametrize(
    "query",
    ["", "?agent=not-a-uuid&token=x", "?agent={bob}&token={alice_token}", f"?agent={uuid4()}&token=x"],
    ids=["missing", "malformed", "other-agents-token", "unknown-agent"],
)
async def test_requests_without_a_valid_agent_url_are_rejected(connect, mcp_access, team, query):
    alice, bob = team
    alice_token = mcp_access.url_for(alice.id).split("token=")[1]
    url = MCP_URL + query.format(bob=bob.id, alice_token=alice_token)
    async with connect(url) as client:
        with pytest.raises(ToolError, match="does not belong to an agent"):
            await client.call_tool("get_team")


async def test_rejected_when_mcp_access_is_not_configured(conn, fake_client, mcp_access, team):
    alice, _ = team
    unconfigured = build_services(conn, ENVIRONMENT_ID, fake_client)
    app = create_app(lambda: unconfigured)

    def http_client(**kwargs):
        return httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="http://testserver", **kwargs)

    async with app.router.lifespan_context(app):
        transport = StreamableHttpTransport(mcp_access.url_for(alice.id), httpx_client_factory=http_client)
        async with Client(transport) as client:
            with pytest.raises(ToolError, match="not configured"):
                await client.call_tool("get_team")


async def test_prompts_describe_the_calling_agent(connect, mcp_access, team):
    alice, _ = team
    async with connect(mcp_access.url_for(alice.id)) as client:
        identity = (await client.get_prompt("assume_identity")).messages[0].content.text
        grounding = (await client.get_prompt("grounding_check")).messages[0].content.text

    assert "You have a unique name: alice." in identity
    assert "You can send messages to: {'bob': ['manager']}." in identity
    assert "Fix bugs" in grounding


async def test_rest_api_still_served_next_to_mcp(http):
    assert http.get("/api/role").json() == []
