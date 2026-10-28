"""The team MCP server: the tools and prompts agents use to work with their team.

It is mounted into the FastAPI app at `/mcp/`. Each agent connects with its own signed URL (see `McpAccess`),
so every tool and prompt acts on behalf of the calling agent.
"""
from collections.abc import Callable
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import PromptError, ToolError
from fastmcp.server.dependencies import get_http_request
from pydantic import Field

from dependencies import Services
from models.agents import AgentWorker, MessageDelivery, RelationshipType, TeamOverview
from services.errors import ConflictError, NotFoundError

INSTRUCTIONS = """
Tools for working with the other agents in your project team.
Call `get_team` to see who is on your team and who you can message, and `send_message` to message them.
"""


def create_team_mcp(get_services: Callable[[], Services]) -> FastMCP:
    """Create the team MCP server, resolving the services on every request."""
    mcp = FastMCP("Agent team", instructions=INSTRUCTIONS)

    def calling_agent(services: Services) -> AgentWorker:
        """The agent whose signed URL the current request was made with."""
        if services.mcp_access is None:
            raise PermissionError("The team MCP server is not configured. Set MCP_PUBLIC_URL and MCP_SECRET.")
        params = get_http_request().query_params
        agent_id = services.mcp_access.verify(params.get("agent"), params.get("token"))
        agent = services.agents.get_agent(agent_id) if agent_id else None
        if not agent:
            raise PermissionError("This MCP URL does not belong to an agent.")
        return agent

    def team_overview() -> TeamOverview:
        services = get_services()
        agent = calling_agent(services)
        return services.agents.team_overview(agent, services.projects.get_project(agent.project))

    # Tools

    @mcp.tool
    async def get_team() -> TeamOverview:
        """Your name and role, your teammates and their roles, and who you can message and hear from."""
        try:
            return team_overview()
        except PermissionError as error:
            raise ToolError(str(error)) from error

    @mcp.tool
    async def send_message(
            to_agent: Annotated[str, Field(description="Name of the teammate to message.")],
            message: str,
            type: Annotated[RelationshipType, Field(description="How you relate to the recipient.")],
    ) -> MessageDelivery:
        """Send a message to a teammate. Only works along links: see `can_message` in `get_team`.

        If it is not delivered, `reason` explains why.
        """
        services = get_services()
        try:
            agent = calling_agent(services)
            return await services.agents.send_message(agent.name, to_agent, message, type, notify_sender=False)
        except (PermissionError, NotFoundError, ConflictError) as error:
            raise ToolError(str(error)) from error

    # Prompts

    @mcp.prompt
    async def assume_identity() -> str:
        """Who you are and how you work with your team."""
        try:
            team = team_overview()
        except PermissionError as error:
            raise PromptError(str(error)) from error
        return f"""
    You are an agent with the following role: {team.role}.
    You have a unique name: {team.name}.
    Your brief role description: {team.role_description}.
    Your project team includes other agents with the following names and roles: {team.teammates}.
    You can receive messages from: {team.can_receive_from}.
    You can send messages to: {team.can_message}.
    Example tasks: {team.task_examples}.
    Example sources to ground your outputs: {team.source_examples}.
    You always stay in the same role.
    """

    @mcp.prompt
    async def grounding_check() -> str:
        """Check that your work still matches your role."""
        try:
            team = team_overview()
        except PermissionError as error:
            raise PromptError(str(error)) from error
        return f"""
    Perform a grounding check. Make sure you are following your role's description and example tasks and sources:
    Role: {team.role}
    Description: {team.role_description}
    Example tasks: {team.task_examples}
    Example sources: {team.source_examples}
    """

    return mcp
