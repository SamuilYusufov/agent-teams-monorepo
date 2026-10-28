"""Project management and running whole project teams."""
import asyncio
from uuid import UUID

from anthropic.types.beta import BetaManagedAgentsSession

from models.context_scope import ContextScope
from models.projects import Project, ProjectRow
from repositories.project_repo import ProjectRepository
from repositories.project_to_role_repo import ProjectToRoleRepository
from repositories.role_repo import RoleRepository
from repositories.scope_repo import ScopeRepository
from services.agent_service import AgentService
from services.errors import ConflictError, NotFoundError


class ProjectService:
    """Creates and manages projects, the roles available in them, and their team's sessions."""

    def __init__(
            self,
            projects: ProjectRepository,
            project_roles: ProjectToRoleRepository,
            roles: RoleRepository,
            scopes: ScopeRepository,
            agent_service: AgentService,
    ):
        self._projects = projects
        self._project_roles = project_roles
        self._roles = roles
        self._scopes = scopes
        self._agent_service = agent_service

    def _to_project(self, row: ProjectRow) -> Project:
        return Project(
            id=row.id,
            name=row.name,
            description=row.description,
            system_prompt=row.system_prompt,
            team=row.team,
            roles=self._project_roles.get_role_ids(row.id),
            main_scope=row.main_scope,
            context_scopes=row.context_scopes,
        )

    def _require_project(self, project_id: UUID) -> Project:
        project = self.get_project(project_id)
        if not project:
            raise NotFoundError(f"Project {project_id} not found")
        return project

    def _require_role(self, role_id: UUID) -> None:
        if not self._roles.get(role_id):
            raise NotFoundError(f"Role {role_id} not found")

    # Projects

    def create_project(
            self,
            name: str,
            description: str,
            system_prompt: str,
            role_ids: list[UUID] | None = None,
    ) -> Project:
        """Create the project together with an empty main scope. Add resources via ScopeService.

        Raises ConflictError if the name is taken, NotFoundError if a role doesn't exist.
        """
        if self._projects.get_by_name(name):
            raise ConflictError(f"Project {name!r} already exists")
        role_ids = role_ids or []
        for role_id in role_ids:
            self._require_role(role_id)

        scope = self._scopes.add(ContextScope(resources=[]))
        try:
            row = self._projects.add(
                ProjectRow(
                    name=name,
                    description=description,
                    system_prompt=system_prompt,
                    team=[],
                    main_scope=scope.id,
                    context_scopes=[scope.id],
                )
            )
        except Exception:
            self._scopes.delete(scope.id)
            raise
        for role_id in role_ids:
            self._project_roles.link(row.id, role_id)
        return self._to_project(row)

    def get_project(self, project_id: UUID) -> Project | None:
        row = self._projects.get(project_id)
        return self._to_project(row) if row else None

    def get_project_by_name(self, name: str) -> Project | None:
        row = self._projects.get_by_name(name)
        return self._to_project(row) if row else None

    def list_projects(self) -> list[Project]:
        """All projects, ordered by name."""
        return [self._to_project(row) for row in self._projects.list()]

    def update_project(self, project: Project) -> Project:
        """Update project fields and sync available roles.

        `team` is managed via AgentService, scopes via ScopeService.
        Raises NotFoundError if the project or a role doesn't exist.
        """
        current = self._projects.get(project.id)
        if not current:
            raise NotFoundError(f"Project {project.id} not found")
        for role_id in project.roles:
            self._require_role(role_id)
        row = current.model_copy(
            update={
                "name": project.name,
                "description": project.description,
                "system_prompt": project.system_prompt,
            }
        )
        self._projects.update(row)

        current_roles = set(self._project_roles.get_role_ids(project.id))
        wanted_roles = set(project.roles)
        for role_id in wanted_roles - current_roles:
            self._project_roles.link(project.id, role_id)
        for role_id in current_roles - wanted_roles:
            self._project_roles.unlink(project.id, role_id)
        return self.get_project(project.id)

    def delete_project(self, project_id: UUID) -> None:
        """Delete the project and all of its context scopes.

        Raises ConflictError while agents belong to the project, NotFoundError if it doesn't exist.
        """
        project = self._require_project(project_id)
        if project.team:
            raise ConflictError(f"Project {project_id} still has {len(project.team)} agent(s)")
        self._projects.delete(project_id)
        for scope_id in project.context_scopes:
            self._scopes.delete(scope_id)

    # Roles

    def add_role(self, project_id: UUID, role_id: UUID) -> Project:
        """Make the role available in the project. Raises NotFoundError if either doesn't exist."""
        self._require_project(project_id)
        self._require_role(role_id)
        self._project_roles.link(project_id, role_id)
        return self.get_project(project_id)

    def remove_role(self, project_id: UUID, role_id: UUID) -> Project:
        """Remove the role from the project. Raises NotFoundError if the project doesn't exist."""
        self._require_project(project_id)
        self._project_roles.unlink(project_id, role_id)
        return self.get_project(project_id)

    # Sessions

    async def start(self, project_id: UUID) -> list[BetaManagedAgentsSession]:
        """Start a session for every agent in the project team. Raises NotFoundError if it doesn't exist."""
        project = self._require_project(project_id)
        return list(await asyncio.gather(*(self._agent_service.start(agent_id) for agent_id in project.team)))

    async def stop(self, project_id: UUID) -> None:
        """Archive the live sessions of every agent in the project team. Raises NotFoundError if it doesn't exist."""
        project = self._require_project(project_id)
        await asyncio.gather(*(self._agent_service.stop(agent_id) for agent_id in project.team))
