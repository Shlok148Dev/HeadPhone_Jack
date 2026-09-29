# ADR-0011: Auth tokens and sessions

- Status: Accepted
- Date: 2026-09-29

SimpleJWT with HS256: access token 15 minutes, held in memory (NFR-SEC-03); refresh token 14 days in an HttpOnly, SameSite=Lax cookie `jingle_refresh` (Secure outside local), rotated and blacklisted on use. Argon2id password hashing (Technical Bible 9.1). Google sign-in uses Google Identity Services: the browser gets an ID token and core-api verifies it server-side; the button is hidden unless `GOOGLE_OAUTH_CLIENT_ID` is set. Sign-up requires age 18 or over (NFR-PRIV-02), checked from birth year.
