# ADR-0011: Auth tokens and sessions

- Status: Accepted
- Date: 2026-09-29

SimpleJWT with HS256: access token 15 minutes, held in memory (NFR-SEC-03); refresh token 14 days in an HttpOnly, SameSite=Lax cookie `jingle_refresh` (Secure outside local), rotated and blacklisted on use. Argon2id password hashing (Technical Bible 9.1). Google sign-in uses Google Identity Services: the browser gets an ID token and core-api verifies it server-side; the button is hidden unless `GOOGLE_OAUTH_CLIENT_ID` is set. Sign-up requires age 18 or over (NFR-PRIV-02), checked from birth year.

## Addendum (2026-10-01, Sprint 11)
A rotated refresh token is still accepted for **30 s** after it was rotated by a refresh (not after logout). A page that navigates while its refresh is in flight never stores the new cookie and would otherwise sign the person out (risk R-E, seen as 69 refresh 401s in a full E2E run). The window is tracked in Redis (`refresh:grace:{jti}`, set only by a refresh). Without Redis there is no grace. The trade-off is a 30 s replay window for a stolen cookie, which is accepted for the pilot. The scenario in `JNG-01-01_sign_up.feature` was amended to match.

