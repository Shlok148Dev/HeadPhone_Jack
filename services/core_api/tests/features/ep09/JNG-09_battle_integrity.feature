Feature: Battle integrity (JNG-09-02)
  Scenario: Late vote
    Given voting closed at 21:00 IST on Sunday
    When a vote arrives at 21:00:05
    Then it is rejected with "Voting has closed"
    And the leaderboard is unchanged
