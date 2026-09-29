# Jingle — Development Plan (Agile/Scrum)

Sep 29, 2026 · @Shlok

## 1. Team, roles and Scrum operating model

A 3-person team runs 2-week Scrum sprints from 5 October 2026 to a
public launch on 14 March 2027, with AI-assisted development raising
each person's throughput but never replacing review.

### 1.1 Roles

The Scrum Guide has three accountabilities; in a team of three, each
person also owns a technical area. Roles rotate at release boundaries if
the team wants breadth.

| Person           | Scrum accountability      | Technical ownership                                                                     |
|------------------|---------------------------|-----------------------------------------------------------------------------------------|
| Member A (Shlok) | Product Owner             | ingest-ml: adapters, identity, push ingestion; ML (suggestions, compatibility, Blends)  |
| Member B         | Scrum Master              | core-api (Django): social graph, circles, rituals, moderation; infrastructure and CI/CD |
| Member C         | Developer lead for client | Next.js web app, design system, realtime gateway, accessibility                         |
| Faculty guide    | Stakeholder               | Sprint reviews; academic gates                                                          |

Everyone is a Developer in Scrum terms and picks up work outside their
area when the sprint needs it.

### 1.2 Events and cadence (2-week sprint)

| Event              | When                                           | Length | Output                                                            |
|--------------------|------------------------------------------------|--------|-------------------------------------------------------------------|
| Sprint planning    | Monday, week 1, 10:00                          | 90 min | Sprint Goal and Sprint Backlog                                    |
| Daily Scrum        | Every weekday, 21:30 (async text on exam days) | 15 min | Plan for the next 24 h; blockers raised                           |
| Backlog refinement | Thursday, week 1                               | 60 min | Next sprint's stories meet the Definition of Ready                |
| Sprint review      | Friday, week 2, 17:00                          | 45 min | Demo on staging to the guide; backlog updated; SRS revision entry |
| Retrospective      | Friday, week 2, after review                   | 30 min | One improvement action for the next sprint                        |

### 1.3 Artefacts and commitments

| Artefact        | Commitment                           | Where                              |
|-----------------|--------------------------------------|------------------------------------|
| Product Backlog | Product Goal (SRS Section 3.1)       | GitHub Projects board              |
| Sprint Backlog  | Sprint Goal, one sentence            | Same board, sprint iteration field |
| Increment       | Definition of Done (SRS Section 3.4) | Deployed to staging every merge    |

### 1.4 Capacity

A normal sprint gives each person about 30 focused hours (15 a week
alongside classes), so 90 team-hours. Exam sprints (S5 and S6) are
planned at 50%. Planned velocity starts at 24 story points and is
re-based on the average of the last three sprints from Sprint 4.

## 2. Product backlog

The backlog holds 105 stories in 13 epics; the Must stories needed for
launch total about 258 story points, which fits the 268 points of
planned capacity to Sprint 11 with a thin margin, so Should and Could
stories wait for Release 3.

### 2.1 Epics

| Epic                              | Stories | Must points (estimate) | Release |
|-----------------------------------|---------|------------------------|---------|
| EP-01 Accounts and sources        | 13      | 34                     | R0–R1   |
| EP-02 Social graph and privacy    | 8       | 18                     | R1      |
| EP-03 Friend suggestions          | 8       | 21                     | R1      |
| EP-04 Friend circles              | 8       | 21                     | R1      |
| EP-05 Activity feed               | 8       | 26                     | R0–R1   |
| EP-06 Recommendations             | 7       | 18                     | R1      |
| EP-07 Blends and sessions         | 9       | 29                     | R2      |
| EP-08 Compatibility and analytics | 7       | 13                     | R2      |
| EP-09 Rituals                     | 9       | 21                     | R2      |
| EP-10 Concerts                    | 5       | 5                      | R2      |
| EP-11 Notifications               | 7       | 13                     | R1–R2   |
| EP-12 Admin and moderation        | 8       | 18                     | R1–R2   |
| EP-13 Platform qualities          | 8       | 21                     | R0–R2   |

### 2.2 Story map

The backbone is the user's journey; each release row takes a thin,
working slice across it.

