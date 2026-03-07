# SafePassage Backend (Flask + Supabase)

This folder contains the backend scaffold for SafePassage’s three pillars:
- **PREVENTION**: itinerary parsing + risk analysis
- **CURE**: heartbeat ingestion + offline anomaly monitoring
- **MITIGATION**: incident-ready data flows and escalation hooks

## Structure (Quick Gist)

- `app/__init__.py` — Flask app factory, config load, blueprint registration
- `app/config.py` — environment-driven settings (Supabase, model, notifications)
- `app/extensions.py` — shared clients (Supabase) and extension init
- `app/models/` — thin Supabase table wrappers (`users`, `trips`, `itineraries`, `risk_reports`, `heartbeats`)
- `app/routes/` — API surface (users, trips, itinerary analysis, heartbeats, auth, healthcheck)
- `app/services/` — business logic (itinerary parsing, risk engine, notifications, connectivity model)
- `app/schemas/` — Pydantic request/response contracts
- `app/tasks/monitor_offline.py` — scheduled CURE monitor flow
- `app/utils/` — shared helpers (geo, HTTP client, logging)
- `tests/` — API/service test placeholders
- `wsgi.py` — WSGI entrypoint
- `requirements.txt` — Python dependencies

## Prerequisites

- Python 3.11+ (Windows launcher `py -3` is supported)
- Network access for package installs
- Supabase project credentials (for DB operations)

## Setup

From repo root:

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If `py -3 -m venv .venv` fails due to stale launcher mappings, use:

```powershell
uv venv .venv --python 3.11 --seed
```

## Environment Variables

Preferred local setup: create `backend/.env` (or copy `backend/.env.example`) and set values there.

```powershell
cd backend
copy .env.example .env
```

Then set at minimum:

```dotenv
OPENAI_API_KEY=<your-openai-key>
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_KEY=<service-or-anon-key>
APP_CONFIG=development
```

The backend now auto-loads `backend/.env` on startup.

Set these before running the API (PowerShell example):

```powershell
$env:SUPABASE_URL="https://<project>.supabase.co"
$env:SUPABASE_KEY="<service-or-anon-key>"
$env:APP_CONFIG="development"

# Optional model providers
$env:OPENAI_API_KEY=""
$env:ANTHROPIC_API_KEY=""

# Optional alert integrations
$env:TWILIO_ACCOUNT_SID=""
$env:TWILIO_AUTH_TOKEN=""
$env:TWILIO_FROM_NUMBER=""
$env:TELEGRAM_BOT_TOKEN=""
$env:TELEGRAM_BOT_ENABLED="0"
$env:TELEGRAM_POLL_INTERVAL_SECONDS="2"

# Heartbeat watchdog scheduling
$env:ENABLE_HEARTBEAT_SCHEDULER="0"
$env:HEARTBEAT_WATCHDOG_INTERVAL_MINUTES="5"
$env:HEARTBEAT_WATCHDOG_KEY=""

# Demo-only heartbeat auth fallback (non-production only)
$env:HEARTBEAT_DEMO_AUTH_FALLBACK="0"
```

## Run the Backend

### Local Flask process (simple)

```powershell
cd backend
.\.venv\Scripts\python.exe wsgi.py
```

Then open healthcheck:
- `GET http://localhost:5000/health`

### Flask CLI (optional)

```powershell
cd backend
$env:FLASK_APP="wsgi.py"
flask run --host 0.0.0.0 --port 5000
```

## Run with Docker (Recommended for GitHub reviewers)

From repo root:

```powershell
Copy-Item backend/.env.example backend/.env
```

Edit `backend/.env` and set at least:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `OPENAI_API_KEY` (if using AI itinerary/risk features)

Then start the backend container:

```powershell
docker compose up --build backend
```

Healthcheck:

- `GET http://localhost:5000/health`

Run in detached mode:

```powershell
docker compose up --build -d backend
```

Stop container:

```powershell
docker compose down
```

PowerShell helper script from repo root:

```powershell
./scripts/backend-docker.ps1 -Action up
./scripts/backend-docker.ps1 -Action logs
./scripts/backend-docker.ps1 -Action status
./scripts/backend-docker.ps1 -Action down
```

Notes:

- `docker-compose.yml` persists local sqlite data in a named volume (`safepassage_data`).
- Compose defaults `APP_CONFIG=production` and disables heartbeat scheduler unless enabled in env.

## Useful Commands

### Syntax sanity check

```powershell
.\.venv\Scripts\python.exe -m compileall app
```

### Run tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

### Run performance tests

The backend includes a comprehensive performance test suite that measures algorithm efficiency and code execution speed for critical heartbeat monitoring and emergency escalation systems.

**Quick start:**

```powershell
cd backend
.\.venv\Scripts\python.exe run_performance_tests.py --all
```

**Test categories:**

