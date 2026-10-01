Feature: Explained score (JNG-08-01, JNG-08-02)
  Scenario: Audio features unavailable
    Given neither friend has tracks with analysed preview audio
    When the score is shown
    Then the breakdown says "Sound comparison unavailable" and no audio numbers appear
