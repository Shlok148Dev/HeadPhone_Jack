# K. J. Somaiya College of Engineering, Mumbai-77
### (Autonomous College Affiliated to University of Mumbai)
### Department of Computer Engineering | TE Sem V (Academic Year 2026–2027)

---

## **LAB EXPERIMENT REPORT**

**Course:** Software Engineering Lab / DevOps  
**Experiment / Assignment No:** 05  
**Title:** Implementation of Case Study on GitHub Actions for CI/CD Pipeline  
**Aim:** To learn, design, implement, and study a production CI/CD pipeline for a multi-tier microservices project (*Jingle / HeadPhone_Jack*).  

---

### **Student Details**
- **Student Name:** Shlok  
- **Batch:** ____________  
- **Roll No:** ____________  
- **Date of Performance:** 18-10-2026  
- **Date of Submission:** ____________  

---

### **Expected Outcome of Experiment:**
1. Understand the core concepts of **Continuous Integration (CI)**, **Continuous Delivery (CD)**, and **Continuous Deployment (CD)** in real-world software engineering.
2. Formulate and automate build, lint, test, security audit, and deployment pipelines using **GitHub Actions**.
3. Understand pipeline matrix builds, dependency caching, service container virtualization (PostgreSQL, Redis), and secret scanning (Gitleaks).
4. Analyze, diagnose, and resolve real-world pipeline failures, test regressions, and automated dependency bot (Dependabot) conflicts.

---

### **Books / Journals / Websites Referred:**
1. Roger Pressman, *Software Engineering: A Practitioner's Approach*, McGraw-Hill, 2010, 6th/7th edition.
2. Ian Sommerville, *Software Engineering*, Addison-Wesley, 2011, 9th edition.
3. Martin Fowler, *Continuous Integration: Improving Software Quality and Reducing Risk*, Addison-Wesley, 2006.
4. GitHub Actions Documentation: `https://docs.github.com/en/actions`
5. IEEE Standard 830-1998, *Recommended Practice for Software Requirements Specifications*.

---

## **1. Introduction**

In traditional software development lifecycles, integrating components, validating code standards, and releasing software were manual, batch processes prone to the "integration hell" anti-pattern. Modern DevOps replaces manual releases with automated pipelines that trigger immediately upon code pushes or pull requests.

### **1.1 Continuous Integration (CI)**
Developers merge their changes back to the shared repository frequently. The automated CI server immediately fetches the changes, installs dependencies, checks code style/typing, and executes unit and regression test suites.  
*Primary Goal:* Detect bugs and integration errors within minutes of introduction.

### **1.2 Continuous Delivery (CD)**
An extension of CI where every build that passes the integration checks is automatically packaged and staged in a deployable state. Deployment to production requires human authorization or business sign-off.  
*Primary Goal:* Ensure software can be reliably released to production at any given moment.

### **1.3 Continuous Deployment**
Every single commit that passes all stages of the production pipeline is deployed directly into production without human intervention.  
*Primary Goal:* Minimize lead time from code commit to customer delivery.

---

## **2. System Architecture & Case Study Overview: Jingle (`HeadPhone_Jack`)**

The case study project, **Jingle**, is a full-stack, distributed music streaming metadata aggregation and social sharing platform. The repository is organized as a monorepo containing multiple heterogeneous languages and frameworks:

| Component | Directory | Technology Stack | Responsibilities |
|---|---|---|---|
| **Core API** | `services/core_api/` | Python 3.12, Django, DRF, Celery | User accounts, circles, social feeds, recommendation engines, PostgreSQL/Mongo/Qdrant storage. |
| **Ingest & ML** | `services/ingest_ml/` | Python 3.12, FastAPI, SQLAlchemy, Motor | Streaming scrobble ingestion (Spotify, Last.fm, ListenBrainz), MusicBrainz identity resolution. |
| **Common Library** | `packages/py-common/` | Python 3.12, Pydantic, Cryptography | Shared schemas, cryptographic token encryption, centralized logging. |
| **Web Frontend** | `apps/web/` | TypeScript, Next.js 14, React, Tailwind | End-user web dashboard, circle playlists, live listening UI. |
| **Realtime Service** | `apps/realtime/` | TypeScript, Node.js, WebSockets | Ephemeral socket connections, presence detection, live listen broadcast. |
| **Browser Extension** | `apps/companion-extension/` | TypeScript, Chrome Extensions API | Client-side scrobbler observing desktop music players. |
| **Infrastructure** | `infra/`, root | Docker Compose, Caddy Edge Reverse Proxy | Multi-container composition, SSL termination, rate limiting. |

