"""Storage for projects."""
import sqlite3
from abc import ABC, abstractmethod
from uuid import UUID

from models.projects import ProjectRow


class ProjectRepository(ABC):
    """Projects together with their main scope and context scopes."""

    @abstractmethod
    def add(self, project: ProjectRow) -> ProjectRow:
        """Store a new project and return it as stored. Names are unique."""

    @abstractmethod
    def get(self, project_id: UUID) -> ProjectRow | None:
        """Return the project, or None if it doesn't exist."""

    @abstractmethod
    def get_by_name(self, name: str) -> ProjectRow | None:
        """Return the project with this name, or None."""

    @abstractmethod
    def get_by_scope(self, scope_id: UUID) -> ProjectRow | None:
        """Return the project that defines `scope_id`, or None."""

    @abstractmethod
    def list(self) -> list[ProjectRow]:
        """All projects, ordered by name."""

    @abstractmethod
    def update(self, project: ProjectRow) -> bool:
        """Overwrite the stored project, including its scopes. Returns False if it doesn't exist."""

    @abstractmethod
    def delete(self, project_id: UUID) -> bool:
        """Delete the project. Returns False if it doesn't exist."""


class SQLiteProjectRepository(ProjectRepository):
    """`team` is derived from `agents.project_id` on read and ignored on write.

    Agents join a project via AgentRepository / AgentToProjectRepository.
    `context_scopes` is stored in `project_to_scope` and always includes `main_scope`.
    The referenced scopes must already exist.
    """

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def _team(self, project_id: str) -> list[UUID]:
        rows = self._conn.execute(
            "SELECT id FROM agents WHERE project_id = ? ORDER BY name", (project_id,)
        ).fetchall()
        return [UUID(row["id"]) for row in rows]

    def _context_scopes(self, project_id: str) -> list[UUID]:
        rows = self._conn.execute(
            "SELECT scope_id FROM project_to_scope WHERE project_id = ?", (project_id,)
        ).fetchall()
        return [UUID(row["scope_id"]) for row in rows]

    def _write_context_scopes(self, project: ProjectRow) -> None:
        scope_ids = {project.main_scope, *project.context_scopes}
        self._conn.execute("DELETE FROM project_to_scope WHERE project_id = ?", (str(project.id),))
        self._conn.executemany(
            "INSERT INTO project_to_scope (project_id, scope_id) VALUES (?, ?)",
            [(str(project.id), str(scope_id)) for scope_id in scope_ids],
        )

    def _to_model(self, row: sqlite3.Row) -> ProjectRow:
        return ProjectRow(
            id=UUID(row["id"]),
            name=row["name"],
            description=row["description"],
            system_prompt=row["system_prompt"],
            team=self._team(row["id"]),
            main_scope=UUID(row["main_scope_id"]),
            context_scopes=self._context_scopes(row["id"]),
        )

    def add(self, project: ProjectRow) -> ProjectRow:
        with self._conn:
            self._conn.execute(
                "INSERT INTO projects (id, name, description, system_prompt, main_scope_id) VALUES (?, ?, ?, ?, ?)",
                (str(project.id), project.name, project.description, project.system_prompt, str(project.main_scope)),
            )
            self._write_context_scopes(project)
        return self.get(project.id)

    def get(self, project_id: UUID) -> ProjectRow | None:
        row = self._conn.execute("SELECT * FROM projects WHERE id = ?", (str(project_id),)).fetchone()
        return self._to_model(row) if row else None

    def get_by_name(self, name: str) -> ProjectRow | None:
        row = self._conn.execute("SELECT * FROM projects WHERE name = ?", (name,)).fetchone()
        return self._to_model(row) if row else None

    def get_by_scope(self, scope_id: UUID) -> ProjectRow | None:
        """Return the project that defines `scope_id`, if any."""
        row = self._conn.execute(
            "SELECT p.* FROM projects p JOIN project_to_scope ps ON ps.project_id = p.id WHERE ps.scope_id = ?",
            (str(scope_id),),
        ).fetchone()
        return self._to_model(row) if row else None

    def list(self) -> list[ProjectRow]:
        rows = self._conn.execute("SELECT * FROM projects ORDER BY name").fetchall()
        return [self._to_model(row) for row in rows]

    def update(self, project: ProjectRow) -> bool:
        with self._conn:
            cur = self._conn.execute(
                "UPDATE projects SET name = ?, description = ?, system_prompt = ?, main_scope_id = ? WHERE id = ?",
                (project.name, project.description, project.system_prompt, str(project.main_scope), str(project.id)),
            )
            if cur.rowcount > 0:
                self._write_context_scopes(project)
        return cur.rowcount > 0

    def delete(self, project_id: UUID) -> bool:
        """Fails with sqlite3.IntegrityError while agents still belong to the project."""
        with self._conn:
            cur = self._conn.execute("DELETE FROM projects WHERE id = ?", (str(project_id),))
        return cur.rowcount > 0
