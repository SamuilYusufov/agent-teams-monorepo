import pytest


@pytest.fixture
def role(services):
    return services.roles.create_role("dev", "Writes code", ["fix bugs"], ["docs"])


@pytest.fixture
def project(services, role):
    return services.projects.create_project("proj", "A project", "Project prompt.", [role.id])


@pytest.fixture
def create_agent(services, role, project):
    """Create an agent in `project` with `role` through AgentService."""

    async def create(name: str, context_scope=None):
        return await services.agents.create_agent(
            name, role, services.projects.get_project(project.id), context_scope
        )

    return create
