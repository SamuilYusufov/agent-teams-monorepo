import pytest


def check(response, status_code=200):
    """Assert the status code and return the JSON body, if any."""
    assert response.status_code == status_code, response.text
    return response.json() if response.content else None


@pytest.fixture
def role(http):
    return check(http.post("/api/role", json={"name": "dev", "description": "Writes code"}), 201)


@pytest.fixture
def project(http, role):
    body = {"name": "proj", "description": "d", "system_prompt": "Prompt.", "role_ids": [role["id"]]}
    return check(http.post("/api/project", json=body), 201)


@pytest.fixture
def create_agent(http, role, project):
    def create(name: str, **extra):
        body = {"name": name, "role_id": role["id"], "project_id": project["id"], **extra}
        return check(http.post("/api/agent", json=body), 201)

    return create
