@JNG-01-13
Feature: Point a scrobbler at Jingle's push endpoint (JNG-01-13)
  As a member on any platform, I want to point my scrobbler app at Jingle's push endpoint,
  so that I show as Live within seconds.
  # Scenarios written for Sprint 1 per ADR-0003 (Companion push first); SRS §6 has no
  # Gherkin for JNG-01-13 yet.

  Scenario: Push playing-now shows Live within seconds
    Given a user with a Jingle scrobble token
    When the Companion sends playing_now for a YouTube Music track
    Then np:{user} exists with platform YOUTUBE_MUSIC and observed_at within 2 s

  Scenario: Unknown token is rejected
    Given a user with a Jingle scrobble token
    When a scrobbler sends playing_now with an unknown token
    Then the response is 401 in ListenBrainz error format
    And nothing is written for the user
