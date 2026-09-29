# Jingle — Technology Stack

Sep 29, 2026 · @Shlok

## 1. Architecture at a glance and selection principles

Jingle runs a Python-first backend (Django for the core API, FastAPI for
ingestion and inference, Celery for jobs) with a Node Socket.IO gateway
for realtime, React/Next.js on the client, and PostgreSQL, MongoDB,
Redis and Qdrant underneath.

<img src="media/image1.png" style="width:6in;height:4.41964in"
alt="Jingle runtime architecture, Release 2" />

Jingle runtime architecture, Release 2

Every client request enters through one edge and lands on the service
that owns it; only FastAPI adapters and Celery jobs talk to external
music services.

### 1.1 How the requested technologies map

| Requested            | Where it is used                                                                                  | Why there                                                      |
|----------------------|---------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| Python               | Django, FastAPI, Celery, all data science and ML                                                  | One language for the whole backend and ML stack                |
| Django               | Core REST API, ORM, migrations, admin and moderation console                                      | Auth, admin, ORM and mature security defaults out of the box   |
| REST API             | Django REST Framework at /api/v1/, OpenAPI 3.1 via drf-spectacular                                | Stable, cacheable, documented contract for web and mobile      |
| FastAPI              | Source adapters, ingestion endpoints, suggestion, compatibility and Blend inference               | Async I/O for many slow external calls; Pydantic v2 validation |
| MERN: MongoDB        | Listening-event store (time-series collections), provider payload archive, notification documents | Append-heavy, schema-flexible data with TTL                    |
| MERN: Express + Node | Socket.IO realtime gateway with the Redis adapter                                                 | Mature WebSocket fan-out and reconnection                      |
| MERN: React          | Next.js web app; React Native mobile in Release 3                                                 | SSR for landing and shareable recap pages; shared components   |
| pandas               | Recap statistics, taste-evolution snapshots, offline evaluation, admin analytics                  | Fast, familiar batch analysis                                  |

### 1.2 Selection principles

1.  **Fit the constraint, not the trend.** Each tool answers a named SRS
    requirement or constraint.

2.  **Python-first.** Node is confined to the realtime gateway; Django
    Channels can replace it without API changes.

3.  **Managed where cheap, self-hosted where costly.** Managed
    PostgreSQL and Redis; self-hosted Qdrant and model serving.

4.  **Open source by default**, with licences checked (Essentia is
    AGPL-3.0 and runs only as an internal service).

5.  **Replaceable at the boundary.** Every external platform sits behind
    one adapter interface.

## 2. Frontend and mobile

The web client is a Next.js (App Router) TypeScript app styled with
Tailwind and shadcn/ui, with TanStack Query for server state and Motion
for animation; React Native with Expo reuses its tokens and API client
in Release 3.

| Concern                | Choice                                                                           | Why                                                                         |
|------------------------|----------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| Framework              | Next.js, App Router, React 19, TypeScript (strict)                               | SSR for the landing page and public recap links; route-level code splitting |
| Styling                | Tailwind CSS with CSS variables for design tokens                                | Dark and light themes from one token set                                    |
| Components             | shadcn/ui on Radix primitives                                                    | Accessible dialogs, menus and tabs we own as source                         |
| Server state           | TanStack Query                                                                   | Caching, polling and stale-while-revalidate match freshness labels          |
| Client state           | Zustand                                                                          | Small store for player bar, theme and session UI                            |
| Realtime               | socket.io-client                                                                 | Auto-reconnect and rooms, matching the Node gateway                         |
| Animation              | Motion (formerly Framer Motion)                                                  | Springs, shared-layout transitions, podium reveal; honours reduced motion   |
| Charts                 | visx or Recharts                                                                 | Taste timeline, compatibility radar                                         |
| Apple sign-in to music | MusicKit JS                                                                      | Browser authorisation for the Music User Token                              |
| Forms and validation   | React Hook Form + Zod                                                            | Types shared with the OpenAPI-generated client                              |
| API client             | openapi-typescript + openapi-fetch, generated from the DRF schema                | One source of truth for request and response types                          |
| Images                 | next/image with a CDN loader; ImageKit or Cloudinary for avatars and recap cards | Responsive artwork, on-the-fly resizing                                     |
| Mobile (R3)            | React Native with Expo; expo-notifications                                       | Shares tokens, API client and business logic                                |

