from uuid import uuid4

import pytest

from services.agent_service import MODEL
from services.errors import ConflictError, NotFoundError
from tests.conftest import ENVIRONMENT_ID

pytestmark = pytest.mark.anyio


# Creating and deleting

async def test_create_agent(services, project, role, create_agent, fake_client):
    agent = await create_agent("alice")

    remote = fake_client.agents[agent.anthropic_id]
    assert remote.model == MODEL
    assert remote.system.startswith("Project prompt.")
    assert "alice" in remote.system
    assert role.name in remote.system
    assert agent.context_scope is None
    assert services.agents.get_agent(agent.id) == agent
    assert services.projects.get_project(project.id).team == [agent.id]


async def test_create_agent_lists_teammates_in_prompt(create_agent, fake_client):
    await create_agent("alice")
    bob = await create_agent("bob")
    assert "'alice': 'dev'" in fake_client.agents[bob.anthropic_id].system


async def test_create_agent_with_scope(services, project, create_agent):
    secondary = services.scopes.create_project_scope(project.id)
    agent = await create_agent("alice", context_scope=secondary.id)
    assert services.agents.get_agent(agent.id).context_scope == secondary.id


async def test_create_agent_rejects_role_outside_project(services, project, fake_client):
    ops = services.roles.create_role("ops", "d", [], [])
    with pytest.raises(ConflictError):
        await services.agents.create_agent("alice", ops, project)
    assert fake_client.agents == {}


async def test_create_agent_rejects_scope_outside_project(services, role, create_agent, fake_client):
    with pytest.raises(ConflictError):
        await create_agent("alice", context_scope=role.context_scope)
    assert fake_client.agents == {}


async def test_create_agent_rejects_duplicate_name(create_agent, fake_client):
    await create_agent("alice")
    with pytest.raises(ConflictError):
        await create_agent("alice")
    assert len(fake_client.agents) == 1


async def test_create_agent_archives_remote_agent_if_save_fails(services, create_agent, fake_client, monkeypatch):
    def fail(agent):
        raise RuntimeError("db down")

    monkeypatch.setattr(services.agents._agents, "add", fail)
    with pytest.raises(RuntimeError):
        await create_agent("alice")
    assert fake_client.archived_agents == list(fake_client.agents)


async def test_get_and_list_agents(services, role, project, create_agent):
    alice = await create_agent("alice")
    other = services.projects.create_project("other", "d", "s", [role.id])
    bob = await services.agents.create_agent("bob", role, other)

    assert services.agents.get_agent_by_name("bob") == bob
    assert services.agents.list_agents() == [alice, bob]
    assert services.agents.list_agents(project.id) == [alice]


async def test_retrieve_agent(services, create_agent, fake_client):
    agent = await create_agent("alice")
    worker, remote = await services.agents.retrieve_agent(agent.id)
    assert worker == agent
    assert remote is fake_client.agents[agent.anthropic_id]
    assert await services.agents.retrieve_agent(uuid4()) is None


async def test_delete_agent(services, create_agent, fake_client):
    agent = await create_agent("alice")
    await services.agents.start(agent.id)

    await services.agents.delete_agent(agent.id)

    assert services.agents.get_agent(agent.id) is None
    assert fake_client.archived_agents == [agent.anthropic_id]
    assert fake_client.live_sessions(agent.anthropic_id) == []


async def test_delete_unknown_agent(services):
    with pytest.raises(NotFoundError):
        await services.agents.delete_agent(uuid4())


# Starting and stopping

async def test_start_creates_session_with_context_scope(services, project, role, create_agent, fake_client):
    notes = services.scopes.create_resource("notes", "text", "in_place", content="Remember this.")
    spec = services.scopes.create_resource("spec", "file", "anthropic_managed", anthropic_file_id="file_1")
    for resource in (notes, spec):
        services.scopes.add_resource(project.main_scope, resource.id)
        services.scopes.add_resource(role.context_scope, resource.id)
    agent = await create_agent("alice")

    session = await services.agents.start(agent.id)

    params = session.params
    assert params["environment_id"] == ENVIRONMENT_ID
    assert params["agent"]["type"] == "agent_with_overrides"
    assert params["agent"]["id"] == agent.anthropic_id
    system = params["agent"]["system"]
    assert system.startswith(fake_client.agents[agent.anthropic_id].system)
    assert "Remember this." in system
    assert "/mnt/session/uploads/file_1" in system
    assert params["resources"] == [{"type": "file", "file_id": "file_1", "mount_path": "/mnt/session/uploads/file_1"}]
    assert params["metadata"] == {"agent_id": str(agent.id), "project_id": str(project.id)}


async def test_start_without_resources_keeps_agent_prompt(services, create_agent, fake_client):
    agent = await create_agent("alice")
    session = await services.agents.start(agent.id)
    assert session.params["agent"]["system"] == fake_client.agents[agent.anthropic_id].system
    assert session.params["resources"] == []


async def test_start_lists_message_recipients_in_prompt(services, create_agent):
    alice = await create_agent("alice")
    bob = await create_agent("bob")
    services.agents.add_link(alice.id, bob.id, "manager")
    services.agents.add_link(alice.id, bob.id, "peer")

    session = await services.agents.start(alice.id)

    assert "{'bob': ['manager', 'peer']}" in session.params["agent"]["system"]


