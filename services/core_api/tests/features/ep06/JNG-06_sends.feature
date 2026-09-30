Feature: Cross-platform send (JNG-06-03)
  Scenario: Spotify track to an Apple Music friend
    Given Riya sends a track resolved to a Recording with an ISRC
    When Dev, who uses Apple Music, opens it
    Then the Open button deep-links to the Apple Music version

  Scenario: No match on the friend's platform
    Given the Recording has no Apple Music link
    When Dev opens it
    Then he sees "Not found on Apple Music" and a search link