---

## **3. Pipeline Design & Implementation**

The CI/CD automation is orchestrated via three dedicated workflows under `.github/workflows/`:
1. **`ci.yml`**: Runs on every push to `main` and pull request. Executes Python matrix tests (with PostgreSQL & Redis services), Node.js workspace typecheck and Vitest, Gitleaks secret scanning, and full Docker Compose stack integration.
2. **`deploy.yml`**: Runs automatically after CI succeeds on `main`. Deploys via SSH to the live production server (Oracle Cloud Always Free tier) and verifies an HTTP 200 health check.
3. **`security.yml`**: Scheduled weekly security scan running Gitleaks and CodeQL static application security testing (SAST).

---

### **3.1 Workflow Configuration: Continuous Integration (`.github/workflows/ci.yml`)**

```yaml
name: ci

on:
  push:
    branches: [main]
  pull_request:

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  python:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        project: [packages/py-common, services/ingest_ml, services/core_api]
    services:
      postgres:
        image: postgres:16-alpine
        env: { POSTGRES_DB: jingle, POSTGRES_USER: jingle, POSTGRES_PASSWORD: jingle-local }
        ports: ["5432:5432"]
        options: --health-cmd "pg_isready -U jingle" --health-interval 5s --health-retries 20
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    env:
      JINGLE_ENV: test
      DATABASE_URL: postgres://jingle:jingle-local@localhost:5432/jingle
      REDIS_URL: redis://localhost:6379/0
      TOKEN_KEK_B64: ZGV2LW9ubHktMzItYnl0ZS1rZXktZm9yLWxvY2FsISE=
    defaults:
      run:
        working-directory: ${{ matrix.project }}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with: { python-version: "3.12" }
      - run: uv sync --all-extras --frozen || uv sync --all-extras
      - run: uv run ruff check .
      - run: uv run mypy jingle_common
        if: matrix.project == 'packages/py-common'
      - run: uv run mypy ingest_ml
        if: matrix.project == 'services/ingest_ml'
      - run: uv run pytest --cov --cov-report=term-missing

  node:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: pnpm }
      - run: pnpm install --frozen-lockfile
      - run: pnpm -r typecheck
      - run: pnpm -r test
      - run: pnpm -r build

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: gitleaks/gitleaks-action@v2
        env: { GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22 }
      - run: pnpm install --frozen-lockfile && pnpm audit --audit-level critical

  compose:
    runs-on: ubuntu-latest
    needs: [python, node]
    steps:
      - uses: actions/checkout@v4
      - run: cp .env.example .env
      - run: docker compose up -d --build --wait --wait-timeout 300
      - run: curl -fsS http://localhost:8080/api/v1/ping && curl -fsS http://localhost:8080/
      - if: failure()
        run: docker compose logs --no-color | tail -200
```

---

### **3.2 Workflow Configuration: Automated Deployment (`.github/workflows/deploy.yml`)**

```yaml
name: deploy

on:
  workflow_run:
    workflows: [ci]
    types: [completed]
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: deploy-production
  cancel-in-progress: false

jobs:
  deploy:
    if: ${{ vars.DEPLOY_ENABLED == 'true' && (github.event_name == 'workflow_dispatch' || github.event.workflow_run.conclusion == 'success') }}
    runs-on: ubuntu-latest
    environment:
      name: production
      url: ${{ vars.PUBLIC_URL }}
    timeout-minutes: 30
    steps:
      - name: Configure SSH
        env:
          SSH_KEY: ${{ secrets.DEPLOY_SSH_KEY }}
          KNOWN_HOSTS: ${{ secrets.DEPLOY_KNOWN_HOSTS }}
        run: |
          install -m 700 -d ~/.ssh
          printf '%s\n' "$SSH_KEY" > ~/.ssh/deploy && chmod 600 ~/.ssh/deploy
          printf '%s\n' "$KNOWN_HOSTS" > ~/.ssh/known_hosts

      - name: Pull and restart on the server
        env:
          HOST: ${{ secrets.DEPLOY_HOST }}
          USER: ${{ secrets.DEPLOY_USER }}
          SHA: ${{ github.event.workflow_run.head_sha || github.sha }}
        run: |
          ssh -i ~/.ssh/deploy -o IdentitiesOnly=yes "$USER@$HOST" "bash -s" -- "$SHA" <<'REMOTE'
          set -euo pipefail
          cd ~/jingle
          git fetch --quiet origin main
          git checkout --quiet --detach "$1"
          docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build --remove-orphans
          docker image prune -f >/dev/null
          REMOTE

      - name: Health check
        env:
          URL: ${{ vars.PUBLIC_URL }}
        run: |
          for i in $(seq 1 30); do
            if curl -fsS -o /dev/null "$URL"; then echo "Live: $URL"; exit 0; fi
            sleep 10
          done
          echo "Site did not come up at $URL" && exit 1
```

