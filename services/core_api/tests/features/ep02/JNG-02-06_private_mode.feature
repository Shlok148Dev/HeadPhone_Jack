@JNG-02-06
Feature: Private mode (JNG-02-06)

  Scenario: Private mode hides my card from friends
    Given Asha and Ravi are friends
    And Asha is Live on Spotify
    When Asha turns on Private mode for 1 hour
    Then Ravi sees Asha's card as HIDDEN with no recording
    And Asha still sees her own card as LIVE
