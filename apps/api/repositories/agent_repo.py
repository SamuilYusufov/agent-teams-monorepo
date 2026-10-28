"""Storage for agents."""
import sqlite3
from abc import ABC, abstractmethod
from uuid import UUID

from models.agents import AgentWorker


class AgentRepository(ABC):
    """Agents, each belonging to one project and having one role."""

    @abstractmethod
    def add(self, agent: AgentWorker) -> AgentWorker:
        """Store a new agent. Names and Anthropic IDs are unique."""

    @abstractmethod
    def get(self, agent_id: UUID) -> AgentWorker | None:
        """Return the agent, or None if it doesn't exist."""

    @abstractmethod
    def get_by_name(self, name: str) -> AgentWorker | None:
        """Return the agent with this name, or None."""

    @abstractmethod
    def list(self) -> list[AgentWorker]:
        """All agents, ordered by name."""

    @abstractmethod
    def update(self, agent: AgentWorker) -> bool:
        """Overwrite the stored agent. Returns False if it doesn't exist."""

    @abstractmethod
    def delete(self, agent_id: UUID) -> bool:
        """Delete the agent. Returns False if it doesn't exist."""


class SQLiteAgentRepository(AgentRepository):
    """The referenced project, role and context scope must already exist."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    @staticmethod
    def _to_model(row: sqlite3.Row) -> AgentWorker:
        return AgentWorker(
            id=UUID(row["id"]),
            anthropic_id=row["anthropic_id"],
            name=row["name"],
            project=UUID(row["project_id"]),
            role=UUID(row["role_id"]),
            context_scope=UUID(row["context_scope_id"]) if row["context_scope_id"] else None,
        )

    def add(self, agent: AgentWorker) -> AgentWorker:
        with self._conn:
            self._conn.execute(
                "INSERT INTO agents (id, anthropic_id, name, project_id, role_id, context_scope_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(agent.id),
                    agent.anthropic_id,
                    agent.name,
                    str(agent.project),
                    str(agent.role),
                    str(agent.context_scope) if agent.context_scope else None,
                ),
            )
        return agent

    def get(self, agent_id: UUID) -> AgentWorker | None:
        row = self._conn.execute("SELECT * FROM agents WHERE id = ?", (str(agent_id),)).fetchone()
        return self._to_model(row) if row else None

    def get_by_name(self, name: str) -> AgentWorker | None:
        row = self._conn.execute("SELECT * FROM agents WHERE name = ?", (name,)).fetchone()
        return self._to_model(row) if row else None

    def list(self) -> list[AgentWorker]:
        rows = self._conn.execute("SELECT * FROM agents ORDER BY name").fetchall()
        return [self._to_model(row) for row in rows]

    def update(self, agent: AgentWorker) -> bool:
        with self._conn:
            cur = self._conn.execute(
                "UPDATE agents SET anthropic_id = ?, name = ?, project_id = ?, role_id = ?, context_scope_id = ? "
                "WHERE id = ?",
                (
                    agent.anthropic_id,
                    agent.name,
                    str(agent.project),
                    str(agent.role),
                    str(agent.context_scope) if agent.context_scope else None,
                    str(agent.id),
                ),
            )
        return cur.rowcount > 0

    def delete(self, agent_id: UUID) -> bool:
        with self._conn:
            cur = self._conn.execute("DELETE FROM agents WHERE id = ?", (str(agent_id),))
        return cur.rowcount > 0