| Release | Join        | Connect                   | Find friends                                                        | See                             | Share               | Together        | Understand            | Come back                                           |
|---------|-------------|---------------------------|---------------------------------------------------------------------|---------------------------------|---------------------|-----------------|-----------------------|-----------------------------------------------------|
| R0      | JNG-01-01   | JNG-01-02, JNG-01-13      | —                                                                   | JNG-05-01 (own card), JNG-05-08 | —                   | —               | —                     | —                                                   |
| R1      | JNG-01-12   | JNG-01-03, 05, 06, 09, 11 | JNG-02-01 to 05, JNG-03-01 to 03, 05 to 07, JNG-04-01 to 04, 06, 08 | JNG-05-02 to 04, 06, 07         | JNG-06-01 to 04, 07 | —               | —                     | JNG-11-01 to 03                                     |
| R2      | JNG-01-10   | JNG-01-04                 | JNG-03-08, JNG-04-05, 07                                            | JNG-05-05                       | JNG-06-05, 06       | JNG-07-01 to 09 | JNG-08-01, 02, 06, 07 | JNG-09-01 to 03, 05, 06; JNG-10-01 to 04; JNG-11-07 |
| R3      | Mobile apps | JNG-01-07, 08             | Learned ranker                                                      | —                               | JNG-11-06           | —               | JNG-08-03 to 05       | JNG-09-04, 07 to 09; JNG-10-05; JNG-11-04, 05       |

New in this plan: **JNG-01-13** — "As a member, I want to point my
scrobbler app at Jingle directly, so that I show as Live within seconds"
(Must), from the Technical Bible's push-ingestion design.

### 2.3 Estimation

- Planning poker with Fibonacci points (1, 2, 3, 5, 8, 13); anything
  above 8 is split.

- Reference story: JNG-02-02 (friend requests, full stack with tests) =
  5 points.

- Spikes (time-boxed research) are 1–2 days and produce an ADR, not
  points.

- Velocity is reviewed at every retrospective; the release plan is
  re-forecast from the 3-sprint average.

## 3. Release roadmap and sprint plan

Twelve sprints take Jingle from an empty repository to a public launch
on 14 March 2027, with a 100-person closed beta opening on 11 January
2027.

**Phases.** Phase 1 is a web app only. It starts as a 10-user pilot
after Sprint 2 that needs no approval from any company: Spotify through
5 direct slots and Spotify's built-in Last.fm link, and all four
platforms through the Jingle Companion browser extension (installed
unpacked for the pilot). Apple Music, Amazon Music and Google
data-portability integrations are built behind flags and switched on
only when their approvals arrive. The beta (100 users) and public launch
stay web-only; Android and iOS apps and store publishing are Phase 2
(Release 3).

<img src="media/image1.png" style="width:6in;height:3.91071in"
alt="sprint calendar, planned; exam dates to confirm against the KJSCE academic calendar" />

sprint calendar, planned; exam dates to confirm against the KJSCE
academic calendar

The two exam sprints carry only small, low-risk stories, and Sprint 7
over the winter break carries the beta-readiness push.

### 3.1 Sprint goals

1.  **S1 Foundations:** monorepo, CI/CD, Docker Compose, staging
    cluster, /design route with tokens and card variants, email and
    Google sign-up (JNG-01-01).

2.  **S2 Push ingest and bridges:** ListenBrainz-compatible push
    endpoint (JNG-01-13), ListenBrainz and Last.fm linking (JNG-01-02),
    identity resolver v1, the user's own now-playing card. **R0 gate:**
    staging stable for 7 days.

3.  **S3 Social graph:** search, requests, remove, block, report,
    privacy settings (JNG-02-01 to 05).

4.  **S4 Live feed:** realtime gateway, Live/Recent/Top cards, Live
    shelf, degraded mode (JNG-05-01 to 07).

5.  **S5 Suggestions (half capacity):** friends-of-friends and
    taste-twin suggestions, dismiss, discoverability (JNG-03-01 to 03,
    05 to 07).

6.  **S6 Circles (half capacity):** create, invite links, roles, circle
    feed (JNG-04-01 to 04, 06, 08).

7.  **S7 Sends and beta prep:** recommendations and inbox (JNG-06-01 to
    04, 07), Apple Music link, YouTube import, onboarding flow, in-app
    notifications, moderation queue v1. **R1 gate:** beta readiness
    review.

8.  **S8 Blends:** Blend generation with reasons, regenerate, save to
    platform (JNG-07-01 to 04).

9.  **S9 Sessions and battles:** live sessions with votes (JNG-07-05 to
    09), weekly battle state machine (JNG-09-01 to 03).

10. **S10 Compatibility and load test:** explained score, stats, recap
    (JNG-08-01, 02, 06, 07; JNG-09-05, 06); full k6 run at 5,000 users.

11. **S11 Hardening:** fix load-test findings, security scan,
    accessibility pass, concerts (JNG-10-01 to 04), push notifications.