---

### **3.3 Dependabot Configuration (`.github/dependabot.yml`)**

```yaml
version: 2
updates:
  - package-ecosystem: npm
    directory: /
    schedule: { interval: weekly }
    open-pull-requests-limit: 3
    groups:
      minor-and-patch: { update-types: [minor, patch] }
    ignore:
      - dependency-name: "*"
        update-types: ["version-update:semver-major"]

  - package-ecosystem: pip
    directories: [/services/core_api, /services/ingest_ml, /packages/py-common]
    schedule: { interval: weekly }
    open-pull-requests-limit: 3
    groups:
      minor-and-patch: { update-types: [minor, patch] }
    ignore:
      - dependency-name: "*"
        update-types: ["version-update:semver-major"]

  - package-ecosystem: docker
    directories: [/services/core_api, /services/ingest_ml, /apps/web, /apps/realtime]
    schedule: { interval: monthly }
    open-pull-requests-limit: 3

  - package-ecosystem: github-actions
    directory: /
    schedule: { interval: monthly }
    open-pull-requests-limit: 3
    ignore:
      - dependency-name: "*"
        update-types: ["version-update:semver-major"]
```

---

## **4. Real-World Case Study: Diagnosing & Fixing CI/CD Failures**

In this experiment, the project experienced widespread CI/CD failures: **100% of pushes and Dependabot PRs failed**, blocking merges and deployments. Below is the systematic root-cause analysis and resolution:

### **Case 1: Missing Coverage Runner in `packages/py-common`**
- **Symptom:** Step `uv run pytest --cov --cov-report=term-missing` terminated with Exit Code 1.
- **Root Cause Analysis:** `ci.yml` instructed pytest to execute with the `--cov` plugin. However, `packages/py-common/pyproject.toml` only declared `pytest>=8`, `mypy`, and `ruff` in its `[dependency-groups] dev` section. The `pytest-cov` package was absent, triggering:
  ```text
  pytest: error: unrecognized arguments: --cov --cov-report=term-missing
  ```
- **Resolution:** Added `pytest-cov>=5` to `packages/py-common/pyproject.toml` and synchronized `uv.lock`.

### **Case 2: Test Collection Failure in `services/core_api`**
- **Symptom:** Test execution failed before running a single test (`2 errors during collection`).
- **Root Cause Analysis:** `tests/circles/test_circles.py` and `tests/suggestions/test_suggestions.py` import `numpy as np`. In `core_api/pyproject.toml`, scientific packages (`numpy`, `pandas`, `scikit-learn`, `python-igraph`) were isolated inside `[project.optional-dependencies] ml`. The CI step ran default `uv sync`, which deliberately excludes optional extras. Pytest crashed with `ModuleNotFoundError: No module named 'numpy'`.
- **Resolution:** Updated `ci.yml` to execute `uv sync --all-extras --frozen || uv sync --all-extras`, ensuring all required test dependencies are provisioned across matrix jobs.

### **Case 3: Security Validation Regression in `services/ingest_ml`**
- **Symptom:** Unit tests `test_settings_musicbrainz_switch` and `test_settings_refuse_weak_service_token_outside_dev` threw `pydantic_core.ValidationError`.
- **Root Cause Analysis:** Commit `34d3fab` added a strict security validator ensuring that development encryption keys (`_DEV_KEK_B64`) are strictly refused when `jingle_env != 'local'/'test'`. In CI, `TOKEN_KEK_B64` was populated with the development key. When unit tests tested the production branch by invoking `Settings(jingle_env="prod")`, Pydantic ingested the environment variable and raised a validation error.
- **Resolution:** Updated test cases in `services/ingest_ml/tests/test_internal_and_infra.py` to explicitly inject a valid test production key (`prod_kek = "cHJvZC1rZWstMzItYnl0ZS1mb3ItdGVzdGluZyE="`) and explicitly configured `JINGLE_ENV: test` in `ci.yml`.

