@JNG-04-01 @JNG-04-05
Feature: Circle limits and suggestions (JNG-04-01, JNG-04-05)

  Scenario: Full circle
    Given a circle has 50 members
    When someone opens its invite link
    Then they see "This circle is full" and are not added

  Scenario: Suggested circle is never auto-joined
    Given the circle detector finds 5 friends with shared taste
    When it suggests the circle to one of them
    Then no one is added until each person accepts an invite
