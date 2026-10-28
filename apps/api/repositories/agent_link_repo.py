"""Storage for links between agents."""
import sqlite3
from abc import ABC, abstractmethod
from uuid import UUID

from models.agents import AgentLink


class AgentLinkRepository(ABC):
    """Directed links: a link lets `from_agent` send messages of its `type` to `to_agent`."""

    @abstractmethod
    def add(self, link: AgentLink) -> AgentLink:
        """Store a new link. A pair of agents can have one link per type."""

    @abstractmethod
    def get(self, link_id: UUID) -> AgentLink | None:
        """Return the link, or None if it doesn't exist."""

    @abstractmethod
    def list_from(self, agent_id: UUID) -> list[AgentLink]:
        """Links the agent sends messages along."""

    @abstractmethod
    def list_to(self, agent_id: UUID) -> list[AgentLink]:
        """Links the agent receives messages along."""

    @abstractmethod
    def list_between(self, from_agent_id: UUID, to_agent_id: UUID) -> list[AgentLink]:
        """Links from one agent to the other, in that direction only."""

    @abstractmethod
    def delete(self, link_id: UUID) -> bool:
        """Delete the link. Returns False if it doesn't exist."""


class SQLiteAgentLinkRepository(AgentLinkRepository):
    """Links are deleted together with either of their agents."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    @staticmethod
    def _to_model(row: sqlite3.Row) -> AgentLink:
        return AgentLink(
            id=UUID(row["id"]),
            from_agent=UUID(row["from_agent_id"]),
            to_agent=UUID(row["to_agent_id"]),
            type=row["type"],
        )

    def add(self, link: AgentLink) -> AgentLink:
        """Fails with sqlite3.IntegrityError if the same link already exists."""
        with self._conn:
            self._conn.execute(
                "INSERT INTO agent_links (id, from_agent_id, to_agent_id, type) VALUES (?, ?, ?, ?)",
                (str(link.id), str(link.from_agent), str(link.to_agent), link.type),
            )
        return link

    def get(self, link_id: UUID) -> AgentLink | None:
        row = self._conn.execute("SELECT * FROM agent_links WHERE id = ?", (str(link_id),)).fetchone()
        return self._to_model(row) if row else None

    def list_from(self, agent_id: UUID) -> list[AgentLink]:
        rows = self._conn.execute(
            "SELECT * FROM agent_links WHERE from_agent_id = ?", (str(agent_id),)
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def list_to(self, agent_id: UUID) -> list[AgentLink]:
        rows = self._conn.execute(
            "SELECT * FROM agent_links WHERE to_agent_id = ?", (str(agent_id),)
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def list_between(self, from_agent_id: UUID, to_agent_id: UUID) -> list[AgentLink]:
        rows = self._conn.execute(
            "SELECT * FROM agent_links WHERE from_agent_id = ? AND to_agent_id = ?",
            (str(from_agent_id), str(to_agent_id)),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def delete(self, link_id: UUID) -> bool:
        with self._conn:
            cur = self._conn.execute("DELETE FROM agent_links WHERE id = ?", (str(link_id),))
        return cur.rowcount > 0