### **Case 4: Dependabot PR Storm & Cascading CI Failures**
- **Symptom:** Dependabot created 17 open pull requests, all failing CI.
- **Root Cause Analysis:**
  1. Dependabot lacked semver ignore filters for major versions, opening PRs for breaking major upgrades (Vite 5 $\to$ 8, TypeScript 5 $\to$ 7, Vitest 2 $\to$ 5, Django 5 $\to$ 6) that broke APIs.
  2. Dependabot was monitoring `/apps/android` (Gradle/Kotlin), an unmaintained prototype folder not configured in CI.
  3. Because `main` CI was failing, every newly generated PR automatically inherited the broken CI baseline.
- **Resolution:** Rewrote `.github/dependabot.yml` with `ignore: [version-update:semver-major]`, removed the Gradle ecosystem block, grouped minor and patch updates, and capped active PRs to 3 per ecosystem.

---

## **5. Guide to Screenshots for the Lab Submission**

Insert the following 5 screenshots in your submission under the **Implementation / Results** section:

### **Screenshot 1: GitHub Actions Failing Baseline (Before Fix)**
- **What to show:** The GitHub Actions Run History showing commits with failing checks (red cross icons showing 3/8 failed).
- **Caption:** *Figure 1: Initial CI/CD pipeline state showing 3 of 8 jobs failing across Python services.*

### **Screenshot 2: Dependabot Failing PR Flood (Before Fix)**
- **What to show:** The GitHub Pull Requests tab showing 17 Dependabot PRs failing CI checks with red cross badges (`X 5/8`, `X 2/10`).
- **Caption:** *Figure 2: Dependabot pull request dashboard displaying major-version breaking PRs and cascading CI failures.*

### **Screenshot 3: Local Test Suite Verification (Python Backend)**
- **What to show:** Terminal execution of `uv run pytest` inside `services/core_api` and `services/ingest_ml`.
- **Command to run & capture:**
  ```powershell
  cd services/ingest_ml
  uv run pytest --cov
  cd ../core_api
  uv run pytest
  ```
- **Visible output:** `171 passed` in `ingest_ml` and `368 passed` in `core_api`.
- **Caption:** *Figure 3: Local terminal output confirming 100% test pass rate across Core API (368 tests) and Ingest ML (171 tests).*

### **Screenshot 4: Local Test Suite Verification (Node.js Workspace)**
- **What to show:** Terminal execution of `pnpm -r typecheck` and `pnpm -r test`.
- **Command to run & capture:**
  ```powershell
  pnpm -r typecheck
  pnpm -r test
  ```
- **Visible output:** All TypeScript builds passing; Vitest output showing `9 passed` (realtime), `76 passed` (companion-extension), `115 passed` (web) — total 200 unit tests passing.
- **Caption:** *Figure 4: Monorepo TypeScript typecheck and Vitest test suite executing successfully across all frontend packages.*

### **Screenshot 5: Green GitHub Actions Pipeline (After Fix & Push)**
- **What to show:** The GitHub Actions run page for `ci.yml` showing all green checkmarks:
  - `python (packages/py-common)` $\to$ Success
  - `python (services/ingest_ml)` $\to$ Success
  - `python (services/core_api)` $\to$ Success
  - `node` $\to$ Success
  - `security` $\to$ Success
  - `compose` $\to$ Success
- **Caption:** *Figure 5: Fully operational and green CI/CD pipeline verifying all build, lint, test, security, and docker-compose stages.*

---

## **6. Post-Lab Subjective Questions & Answers**

### **Q1: What are the advantages and disadvantages of a CI/CD pipeline?**

#### **Advantages:**
1. **Accelerated Feedback Loops:** Developers know within 2–5 minutes whether new code breaks existing functionality, adheres to type standards, or violates style rules.
2. **Elimination of Integration Hell:** Rather than merging weeks of divergent code branches right before a release, code is continuously merged and verified daily.
3. **Automated Regression Prevention:** Comprehensive unit, contract, and BDD acceptance test suites run systematically on every push, ensuring existing features remain intact.
4. **Enhanced Security Posture (DevSecOps):** Integration of static tools (CodeQL) and secret scanners (Gitleaks) prevents accidental credential leakage and vulnerable dependencies from reaching production.
5. **Repeatable, Idempotent Deployments:** Automated scripts (Docker Compose, Kubernetes, Helm) eliminate human configuration errors during deployment.
6. **Faster Mean Time to Resolution (MTTR):** Small, incremental commits make identifying and reverting the precise commit that introduced a defect straightforward.

