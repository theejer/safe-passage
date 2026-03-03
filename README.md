# SafePassage (DLW Track)

This repository hosts the SafePassage hackathon build: an offline-first safety companion for solo travelers.

## Project Direction
- Primary app surface: Expo Router React Native app in `frontend`.
- Styling: NativeWind (Tailwind utility classes).
- Product pillars: **PREVENTION** (itinerary risk analysis), **CURE** (connectivity-aware heartbeat/anomaly alerting), **MITIGATION** (offline emergency guidance + incident logging).

## Deterministic Connectivity Predictor (Standalone)

A reusable service module is available at `backend/app/services/connectivity_predictor.py`.

- Function signature: `predict_connectivity_for_latlon(latitude: float, longitude: float) -> dict`
- Dataset location (colocated): `backend/app/services/data/signal_metrics.csv`
- Grouping bands:
	- `Poor`: 0-24
	- `Average`: 25-49
	- `Good`: 50-74
	- `Excellent`: 75-100

Returned fields include:
- `connectivity_score` (0-100)
- `connectivity_group`
- `expected_connectivity`
- `expected_offline_minutes`
- `confidence`
- `data_points_used`
- `nearest_distance_km`
- `is_sparse`
- `fallback_reason`

Minimal usage example (from `backend` working directory):

```python
from app.services.connectivity_predictor import predict_connectivity_for_latlon

result = predict_connectivity_for_latlon(25.6009, 85.1452)
print(result["connectivity_score"], result["connectivity_group"], result["expected_offline_minutes"])
```

## Dependencies

This repo has three runnable surfaces:

1) **Frontend mobile/web app** (`frontend`)
- Package manager: `npm`
- Source of truth: `frontend/package.json`
- Install command: `cd frontend && npm install`
- Key runtime deps include Expo 54, React Native 0.81, Expo Router, AsyncStorage, NetInfo, SQLite, Supabase JS, NativeWind.

2) **Backend API** (`backend`)
- Package manager: `pip`
- Source of truth: `backend/requirements.txt`
- Install command: `cd backend && py -3 -m pip install -r requirements.txt` (inside venv recommended)
- Key deps include Flask, SQLAlchemy, psycopg2-binary, pydantic, supabase, requests, twilio, firebase-admin, openai, APScheduler, pytest.

3) **Optional Telegram bot** (`telegram-bot`)
- Package manager: `pip`
- Source of truth: `telegram-bot/requirements.txt`
- Install command: `cd telegram-bot && py -3 -m pip install -r requirements.txt` (inside venv recommended)

## Judge Setup (Recommended Path)

This path minimizes host setup risk: **Backend in Docker + Frontend via Expo**.

### 1) Prerequisites
- Node.js 20+ and npm
- Docker Desktop (for backend container)
- (Optional) Python 3.11+ only if you want to run backend/bot outside Docker

### 2) Prepare environment files
From repository root:

```powershell
Copy-Item frontend/.env.example frontend/.env
Copy-Item backend/.env.example backend/.env
```

Set these minimum values:

- `frontend/.env`
	- `EXPO_PUBLIC_BACKEND_URL=http://localhost:5000`
- `backend/.env`
	- `APP_CONFIG=development`
	- `OPENAI_API_KEY=<optional-but-needed-for-itinerary-analysis>`

Notes:
- Backend works with local SQLite by default if `SQLALCHEMY_DATABASE_URI` is not set.
- `SUPABASE_URL` / `SUPABASE_KEY` are optional for local judge runs unless testing Supabase-linked behavior.

### 3) Start backend (Docker)
From repository root:

```powershell
docker compose up --build backend
```

Healthcheck:
- `http://localhost:5000/health`

### 4) Start frontend (Expo)
In a second terminal:

```powershell
cd frontend
npm install
npm start
```

Then launch via Expo (Web/Android/iOS) from the terminal prompt.

### 5) Quick verification
- Backend health returns success at `GET /health`
- Frontend loads and can reach backend URL configured in `EXPO_PUBLIC_BACKEND_URL`
- If itinerary analysis is tested, `OPENAI_API_KEY` must be valid

## Local-Only Setup (No Docker)

### Backend local run

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe wsgi.py
```

### Frontend local run

```powershell
cd frontend
npm install
npm start
```

## Optional: Telegram Bot Setup

```powershell
cd telegram-bot
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe bot.py
```

Required bot env values:
- `TELEGRAM_BOT_TOKEN`
- `SQLALCHEMY_DATABASE_URI`

## Troubleshooting
- `npm start` fails in `frontend`: run `npm install` first, then retry.
- Expo cache issues: run `npx expo start -c`.
- Backend container fails early: verify `backend/.env` exists and Docker Desktop is running.
- Itinerary analysis errors with 401/LLM failure: verify `OPENAI_API_KEY`.

## Docker Helper Script (Optional)

From repository root:

```powershell
./scripts/backend-docker.ps1 -Action up
./scripts/backend-docker.ps1 -Action status
./scripts/backend-docker.ps1 -Action logs
./scripts/backend-docker.ps1 -Action down
```