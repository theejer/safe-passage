# SQLite Storage Guide (Collaborators)

This guide explains how SafePassage frontend uses SQLite for offline-first data paths.

## Scope

Storage lives in:
- `src/features/storage/services/offlineDb.ts`
- `src/features/storage/services/localStore.ts`
- `src/features/storage/hooks/useOfflineSync.ts`

Primary goals:
- Persist safety-critical records locally (days/weeks offline).
- Provide deterministic read/write fallback when network is unavailable.
- Replay queued sync jobs after reconnect.

## Data Domains

SQLite schema currently includes:
- `metadata` (key/value app metadata)
- `trips`
- `itinerary_days`
- `itinerary_locations`
- `risk_reports` (cached risk snapshot JSON)
- `incidents`
- `incident_attachments`
- `sync_queue`

## Initialization Contract

Always initialize before using storage APIs.

```ts
import { initializeOfflineDb } from "@/features/storage/services/offlineDb";

await initializeOfflineDb();
```

Behavior:
- Single-flight initialization (`initPromise`) prevents concurrent schema races.
- Initialization timeout is guarded (`INIT_TIMEOUT_MS`).
- Logs are emitted for start, completion, and failures.

## API Quick Reference

### Metadata (lightweight app flags)

```ts
setMetadata(key, value)
getMetadata(key)
deleteMetadata(key)
```

Use for values like active user ID, cursors, and feature flags.

### Trips

```ts
upsertTrip(trip)
listTrips(userId)
```

- `upsertTrip` marks `sync_status='pending'` for unsynced local changes.
- `listTrips` returns local projections mapped to app-level `Trip` type.

### Itinerary

```ts
upsertItinerary(tripId, days)
getItinerary(tripId)
```

- `upsertItinerary` writes inside a transaction (delete old day/location rows, insert new snapshot).
- `getItinerary` reconstructs `Day[]` from normalized day + location tables.

### Risk Cache

```ts
cacheRiskReport(tripId, report)
getLatestRiskReport(tripId)
```

- Stores JSON payload in `risk_reports.report_json`.
- Used as PREVENTION fallback when network risk endpoint fails.

### Incidents

```ts
upsertIncident(incident)
listPendingIncidents()
markIncidentSynced(incidentId)
```

- Persist incident immediately on capture.
- Transition `sync_status` when backend sync succeeds.

### Sync Queue

```ts
enqueueSyncJob({ entityType, entityId, operation, payload })
getPendingSyncJobs(limit?)
markSyncJobDone(jobId)
markSyncJobFailed(jobId, attempts)
```

- Queue failed network writes for deterministic replay.
- `markSyncJobFailed` applies retry backoff by setting `next_retry_at`.

## Integration Pattern (Service Layer)

Preferred pattern for API wrappers:
1. `await initializeOfflineDb()`
2. Attempt network call.
3. On success: update local SQLite cache/state.
4. On failure: persist local state and enqueue sync job.

This is implemented in:
- `src/features/trips/services/tripsApi.ts`
- `src/features/trips/services/itineraryApi.ts`
- `src/features/risk/services/riskApi.ts`
- `src/features/emergency/services/emergencyApi.ts`

## Using `useOfflineSync`

`useOfflineSync` replays queued jobs:

```ts
const { syncing, runSync, lastRunSummary } = useOfflineSync();

await runSync(async (job) => {
  // route by job.entity_type and send to backend
});
```

Expected usage:
- Trigger on reconnect (`useOnlineStatus`) or manual debug action.
- Keep processor deterministic and idempotent.

## Testing

Runtime smoke test:
- `tests/storage/sqliteCrud.smoke.ts`
- Dev route: `/dev/storage-test`

Covers:
- DB init
- metadata CRUD
- trip upsert/list
- itinerary upsert/get
- risk cache
- incident pending -> synced lifecycle

## Troubleshooting

### Init hangs or timeout

Check logs in:
- `/dev/storage-test` Live Logs panel
- Metro terminal running Expo

Look for:
- `[offlineDb] initialize start`
- `openDatabaseAsync timed out`
- `schema statement N timed out`
- `[offlineDb] initialize failed`

### Web bundling fails for WASM

If you see `Unable to resolve ... wa-sqlite.wasm`, ensure Metro supports wasm assets:
- `metro.config.js` includes `"wasm"` in `resolver.assetExts`.

## Security Notes / Residual Risk

- Current local SQLite data is not encrypted at rest.
- Sensitive incident/location fields should move to encrypted local storage strategy in a later hardening phase.
- Until then, treat local-device access as a risk boundary and communicate this in release notes.
