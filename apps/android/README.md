# Jingle for Android

Jingle (the web app) in a native shell, plus the one thing a website can't do on a phone: see what
Spotify, YouTube Music, Amazon Music or Apple Music is playing, through Android's official
media-session API (D-CONNECT-01).

What the listener does: install, sign in to Jingle, tap their music app, turn on one toggle
("notification access" for Jingle). Plays then go to the same endpoint as the browser extension
(`/ingest/1/submit-listens`, ListenBrainz format) with a scrobble token stored encrypted on the phone.

- `PlayListener.kt`: media sessions of the four music apps only; "playing now" every 45 s while
  playing (Live = signal under 90 s old), a listen at half the song or 4 minutes.
- `MainActivity.kt`: WebView of Jingle; `window.JingleAndroid` bridge offered only to Jingle's origin.
- `TokenStore.kt`: EncryptedSharedPreferences (Android Keystore). The token is never logged.

## Build

Needs the Android SDK (Android Studio installs it) and JDK 17.

```bash
gradle wrapper
./gradlew assembleDebug                                  # emulator, Jingle at http://10.0.2.2:8080
./gradlew assembleRelease -PjingleUrl=https://jingle.example
```

Publishing: Google Play Console (one-time US$25). Set `ANDROID_APP_URL` in `.env` to the Play link
so the web Connect screen offers "Get the Jingle app" on Android phones. See HUMAN_ACTIONS (HA-CONNECT-4).
