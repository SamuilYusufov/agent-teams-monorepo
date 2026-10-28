Feature: Messaging between agents
  Agents can only message each other along links. A link allows one agent to send
  messages of one type to another agent in the same project, in that direction only.

  Background:
    Given a role "developer"
    And a project "Apollo" with the role "developer"
    And an agent "alice" with the role "developer" in the project "Apollo"
    And an agent "bob" with the role "developer" in the project "Apollo"
    And "alice" may send "manager" messages to "bob"
    And the agent "alice" is running

  Scenario: A message along a link is delivered and wakes up the recipient
    When "alice" sends "bob" the "manager" message "Please review the spec."
    Then the message is delivered
    And the agent "bob" is running
    And "bob" receives a message containing "Message from alice (manager)"
    And "bob" receives a message containing "Please review the spec."

  Scenario Outline: Messages of other types are returned to the sender
    When "alice" sends "bob" the "<type>" message "Hi."
    Then the message is not delivered
    And "alice" receives a message containing "only send them messages of these types: ['manager']"
    And the agent "bob" is not running

    Examples:
      | type      |
      | peer      |
      | report    |
      | assistant |

  Scenario: Links only work in one direction
    Given the agent "bob" is running
    When "bob" sends "alice" the "report" message "Done."
    Then the message is not delivered
    And "bob" receives a message containing "not allowed to message them"

  Scenario: Agents see who they can message when they start
    When I start the agent "alice"
    Then the session of "alice" includes "{'bob': ['manager']}"

  Scenario: Agents in different projects cannot be linked
    Given a project "Gemini" with the role "developer"
    And an agent "carol" with the role "developer" in the project "Gemini"
    When I allow "alice" to send "peer" messages to "carol"
    Then the request fails with status 409
    And the error mentions "same project"

  Scenario: Messages to unknown agents fail
    When "alice" sends "nobody" the "manager" message "Hello?"
    Then the request fails with status 404
