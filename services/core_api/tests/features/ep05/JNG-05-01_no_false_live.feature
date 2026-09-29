@JNG-05-01
Feature: No false Live (JNG-05-01, BR-01)
  # amended by ADR-0002: labels never name the route; "via" is never sent to clients

  Scenario: Apple Music only
    Given Kabir has only Apple Music linked
    When his card is rendered
    Then its state is RECENT or TOP and never LIVE

  Scenario: Stale now-playing
    Given Kabir's last ListenBrainz playing-now signal is 120 seconds old
    When his card is rendered
    Then its state is RECENT with label "2 min ago"

  Scenario: Card never carries the route
    Given Kabir's Companion now-playing signal is 10 seconds old
    When his card is rendered
    Then its state is LIVE
    And no "via" key appears anywhere in the card JSON
