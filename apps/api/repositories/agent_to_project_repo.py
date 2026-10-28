"""Lookups between agents and the project they belong to."""
import sqlite3
from abc import ABC, abstractmethod
from uuid import UUID


class AgentToProjectRepository(ABC):
    """One-to-many: each agent belongs to exactly one project."""

    @abstractmethod
    def assign(self, agent_id: UUID, project_id: UUID) -> bool:
        """Move the agent to `project_id`. Returns False if the agent doesn't exist."""

    @abstractmethod
    def get_project_id(self, agent_id: UUID) -> UUID | None:
        """The agent's project, or None if the agent doesn't exist."""

    @abstractmethod
    def get_agent_ids(self, project_id: UUID) -> list[UUID]:
        """Agents in the project, ordered by name."""


class SQLiteAgentToProjectRepository(AgentToProjectRepository):
    """Backed by the `agents.project_id` column."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def assign(self, agent_id: UUID, project_id: UUID) -> bool:
        """Move the agent to `project_id`. Returns False if the agent doesn't exist."""
        with self._conn:
            cur = self._conn.execute(
                "UPDATE agents SET project_id = ? WHERE id = ?", (str(project_id), str(agent_id))
            )
        return cur.rowcount > 0

    def get_project_id(self, agent_id: UUID) -> UUID | None:
        row = self._conn.execute(
            "SELECT project_id FROM agents WHERE id = ?", (str(agent_id),)
        ).fetchone()
        return UUID(row["project_id"]) if row else None

    def get_agent_ids(self, project_id: UUID) -> list[UUID]:
        rows = self._conn.execute(
            "SELECT id FROM agents WHERE project_id = ? ORDER BY name", (str(project_id),)
        ).fetchall()
        return [UUID(row["id"]) for row in rows]
