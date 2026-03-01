# Heartbeat Frontend Runtime

This feature implements the CURE heartbeat loop for SafePassage mobile clients, with offline queueing and reconnect replay.

## What it does

- Sends heartbeat payloads while the app is active (foreground interval).
- Registers a best-effort background fetch task on supported platforms (non-web).
- Queues heartbeat jobs to local storage when network/API send fails.
- Replays queued heartbeat jobs when connectivity returns.

## Runtime flow

1. `app/_layout.tsx` wires heartbeat startup at app boot:
	 - `registerHeartbeatTask()`
	 - `startForegroundHeartbeatLoop()`
2. Scheduler resolves context (`active_user_id`, `active_trip_id`).
3. Scheduler builds payload using timestamp + connectivity + battery + source.
4. `sendOrQueueHeartbeat()` sends to backend, or enqueues a `sync_queue` heartbeat job on failure.
5. When online status flips true, `replayQueuedHeartbeats()` flushes queued heartbeat jobs.

## Integration points (use in other features)

### 1) Turn heartbeat on/off for a trip

Heartbeat is controlled per trip by `Trip.heartbeatEnabled` (frontend) / `heartbeat_enabled` (wire format).

When creating trips via `createTrip`, pass the value explicitly:

```ts
await createTrip({
	userId,
	title,
	startDate,
	endDate,
	heartbeatEnabled: true,
});
```

If `heartbeatEnabled` is false, scheduler context resolution will skip that trip.

### 2) Ensure auth/context keys are set

Required local keys:

- `active_user_id`: currently selected user.
- `active_trip_id`: trip selected for heartbeat sends.
- `auth_bearer_token`: JWT used by backend `POST /heartbeat` auth.

If `active_trip_id` is missing or invalid, scheduler auto-selects the first local trip where `heartbeatEnabled === true`.

### 3) Trigger heartbeat from another screen/service

Use `sendScheduledHeartbeat(source)` from `heartbeatScheduler.ts`:

```ts
import { sendScheduledHeartbeat } from "@/features/heartbeat/services/heartbeatScheduler";

await sendScheduledHeartbeat("manual_debug");
```

Supported sources: `foreground`, `background_fetch`, `manual_debug`.

### 4) Plug replay into reconnect flows

Use `replayQueuedHeartbeats()` after reconnect if you create custom connectivity handlers:

```ts
import { replayQueuedHeartbeats } from "@/features/heartbeat/services/heartbeatScheduler";

await replayQueuedHeartbeats();
```

## Variables and settings that control current behavior

### Frontend constants/config

- `HEARTBEAT_INTERVAL_MINUTES` (`src/shared/config/constants.ts`)
	- Default `10`; controls both foreground interval and requested background minimum interval.

### Local storage keys

- `active_user_id` (required)
- `active_trip_id` (required for deterministic trip targeting; auto-recovered when missing)
- `auth_bearer_token` (required for authenticated backend ingest)

### Per-trip switch

- `Trip.heartbeatEnabled` / wire `heartbeat_enabled`
	- Default true at trip creation.
	- If false, heartbeat context resolution skips the trip.

### Platform behavior switch

- `Platform.OS === "web"`
	- Background task registration is skipped.
	- Foreground send + queue/replay still works.

## Payload contract sent from frontend

`HeartbeatPayload` currently includes:

- `user_id`, `trip_id`, `timestamp`
- `gps` (optional)
- `battery_percent` (optional)
- `network_status` (`online | offline | unknown`)
- `offline_minutes` (optional)
- `source` (`foreground | background_fetch | manual_debug`)
- `network_type` (optional)
- `app_state` (optional)

Backend currently validates/uses the documented ingest schema fields and ignores extra fields not in schema.

## Files to touch when extending heartbeat

- `src/features/heartbeat/services/heartbeatScheduler.ts`
	- Interval policy, app-state gating, background registration, replay policy.
- `src/features/heartbeat/services/heartbeatApi.ts`
	- Wire contract, send/queue/replay logic.
- `src/features/trips/services/tripsApi.ts`
	- Trip-level heartbeat opt-in defaults.
- `src/lib/apiClient.ts`
	- Authorization header wiring via `auth_bearer_token`.
- `app/_layout.tsx`
	- Global lifecycle wiring.

## Validation checklist

- Set `active_user_id`, `active_trip_id`, and `auth_bearer_token`.
- Ensure selected trip has `heartbeatEnabled=true`.
- Send manual heartbeat from `app/heartbeat.tsx`.
- Disable network and verify heartbeat queues.
- Re-enable network and verify replay marks jobs done.