12. **S12 Launch:** launch checklist (section 7), campus launch event,
    on-call rota. **R2 gate:** all Must NFRs met.

Release 3 (from 22 March 2027) continues in 2-week sprints with mobile
apps, the learned suggestion ranker, and remaining Should and Could
stories.

## 4. Platform access and approvals timeline

Spotify is Jingle's core platform, so every Spotify-related access
request starts in Sprint 1: the Last.fm commercial agreement (which
carries Spotify listeners at scale), the Spotify developer app for 5
testers, and the company registration that Spotify's Extended Quota
requires.

### 4.1 How Spotify users get the full Jingle experience

Direct Spotify API access is capped at 5 users for a new app (owner must
have Premium) and Extended Quota needs a registered business with
250,000 MAU. So Spotify listeners reach Jingle through three paths, in
order of preference, and all three give Live, Recent and Top:

1.  **Spotify → Last.fm (built into Spotify).** One toggle in Spotify
    links Last.fm; scrobbling then runs from every device, iPhone
    included. Jingle reads Last.fm. This is why the Last.fm commercial
    agreement is the top access item.

2.  **Push to Jingle.** On Android (Pano Scrobbler) and desktop or web
    (Web Scrobbler), Spotify plays post straight to Jingle's push
    endpoint: Live within seconds, no rate limit.

3.  **Direct Spotify link.** Built and contract-tested from Sprint 2
    with the 5 allowlisted testers, so it can be switched on for
    everyone the day Extended Quota is granted.

Apple Music, Amazon Music and YouTube Music listeners use the same push
and bridge paths, plus their own direct links where available.

### 4.2 Access actions

| Action                                                                                | Owner                        | Start                       | Expected lead time                              | Blocks                                                 |
|---------------------------------------------------------------------------------------|------------------------------|-----------------------------|-------------------------------------------------|--------------------------------------------------------|
| Request a Last.fm commercial-use agreement and higher rate limit (partners@last.fm)   | Member A                     | S1                          | Weeks; not guaranteed                           | Spotify users at scale; model training on Last.fm data |
| Create Spotify developer app; allowlist 5 testers (owner on Premium)                  | Member A                     | S1                          | Same day                                        | Spotify adapter tests                                  |
| Ask Spotify in writing about Policy III.5 for a multi-platform product                | Member A                     | S1                          | Weeks                                           | Opening the direct Spotify link widely                 |
| Register a legal entity (LLP or private limited)                                      | Member A, with faculty guide | S7                          | 2–4 weeks                                       | Spotify Extended Quota application; Last.fm agreement  |
| Apply for Spotify Extended Quota                                                      | Member A                     | When MAU approaches 250,000 | Spotify review                                  | Direct Spotify for all users                           |
| Enrol in the Apple Developer Program (USD 99 a year)                                  | Member B                     | S1                          | 1–2 weeks                                       | Apple Music linking                                    |
| Request Amazon Music Web API access through Amazon business development               | Member A                     | S1                          | Unknown                                         | Direct Amazon link (flag stays off until then)         |
| Google OAuth verification for the restricted dataportability.myactivity.youtube scope | Member B                     | S7                          | Weeks to months, may need a security assessment | Automatic YouTube exports (JNG-01-07)                  |
| Verify custom-endpoint support in Web Scrobbler and Pano Scrobbler                    | Member C                     | S2 spike                    | 2 days                                          | Push onboarding copy                                   |
| Firebase project for push                                                             | Member C                     | S3                          | Same day                                        | Push notifications                                     |
| Ticketmaster Discovery API key                                                        | Member B                     | S10                         | Same day                                        | Concerts                                               |

If the Last.fm agreement has not arrived by the beta (11 January 2027),
the beta stays within the default Last.fm budget (about 240
Spotify-via-Last.fm users Live at once) and onboarding steers Android
and desktop Spotify users to push.

## 5. Engineering workflow

Every story travels the same path: plan with the AI assistant, branch,
build behind a flag if needed, open a pull request, pass CI, get one
review, merge to main, and auto-deploy to staging.

### 5.1 Branching and pull requests

- Trunk-based: short-lived branches named JNG-03-02-fof-suggestions,
  merged within 2 days.

- Pull requests link one story, list its Gherkin scenarios, and include
  screenshots for UI in both themes.

- One approval required; the author never merges their own red build.

- Unfinished features merge behind django-waffle flags rather than
  living on long branches.

### 5.2 CI/CD pipeline (GitHub Actions)

1.  Lint and format (Ruff, ESLint, Prettier), type checks (mypy, tsc)

