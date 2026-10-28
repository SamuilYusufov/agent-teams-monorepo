"""Storage for resources."""
import sqlite3
from abc import ABC, abstractmethod
from uuid import UUID

from models.context_scope import Resource


class ResourceRepository(ABC):
    """Resources that context scopes are built from."""

    @abstractmethod
    def add(self, resource: Resource) -> Resource:
        """Store a new resource."""

    @abstractmethod
    def get(self, resource_id: UUID) -> Resource | None:
        """Return the resource, or None if it doesn't exist."""

    @abstractmethod
    def get_many(self, resource_ids: list[UUID]) -> list[Resource]:
        """Return the existing resources among `resource_ids`, ordered by name."""

    @abstractmethod
    def list(self) -> list[Resource]:
        """All resources, ordered by name."""

    @abstractmethod
    def update(self, resource: Resource) -> bool:
        """Overwrite the stored resource. Returns False if it doesn't exist."""

    @abstractmethod
    def delete(self, resource_id: UUID) -> bool:
        """Delete the resource and remove it from every scope. Returns False if it doesn't exist."""


class SQLiteResourceRepository(ResourceRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    @staticmethod
    def _to_model(row: sqlite3.Row) -> Resource:
        return Resource(
            id=UUID(row["id"]),
            name=row["name"],
            type=row["type"],
            storage=row["storage"],
            content=row["content"],
            anthropic_file_id=row["anthropic_file_id"],
        )

    def add(self, resource: Resource) -> Resource:
        with self._conn:
            self._conn.execute(
                "INSERT INTO resources (id, name, type, storage, content, anthropic_file_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(resource.id),
                    resource.name,
                    resource.type,
                    resource.storage,
                    resource.content,
                    resource.anthropic_file_id,
                ),
            )
        return resource

    def get(self, resource_id: UUID) -> Resource | None:
        row = self._conn.execute("SELECT * FROM resources WHERE id = ?", (str(resource_id),)).fetchone()
        return self._to_model(row) if row else None

    def get_many(self, resource_ids: list[UUID]) -> list[Resource]:
        """Return the existing resources among `resource_ids`, ordered by name."""
        if not resource_ids:
            return []
        placeholders = ", ".join("?" for _ in resource_ids)
        rows = self._conn.execute(
            # Only `?` placeholders are interpolated; the ids are bound as parameters.
            f"SELECT * FROM resources WHERE id IN ({placeholders}) ORDER BY name",  # noqa: S608
            [str(resource_id) for resource_id in resource_ids],
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def list(self) -> list[Resource]:
        rows = self._conn.execute("SELECT * FROM resources ORDER BY name").fetchall()
        return [self._to_model(row) for row in rows]

    def update(self, resource: Resource) -> bool:
        with self._conn:
            cur = self._conn.execute(
                "UPDATE resources SET name = ?, type = ?, storage = ?, content = ?, anthropic_file_id = ? "
                "WHERE id = ?",
                (
                    resource.name,
                    resource.type,
                    resource.storage,
                    resource.content,
                    resource.anthropic_file_id,
                    str(resource.id),
                ),
            )
        return cur.rowcount > 0

    def delete(self, resource_id: UUID) -> bool:
        """Also removes the resource from every scope that contains it."""
        with self._conn:
            cur = self._conn.execute("DELETE FROM resources WHERE id = ?", (str(resource_id),))
        return cur.rowcount > 0