#### **Disadvantages:**
1. **Initial Setup and Maintenance Overhead:** Configuring complex monorepo matrix jobs, secrets, and environments requires specialized DevOps expertise and continuous maintenance.
2. **False Positives & Fragile Tests:** Flaky network-dependent tests or race conditions cause false pipeline failures, leading to "alert fatigue" and stalled merges.
3. **Resource & Infrastructure Costs:** Continuous execution of test containers, matrix builds, and virtual machines on GitHub Actions or cloud runners incurs ongoing compute expenses.
4. **Tooling & Dependency Vulnerability:** Misconfigured automated dependency bots (e.g., Dependabot without semver limits) can flood repositories with breaking upgrades.
5. **Security Risks in CI Runners:** Malicious pull requests from forks can attempt to expose secrets or abuse compute runners if pipeline permissions are poorly scoped.

---

### **Q2: Explain MLOps Pipelines in Detail.**

**MLOps (Machine Learning Operations)** is an engineering discipline that combines Machine Learning, DevOps, and Data Engineering to standardize and automate the continuous delivery of high-performing machine learning models in production.

Unlike traditional software pipelines that only track **Code**, an MLOps pipeline manages three interdependent components: **Code**, **Data**, and the **Model**.

#### **Key Stages of an MLOps Pipeline:**
1. **Continuous Data Integration (Data CI):**
   - Ingests raw data streams from databases, event buses (Kafka), and cloud buckets.
   - Validates data distributions, detects missing attributes, and prevents data schema corruption (e.g., Great Expectations).
2. **Continuous Model Training (CT):**
   - Automatically executes training runs when new data arrives or performance degrades below acceptable thresholds.
   - Utilizes hyperparameter tuning and tracks artifacts using tools like MLflow, Weights & Biases, or Kubeflow.
3. **Continuous Model Evaluation & Validation:**
   - Evaluates candidate models against held-out golden benchmark datasets.
   - Verifies fairness, bias, latency, and memory footprints alongside raw metrics (Accuracy, F1-Score, AUC-ROC).
4. **Model Registry & Governance:**
   - Stores approved, versioned model weights, signatures, and lineage metadata.
5. **Continuous Deployment (Model CD):**
   - Serves models as microservices via high-throughput inference runtimes (Triton, FastAPI, TorchServe).
   - Uses progressive rollout strategies (Shadow deployment, Canary releases, A/B testing).
6. **Continuous Monitoring & Feedback Loop:**
   - Monitors serving endpoints for **Data Drift** (input feature distribution shifts) and **Concept Drift** (statistical relationships between features and target labels changing over time).
   - Automatically triggers the Continuous Training (CT) pipeline upon drift detection.

---

## **7. Post-Lab Descriptive Questions & Answers**

### **State various Scheduling principles and explain them in detail.**

Scheduling is the computational method by which CPU resources, execution threads, or CI/CD runner jobs are allocated to competing processes to achieve system performance objectives.

#### **Key Scheduling Criteria & Principles:**
- **CPU Utilization:** Keeping the processor as busy as possible ($40\%$ under light load to $90\%$ under heavy load).
- **Throughput:** Number of processes/jobs completed per unit time.
- **Turnaround Time ($T_t$):** Interval from job submission to job completion:
  $$T_t = T_{\text{completion}} - T_{\text{submission}}$$
- **Waiting Time ($T_w$):** Total time spent by a process in the ready queue waiting for CPU allocation:
  $$T_w = T_t - T_{\text{burst}}$$
- **Response Time ($T_r$):** Time from job submission until the first output or response is produced.
- **Fairness:** Ensuring every task receives an equitable share of resources without starvation.

---

### **Major Scheduling Algorithms & Principles:**

#### **1. First-Come, First-Served (FCFS)**
- **Principle:** Non-preemptive. The process that requests the CPU first is allocated the CPU first using a standard FIFO queue.
- **Characteristics:**
  - Simple to implement with minimal scheduling overhead.
  - Suffer from the **Convoy Effect**: when a long CPU-bound process occupies the CPU, short I/O-bound processes are blocked behind it, resulting in poor CPU and device utilization and high average waiting times.

#### **2. Shortest Job First (SJF) / Shortest Remaining Time First (SRTF)**
- **Principle:** Allocates the CPU to the process with the smallest execution burst time.
  - *Non-preemptive (SJF):* Once assigned, the CPU runs the process to completion.
  - *Preemptive (SRTF):* If a new process arrives with a remaining burst time shorter than the currently running process, the current process is preempted.