### 2.1 Design-system first

A /design route ships in Sprint 1 with tokens (colours for both themes,
type scale, spacing, radius), every card variant (Live, Recent, Top,
Hidden, Degraded), buttons, chips, and Blip's poses. Feature screens
only compose these parts. This follows the "design system before
screens" practice from the Claude Code workflow the team studied.

### 2.2 Frontend performance budget

| Budget                               | Limit                       |
|--------------------------------------|-----------------------------|
| JavaScript on first load (gzip)      | ≤ 180 KB for the home route |
| Largest Contentful Paint (4G mobile) | ≤ 2.5 s                     |
| Interaction to Next Paint            | ≤ 200 ms                    |
| Cumulative Layout Shift              | ≤ 0.1                       |

Lighthouse CI fails the build when a budget is exceeded.

## 3. Backend services

Four deployable services split the backend by workload: Django owns
business data and rules, FastAPI owns slow external I/O and model
inference, Node owns live connections, and Celery owns scheduled and
background work.

### 3.1 Ownership

| Service                                   | Owns                                                                                                                                                                                                              | Does not own                                                   |
|-------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| **core-api** (Django + DRF)               | Users, auth, profiles, privacy settings, friendships, blocks, circles and roles, recommendations and mixtapes, Blend metadata, battles, recaps, concerts, notifications, moderation, feature flags, admin console | Talking to music platforms; WebSocket connections              |
| **ingest-ml** (FastAPI)                   | Source adapters (ListenBrainz, Last.fm, Apple Music, Spotify, Amazon, Google export), track identity resolution, listening-event writes, inference endpoints for suggestions, compatibility and Blends            | User-facing business rules                                     |
| **realtime** (Node + Express + Socket.IO) | WebSocket auth, rooms per session and circle, votes fan-out, presence, live feed pushes                                                                                                                           | Persisting state (it writes through core-api or Redis streams) |
| **workers** (Celery + Beat, Python)       | Polling schedules, snapshots, recap generation, battle state machine, concert sync, suggestion and circle recompute, email and push delivery                                                                      | Serving HTTP                                                   |

### 3.2 Libraries per service

| Service   | Key libraries                                                                                                                                                                                                                                                                              |
|-----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| core-api  | Django 5.x, Django REST Framework, drf-spectacular (OpenAPI), django-allauth (Google, Apple, email), SimpleJWT, django-filter, django-cors-headers, django-guardian or rules (object permissions), django-waffle (feature flags), django-environ, psycopg 3, gunicorn with uvicorn workers |
| ingest-ml | FastAPI, Pydantic v2, httpx (async), tenacity (retries with backoff), motor (async MongoDB), redis-py, rapidfuzz, musicbrainzngs, uvicorn                                                                                                                                                  |
| realtime  | Node LTS, Express, Socket.IO, @socket.io/redis-adapter, jose (JWT verify), pino (logs)                                                                                                                                                                                                     |
| workers   | Celery, django-celery-beat, redis, pandas, NumPy, scikit-learn                                                                                                                                                                                                                             |

### 3.3 Service contracts

- Browser and mobile clients call only core-api (/api/v1/) and realtime
  (/rt).

- core-api calls ingest-ml over internal HTTP with a service token for
  inference and on-demand adapter actions.

- Services publish domain events (listen.observed, rec.played,
  vote.cast) on Redis Streams; realtime and workers consume them.

- One JWT signing key set; realtime verifies tokens locally without a
  database call.

### 3.4 If the team drops Node

Django Channels with channels-redis can host the same /rt rooms and
events. The client contract does not change. Keep Node unless the team
wants a single language; Socket.IO's reconnection and rooms are more
mature.

## 4. Data layer

PostgreSQL holds everything that must be correct and related; MongoDB
holds the high-volume stream of listening events; Redis holds everything
that must be fast and short-lived; Qdrant holds vectors.

