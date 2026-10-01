@JNG-01-01
Feature: Sign up and stay signed in (JNG-01-01, NFR-PRIV-02, ADR-0011)

  Scenario: Under-18 sign-up is rejected
    Given a visitor born 16 years ago
    When they sign up with email
    Then the sign-up is rejected with code "AGE_RESTRICTED"
    And no account is created

  Scenario: Refresh token rotation
    Given a signed-in member with a refresh cookie
    When the web app refreshes the session
    Then it receives a new access token and a new refresh cookie
    And the old refresh cookie is rejected once its 30-second grace has passed
