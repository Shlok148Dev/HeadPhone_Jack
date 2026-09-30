@JNG-02-03 @JNG-02-04
Feature: Remove and block (JNG-02-03, JNG-02-04)

  Scenario: Blocking hides everything both ways
    Given Asha and Ravi are friends
    When Asha blocks Ravi
    Then neither sees the other in feed, search, friends or requests
    And Ravi receives no notification of the block

  Scenario: Duplicate request
    Given Ravi has a pending request to Asha
    When Asha sends a request to Ravi
    Then both requests resolve into one accepted friendship
