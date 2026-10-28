"""Storage for roles."""
import json
import sqlite3
from abc import ABC, abstractmethod
from uuid import UUID

from models.roles import AgentRole


class RoleRepository(ABC):
    """Roles, each with its own default context scope."""

    @abstractmethod
    def add(self, role: AgentRole) -> AgentRole:
        """Store a new role. Names are unique."""

    @abstractmethod
    def get(self, role_id: UUID) -> AgentRole | None:
        """Return the role, or None if it doesn't exist."""

    @abstractmethod
    def get_by_name(self, name: str) -> AgentRole | None:
        """Return the role with this name, or None."""

    @abstractmethod
    def list(self) -> list[AgentRole]:
        """All roles, ordered by name."""

    @abstractmethod
    def update(self, role: AgentRole) -> bool:
        """Overwrite the stored role. Returns False if it doesn't exist."""

    @abstractmethod
    def delete(self, role_id: UUID) -> bool:
        """Delete the role. Returns False if it doesn't exist."""


class SQLiteRoleRepository(RoleRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    @staticmethod
    def _to_model(row: sqlite3.Row) -> AgentRole:
        return AgentRole(
            id=UUID(row["id"]),
            name=row["name"],
            description=row["description"],
            task_examples=json.loads(row["task_examples"]),
            source_examples=json.loads(row["source_examples"]),
            context_scope=UUID(row["context_scope_id"]),
        )

    def add(self, role: AgentRole) -> AgentRole:
        with self._conn:
            self._conn.execute(
                "INSERT INTO roles (id, name, description, task_examples, source_examples, context_scope_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(role.id),
                    role.name,
                    role.description,
                    json.dumps(role.task_examples),
                    json.dumps(role.source_examples),
                    str(role.context_scope),
                ),
            )
        return role

    def get(self, role_id: UUID) -> AgentRole | None:
        row = self._conn.execute("SELECT * FROM roles WHERE id = ?", (str(role_id),)).fetchone()
        return self._to_model(row) if row else None

    def get_by_name(self, name: str) -> AgentRole | None:
        row = self._conn.execute("SELECT * FROM roles WHERE name = ?", (name,)).fetchone()
        return self._to_model(row) if row else None

    def list(self) -> list[AgentRole]:
        rows = self._conn.execute("SELECT * FROM roles ORDER BY name").fetchall()
        return [self._to_model(row) for row in rows]

    def update(self, role: AgentRole) -> bool:
        with self._conn:
            cur = self._conn.execute(
                "UPDATE roles SET name = ?, description = ?, task_examples = ?, source_examples = ?, "
                "context_scope_id = ? WHERE id = ?",
                (
                    role.name,
                    role.description,
                    json.dumps(role.task_examples),
                    json.dumps(role.source_examples),
                    str(role.context_scope),
                    str(role.id),
                ),
            )
        return cur.rowcount > 0

    def delete(self, role_id: UUID) -> bool:
        with self._conn:
            cur = self._conn.execute("DELETE FROM roles WHERE id = ?", (str(role_id),))
        return cur.rowcount > 0
