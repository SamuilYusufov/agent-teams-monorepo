"""Role management."""
from uuid import UUID

from models.context_scope import ContextScope
from models.roles import AgentRole
from repositories.agent_to_role_repo import AgentToRoleRepository
from repositories.resource_repo import ResourceRepository
from repositories.role_repo import RoleRepository
from repositories.scope_repo import ScopeRepository
from services.errors import ConflictError, NotFoundError


class RoleService:
    """Creates and manages roles together with their default context scopes."""

    def __init__(
            self,
            roles: RoleRepository,
            agent_roles: AgentToRoleRepository,
            scopes: ScopeRepository,
            resources: ResourceRepository,
    ):
        self._roles = roles
        self._agent_roles = agent_roles
        self._scopes = scopes
        self._resources = resources

    def create_role(
            self,
            name: str,
            description: str,
            task_examples: list[str],
            source_examples: list[str],
            resource_ids: list[UUID] | None = None,
    ) -> AgentRole:
        """Create the role together with its default context scope, holding `resource_ids`.

        Raises ConflictError if the name is taken, NotFoundError if a resource doesn't exist.
        """
        if self._roles.get_by_name(name):
            raise ConflictError(f"Role {name!r} already exists")
        resource_ids = resource_ids or []
        if len(self._resources.get_many(resource_ids)) != len(set(resource_ids)):
            raise NotFoundError("Some of the role's resources were not found")

        scope = self._scopes.add(ContextScope(resources=resource_ids))
        try:
            return self._roles.add(
                AgentRole(
                    name=name,
                    description=description,
                    task_examples=task_examples,
                    source_examples=source_examples,
                    context_scope=scope.id,
                )
            )
        except Exception:
            self._scopes.delete(scope.id)
            raise

    def get_role(self, role_id: UUID) -> AgentRole | None:
        return self._roles.get(role_id)

    def get_role_by_name(self, name: str) -> AgentRole | None:
        return self._roles.get_by_name(name)

    def list_roles(self) -> list[AgentRole]:
        """All roles, ordered by name."""
        return self._roles.list()

    def update_role(self, role: AgentRole) -> AgentRole:
        """Update role fields. The context scope stays the same; edit its resources via ScopeService.

        Raises NotFoundError if the role doesn't exist.
        """
        current = self._roles.get(role.id)
        if not current:
            raise NotFoundError(f"Role {role.id} not found")
        role = role.model_copy(update={"context_scope": current.context_scope})
        self._roles.update(role)
        return role

    def delete_role(self, role_id: UUID) -> None:
        """Delete the role and its context scope.

        Raises ConflictError while agents have the role, NotFoundError if it doesn't exist.
        """
        if self._agent_roles.get_agent_ids(role_id):
            raise ConflictError(f"Role {role_id} is still assigned to agents")
        role = self._roles.get(role_id)
        if not role:
            raise NotFoundError(f"Role {role_id} not found")
        self._roles.delete(role_id)
        self._scopes.delete(role.context_scope)
