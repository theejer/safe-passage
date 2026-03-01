# Heartbeat Backend Guide

This document describes how backend heartbeat ingest + watchdog escalation works, how to integrate it into other backend/app surfaces, and which settings control behavior.

## Scope

Heartbeat backend covers:

- Authenticated heartbeat ingest (`POST /heartbeat` and `POST /heartbeats`).
- Traveler status updates on each ingest.
- Watchdog evaluation loop for delayed reconnect detection.
- Stage-based escalation (`stage_1`, `stage_2`) and auto-recovery alert (`stage_3`).

## Endpoints

- `POST /heartbeat`
- `POST /heartbeats`
- `POST /heartbeats/watchdog/run`

### Ingest endpoint behavior

Route: `app/routes/heartbeats.py`

1. Extract and verify bearer token (`extract_bearer_token`, `verify_supabase_user_id`).
2. Validate payload using `HeartbeatIngestSchema`.
3. Enforce ownership:
   - payload `user_id` must match token subject.
   - `trip_id` must exist and belong to token user.
4. Enforce trip heartbeat switch:
   - if `trip.heartbeat_enabled` is `False`, returns `409`.
5. Persist row to `heartbeats` table.
6. Execute ingest side effects via `process_heartbeat_ingest`.

## Watchdog behavior

Service: `app/services/heartbeat_monitor.py`

- `run_watchdog_cycle()` loads active heartbeat-enabled trips for today.
- Evaluates each status with `evaluate_status_for_alert()`.
- Threshold model:
  - expected offline window from itinerary segments (`derive_expected_offline_minutes`, fallback 90 min)
  - multiplied by risk and context (`_risk_multiplier`) using connectivity risk, battery, time-of-day, weekend.
- Stage transitions:
  - `stage_1_initial_alert` when offline exceeds adjusted expected window
  - `stage_2_escalation` when offline exceeds stronger threshold
  - `stage_3_auto_reconnection` when a previously alerted user comes back online
- Alert dedupe windows:
  - Stage 1 dedupe: 30 minutes
  - Stage 2 dedupe: 60 minutes

## Integration map (backend)

### Route-level integration

- Registers heartbeat blueprint in `app/__init__.py` under:
  - `/heartbeat` (alias)
  - `/heartbeats`
- If scheduler is enabled, app factory starts APScheduler and runs watchdog periodically.

### Model/service dependencies

- `app/models/heartbeats.py`: write heartbeat rows.
- `app/models/trips.py`: heartbeat opt-in via `heartbeat_enabled`; active-trip selection.
- `app/models/traveler_status.py`: status upsert/update used by ingest and watchdog.
- `app/models/alerts.py`: escalation event persistence and dedupe checks.
- `app/models/itinerary_segments.py`: expected offline windows.
- `app/services/notifications.py`: SMS dispatch.

### Integrating heartbeat into new backend features

When adding a feature that depends on live monitoring state:

1. Read traveler status from `traveler_status` rather than raw heartbeats when possible.
2. Respect trip-level switch (`heartbeat_enabled`) before making alerting decisions.
3. Reuse stage constants from `heartbeat_monitor.py` (`STAGE_1`, `STAGE_2`, `STAGE_3`) for consistency.
4. If adding channels (email/push), extend `_send_and_record_stage_alert` so dispatch + persistence remain unified.

## Payload contract

Schema: `app/schemas/heartbeat_schema.py`

Required fields:

- `user_id`
- `trip_id`
- `timestamp`

Optional fields:

- `gps.lat`, `gps.lng`, `gps.accuracy_meters`
- `battery_percent` (0..100)
- `network_status` (`online | offline | unknown`)
- `offline_minutes` (>=0)
- `source` (`background_fetch | manual_debug | foreground`)
- `emergency_phone`

## Variables/settings that control current functionality

### Trip-level switch (primary on/off)

- `trips.heartbeat_enabled` (boolean)
  - Defaults to `True` in `TripCreateSchema`.
  - Enforced in ingest route and active-trip watchdog selection.

### Environment variables

Defined in `app/config.py`:

- `ENABLE_HEARTBEAT_SCHEDULER`
  - `"1"` enables periodic watchdog scheduling in app factory.
  - `"0"` disables scheduler; watchdog can still be run manually via endpoint.
- `HEARTBEAT_WATCHDOG_INTERVAL_MINUTES`
  - Poll interval for scheduled watchdog job (default `5`).
- `HEARTBEAT_WATCHDOG_KEY`
  - Optional key required on `POST /heartbeats/watchdog/run` via `x-watchdog-key` header.

### Runtime stage constants

In `app/services/heartbeat_monitor.py`:

- `STAGE_1 = "stage_1_initial_alert"`
- `STAGE_2 = "stage_2_escalation"`
- `STAGE_3 = "stage_3_auto_reconnection"`

## Quick integration examples

### 1) Create a trip with heartbeat disabled

Send `heartbeat_enabled: false` in trip creation payload:

```json
{
  "user_id": "usr_1",
  "title": "Patna to Gaya",
  "start_date": "2026-03-02",
  "end_date": "2026-03-04",
  "heartbeat_enabled": false
}
```

### 2) Run watchdog manually from internal tooling

```bash
curl -X POST http://localhost:5000/heartbeats/watchdog/run \
  -H "x-watchdog-key: <HEARTBEAT_WATCHDOG_KEY>"
```

## Operational notes

- If scheduler is disabled, ingest still works and stage-3 recovery can still occur on new heartbeats.
- Ensure alert channel credentials are configured (for SMS) in environments where escalation should notify real contacts.
- For low-connectivity regions, keep itinerary segment `expected_offline_minutes` realistic to reduce false positives.
