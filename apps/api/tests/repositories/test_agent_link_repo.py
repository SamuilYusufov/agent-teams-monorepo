import sqlite3
from uuid import uuid4

import pytest

from models.agents import AgentLink


@pytest.fixture
def team(seed):
    project, role = seed.project(), seed.role()
    return seed.agent(project, role, "alice"), seed.agent(project, role, "bob"), seed.agent(project, role, "carol")


def test_add_and_get(repos, team):
    alice, bob, _ = team
    link = repos.links.add(AgentLink(from_agent=alice.id, to_agent=bob.id, type="manager"))
    assert repos.links.get(link.id) == link


def test_get_missing_returns_none(repos):
    assert repos.links.get(uuid4()) is None


def test_duplicate_link_is_rejected(repos, team):
    alice, bob, _ = team
    repos.links.add(AgentLink(from_agent=alice.id, to_agent=bob.id, type="manager"))
    with pytest.raises(sqlite3.IntegrityError):
        repos.links.add(AgentLink(from_agent=alice.id, to_agent=bob.id, type="manager"))


def test_same_pair_can_have_several_types(repos, team):
    alice, bob, _ = team
    repos.links.add(AgentLink(from_agent=alice.id, to_agent=bob.id, type="manager"))
    repos.links.add(AgentLink(from_agent=alice.id, to_agent=bob.id, type="peer"))
    assert {link.type for link in repos.links.list_between(alice.id, bob.id)} == {"manager", "peer"}


def test_requires_existing_agents(repos, team):
    alice, _, _ = team
    with pytest.raises(sqlite3.IntegrityError):
        repos.links.add(AgentLink(from_agent=alice.id, to_agent=uuid4(), type="peer"))


def test_rejects_unknown_type(repos, team):
    alice, bob, _ = team
    invalid = AgentLink.model_construct(id=uuid4(), from_agent=alice.id, to_agent=bob.id, type="boss")
    with pytest.raises(sqlite3.IntegrityError):
        repos.links.add(invalid)


def test_list_from_to_and_between_are_directional(repos, team):
    alice, bob, carol = team
    a_to_b = repos.links.add(AgentLink(from_agent=alice.id, to_agent=bob.id, type="manager"))
    b_to_a = repos.links.add(AgentLink(from_agent=bob.id, to_agent=alice.id, type="report"))
    c_to_b = repos.links.add(AgentLink(from_agent=carol.id, to_agent=bob.id, type="peer"))

    assert repos.links.list_from(alice.id) == [a_to_b]
    assert {link.id for link in repos.links.list_to(bob.id)} == {a_to_b.id, c_to_b.id}
    assert repos.links.list_between(alice.id, bob.id) == [a_to_b]
    assert repos.links.list_between(bob.id, alice.id) == [b_to_a]
    assert repos.links.list_between(alice.id, carol.id) == []


def test_delete(repos, team):
    alice, bob, _ = team
    link = repos.links.add(AgentLink(from_agent=alice.id, to_agent=bob.id, type="peer"))
    assert repos.links.delete(link.id) is True
    assert repos.links.get(link.id) is None
    assert repos.links.delete(link.id) is False


def test_links_are_deleted_with_agent(repos, team):
    alice, bob, _ = team
    outgoing = repos.links.add(AgentLink(from_agent=alice.id, to_agent=bob.id, type="peer"))
    incoming = repos.links.add(AgentLink(from_agent=bob.id, to_agent=alice.id, type="peer"))
    repos.agents.delete(alice.id)
    assert repos.links.get(outgoing.id) is None
    assert repos.links.get(incoming.id) is None
