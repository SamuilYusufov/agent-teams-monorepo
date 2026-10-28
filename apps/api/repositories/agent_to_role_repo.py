"""Lookups between agents and their role."""
import sqlite3
from abc import ABC, abstractmethod
from uuid import UUID


class AgentToRoleRepository(ABC):
    """One-to-many: each agent has exactly one role."""

    @abstractmethod
    def assign(self, agent_id: UUID, role_id: UUID) -> bool:
        """Give the agent `role_id`. Returns False if the agent doesn't exist."""

    @abstractmethod
    def get_role_id(self, agent_id: UUID) -> UUID | None:
        """The agent's role, or None if the agent doesn't exist."""

    @abstractmethod
    def get_agent_ids(self, role_id: UUID) -> list[UUID]:
        """Agents with the role, ordered by name."""


class SQLiteAgentToRoleRepository(AgentToRoleRepository):
    """Backed by the `agents.role_id` column."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def assign(self, agent_id: UUID, role_id: UUID) -> bool:
        """Give the agent `role_id`. Returns False if the agent doesn't exist."""
        with self._conn:
            cur = self._conn.execute(
                "UPDATE agents SET role_id = ? WHERE id = ?", (str(role_id), str(agent_id))
            )
        return cur.rowcount > 0

    def get_role_id(self, agent_id: UUID) -> UUID | None:
        row = self._conn.execute(
            "SELECT role_id FROM agents WHERE id = ?", (str(agent_id),)
        ).fetchone()
        return UUID(row["role_id"]) if row else None

    def get_agent_ids(self, role_id: UUID) -> list[UUID]:
        rows = self._conn.execute(
            "SELECT id FROM agents WHERE role_id = ? ORDER BY name", (str(role_id),)
        ).fetchall()
        return [UUID(row["id"]) for row in rows]
