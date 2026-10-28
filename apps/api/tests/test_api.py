import sqlite3

import pytest
from fastapi.testclient import TestClient

from api import create_app
from services.errors import ConflictError, NotFoundError


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (NotFoundError("missing"), 404),
        (ConflictError("conflict"), 409),
        (sqlite3.IntegrityError("constraint"), 409),
    ],
)
def test_error_handlers(error, status_code):
    app = create_app()

    @app.get("/boom")
    async def boom():
        raise error

    response = TestClient(app).get("/boom")
    assert response.status_code == status_code
    assert response.json() == {"detail": str(error)}


def test_all_routers_are_mounted():
    paths = create_app().openapi()["paths"]
    for prefix in ("/api/project", "/api/role", "/api/agent", "/api/resource", "/api/scope/{scope_id}"):
        assert prefix in paths
