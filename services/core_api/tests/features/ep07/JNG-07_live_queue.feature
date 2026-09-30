Feature: Live queue (JNG-07-07, JNG-07-09)
  Scenario: Concurrent votes
    Given 30 participants are in a session
    When 10 of them vote on the same track within one second
    Then all 10 votes count
    And every participant sees the same order within 1 second at p95

  Scenario: Reconnect
    Given my connection drops for 20 seconds
    When it returns
    Then my queue matches the server's within 2 seconds
