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

## Useful Commands

### Syntax sanity check

```powershell
.\.venv\Scripts\python.exe -m compileall app
```

### Run tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

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

## Focused Guides

- Heartbeat backend integration and controls: `HEARTBEAT.md`

## Notes

- This backend is scaffold-first: routes/services/models are intentionally minimal with comments for fast agentic iteration.
- Telegram emergency alerting is supported via bot polling (`/start` + phone number activation).
- Some integrations remain placeholders (SMS/FCM/email dispatch logic is stubbed).
- For production, add auth hardening, request rate limits, and encrypted handling for sensitive location/incident data.