```powershell
# Run all tests
.\.venv\Scripts\python.exe run_performance_tests.py --all

# Run specific categories
.\.venv\Scripts\python.exe run_performance_tests.py --load         # Heartbeat ingestion
.\.venv\Scripts\python.exe run_performance_tests.py --watchdog     # Watchdog cycle scalability
.\.venv\Scripts\python.exe run_performance_tests.py --escalation   # Emergency escalation workflow
.\.venv\Scripts\python.exe run_performance_tests.py --alerts       # Alert delivery testing

# Multiple categories
.\.venv\Scripts\python.exe run_performance_tests.py --load --watchdog --escalation

# Help and options
.\.venv\Scripts\python.exe run_performance_tests.py --help
```

**What the tests measure:**

These tests measure **algorithm efficiency and code execution speed** using:
- **Synthetic data generation**: Test users, trips, and heartbeats created in-memory
- **Mocked database**: In-memory dictionary-based storage (no actual PostgreSQL I/O)
- **Mocked external services**: HTTP calls to Telegram API and other services are intercepted
- **Real production code**: Actual functions from `app.services` and `app.models` are executed

**Important limitations:**

⚠️ **These tests do NOT measure production performance.** They validate:
- Code correctness and logic flow
- Algorithm efficiency without I/O overhead
- Memory usage patterns
- Error handling robustness

**What is NOT measured:**
- Real database query latency (PostgreSQL connection overhead, network I/O)
- Actual HTTP request/response times
- Production infrastructure constraints (CPU, memory, network)
- Real-world concurrency and connection pooling behavior

**Realistic production estimates:**

| Metric | Test Result (Mocked) | Production Estimate (Real I/O) |
|--------|---------------------|--------------------------------|
| Heartbeat ingestion latency | 0.12ms | 15-40ms |
| Watchdog cycle (1000 trips) | 2ms | 7-20 seconds |
| Alert delivery | 3-5ms | 250-3000ms |
| Throughput | 6000+ req/sec | 100-300 req/sec |

**Test output:**

Results are saved to `backend/test_results/`:
- `performance_YYYYMMDD_HHMMSS.json` - Detailed metrics in JSON format
- `performance_report.html` - Interactive HTML dashboard

**Exit codes:**
- `0` - All tests passed
- `1` - One or more tests failed
- `2` - Tests passed with warnings

### Run end-to-end smoke flow (API + DB)

1) Start backend in one terminal:

```powershell
cd backend
.\.venv\Scripts\python.exe wsgi.py
```

2) In a second terminal, run smoke flow:

```powershell
cd backend
.\.venv\Scripts\python.exe tools\smoke_user_flow.py --base-url http://127.0.0.1:5000 --cleanup
```

3) Expected result:
- Every step prints `[PASS]`
- Final line prints `Smoke flow PASSED.`

Heartbeat mode options:

```powershell
# Expect auth-enforced heartbeat (401)
.\.venv\Scripts\python.exe tools\smoke_user_flow.py --heartbeat-check auth

# Expect demo fallback ingest (204) when HEARTBEAT_DEMO_AUTH_FALLBACK=1
.\.venv\Scripts\python.exe tools\smoke_user_flow.py --heartbeat-check demo
```

Useful flags:

```powershell
# Skip direct DB checks
.\.venv\Scripts\python.exe tools\smoke_user_flow.py --skip-db

# Show all options
.\.venv\Scripts\python.exe tools\smoke_user_flow.py --help
```

Troubleshooting:
- If you still see an old error after code changes, restart backend before rerunning smoke (the local runner uses `use_reloader=False`).
- If `health` fails, backend is not running or `--base-url` is wrong.
- If `db_verify` fails, check `SQLALCHEMY_DATABASE_URI` in `backend/.env`.

### Run one test file

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_risk_engine.py -q
```

### Install missing test tooling (if needed)

```powershell
.\.venv\Scripts\python.exe -m pip install pytest
```

### Freeze current environment (optional)

```powershell
.\.venv\Scripts\python.exe -m pip freeze > requirements.lock.txt
```

## Current API Endpoints (Scaffold)

- `GET /health`
- `POST /auth/validate-key`
- `POST /users`
- `PATCH /users/<user_id>/emergency-contact`
- `POST /trips`
- `GET /trips?user_id=<id>`
- `PUT /trips/<trip_id>/itinerary`
- `GET /trips/<trip_id>/itinerary`
- `POST /itinerary/analyze`
- `POST /itinerary/analyze-pipeline`
- `POST /heartbeat` (JWT required; in non-production, optional demo fallback when `HEARTBEAT_DEMO_AUTH_FALLBACK=1`)
- `POST /heartbeats`
- `POST /heartbeats/watchdog/run` (internal key optional via `x-watchdog-key`)
- `POST /incidents/sync`

## Focused Guides

- Heartbeat backend integration and controls: `HEARTBEAT.md`

## Notes

- This backend is scaffold-first: routes/services/models are intentionally minimal with comments for fast agentic iteration.
- Telegram emergency alerting is supported via bot polling (`/start` + phone number activation).
- Some integrations remain placeholders (SMS/FCM/email dispatch logic is stubbed).
- Persistence guardrail: direct Supabase SDK table writes are blocked by tests; DB writes should flow through SQLAlchemy-backed model helpers.
- For production, add auth hardening, request rate limits, and encrypted handling for sensitive location/incident data.
