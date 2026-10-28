Feature: Agents
  An agent works in one project with one role, and runs in at most one live session at a time.

  Background:
    Given a role "developer"
    And a project "Apollo" with the role "developer"

  Scenario: Adding an agent to a project team
    When I create an agent "alice" with the role "developer" in the project "Apollo"
    Then the request succeeds
    And the team of the project "Apollo" is:
      | alice |

  Scenario: An agent's role must be offered by its project
    Given a role "designer"
    When I create an agent "alice" with the role "designer" in the project "Apollo"
    Then the request fails with status 409
    And the error mentions "not available in project"

  Scenario: Agent names are unique
    Given an agent "alice" with the role "developer" in the project "Apollo"
    When I create an agent "alice" with the role "developer" in the project "Apollo"
    Then the request fails with status 409

  Scenario: Starting an agent twice keeps its session
    Given an agent "alice" with the role "developer" in the project "Apollo"
    When I start the agent "alice"
    And I start the agent "alice"
    Then the agent "alice" has exactly one live session

  Scenario: Stopping an agent
    Given an agent "alice" with the role "developer" in the project "Apollo"
    And the agent "alice" is running
    When I stop the agent "alice"
    Then the request succeeds
    And the agent "alice" is not running

  Scenario: Starting and stopping a whole project
    Given an agent "alice" with the role "developer" in the project "Apollo"
    And an agent "bob" with the role "developer" in the project "Apollo"
    When I start the project "Apollo"
    Then the agent "alice" is running
    And the agent "bob" is running
    When I stop the project "Apollo"
    Then the agent "alice" is not running
    And the agent "bob" is not running

  Scenario: Deleting an agent stops it and removes it from its team
    Given an agent "alice" with the role "developer" in the project "Apollo"
    And the agent "alice" is running
    When I delete the agent "alice"
    Then the request succeeds
    And the agent "alice" is not running
    And the team of the project "Apollo" is empty
