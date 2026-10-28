import sqlite3
from uuid import uuid4

import pytest

from models.projects import ProjectRow


def test_add_returns_stored_project(repos, seed):
    scope = seed.scope()
    project = repos.projects.add(
        ProjectRow(name="p", description="d", system_prompt="s", team=[], main_scope=scope.id, context_scopes=[])
    )
    assert project.main_scope == scope.id
    # The main scope is always part of the project's context scopes.
    assert project.context_scopes == [scope.id]
    assert repos.projects.get(project.id) == project


def test_add_requires_existing_main_scope(repos):
    with pytest.raises(sqlite3.IntegrityError):
        repos.projects.add(ProjectRow(name="p", description="d", system_prompt="s", team=[], context_scopes=[]))


def test_get_missing_returns_none(repos):
    assert repos.projects.get(uuid4()) is None


def test_get_by_name(repos, seed):
    project = seed.project("p")
    assert repos.projects.get_by_name("p") == project
    assert repos.projects.get_by_name("nope") is None


def test_get_by_scope(repos, seed):
    project = seed.project()
    extra = seed.scope()
    repos.projects.update(project.model_copy(update={"context_scopes": [project.main_scope, extra.id]}))
    assert repos.projects.get_by_scope(project.main_scope).id == project.id
    assert repos.projects.get_by_scope(extra.id).id == project.id
    assert repos.projects.get_by_scope(seed.scope().id) is None


def test_list_orders_by_name(repos, seed):
    b, a = seed.project("b"), seed.project("a")
    assert [p.id for p in repos.projects.list()] == [a.id, b.id]


def test_team_is_derived_from_agents(repos, seed):
    project, role = seed.project(), seed.role()
    bob = seed.agent(project, role, "bob")
    alice = seed.agent(project, role, "alice")
    assert repos.projects.get(project.id).team == [alice.id, bob.id]


def test_update_changes_fields_and_scopes(repos, seed):
    project = seed.project()
    new_main, extra = seed.scope(), seed.scope()
    changed = project.model_copy(
        update={"name": "renamed", "system_prompt": "new", "main_scope": new_main.id, "context_scopes": [extra.id]}
    )
    assert repos.projects.update(changed) is True
    stored = repos.projects.get(project.id)
    assert (stored.name, stored.system_prompt, stored.main_scope) == ("renamed", "new", new_main.id)
    assert set(stored.context_scopes) == {new_main.id, extra.id}


def test_update_missing_returns_false(repos, seed):
    scope = seed.scope()
    row = ProjectRow(name="ghost", description="d", system_prompt="s", team=[], main_scope=scope.id, context_scopes=[])
    assert repos.projects.update(row) is False
    assert repos.projects.get_by_scope(scope.id) is None


def test_scope_belongs_to_one_project(repos, seed):
    shared = seed.scope()
    seed.project("a", main_scope=shared)
    with pytest.raises(sqlite3.IntegrityError):
        seed.project("b", main_scope=shared)


def test_delete_unlinks_scopes(repos, seed):
    project = seed.project()
    assert repos.projects.delete(project.id) is True
    assert repos.projects.get(project.id) is None
    assert repos.projects.get_by_scope(project.main_scope) is None
    assert repos.projects.delete(project.id) is False


def test_delete_fails_while_agents_belong_to_project(repos, seed):
    project = seed.project()
    seed.agent(project, seed.role())
    with pytest.raises(sqlite3.IntegrityError):
        repos.projects.delete(project.id)
