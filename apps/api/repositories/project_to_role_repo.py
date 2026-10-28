"""Links between projects and the roles available in them."""
import sqlite3
from abc import ABC, abstractmethod
from uuid import UUID


class ProjectToRoleRepository(ABC):
    """Many-to-many: roles available inside a project."""

    @abstractmethod
    def link(self, project_id: UUID, role_id: UUID) -> None:
        """Make the role available in the project. Linking twice is a no-op."""

    @abstractmethod
    def unlink(self, project_id: UUID, role_id: UUID) -> bool:
        """Remove the role from the project. Returns False if it wasn't linked."""

    @abstractmethod
    def is_linked(self, project_id: UUID, role_id: UUID) -> bool:
        """Whether the role is available in the project."""

    @abstractmethod
    def get_role_ids(self, project_id: UUID) -> list[UUID]:
        """Roles available in the project."""

    @abstractmethod
    def get_project_ids(self, role_id: UUID) -> list[UUID]:
        """Projects the role is available in."""


class SQLiteProjectToRoleRepository(ProjectToRoleRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def link(self, project_id: UUID, role_id: UUID) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO project_to_role (project_id, role_id) VALUES (?, ?)",
                (str(project_id), str(role_id)),
            )

    def unlink(self, project_id: UUID, role_id: UUID) -> bool:
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM project_to_role WHERE project_id = ? AND role_id = ?",
                (str(project_id), str(role_id)),
            )
        return cur.rowcount > 0

    def is_linked(self, project_id: UUID, role_id: UUID) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM project_to_role WHERE project_id = ? AND role_id = ?",
            (str(project_id), str(role_id)),
        ).fetchone()
        return row is not None

    def get_role_ids(self, project_id: UUID) -> list[UUID]:
        rows = self._conn.execute(
            "SELECT role_id FROM project_to_role WHERE project_id = ?", (str(project_id),)
        ).fetchall()
        return [UUID(row["role_id"]) for row in rows]

    def get_project_ids(self, role_id: UUID) -> list[UUID]:
        rows = self._conn.execute(
            "SELECT project_id FROM project_to_role WHERE role_id = ?", (str(role_id),)
        ).fetchall()
        return [UUID(row["project_id"]) for row in rows]
