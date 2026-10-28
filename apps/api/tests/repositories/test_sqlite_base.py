from repositories.sqlite_base import connect, init_schema

TABLES = {
    "resources",
    "context_scopes",
    "scope_to_resource",
    "roles",
    "projects",
    "project_to_scope",
    "agents",
    "agent_links",
    "project_to_role",
}


def test_connect_creates_all_tables(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    assert {row["name"] for row in rows} >= TABLES


def test_connect_enables_foreign_keys(conn):
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_init_schema_is_idempotent(conn):
    init_schema(conn)
    init_schema(conn)


def test_connect_to_file_persists(tmp_path):
    path = tmp_path / "agents.db"
    first = connect(path)
    with first:
        first.execute("INSERT INTO context_scopes (id) VALUES ('scope')")
    first.close()

    second = connect(path)
    assert second.execute("SELECT id FROM context_scopes").fetchone()["id"] == "scope"
    second.close()
