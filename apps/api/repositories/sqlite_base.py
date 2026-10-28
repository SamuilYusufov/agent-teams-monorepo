"""SQLite schema and connection setup shared by the SQLite repositories."""
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS resources (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    type              TEXT NOT NULL CHECK (type IN ('file', 'text', 'url')),
    storage           TEXT NOT NULL CHECK (storage IN ('in_place', 'anthropic_managed')),
    content           TEXT,
    anthropic_file_id TEXT
);

CREATE TABLE IF NOT EXISTS context_scopes (
    id TEXT PRIMARY KEY
);

-- Resources inside a context scope (many-to-many).
CREATE TABLE IF NOT EXISTS scope_to_resource (
    scope_id    TEXT NOT NULL REFERENCES context_scopes(id) ON DELETE CASCADE,
    resource_id TEXT NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    PRIMARY KEY (scope_id, resource_id)
);
CREATE INDEX IF NOT EXISTS idx_scope_to_resource_resource_id ON scope_to_resource(resource_id);

CREATE TABLE IF NOT EXISTS roles (
    id               TEXT PRIMARY KEY,
    name             TEXT NOT NULL UNIQUE,
    description      TEXT NOT NULL,
    task_examples    TEXT NOT NULL,
    source_examples  TEXT NOT NULL,
    context_scope_id TEXT NOT NULL REFERENCES context_scopes(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS projects (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    description   TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    main_scope_id TEXT NOT NULL REFERENCES context_scopes(id) ON DELETE RESTRICT
);

-- Context scopes defined inside a project, including its main scope. Each scope belongs to one project.
CREATE TABLE IF NOT EXISTS project_to_scope (
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scope_id   TEXT NOT NULL UNIQUE REFERENCES context_scopes(id) ON DELETE CASCADE,
    PRIMARY KEY (project_id, scope_id)
);

-- Each agent belongs to exactly one project and has exactly one role.
-- A NULL context_scope_id means the agent uses the intersection of its project's main scope and its role's scope.
CREATE TABLE IF NOT EXISTS agents (
    id               TEXT PRIMARY KEY,
    anthropic_id     TEXT NOT NULL UNIQUE,
    name             TEXT NOT NULL UNIQUE,
    project_id       TEXT NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    role_id          TEXT NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    context_scope_id TEXT REFERENCES context_scopes(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_agents_project_id ON agents(project_id);
CREATE INDEX IF NOT EXISTS idx_agents_role_id ON agents(role_id);

-- Directed links between agents: from_agent may send messages of `type` to to_agent.
CREATE TABLE IF NOT EXISTS agent_links (
    id            TEXT PRIMARY KEY,
    from_agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    to_agent_id   TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    type          TEXT NOT NULL CHECK (type IN ('report', 'manager', 'peer', 'assistant')),
    UNIQUE (from_agent_id, to_agent_id, type)
);
CREATE INDEX IF NOT EXISTS idx_agent_links_to_agent_id ON agent_links(to_agent_id);

-- Roles available inside a project (many-to-many).
CREATE TABLE IF NOT EXISTS project_to_role (
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    role_id    TEXT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (project_id, role_id)
);
CREATE INDEX IF NOT EXISTS idx_project_to_role_role_id ON project_to_role(role_id);
"""


def init_schema(conn: sqlite3.Connection) -> None:
    with conn:
        conn.executescript(SCHEMA)


def connect(path: str | Path = ":memory:") -> sqlite3.Connection:
    """Open a SQLite connection configured for the repositories, creating tables if needed."""
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    return conn
