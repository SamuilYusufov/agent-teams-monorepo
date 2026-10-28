from uuid import uuid4

import pytest

from dependencies import get_services
from services.agent_service import AgentService


@pytest.fixture(autouse=True)
def fresh_services(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTS_DB_PATH", str(tmp_path / "agents.db"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("MCP_PUBLIC_URL", raising=False)
    monkeypatch.delenv("MCP_SECRET", raising=False)
    get_services.cache_clear()
    yield
    get_services.cache_clear()


def test_requires_environment_id(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_ENVIRONMENT_ID", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_ENVIRONMENT_ID"):
        get_services()


def test_builds_services_once(monkeypatch, tmp_path):
    db_path = tmp_path / "agents.db"
    monkeypatch.setenv("ANTHROPIC_ENVIRONMENT_ID", "env_123")
    monkeypatch.setenv("AGENTS_DB_PATH", str(db_path))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    services = get_services()

    assert get_services() is services
    assert isinstance(services.agents, AgentService)
    assert services.agents._environment_id == "env_123"
    assert db_path.exists()
    # The services share one database.
    role = services.roles.create_role("dev", "d", [], [])
    assert services.scopes.get_scope(role.context_scope) is not None


def test_mcp_access_is_off_by_default(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_ENVIRONMENT_ID", "env_123")
    assert get_services().mcp_access is None


def test_mcp_access_from_environment(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_ENVIRONMENT_ID", "env_123")
    monkeypatch.setenv("MCP_PUBLIC_URL", "https://example.com/mcp/")
    monkeypatch.setenv("MCP_SECRET", "secret")
    assert get_services().mcp_access.url_for(uuid4()).startswith("https://example.com/mcp/?agent=")


def test_mcp_public_url_requires_a_secret(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_ENVIRONMENT_ID", "env_123")
    monkeypatch.setenv("MCP_PUBLIC_URL", "https://example.com/mcp/")
    with pytest.raises(RuntimeError, match="MCP_SECRET"):
        get_services()
