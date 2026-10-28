"""Storage for context scopes."""
import sqlite3
from abc import ABC, abstractmethod
from uuid import UUID

from models.context_scope import ContextScope


class ScopeRepository(ABC):
    """Context scopes and the resources inside them."""

    @abstractmethod
    def add(self, scope: ContextScope) -> ContextScope:
        """Store a new scope with its resources."""

    @abstractmethod
    def get(self, scope_id: UUID) -> ContextScope | None:
        """Return the scope, or None if it doesn't exist."""

    @abstractmethod
    def update(self, scope: ContextScope) -> bool:
        """Replace the scope's resources with `scope.resources`. Returns False if it doesn't exist."""

    @abstractmethod
    def delete(self, scope_id: UUID) -> bool:
        """Delete the scope, keeping its resources. Returns False if it doesn't exist."""

    @abstractmethod
    def add_resource(self, scope_id: UUID, resource_id: UUID) -> None:
        """Add a resource to the scope. Adding it twice is a no-op."""

    @abstractmethod
    def remove_resource(self, scope_id: UUID, resource_id: UUID) -> bool:
        """Remove a resource from the scope. Returns False if it wasn't there."""

    @abstractmethod
    def get_scope_ids(self, resource_id: UUID) -> list[UUID]:
        """Scopes containing the resource."""


class SQLiteScopeRepository(ScopeRepository):
    """`resources` is stored in the `scope_to_resource` table."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def _resources(self, scope_id: str) -> list[UUID]:
        rows = self._conn.execute(
            "SELECT resource_id FROM scope_to_resource WHERE scope_id = ?", (scope_id,)
        ).fetchall()
        return [UUID(row["resource_id"]) for row in rows]

    def _insert_resources(self, scope: ContextScope) -> None:
        self._conn.executemany(
            "INSERT OR IGNORE INTO scope_to_resource (scope_id, resource_id) VALUES (?, ?)",
            [(str(scope.id), str(resource_id)) for resource_id in scope.resources],
        )

    def add(self, scope: ContextScope) -> ContextScope:
        with self._conn:
            self._conn.execute("INSERT INTO context_scopes (id) VALUES (?)", (str(scope.id),))
            self._insert_resources(scope)
        return scope

    def get(self, scope_id: UUID) -> ContextScope | None:
        row = self._conn.execute("SELECT id FROM context_scopes WHERE id = ?", (str(scope_id),)).fetchone()
        return ContextScope(id=UUID(row["id"]), resources=self._resources(row["id"])) if row else None

    def update(self, scope: ContextScope) -> bool:
        """Replace the scope's resources with `scope.resources`."""
        if not self.get(scope.id):
            return False
        with self._conn:
            self._conn.execute("DELETE FROM scope_to_resource WHERE scope_id = ?", (str(scope.id),))
            self._insert_resources(scope)
        return True

    def delete(self, scope_id: UUID) -> bool:
        """Fails with sqlite3.IntegrityError while a role or a project's main scope still points to it."""
        with self._conn:
            cur = self._conn.execute("DELETE FROM context_scopes WHERE id = ?", (str(scope_id),))
        return cur.rowcount > 0

    def add_resource(self, scope_id: UUID, resource_id: UUID) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO scope_to_resource (scope_id, resource_id) VALUES (?, ?)",
                (str(scope_id), str(resource_id)),
            )

    def remove_resource(self, scope_id: UUID, resource_id: UUID) -> bool:
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM scope_to_resource WHERE scope_id = ? AND resource_id = ?",
                (str(scope_id), str(resource_id)),
            )
        return cur.rowcount > 0

    def get_scope_ids(self, resource_id: UUID) -> list[UUID]:
        rows = self._conn.execute(
            "SELECT scope_id FROM scope_to_resource WHERE resource_id = ?", (str(resource_id),)
        ).fetchall()
        return [UUID(row["scope_id"]) for row in rows]
