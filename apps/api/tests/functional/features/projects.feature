Feature: Projects
  A project groups a team of agents that work towards a shared goal.
  Every project gets an empty main context scope when it is created,
  and it can only be deleted once its team is empty.

  Background:
    Given a role "developer"

  Scenario: Creating a project
    When I create the project "Apollo" with the role "developer"
    Then the request succeeds
    And the project "Apollo" offers the role "developer"
    And the main scope of the project "Apollo" contains no resources

  Scenario: Project names are unique
    Given a project "Apollo" with the role "developer"
    When I create the project "Apollo" with the role "developer"
    Then the request fails with status 409
    And the error mentions "already exists"

  Scenario: A project cannot be created with an unknown role
    When I create the project "Apollo" with the role "astronaut"
    Then the request fails with status 404

  Scenario: Deleting an empty project
    Given a project "Apollo" with the role "developer"
    When I delete the project "Apollo"
    Then the request succeeds
    And the project "Apollo" no longer exists

  Scenario: A project with agents cannot be deleted
    Given a project "Apollo" with the role "developer"
    And an agent "alice" with the role "developer" in the project "Apollo"
    When I delete the project "Apollo"
    Then the request fails with status 409
    And the error mentions "still has 1 agent(s)"
