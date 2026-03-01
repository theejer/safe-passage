import { sendScheduledHeartbeat, replayQueuedHeartbeats } from "@/features/heartbeat/services/heartbeatScheduler";
import { queueHeartbeat, replayHeartbeatSyncJob, type HeartbeatPayload } from "@/features/heartbeat/services/heartbeatApi";
import {
  getPendingSyncJobs,
  initializeOfflineDb,
  upsertTrip,
  type SyncQueueJob,
} from "@/features/storage/services/offlineDb";
import { removeItem, setItem } from "@/features/storage/services/localStore";
import type { Trip } from "@/features/trips/types";

export type HeartbeatSmokeCheck = {
  name: string;
  ok: boolean;
  detail?: string;
};

export type HeartbeatSmokeReport = {
  ok: boolean;
  startedAt: string;
  finishedAt: string;
  checks: HeartbeatSmokeCheck[];
};

type SmokeLogger = (message: string) => void;

type HeartbeatSmokeOptions = {
  onLog?: SmokeLogger;
  checkTimeoutMs?: number;
};

const ACTIVE_USER_ID_KEY = "active_user_id";
const ACTIVE_TRIP_ID_KEY = "active_trip_id";

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

async function runCheck(
  checks: HeartbeatSmokeCheck[],
  name: string,
  task: () => Promise<void>,
  options?: HeartbeatSmokeOptions
) {
  const onLog = options?.onLog;
  const timeoutMs = options?.checkTimeoutMs ?? 15000;

  const startedAt = Date.now();
  onLog?.(`▶️ START ${name}`);
  console.log(`[heartbeat-smoke] START ${name}`);

  try {
    await Promise.race([
      task(),
      new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error(`Timed out after ${timeoutMs}ms`)), timeoutMs);
      }),
    ]);

    checks.push({ name, ok: true });
    const duration = Date.now() - startedAt;
    onLog?.(`✅ PASS ${name} (${duration}ms)`);
    console.log(`[heartbeat-smoke] PASS ${name} (${duration}ms)`);
  } catch (error) {
    const duration = Date.now() - startedAt;
    const detail = error instanceof Error ? error.message : "Unknown error";
    checks.push({ name, ok: false, detail });
    onLog?.(`❌ FAIL ${name} (${duration}ms) - ${detail}`);
    console.log(`[heartbeat-smoke] FAIL ${name} (${duration}ms) - ${detail}`);
  }
}

function makePayload(userId: string, tripId: string): HeartbeatPayload {
  return {
    user_id: userId,
    trip_id: tripId,
    timestamp: new Date().toISOString(),
    network_status: "online",
    battery_percent: 80,
    source: "manual_debug",
    app_state: "active",
  };
}

export async function runHeartbeatRuntimeSmokeTest(options?: HeartbeatSmokeOptions): Promise<HeartbeatSmokeReport> {
  const onLog = options?.onLog;
  const checks: HeartbeatSmokeCheck[] = [];
  const startedAt = new Date().toISOString();

  const stamp = Date.now();
  const userId = `hb-user-${stamp}`;
  const tripIdEnabled = `hb-trip-enabled-${stamp}`;
  const tripIdDisabled = `hb-trip-disabled-${stamp}`;

  onLog?.(`ℹ️ Heartbeat smoke started at ${startedAt}`);

  await runCheck(
    checks,
    "initialize db",
    async () => {
      const init = await initializeOfflineDb();
      assert(init.initialized === true, "DB init failed");
    },
    options
  );

  await runCheck(
    checks,
    "queue heartbeat job",
    async () => {
      await queueHeartbeat(makePayload(userId, tripIdEnabled));
      const jobs = await getPendingSyncJobs(200);
      const hasHeartbeatJob = jobs.some(
        (job) =>
          job.entity_type === "heartbeat" &&
          job.entity_id.includes(tripIdEnabled)
      );
      assert(hasHeartbeatJob, "Expected queued heartbeat sync job");
    },
    options
  );

  await runCheck(
    checks,
    "replay job type guard",
    async () => {
      const nonHeartbeatJob: SyncQueueJob = {
        id: -1,
        entity_type: "trip",
        entity_id: "trip_123",
        operation: "upsert",
        payload_json: "{}",
        attempts: 0,
        status: "pending",
        next_retry_at: null,
        created_at: new Date().toISOString(),
      };

      let threw = false;
      try {
        await replayHeartbeatSyncJob(nonHeartbeatJob);
      } catch {
        threw = true;
      }
      assert(threw, "Expected replayHeartbeatSyncJob to reject non-heartbeat job");
    },
    options
  );

  await runCheck(
    checks,
    "scheduler skips without active context",
    async () => {
      await removeItem(ACTIVE_USER_ID_KEY);
      await removeItem(ACTIVE_TRIP_ID_KEY);
      const result = await sendScheduledHeartbeat("manual_debug");
      assert(result.status === "skipped", "Expected skipped when no active user/trip");
    },
    options
  );

  await runCheck(
    checks,
    "scheduler skips when active trip heartbeat disabled",
    async () => {
      const tripDisabled: Trip = {
        id: tripIdDisabled,
        userId,
        title: "HB Disabled",
        startDate: "2026-03-02",
        endDate: "2026-03-03",
        heartbeatEnabled: false,
      };
      await upsertTrip(tripDisabled);
      await setItem(ACTIVE_USER_ID_KEY, userId);
      await setItem(ACTIVE_TRIP_ID_KEY, tripIdDisabled);

      const result = await sendScheduledHeartbeat("manual_debug");
      assert(result.status === "skipped", "Expected skipped for heartbeat-disabled trip");
    },
    options
  );

  await runCheck(
    checks,
    "scheduler attempts send when heartbeat enabled",
    async () => {
      const tripEnabled: Trip = {
        id: tripIdEnabled,
        userId,
        title: "HB Enabled",
        startDate: "2026-03-02",
        endDate: "2026-03-03",
        heartbeatEnabled: true,
      };
      await upsertTrip(tripEnabled);
      await setItem(ACTIVE_USER_ID_KEY, userId);
      await setItem(ACTIVE_TRIP_ID_KEY, tripIdEnabled);

      const result = await sendScheduledHeartbeat("manual_debug");
      assert(result.status === "sent" || result.status === "queued", "Expected sent or queued for enabled trip");
    },
    options
  );

  await runCheck(
    checks,
    "replay queued heartbeat jobs",
    async () => {
      const replayResult = await replayQueuedHeartbeats();
      assert(replayResult.total >= 0, "Replay result should include total");
      assert(replayResult.replayed + replayResult.failed === replayResult.total, "Replay accounting should balance");
    },
    options
  );

  const finishedAt = new Date().toISOString();
  const ok = checks.every((check) => check.ok);

  onLog?.(`ℹ️ Heartbeat smoke finished at ${finishedAt} (${ok ? "PASS" : "FAIL"})`);

  return {
    ok,
    startedAt,
    finishedAt,
    checks,
  };
}
