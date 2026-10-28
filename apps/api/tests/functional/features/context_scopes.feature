Feature: Context scopes
  Resources are grouped into context scopes. By default an agent gets the resources that are
  in both its project's main scope and its role's scope. An agent can instead be pinned to
  another scope of its project, which may only contain resources from the main scope.

  Background:
    Given a role "developer"
    And a project "Apollo" with the role "developer"
    And a text resource "style guide" containing "Use tabs."
    And a text resource "roadmap" containing "Ship in May."
    And an uploaded file "spec.pdf" with the file ID "file_123"

  Scenario: By default an agent gets the resources shared by its project and role
    Given the main scope of the project "Apollo" contains:
      | style guide |
      | spec.pdf    |
    And the scope of the role "developer" contains:
      | style guide |
      | roadmap     |
      | spec.pdf    |
    And an agent "alice" with the role "developer" in the project "Apollo"
    When I start the agent "alice"
    Then the session of "alice" includes "Use tabs."
    And the session of "alice" mounts the file "file_123"
    But the session of "alice" does not include "Ship in May."

  Scenario: An agent pinned to a scope only gets that scope's resources
    Given the main scope of the project "Apollo" contains:
      | style guide |
      | spec.pdf    |
    And the scope of the role "developer" contains:
      | style guide |
      | spec.pdf    |
    And a scope "docs only" in the project "Apollo" containing:
      | style guide |
    And an agent "alice" with the role "developer" in the project "Apollo"
    When I pin the agent "alice" to the scope "docs only"
    And I start the agent "alice"
    Then the session of "alice" includes "Use tabs."
    But the session of "alice" mounts no files

  Scenario: An agent can only be pinned to a scope of its own project
    Given a project "Gemini" with the role "developer"
    And an empty scope "gemini docs" in the project "Gemini"
    And an agent "alice" with the role "developer" in the project "Apollo"
    When I pin the agent "alice" to the scope "gemini docs"
    Then the request fails with status 409

  Scenario: Project scopes only take resources from the main scope
    Given the main scope of the project "Apollo" contains:
      | style guide |
    And an empty scope "docs only" in the project "Apollo"
    When I add the resource "roadmap" to the scope "docs only"
    Then the request fails with status 409
    And the error mentions "not in the main scope"

  Scenario: Removing a resource from the main scope removes it from every project scope
    Given the main scope of the project "Apollo" contains:
      | style guide |
      | roadmap     |
    And a scope "docs only" in the project "Apollo" containing:
      | style guide |
    When I remove the resource "style guide" from the main scope of the project "Apollo"
    Then the scope "docs only" contains no resources

  Scenario: Agents fall back to the default scope when their scope is deleted
    Given an empty scope "docs only" in the project "Apollo"
    And an agent "alice" with the role "developer" in the project "Apollo"
    And the agent "alice" is pinned to the scope "docs only"
    When I delete the scope "docs only"
    Then the request succeeds
    And the agent "alice" uses the default scope

  Scenario: A project's main scope cannot be deleted on its own
    When I delete the main scope of the project "Apollo"
    Then the request fails with status 409