- **Characteristics:**
  - **Provably optimal** in minimizing average waiting time.
  - Difficult to implement in general operating systems because the exact future CPU burst duration cannot be known in advance (must be estimated using exponential smoothing: $\tau_{n+1} = \alpha t_n + (1 - \alpha)\tau_n$).
  - Risk of **starvation** for long-running processes if short processes continuously arrive.

#### **3. Round Robin (RR) Scheduling**
- **Principle:** Preemptive algorithm designed specifically for time-sharing systems. The ready queue is treated as a circular FIFO queue. The CPU scheduler allocates a small unit of time called a **Time Quantum** (typically 10 to 100 milliseconds).
- **Characteristics:**
  - If process burst $< \text{quantum}$, the process voluntarily releases the CPU.
  - If process burst $> \text{quantum}$, a hardware timer interrupts the CPU, context-switches the process, and appends it to the tail of the ready queue.
  - Prevents starvation and provides excellent response times.
  - Performance depends heavily on quantum size: if too large, it degrades to FCFS; if too small, CPU cycles are wasted on excessive context-switching overhead.

#### **4. Priority Scheduling**
- **Principle:** Each process is assigned an integer priority value. The CPU is allocated to the process with the highest priority (lowest integer value in many OS conventions).
- **Characteristics:**
  - Can be preemptive or non-preemptive.
  - **Major Pitfall: Indefinite Blocking (Starvation)** — low-priority processes may wait indefinitely if high-priority processes keep arriving.
  - **Solution: Aging** — gradually increasing the priority of processes that wait in the system for extended periods.

#### **5. Multi-Level Queue & Multi-Level Feedback Queue (MLFQ)**
- **Principle:** Partitions the ready queue into several separate queues categorized by process type (e.g., interactive system processes vs. background batch jobs).
- **Feedback Mechanism:** Allows processes to move between queues based on their runtime characteristics:
  - CPU-bound jobs consuming entire time quantums are demoted to lower-priority queues with larger time slices.
  - I/O-bound and interactive jobs that yield the CPU quickly remain in or are promoted to high-priority queues.
  - Solves starvation via periodic priority boosts (aging all processes back to top priority).

#### **6. Real-Time Scheduling Principles (RMS and EDF)**
- **Rate Monotonic Scheduling (RMS):** Static-priority preemptive algorithm for periodic tasks where priority is inversely proportional to period (shorter period = higher priority).
  - Feasible if CPU utilization $U \le n(2^{1/n} - 1)$ (where $U \le 69.3\%$ for large $n$).
- **Earliest Deadline First (EDF):** Dynamic-priority algorithm where priority is assigned based on approaching deadlines. The task whose absolute deadline is nearest gets highest priority.
  - Optimally utilizes up to $100\%$ of CPU capacity without missing deadlines under theoretical conditions.

#### **7. Scheduling in CI/CD and Cloud Pipelines**
In CI/CD environments like GitHub Actions, Jenkins, and Kubernetes:
- **Matrix Scheduling:** Parallelizes independent test suites across multiple virtual machine runners (e.g., Python matrix testing `py-common`, `ingest_ml`, and `core_api` simultaneously).
- **Fair-Share & Concurrency Control:** Uses concurrency groups (`concurrency: cancel-in-progress: true`) to prevent obsolete build queuing when a developer pushes successive commits.
- **Resource-Aware Scheduling:** Assigns resource-intensive integration tests (Docker Compose) to run only after lightweight lint and unit test stages complete successfully (`needs: [python, node]`).

---

## **8. Conclusion**

Through this experiment, the lifecycle, operational architecture, and diagnostic methodologies of modern Continuous Integration, Continuous Delivery, and Continuous Deployment pipelines were implemented and studied using **GitHub Actions**.

By applying these principles to the **Jingle (`HeadPhone_Jack`)** microservices monorepo:
1. Automated quality gates were established across heterogeneous technology stacks (Python Django, FastAPI, Next.js, and Docker Compose).
2. Real-world pipeline regressions—including missing test dependencies (`pytest-cov`), missing optional dependency installation (`uv sync --all-extras`), and environment variable leakage in production security validators—were systematically diagnosed and resolved.
3. Automated dependency governance was configured in Dependabot to eliminate cascading failures and breaking major-version PR storms.
4. The deployment pipeline was structured to ensure zero-touch, zero-downtime containerized releases to cloud infrastructure upon successful verification on the `main` branch.

The experiment demonstrated that robust CI/CD pipelines significantly enhance code quality, reduce time-to-market, and prevent defective code from reaching end-users.
