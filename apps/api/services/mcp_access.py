"""Signed per-agent URLs for the team MCP server.

Managed Agents connect to MCP servers by URL only, so each agent gets its own URL carrying its ID and an HMAC
of that ID. The server derives the calling agent from the URL, which stops agents from acting as each other.
"""
import hashlib
import hmac
from urllib.parse import urlencode
from uuid import UUID


class McpAccess:
    """Builds and verifies the agents' MCP URLs."""

    def __init__(self, public_url: str, secret: str):
        """`public_url` is where Managed Agents can reach the MCP endpoint, e.g. `https://example.com/mcp/`."""
        self._public_url = public_url
        self._secret = secret.encode()

    def _token(self, agent_id: UUID) -> str:
        return hmac.new(self._secret, str(agent_id).encode(), hashlib.sha256).hexdigest()

    def url_for(self, agent_id: UUID) -> str:
        """The MCP URL the agent connects with."""
        return f"{self._public_url}?{urlencode({'agent': str(agent_id), 'token': self._token(agent_id)})}"

    def verify(self, agent: str | None, token: str | None) -> UUID | None:
        """The agent ID if `token` was issued for `agent`, otherwise None."""
        if not agent or not token:
            return None
        try:
            agent_id = UUID(agent)
        except ValueError:
            return None
        return agent_id if hmac.compare_digest(self._token(agent_id), token) else None
