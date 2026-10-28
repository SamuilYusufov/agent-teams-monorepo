Feature: Roles
  A role is a reusable job description that can be offered in several projects.
  Each role has its own context scope with the resources its agents should use.

  Scenario: Creating a role with resources
    Given a text resource "style guide" containing "Use tabs."
    When I create the role "developer" with the resource "style guide"
    Then the request succeeds
    And the scope of the role "developer" contains:
      | style guide |

  Scenario: Role names are unique
    Given a role "developer"
    When I create the role "developer" with no resources
    Then the request fails with status 409

  Scenario: A role in use cannot be deleted
    Given a role "developer"
    And a project "Apollo" with the role "developer"
    And an agent "alice" with the role "developer" in the project "Apollo"
    When I delete the role "developer"
    Then the request fails with status 409
    And the error mentions "still assigned to agents"

  Scenario: Deleting an unused role
    Given a role "developer"
    When I delete the role "developer"
    Then the request succeeds
    And the role "developer" no longer exists