async def test_start_reuses_live_session(services, create_agent, fake_client):
    agent = await create_agent("alice")
    first = await services.agents.start(agent.id)
    second = await services.agents.start(agent.id)
    assert second is first
    assert len(fake_client.sessions) == 1


async def test_start_after_stop_creates_new_session(services, create_agent):
    agent = await create_agent("alice")
    first = await services.agents.start(agent.id)
    await services.agents.stop(agent.id)
    second = await services.agents.start(agent.id)
    assert second.id != first.id


async def test_stop_archives_all_live_sessions(services, create_agent, fake_client):
    agent = await create_agent("alice")
    await fake_client.beta.sessions.create(agent={"id": agent.anthropic_id})
    await fake_client.beta.sessions.create(agent={"id": agent.anthropic_id})

    await services.agents.stop(agent.id)

    assert fake_client.live_sessions(agent.anthropic_id) == []


async def test_start_and_stop_unknown_agent(services):
    with pytest.raises(NotFoundError):
        await services.agents.start(uuid4())
    with pytest.raises(NotFoundError):
        await services.agents.stop(uuid4())


# Links

async def test_add_and_list_links(services, create_agent):
    alice = await create_agent("alice")
    bob = await create_agent("bob")
    outgoing = services.agents.add_link(alice.id, bob.id, "manager")
    incoming = services.agents.add_link(bob.id, alice.id, "report")

    assert services.agents.list_links(alice.id) == [outgoing, incoming]


async def test_add_link_validation(services, role, create_agent):
    alice = await create_agent("alice")
    bob = await create_agent("bob")
    other = services.projects.create_project("other", "d", "s", [role.id])
    carol = await services.agents.create_agent("carol", role, other)
    services.agents.add_link(alice.id, bob.id, "peer")

    with pytest.raises(NotFoundError):
        services.agents.add_link(alice.id, uuid4(), "peer")
    with pytest.raises(ConflictError):
        services.agents.add_link(alice.id, alice.id, "peer")
    with pytest.raises(ConflictError):
        services.agents.add_link(alice.id, carol.id, "peer")
    with pytest.raises(ConflictError):
        services.agents.add_link(alice.id, bob.id, "peer")


async def test_remove_link(services, create_agent):
    alice = await create_agent("alice")
    bob = await create_agent("bob")
    link = services.agents.add_link(alice.id, bob.id, "peer")

    services.agents.remove_link(link.id)

    assert services.agents.list_links(alice.id) == []
    with pytest.raises(NotFoundError):
        services.agents.remove_link(link.id)


# Messaging

@pytest.fixture
async def team(services, create_agent):
    alice = await create_agent("alice")
    bob = await create_agent("bob")
    services.agents.add_link(alice.id, bob.id, "manager")
    return alice, bob


async def test_send_message_starts_recipient_and_delivers(services, team, fake_client):
    _, bob = team

    assert (await services.agents.send_message("alice", "bob", "Ship it.", "manager")).delivered is True

    [bob_session] = fake_client.live_sessions(bob.anthropic_id)
    assert fake_client.texts_sent_to(bob_session.id) == ["Message from alice (manager):\nShip it."]


async def test_send_message_reuses_recipient_session(services, team, fake_client):
    _, bob = team
    session = await services.agents.start(bob.id)
    await services.agents.send_message("alice", "bob", "Ship it.", "manager")
    assert len(fake_client.texts_sent_to(session.id)) == 1
    assert len(fake_client.live_sessions(bob.anthropic_id)) == 1


async def test_send_message_with_wrong_type_notifies_sender(services, team, fake_client):
    alice, bob = team
    alice_session = await services.agents.start(alice.id)

    assert (await services.agents.send_message("alice", "bob", "Hi.", "peer")).delivered is False

    [notice] = fake_client.texts_sent_to(alice_session.id)
    assert "'peer'" in notice
    assert "['manager']" in notice
    assert fake_client.live_sessions(bob.anthropic_id) == []


async def test_send_message_without_link_notifies_sender(services, team, fake_client):
    alice, bob = team
    bob_session = await services.agents.start(bob.id)

    assert (await services.agents.send_message("bob", "alice", "Done.", "report")).delivered is False

    [notice] = fake_client.texts_sent_to(bob_session.id)
    assert "not allowed" in notice
    assert fake_client.live_sessions(alice.anthropic_id) == []


async def test_send_message_rejected_without_sender_session(services, team):
    with pytest.raises(ConflictError):
        await services.agents.send_message("bob", "alice", "Done.", "report")


async def test_send_message_unknown_agents(services, team):
    with pytest.raises(NotFoundError):
        await services.agents.send_message("nobody", "bob", "Hi.", "peer")
    with pytest.raises(NotFoundError):
        await services.agents.send_message("alice", "nobody", "Hi.", "peer")


async def test_send_message_across_projects(services, role, team):
    other = services.projects.create_project("other", "d", "s", [role.id])
    await services.agents.create_agent("carol", role, other)
    with pytest.raises(ConflictError):
        await services.agents.send_message("alice", "carol", "Hi.", "peer")