2.  Unit tests with coverage gate (80%)

3.  API schema diff; adapter contract tests

4.  Security: Gitleaks, pip-audit, npm audit, Trivy image scan, Semgrep

5.  Build images, push to registry, sign

6.  Deploy to staging via Argo CD; Playwright smoke tests and axe
    accessibility scan

7.  Production deploy on a tagged release after Product Owner sign-off;
    rolling update with automatic rollback on failed health checks

### 5.3 Environments

| Environment | Deploys                  | Who uses it                            |
|-------------|--------------------------|----------------------------------------|
| Local       | Docker Compose           | Each developer                         |
| Preview     | Every web pull request   | Reviewers                              |
| Staging     | Every merge to main      | Team, faculty guide, 5 Spotify testers |
| Production  | Tagged releases, from R1 | Beta users, then everyone              |

### 5.4 AI-assisted development practice

Adapted from the Claude Code workflow the team studied:

| Practice                        | How Jingle uses it                                                                                                                |
|---------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| Plan mode first                 | Each story starts in plan mode; the assistant asks clarifying questions and writes a short plan into the pull request description |
| Skills                          | A frontend design skill keeps generated UI on the Jingle design system; the /design route is the reference                        |
| Database through MCP            | A read-only PostgreSQL MCP server on staging lets the assistant inspect schema and query plans                                    |
| Scaffolding in auto mode        | Allowed for boilerplate (serializers, tests, fixtures); never for auth, token handling or payments of any kind                    |
| Debug by describing the failure | Paste the failing Gherkin scenario, logs and trace ID, not "it's broken"                                                          |
| Guardrails                      | No production credentials in any AI session; every AI-written line goes through the same review and CI                            |

## 6. Quality strategy

Quality is built into every sprint through the Definition of Done, and
proven at scale by a full k6 run at 5,000 concurrent users in Sprint 10,
with Sprint 11 reserved for what it finds.

### 6.1 Testing pyramid

| Layer               | Share of tests | Runs                                                         | Examples                                                                 |
|---------------------|----------------|--------------------------------------------------------------|--------------------------------------------------------------------------|
| Unit                | about 70%      | Every push                                                   | Suggestion scoring, compatibility maths, battle rules, adapter parsing   |
| Integration and API | about 20%      | Every push                                                   | DRF endpoints with a real PostgreSQL; FastAPI with MongoDB; schema tests |
| Contract            | per adapter    | Every push, and nightly against live sandboxes where allowed | Spotify, Apple Music, Last.fm, ListenBrainz fixtures                     |
| End to end          | about 10%      | Every merge to staging                                       | Gherkin scenarios from the SRS in Playwright                             |
| Load and chaos      | scheduled      | S4 (baseline), S10 (full), S11 (re-test)                     | k6 ramp, soak, spike, session storm, source outage                       |

### 6.2 Load testing to 5,000 concurrent users

| Sprint | Test                                                                                         | Purpose                                           |
|--------|----------------------------------------------------------------------------------------------|---------------------------------------------------|
| S4     | 500 users, feed and sockets                                                                  | Baseline numbers per pod; set initial autoscaling |
| S8     | 2,000 users with Blends                                                                      | Find the first bottleneck early                   |
| S10    | 5,000 users: ramp, 4-hour soak, battle-reveal spike, 100 sessions × 50 voters, bridge outage | Prove SRS NFR-SCAL-01 and NFR-PERF-01 to 05       |
| S11    | Re-run failed scenarios                                                                      | Confirm fixes                                     |

k6 scripts live in infra/k6/, run from 2 generator nodes in the same
region, and push results to Grafana so each run is compared with the
last.

### 6.3 Definition of Done

The Definition of Done is the one in the SRS (Section 3.4): reviewed and
merged, Gherkin scenarios automated and green, 80% unit coverage on
changed code, schema and contract tests updated, feature-flagged if
externally dependent, observable, zero automated WCAG 2.2 AA failures,
privacy-reviewed where personal data is touched, deployed to staging and
accepted by the Product Owner.

### 6.4 Beta quality gates

- [ ] Crash-free sessions ≥ 99.5% over the last 7 days of beta

- [ ] Zero false-Live incidents in beta

- [ ] All P1 bugs fixed; P2 bugs have a planned sprint

- [ ] 7-day retention of beta users ≥ 30%

- [ ] Usability: 8 of 10 test users reach a populated feed in ≤ 5
  minutes

## 7. Launch and publishing checklist

