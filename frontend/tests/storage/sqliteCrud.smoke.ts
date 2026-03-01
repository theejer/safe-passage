import {
  cacheRiskReport,
  deleteMetadata,
  getItinerary,
  getLatestRiskReport,
  getMetadata,
  initializeOfflineDb,
  listPendingIncidents,
  listTrips,
  markIncidentSynced,
  setMetadata,
  upsertIncident,
  upsertItinerary,
  upsertTrip,
} from "@/features/storage/services/offlineDb";

import type { RiskReport } from "@/features/risk/types";
import type { Day, Trip } from "@/features/trips/types";

export type SmokeCheck = {
  name: string;
  ok: boolean;
  detail?: string;
};

export type SmokeReport = {
  ok: boolean;
  startedAt: string;
  finishedAt: string;
  checks: SmokeCheck[];
};

type SmokeLogger = (message: string) => void;

type SmokeOptions = {
  onLog?: SmokeLogger;
  checkTimeoutMs?: number;
};

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

async function runCheck(
  checks: SmokeCheck[],
  name: string,
  task: () => Promise<void>,
  options?: SmokeOptions
) {
  const onLog = options?.onLog;
  const timeoutMs = options?.checkTimeoutMs ?? 15000;

  const startedAt = Date.now();
  onLog?.(`▶️ START ${name}`);
  console.log(`[sqlite-smoke] START ${name}`);

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
    console.log(`[sqlite-smoke] PASS ${name} (${duration}ms)`);
  } catch (error) {
    const duration = Date.now() - startedAt;
    const detail = error instanceof Error ? error.message : "Unknown error";

    checks.push({
      name,
      ok: false,
      detail,
    });

    onLog?.(`❌ FAIL ${name} (${duration}ms) - ${detail}`);
    console.log(`[sqlite-smoke] FAIL ${name} (${duration}ms) - ${detail}`);
  }
}

export async function runSqliteCrudSmokeTest(options?: SmokeOptions): Promise<SmokeReport> {
  const onLog = options?.onLog;
  const checks: SmokeCheck[] = [];
  const startedAt = new Date().toISOString();

  const stamp = Date.now();
  const userId = `smoke-user-${stamp}`;
  const tripId = `smoke-trip-${stamp}`;
  const incidentId = `smoke-incident-${stamp}`;
  const metadataKey = `smoke-meta-${stamp}`;

  onLog?.(`ℹ️ Smoke test started at ${startedAt}`);
  console.log(`[sqlite-smoke] Smoke test started at ${startedAt}`);

  await runCheck(checks, "initializeOfflineDb", async () => {
    const init = await initializeOfflineDb();
    assert(init.initialized === true, "DB did not initialize");
  }, options);

  await runCheck(checks, "metadata CRUD", async () => {
    await setMetadata(metadataKey, "ok");
    const value = await getMetadata(metadataKey);
    assert(value === "ok", "Expected metadata value 'ok'");

    await deleteMetadata(metadataKey);
    const removed = await getMetadata(metadataKey);
    assert(removed === null, "Expected metadata row to be deleted");
  }, options);

  await runCheck(checks, "trip upsert/list", async () => {
    const trip: Trip = {
      id: tripId,
      userId,
      title: "SQLite Smoke Trip",
      startDate: "2026-03-02",
      endDate: "2026-03-05",
    };

    await upsertTrip(trip);

    const trips = await listTrips(userId);
    assert(Array.isArray(trips), "Expected listTrips to return array");
    assert(trips.some((item) => item.id === tripId), "Expected inserted trip in listTrips result");
  }, options);

  await runCheck(checks, "itinerary upsert/get", async () => {
    const days: Day[] = [
      {
        date: "2026-03-02",
        accommodation: "Sample Lodge",
        locations: [
          {
            name: "Gaya Station",
            district: "Gaya",
            block: "Gaya Town",
            connectivityZone: "moderate",
          },
        ],
      },
    ];

    await upsertItinerary(tripId, days);

    const itinerary = await getItinerary(tripId);
    assert(itinerary.length === 1, "Expected one itinerary day");
    assert(itinerary[0]?.locations?.[0]?.name === "Gaya Station", "Expected saved itinerary location");
  }, options);

  await runCheck(checks, "risk report cache/get", async () => {
    const report: RiskReport = {
      summary: "Moderate route risk and intermittent connectivity.",
      days: [
        {
          date: "2026-03-02",
          locations: [
            {
              name: "Gaya Station",
              locationRisk: "moderate",
              connectivityRisk: "high",
              expectedOfflineMinutes: 45,
            },
          ],
        },
      ],
    };

    await cacheRiskReport(tripId, report);

    const cached = await getLatestRiskReport(tripId);
    assert(!!cached, "Expected cached risk report");
    assert(cached?.summary === report.summary, "Expected cached summary to match");
  }, options);

  await runCheck(checks, "incident pending->synced lifecycle", async () => {
    await upsertIncident({
      id: incidentId,
      user_id: userId,
      trip_id: tripId,
      scenario_key: "medical",
      occurred_at: new Date().toISOString(),
      notes: "Smoke incident",
      severity: "moderate",
      sync_status: "pending",
    });

    const pendingBefore = await listPendingIncidents();
    assert(pendingBefore.some((item) => item.id === incidentId), "Expected incident in pending list");

    await markIncidentSynced(incidentId);

    const pendingAfter = await listPendingIncidents();
    assert(!pendingAfter.some((item) => item.id === incidentId), "Expected incident removed after sync mark");
  }, options);

  const finishedAt = new Date().toISOString();
  const ok = checks.every((check) => check.ok);

  onLog?.(`ℹ️ Smoke test finished at ${finishedAt} (overall: ${ok ? "PASS" : "FAIL"})`);
  console.log(`[sqlite-smoke] Smoke test finished at ${finishedAt} (overall: ${ok ? "PASS" : "FAIL"})`);

  return {
    ok,
    startedAt,
    finishedAt,
    checks,
  };
}
