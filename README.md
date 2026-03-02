# SafePassage (DLW Track)

This repository hosts the SafePassage hackathon build: an offline-first safety companion for solo travelers.

## Project Direction
- Primary app surface: Expo-managed React Native in `my-app`.
- Frontend scaffold: Expo Router React Native app in `frontend` (agentic implementation workspace).
- Styling: NativeWind (Tailwind utility classes).
- Priority capabilities: itinerary risk prep (online), emergency guidance (offline), offline maps, and phrase helper.

## Contributor and Agent Guidance
- Authoritative instructions live in `AGENTS.md`.
- Use `skills/react-native-tailwind-builder` for default feature work.
- Apply `skills/security-best-practices` for emergency, GPS/location, storage, and on-device AI related changes.
- Use `skills/react-feature-builder` only for explicit legacy web maintenance.

## Feature Guides
- Heartbeat backend integration and controls: [backend/HEARTBEAT.md](backend/HEARTBEAT.md)
- Heartbeat frontend runtime and integration: [frontend/src/features/heartbeat/README.md](frontend/src/features/heartbeat/README.md)
- SQLite/offline storage guide: [frontend/src/features/storage/README.md](frontend/src/features/storage/README.md)

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

## Verification Baseline
Run commands from `frontend` for the new Expo scaffold, and from `my-app` only for legacy surfaces:
- `npm start`
- `npm run typecheck` (if present)
- `npx expo-doctor` (if Expo CLI/deps are installed)

Legacy/compatibility commands in `my-app`:
- `npm start`
- `npm test`
- `npm run lint` (if present)
- `npm run typecheck` (if present)
- `npx expo-doctor`

## Environment Setup

Use the provided example files as templates:
- Frontend: `frontend/.env.example`
- Backend: `backend/.env.example`

PowerShell quick copy commands:
- `Copy-Item frontend/.env.example frontend/.env`
- `Copy-Item backend/.env.example backend/.env`

Then fill in real values (especially backend keys like `SUPABASE_URL` and `SUPABASE_KEY`).