| Store                                          | What it holds                                                                                                                                                                                        | Why this store                                                     | Sizing at launch                                                         |
|------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|--------------------------------------------------------------------------|
| **PostgreSQL 16** (managed)                    | Users, linked sources (encrypted tokens), friendships, blocks, circles, memberships, recordings and platform links, recommendations, Blends, battles, votes, recaps, concerts, moderation, audit log | Relational integrity, transactions, rich indexes for graph queries | 4 vCPU, 16 GB RAM, 200 GB; 1 read replica; PgBouncer in transaction mode |
| **MongoDB** (Atlas or self-hosted replica set) | listens time-series collection (user, recording, source, via, played_at), raw provider payloads, notification documents                                                                              | Append-heavy writes, flexible payloads, TTL expiry at 13 months    | 3-node replica set, M30-class                                            |
| **Redis 7** (managed)                          | Feed cache (sorted sets per user), now-playing state with 90 s TTL, presence, rate-limit token buckets, Celery broker, Socket.IO adapter, Redis Streams for domain events                            | Sub-millisecond reads, pub/sub, TTL                                | 2 separate instances: cache and broker, 4 GB each, with replicas         |
| **Qdrant** (self-hosted)                       | User taste vectors, recording embeddings, artist embeddings                                                                                                                                          | Fast approximate nearest-neighbour search with payload filters     | 1 node, 4 vCPU, 8 GB; snapshots to object storage                        |
| **Object storage** (S3-compatible)             | Recap images, avatars, Takeout uploads (24 h), backups                                                                                                                                               | Cheap, durable                                                     | Lifecycle rules per prefix                                               |

### 4.1 Why not one database

Listening events arrive at up to 20,000 a minute and are read mostly as
time windows per user. Putting them in PostgreSQL would bloat the
system-of-record tables and its backups. MongoDB time-series collections
bucket them efficiently and expire them automatically. The alternative,
TimescaleDB on PostgreSQL, is equally valid; Jingle picks MongoDB
because the team asked for MERN coverage and it isolates the heaviest
write path from transactional data.

### 4.2 pgvector or Qdrant

