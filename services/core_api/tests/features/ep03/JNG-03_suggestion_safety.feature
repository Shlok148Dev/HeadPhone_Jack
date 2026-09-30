@JNG-03-01 @JNG-03-06
Feature: Suggestion safety (JNG-03-01, JNG-03-06)

  Scenario: Excluded people never appear
    Given Meera and Arjun share two mutual friends and the same taste
    And Meera has blocked Arjun, or Arjun turned discoverability off, or Meera dismissed Arjun 30 days ago
    When Meera's suggestions are generated
    Then Arjun is not in the list

  Scenario: Reasons never leak private listening
    Given Arjun has Private mode on
    When Arjun appears as a suggestion for Meera
    Then the reasons use only public profile data and mutual-friend counts
    And no track, artist or listening time from Arjun is shown

  Scenario: Minors and adults
    Given Meera is 16 and Arjun is 24
    When suggestions are generated for either
    Then neither appears in the other's suggestions