Public launch on 14 March 2027 goes ahead only when every item below is
ticked; the list is the R2 gate.

### 7.1 Product and platforms

- [ ] All Must stories for R2 done and accepted

- [ ] Spotify onboarding path tested end to end on iPhone and Android:
  Spotify → Last.fm → Jingle, and push via Pano Scrobbler

- [ ] Apple Music, YouTube Music and Amazon Music paths tested end to
  end

- [ ] Branding and attribution checked against Spotify, Apple, Last.fm
  and ListenBrainz guidelines

- [ ] Feature flags set: Amazon Music off unless approved; direct
  Spotify limited to testers unless Extended Quota granted

### 7.2 Reliability

- [ ] k6 5,000-user run passed (S10 or S11)

- [ ] Dashboards and alerts live for every SLO; on-call rota for launch
  week

- [ ] Backups restored successfully in a drill

- [ ] Runbooks reviewed; status page live

### 7.3 Legal and privacy

- [ ] Privacy notice and consent screens (DPDP Act 2023 and Rules 2025)

- [ ] Terms of service, community guidelines, cookie notice

- [ ] 18+ age gate at sign-up

- [ ] Data export and account deletion work from inside the app

- [ ] Grievance contact published

### 7.4 Safety

- [ ] Report and block on every user surface

- [ ] Moderation queue staffed daily during launch week

- [ ] Profanity filter for names, notes and comments (English and Hindi)

### 7.5 Go-to-market

- [ ] Campus launch event and circle-vs-circle battle scheduled

- [ ] Landing page, demo video and onboarding help videos per platform

- [ ] Recap and battle share cards tested on Instagram stories

### 7.6 Mobile stores (Release 3)

- [ ] Sign in with Apple offered alongside other third-party logins

- [ ] In-app account deletion; report and block (App Store guideline 1.2
  for user-generated content)

- [ ] Google Play data safety form and account-deletion link

## 8. Risk register

The two biggest delivery risks both concern Spotify, Jingle's core
platform: access to Spotify listeners at scale, and a policy objection
to multi-platform display; both have owners and mitigations from Sprint
1.

| ID   | Risk                                                                                       | Likelihood | Impact | Mitigation                                                                                                      | Owner        | Trigger to act                        |
|------|--------------------------------------------------------------------------------------------|------------|--------|-----------------------------------------------------------------------------------------------------------------|--------------|---------------------------------------|
| R-01 | Last.fm agreement not granted, capping Spotify-via-Last.fm Live users at about 240 at once | Medium     | High   | Push ingestion for Android and desktop; ListenBrainz Spotify import as a second bridge; request agreement in S1 | A            | No reply by S5                        |
| R-02 | Spotify objects to Spotify data in a multi-platform app (Policy III.5)                     | Low        | High   | Direct Spotify stays tester-only and attributed; bridges carry Spotify listeners                                | A            | Any Spotify notice                    |
| R-03 | Scrobbler custom-endpoint support differs from expectations                                | Medium     | Medium | S2 spike before onboarding copy; fall back to bridges                                                           | C            | Spike fails                           |
| R-04 | Scrobbler setup too hard, low activation                                                   | Medium     | High   | Guided flows per platform and device; help videos; measure step completion weekly                               | C            | Activation under 50% in beta          |
| R-05 | Apple Developer or Google verification delays                                              | Medium     | Medium | Start in S1 and S7; features behind flags                                                                       | B            | Not approved 2 sprints before needed  |
| R-06 | Exam weeks cut capacity more than 50%                                                      | High       | Medium | Only small stories in S5 and S6; buffer in S7                                                                   | B            | Velocity under 12 in S5               |
| R-07 | Load test misses targets                                                                   | Medium     | High   | Baseline in S4, partial in S8, full in S10, fix sprint S11                                                      | B            | Any NFR-PERF failure                  |
| R-08 | Cold start: users arrive with no friends on Jingle                                         | High       | High   | Taste twins, college circles, invite links, recap sharing                                                       | A            | Median time to first friend over 48 h |
| R-09 | Abuse through friend requests or notes                                                     | Medium     | High   | Rate limits, block, report, moderation queue                                                                    | B            | Block rate over 1%                    |
| R-10 | Hosting cost over budget                                                                   | Medium     | Medium | Student credits, autoscaling floors, cost alerts at 80%                                                         | B            | Monthly bill over estimate by 25%     |
| R-11 | A team member leaves or is unavailable                                                     | Low        | High   | Shared ownership, ADRs and runbooks, pairing on critical paths                                                  | Scrum Master | Absence over 1 sprint                 |