For under 100,000 vectors, pgvector in PostgreSQL would work. Qdrant is
chosen for filtered search (for example "taste twins who are
discoverable, not blocked, same age band") and to keep ANN load off the
primary database. Start with pgvector if the team wants one fewer
service in R0, and move to Qdrant before R2.

## 5. Data science and ML

Deterministic, testable models make every decision (who to suggest, what
goes in a Blend, what the score is), and a small self-hosted language
model only writes the one-line explanation afterwards.

| Job                                                     | Tools                                                                                                                                              | Notes                                                                                                                                                                                                                             |
|---------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Batch analytics: recaps, taste snapshots, admin reports | pandas, NumPy, (Polars for large rollups)                                                                                                          | Runs in Celery workers over MongoDB exports                                                                                                                                                                                       |
| Audio features (tempo, key, energy, danceability, mood) | [Essentia](https://github.com/MTG/essentia) with pretrained discogs-effnet and MusiCNN models                                                      | Replaces Spotify's retired audio-features endpoint; runs on catalog preview clips only where the provider's terms allow analysis (to confirm with Apple), otherwise falls back to tag embeddings; AGPL-3.0, internal service only |
| Taste vectors                                           | scikit-learn (TF-IDF over artists and tags, TruncatedSVD), sentence-transformers for tag text                                                      | One 128-dimension vector per user, refreshed nightly                                                                                                                                                                              |
| Friend suggestions                                      | networkx or python-igraph (Adamic–Adar, friends of friends), Qdrant ANN for taste twins, LightGBM ranker from R3                                   | Heuristic weights until 10,000 labelled outcomes                                                                                                                                                                                  |
| Circle detection                                        | python-igraph + leidenalg (Leiden community detection)                                                                                             | Weekly on the friend-plus-taste graph; suggestions only, never auto-join                                                                                                                                                          |
| Recommendations and Blends                              | [LightFM](https://github.com/lyst/lightfm) (hybrid, cold-start aware), [implicit](https://github.com/benfred/implicit) (ALS on plays)              | Trained only on permitted data (SRS BR-04)                                                                                                                                                                                        |
| Evaluation                                              | scikit-learn metrics, recometrics, pandas notebooks                                                                                                | Precision@k, NDCG, acceptance rate                                                                                                                                                                                                |
| Explanation text                                        | [Ollama](https://github.com/ollama/ollama) (dev) or [vLLM](https://github.com/vllm-project/vllm) (prod) serving a small open-weight instruct model | Input is structured reasons; output checked for length and banned words before display                                                                                                                                            |
| Experiment tracking                                     | MLflow                                                                                                                                             | Model versions, metrics, rollbacks                                                                                                                                                                                                |

### 5.1 Data-use rules applied to ML

- Never train on data obtained through the Spotify Web API (Spotify
  Developer Policy III.14).

- Train on Jingle-native events, ListenBrainz data (openly licensed) and
  MusicBrainz metadata.

- Use Last.fm data for display only until a commercial agreement allows
  more.

- Keep a data-lineage tag (via) on every event so training jobs can
  filter by permitted source.

## 6. Music platform integrations and identity tooling

Six adapters and one identity resolver sit in ingest-ml; each adapter
declares its capabilities, so code that asks a non-live source for
now-playing fails at the type level, not in front of a user.

| Adapter       | Access                                                                                         | Tooling                                                                                             | Capabilities                               |
|---------------|------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------|--------------------------------------------|
| ListenBrainz  | User token                                                                                     | httpx client over the [core API](https://listenbrainz.readthedocs.io/en/latest/users/api/core.html) | Live, Recent, Top                          |
| Last.fm       | API key; username or web auth                                                                  | httpx; user.getRecentTracks, user.getTopArtists, track.getTopTags                                   | Live, Recent, Top                          |
| Apple Music   | Developer JWT (ES256, signed with the team key) + Music User Token from MusicKit JS / MusicKit | PyJWT, httpx                                                                                        | Recent, heavy rotation, library, playlists |
| Spotify       | OAuth 2.0 Authorization Code with PKCE                                                         | spotipy or httpx; allowlist of 5 testers                                                            | Live, Recent, Top (tester-only)            |
| Amazon Music  | Login with Amazon                                                                              | httpx; behind amazon_music_enabled                                                                  | Library, playlists (closed beta)           |
| YouTube Music | Takeout upload; Google Data Portability API (dataportability.myactivity.youtube)               | ijson streaming parser; google-auth                                                                 | History snapshot, Top                      |

### 6.1 Identity resolution

| Step | Tool                                                                                                            | Match rule                                              |
|------|-----------------------------------------------------------------------------------------------------------------|---------------------------------------------------------|
| 1    | Source ISRC (Apple Music, Spotify)                                                                              | Exact ISRC → Recording                                  |
| 2    | MusicBrainz recording MBID (ListenBrainz, Last.fm)                                                              | Exact MBID → Recording; MBID → ISRC via MusicBrainz     |
| 3    | [rapidfuzz](https://github.com/rapidfuzz/RapidFuzz) over normalised artist and title against MusicBrainz search | token_set_ratio ≥ 90 and duration within 5 s when known |
| 4    | Apple Music catalog search by ISRC or text                                                                      | Fills the Apple Music link for a Recording              |
| 5    | Unresolved                                                                                                      | Shown as text; excluded from Blends and scores          |

MusicBrainz allows about 1 request per second per client, so resolution
runs through a queue with a shared limiter and caches results
permanently in PostgreSQL. A self-hosted MusicBrainz mirror is the
upgrade path if volume grows.

### 6.2 Metadata and artwork

- Genres and tags: MusicBrainz tags first, Last.fm top tags for display.

- Artwork: Apple Music catalog artwork with attribution; Cover Art
  Archive by release MBID; generative fallback pattern when neither
  exists.

- Concerts: Ticketmaster Discovery API (5,000 calls a day, 5 per second
  by default), cached per artist per day.

### 6.3 Contract testing

Every adapter has recorded fixtures of real responses and Pact-style
contract tests in CI, so a platform changing its response shape breaks a
build, not the feed.

## 7. Async jobs, realtime, infrastructure, DevOps, observability and security

Everything runs as containers on one managed Kubernetes cluster in an
India region, deployed by GitHub Actions through Argo CD, and observed
end to end with OpenTelemetry into Grafana.

### 7.1 Async and realtime

| Concern    | Choice                                                                                                                                |
|------------|---------------------------------------------------------------------------------------------------------------------------------------|
| Job queue  | Celery with Redis broker; separate queues poll, ingest, ml, notify, default so slow ML jobs never delay polling                       |
| Scheduling | Celery Beat (django-celery-beat) for fixed jobs; per-user polling is self-rescheduling tasks with jitter, not one Beat entry per user |
| Event bus  | Redis Streams with consumer groups (upgrade path: NATS JetStream or Kafka beyond 50,000 concurrent)                                   |
| Realtime   | Socket.IO on Node with @socket.io/redis-adapter; sticky sessions at the ingress                                                       |
| Push       | Firebase Cloud Messaging for web and mobile push                                                                                      |
| Email      | Amazon SES or Resend, templated with MJML                                                                                             |

### 7.2 Infrastructure

| Layer                  | Choice                                                                                                          |
|------------------------|-----------------------------------------------------------------------------------------------------------------|
| Containers             | Docker, multi-stage builds, distroless or slim base images                                                      |
| Orchestration          | Managed Kubernetes (AWS EKS in ap-south-1 or DigitalOcean Kubernetes in Bangalore); k3s for the staging cluster |
| Ingress and edge       | Cloudflare (DNS, CDN, WAF) in front of ingress-nginx; cert-manager for TLS                                      |
| Infrastructure as code | Terraform for cloud resources; Helm charts per service                                                          |
| GitOps                 | Argo CD syncing Helm releases from the repo                                                                     |
| Autoscaling            | Horizontal Pod Autoscaler on CPU and custom metrics (queue depth, socket count)                                 |
| Secrets                | Cloud KMS for token encryption keys; External Secrets Operator or Infisical for app secrets                     |
| Local development      | Docker Compose with all services and seeded data                                                                |

### 7.3 Observability

| Signal  | Tool                                                                   |
|---------|------------------------------------------------------------------------|
| Traces  | OpenTelemetry SDKs in Django, FastAPI, Node and Celery → Grafana Tempo |
| Metrics | Prometheus (kube-prometheus-stack) → Grafana dashboards per NFR        |
| Logs    | Structured JSON → Grafana Loki                                         |
| Errors  | Sentry (or self-hosted GlitchTip) for web and backend                  |
| Uptime  | Grafana synthetic checks plus a public status page                     |
| Alerts  | Grafana Alerting → Slack or Discord and phone for page-level alerts    |

### 7.4 Security tooling

| Concern             | Tool                                                                                                              |
|---------------------|-------------------------------------------------------------------------------------------------------------------|
| Dependency scanning | GitHub Dependabot, pip-audit, npm audit                                                                           |
| Container scanning  | Trivy in CI                                                                                                       |
| Static analysis     | Ruff and Bandit (Python), ESLint with security plugins, Semgrep                                                   |
| Secrets in code     | Gitleaks pre-commit and CI                                                                                        |
| Web security        | Django security middleware, CSP headers, Cloudflare WAF rules, rate limiting (django-ratelimit and Redis buckets) |
| Content moderation  | better-profanity or a custom wordlist in English and Hindi; image checks for avatars                              |

### 7.5 AI-assisted development tooling

| Tool                                         | Use                                                                                       |
|----------------------------------------------|-------------------------------------------------------------------------------------------|
| Claude Code in plan mode                     | Break each story into a plan and let the assistant ask clarifying questions before coding |
| Frontend design skill                        | Keep generated UI on the Jingle design system                                             |
| PostgreSQL MCP server (read-only on staging) | Let the assistant inspect schema and query plans directly                                 |
| GitHub MCP / CLI                             | Issues, pull requests and CI status from the terminal                                     |
| Dictation (optional)                         | Longer, higher-context prompts                                                            |

Rules: the assistant never has production credentials; every AI-written
change goes through the same review and CI as human code.

## 8. Testing, open-source index and cost

The test stack proves every SRS target automatically, and the whole
Release 2 platform is estimated at about 1,000 US dollars a month at
5,000 concurrent users, before student cloud credits.

### 8.1 Testing and quality tooling

| Level             | Tools                                                              | What it proves                                       |
|-------------------|--------------------------------------------------------------------|------------------------------------------------------|
| Unit              | pytest, pytest-django, factory_boy, Vitest, React Testing Library  | Logic and components; 80% coverage gate              |
| API               | pytest with DRF APIClient; schemathesis against the OpenAPI schema | Every endpoint honours its schema and error envelope |
| Adapter contracts | Pact-style tests with recorded fixtures (VCR.py)                   | Platform response shapes have not changed            |
| End to end        | Playwright (Chromium, WebKit, Firefox)                             | Gherkin scenarios from the SRS in a real browser     |
| Accessibility     | axe-core in Playwright; Lighthouse CI                              | Zero WCAG 2.2 AA automated failures                  |
| Load              | k6 (HTTP and WebSocket), Locust for Python-heavy scenarios         | 5,000 concurrent users, p95 targets                  |
| Security          | OWASP ZAP baseline scan in CI; Trivy; Semgrep                      | No high or critical findings                         |
| Chaos             | Pod kills and source-outage toggles in staging                     | Degraded modes behave as specified                   |

### 8.2 Open-source repository index

| Area                       | Repository                                                                                                   | Role in Jingle                                                   |
|----------------------------|--------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------|
| Web framework              | [django/django](https://github.com/django/django)                                                            | Core API                                                         |
| REST                       | [encode/django-rest-framework](https://github.com/encode/django-rest-framework)                              | REST layer                                                       |
| OpenAPI                    | [tfranzel/drf-spectacular](https://github.com/tfranzel/drf-spectacular)                                      | Schema generation                                                |
| Async API                  | [fastapi/fastapi](https://github.com/fastapi/fastapi)                                                        | Ingest and inference                                             |
| Jobs                       | [celery/celery](https://github.com/celery/celery)                                                            | Background work                                                  |
| Realtime                   | [socketio/socket.io](https://github.com/socketio/socket.io)                                                  | Live sessions                                                    |
| Frontend                   | [vercel/next.js](https://github.com/vercel/next.js)                                                          | Web app                                                          |
| UI kit                     | [shadcn-ui/ui](https://github.com/shadcn-ui/ui)                                                              | Components                                                       |
| Data fetching              | [TanStack/query](https://github.com/TanStack/query)                                                          | Server state                                                     |
| Audio analysis             | [MTG/essentia](https://github.com/MTG/essentia)                                                              | Audio features                                                   |
| Recommender                | [lyst/lightfm](https://github.com/lyst/lightfm)                                                              | Hybrid recommendations                                           |
| Recommender                | [benfred/implicit](https://github.com/benfred/implicit)                                                      | Implicit-feedback ALS                                            |
| Recommender server (later) | [gorse-io/gorse](https://github.com/gorse-io/gorse)                                                          | Option if recommendations become their own service               |
| Communities                | [vtraag/leidenalg](https://github.com/vtraag/leidenalg)                                                      | Circle detection                                                 |
| Graphs                     | [networkx/networkx](https://github.com/networkx/networkx)                                                    | Friend-of-friend scoring                                         |
| Vectors                    | [qdrant/qdrant](https://github.com/qdrant/qdrant)                                                            | Taste search                                                     |
| Fuzzy match                | [rapidfuzz/RapidFuzz](https://github.com/rapidfuzz/RapidFuzz)                                                | Track identity                                                   |
| Embeddings                 | [UKPLab/sentence-transformers](https://github.com/UKPLab/sentence-transformers)                              | Tag and text embeddings                                          |
| Model serving              | [vllm-project/vllm](https://github.com/vllm-project/vllm), [ollama/ollama](https://github.com/ollama/ollama) | Explanation text                                                 |
| Scrobbling (user side)     | [web-scrobbler/web-scrobbler](https://github.com/web-scrobbler/web-scrobbler)                                | Browser scrobbling for YouTube Music, Apple Music web and others |
| Load testing               | [grafana/k6](https://github.com/grafana/k6)                                                                  | Scale tests                                                      |
| E2E                        | [microsoft/playwright](https://github.com/microsoft/playwright)                                              | Browser tests                                                    |
| Observability              | [open-telemetry/opentelemetry-python](https://github.com/open-telemetry/opentelemetry-python)                | Tracing                                                          |

### 8.3 Monthly cost at Release 2 scale

<img src="media/image2.png" style="width:6in;height:3.45536in"
alt="estimated from typical managed-cloud list prices, not quotes; Release 2 sizing" />

estimated from typical managed-cloud list prices, not quotes; Release 2
sizing

Compute and the three databases make up almost all of the bill; logs,
storage and email are small. Student credits (for example the GitHub
Student Developer Pack's cloud offers) can cover the R0–R1 months.
