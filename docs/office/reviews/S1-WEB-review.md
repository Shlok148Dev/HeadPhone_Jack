# S1-WEB combined review (Orchestrator, against design-system, code and security checklists)

Screens: landing, sign-up, sign-in, onboarding (sources), home, settings/connections, connect/companion, friends placeholder — dark + light × 1440 + 390 (`artifacts/screenshots/s1/`, 32 files).

- Design: both themes render; coral only on Live; gradient only on primary actions; platform names as text badges; Blip in empty states; no horizontal scroll. Fixed: own card was full-width on mobile (now ≤ 240/280 px, the NowPlayingBar already shows it); removed developer copy on Home.
- A11y: axe clean on sign-up, home, connections after fixing the toast live region (`role="region"`).
- Code: auth token in memory only, single-flight refresh, safe `next` redirect, error envelope mapping; unit tests 94; E2E JNG-01-01 (2 scenarios) and JNG-05-01 (2 scenarios) green.
- Security: nonce CSP site-wide, `frame-ancestors 'none'`; `/connect/companion` loads no third-party origin; token minted only on click and consent-gated (409 CONSENT_REQUIRED); same-origin postMessage checks.
- Known limits: refresh rotation race across two tabs (STATE R-E); Google button untested live until HA-3.

VERDICT: APPROVED
