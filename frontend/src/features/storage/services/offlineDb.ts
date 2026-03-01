import { openDatabaseAsync, type SQLiteDatabase } from "expo-sqlite";
import type { ScenarioKey } from "@/features/emergency/types";
import type { RiskReport } from "@/features/risk/types";
import type { Day, Trip } from "@/features/trips/types";

const DB_NAME = "safepassage.db";
const SCHEMA_VERSION = "1";

let dbPromise: Promise<SQLiteDatabase> | null = null;
let initPromise: Promise<{ initialized: true; dbName: string; schemaVersion: string }> | null = null;
let initialized = false;

const INIT_TIMEOUT_MS = 30000;

export type SyncQueueJob = {
  id: number;
  entity_type: string;
  entity_id: string;
  operation: "upsert" | "delete" | "sync";
  payload_json: string;
  attempts: number;
  status: "pending" | "processing" | "done" | "failed";
  next_retry_at: string | null;
  created_at: string;
};

export type LocalIncident = {
  id: string;
  user_id: string;
  trip_id?: string;
  scenario_key: ScenarioKey;
  occurred_at: string;
  gps_lat?: number;
  gps_lng?: number;
  notes?: string;
  severity?: "low" | "moderate" | "high" | "severe";
  sync_status?: "pending" | "synced" | "failed";
};

async function getDb() {
  if (!dbPromise) {
    console.log("[offlineDb] opening database", DB_NAME);
    dbPromise = openDatabaseAsync(DB_NAME);
  }
  return dbPromise;
}

function withTimeout<T>(task: Promise<T>, timeoutMs: number, label: string): Promise<T> {
  return Promise.race([
    task,
    new Promise<never>((_, reject) => {
      setTimeout(() => reject(new Error(`${label} timed out after ${timeoutMs}ms`)), timeoutMs);
    }),
  ]);
}

function nowIso() {
  return new Date().toISOString();
}

export async function initializeOfflineDb() {
  if (initialized) {
    return { initialized: true as const, dbName: DB_NAME, schemaVersion: SCHEMA_VERSION };
  }

  if (initPromise) {
    return initPromise;
  }

  initPromise = (async () => {
    console.log("[offlineDb] initialize start");
    const db = await withTimeout(getDb(), INIT_TIMEOUT_MS, "openDatabaseAsync");

    const statements = [
      "PRAGMA foreign_keys = ON",
      `CREATE TABLE IF NOT EXISTS metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
      )`,
      `CREATE TABLE IF NOT EXISTS trips (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        title TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        sync_status TEXT NOT NULL DEFAULT 'pending'
      )`,
      `CREATE TABLE IF NOT EXISTS itinerary_days (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_id TEXT NOT NULL,
        day_index INTEGER NOT NULL,
        date TEXT NOT NULL,
        accommodation TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(trip_id, day_index)
      )`,
      `CREATE TABLE IF NOT EXISTS itinerary_locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_id TEXT NOT NULL,
        day_index INTEGER NOT NULL,
        location_index INTEGER NOT NULL,
        name TEXT NOT NULL,
        district TEXT,
        block TEXT,
        connectivity_zone TEXT,
        assumed_location_risk TEXT,
        UNIQUE(trip_id, day_index, location_index)
      )`,
      `CREATE TABLE IF NOT EXISTS risk_reports (
        id TEXT PRIMARY KEY,
        trip_id TEXT NOT NULL,
        report_json TEXT NOT NULL,
        summary TEXT,
        created_at TEXT NOT NULL,
        sync_status TEXT NOT NULL DEFAULT 'synced'
      )`,
      `CREATE TABLE IF NOT EXISTS incidents (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        trip_id TEXT,
        scenario_key TEXT NOT NULL,
        occurred_at TEXT NOT NULL,
        gps_lat REAL,
        gps_lng REAL,
        notes TEXT,
        severity TEXT,
        sync_status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      )`,
      `CREATE TABLE IF NOT EXISTS incident_attachments (
        id TEXT PRIMARY KEY,
        incident_id TEXT NOT NULL,
        attachment_type TEXT NOT NULL,
        local_uri TEXT,
        metadata_json TEXT,
        captured_at TEXT,
        created_at TEXT NOT NULL
      )`,
      `CREATE TABLE IF NOT EXISTS sync_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        operation TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'pending',
        next_retry_at TEXT,
        created_at TEXT NOT NULL
      )`,
      "CREATE INDEX IF NOT EXISTS idx_trips_user ON trips(user_id)",
      "CREATE INDEX IF NOT EXISTS idx_itinerary_day_trip ON itinerary_days(trip_id, day_index)",
      "CREATE INDEX IF NOT EXISTS idx_sync_queue_status ON sync_queue(status, created_at)",
      "CREATE INDEX IF NOT EXISTS idx_incidents_sync ON incidents(sync_status, occurred_at)",
    ];

    for (let index = 0; index < statements.length; index += 1) {
      await withTimeout(db.execAsync(statements[index]), INIT_TIMEOUT_MS, `schema statement ${index + 1}`);
    }

    await withTimeout(setMetadata("schema_version", SCHEMA_VERSION), INIT_TIMEOUT_MS, "schema metadata write");

    initialized = true;
    console.log("[offlineDb] initialize complete");
    return { initialized: true as const, dbName: DB_NAME, schemaVersion: SCHEMA_VERSION };
  })();

  try {
    return await initPromise;
  } catch (error) {
    console.log("[offlineDb] initialize failed", error);
    dbPromise = null;
    throw error;
  } finally {
    initPromise = null;
  }
}

export async function setMetadata(key: string, value: string) {
  const db = await getDb();
  await db.runAsync(
    `
      INSERT INTO metadata (key, value, updated_at)
      VALUES (?, ?, ?)
      ON CONFLICT(key) DO UPDATE SET
        value = excluded.value,
        updated_at = excluded.updated_at
    `,
    [key, value, nowIso()]
  );
}

export async function getMetadata(key: string) {
  const db = await getDb();
  const row = await db.getFirstAsync<{ value: string }>("SELECT value FROM metadata WHERE key = ?", [key]);
  return row?.value ?? null;
}

export async function deleteMetadata(key: string) {
  const db = await getDb();
  await db.runAsync("DELETE FROM metadata WHERE key = ?", [key]);
}

export async function upsertTrip(trip: Trip) {
  const db = await getDb();
  const createdAt = nowIso();
  await db.runAsync(
    `
      INSERT INTO trips (id, user_id, title, start_date, end_date, created_at, updated_at, sync_status)
      VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
      ON CONFLICT(id) DO UPDATE SET
        user_id = excluded.user_id,
        title = excluded.title,
        start_date = excluded.start_date,
        end_date = excluded.end_date,
        updated_at = excluded.updated_at,
        sync_status = 'pending'
    `,
    [trip.id, trip.userId, trip.title, trip.startDate, trip.endDate, createdAt, createdAt]
  );
}

export async function listTrips(userId: string) {
  const db = await getDb();
  const rows = await db.getAllAsync<{
    id: string;
    user_id: string;
    title: string;
    start_date: string;
    end_date: string;
  }>(
    "SELECT id, user_id, title, start_date, end_date FROM trips WHERE user_id = ? ORDER BY start_date DESC",
    [userId]
  );

  return rows.map((row) => ({
    id: row.id,
    userId: row.user_id,
    title: row.title,
    startDate: row.start_date,
    endDate: row.end_date,
  })) as Trip[];
}

export async function upsertItinerary(tripId: string, days: Day[]) {
  const db = await getDb();
  const timestamp = nowIso();

  await db.withTransactionAsync(async () => {
    await db.runAsync("DELETE FROM itinerary_locations WHERE trip_id = ?", [tripId]);
    await db.runAsync("DELETE FROM itinerary_days WHERE trip_id = ?", [tripId]);

    for (let dayIndex = 0; dayIndex < days.length; dayIndex += 1) {
      const day = days[dayIndex];
      await db.runAsync(
        `
          INSERT INTO itinerary_days (trip_id, day_index, date, accommodation, created_at, updated_at)
          VALUES (?, ?, ?, ?, ?, ?)
        `,
        [tripId, dayIndex, day.date, day.accommodation ?? null, timestamp, timestamp]
      );

      for (let locationIndex = 0; locationIndex < day.locations.length; locationIndex += 1) {
        const location = day.locations[locationIndex];
        await db.runAsync(
          `
            INSERT INTO itinerary_locations
              (trip_id, day_index, location_index, name, district, block, connectivity_zone, assumed_location_risk)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
          `,
          [
            tripId,
            dayIndex,
            locationIndex,
            location.name,
            location.district ?? null,
            location.block ?? null,
            location.connectivityZone ?? null,
            null,
          ]
        );
      }
    }
  });
}

export async function getItinerary(tripId: string) {
  const db = await getDb();
  const dayRows = await db.getAllAsync<{
    day_index: number;
    date: string;
    accommodation: string | null;
  }>(
    "SELECT day_index, date, accommodation FROM itinerary_days WHERE trip_id = ? ORDER BY day_index ASC",
    [tripId]
  );

  const locationRows = await db.getAllAsync<{
    day_index: number;
    location_index: number;
    name: string;
    district: string | null;
    block: string | null;
    connectivity_zone: string | null;
  }>(
    `
      SELECT day_index, location_index, name, district, block, connectivity_zone
      FROM itinerary_locations
      WHERE trip_id = ?
      ORDER BY day_index ASC, location_index ASC
    `,
    [tripId]
  );

  const locationsByDay = new Map<number, typeof locationRows>();
  for (const row of locationRows) {
    const existing = locationsByDay.get(row.day_index) ?? [];
    existing.push(row);
    locationsByDay.set(row.day_index, existing);
  }

  return dayRows.map((day) => ({
    date: day.date,
    accommodation: day.accommodation ?? undefined,
    locations: (locationsByDay.get(day.day_index) ?? []).map((location) => ({
      name: location.name,
      district: location.district ?? undefined,
      block: location.block ?? undefined,
      connectivityZone: location.connectivity_zone as Day["locations"][number]["connectivityZone"],
    })),
  })) as Day[];
}

export async function cacheRiskReport(tripId: string, report: RiskReport) {
  const db = await getDb();
  const id = `risk_${tripId}`;
  const createdAt = nowIso();
  await db.runAsync(
    `
      INSERT INTO risk_reports (id, trip_id, report_json, summary, created_at, sync_status)
      VALUES (?, ?, ?, ?, ?, 'synced')
      ON CONFLICT(id) DO UPDATE SET
        report_json = excluded.report_json,
        summary = excluded.summary,
        created_at = excluded.created_at
    `,
    [id, tripId, JSON.stringify(report), report.summary ?? null, createdAt]
  );
}

export async function getLatestRiskReport(tripId: string) {
  const db = await getDb();
  const row = await db.getFirstAsync<{ report_json: string }>(
    "SELECT report_json FROM risk_reports WHERE trip_id = ? ORDER BY created_at DESC LIMIT 1",
    [tripId]
  );
  if (!row) return null;

  try {
    return JSON.parse(row.report_json) as RiskReport;
  } catch {
    return null;
  }
}

export async function upsertIncident(incident: LocalIncident) {
  const db = await getDb();
  const timestamp = nowIso();
  await db.runAsync(
    `
      INSERT INTO incidents
        (id, user_id, trip_id, scenario_key, occurred_at, gps_lat, gps_lng, notes, severity, sync_status, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(id) DO UPDATE SET
        user_id = excluded.user_id,
        trip_id = excluded.trip_id,
        scenario_key = excluded.scenario_key,
        occurred_at = excluded.occurred_at,
        gps_lat = excluded.gps_lat,
        gps_lng = excluded.gps_lng,
        notes = excluded.notes,
        severity = excluded.severity,
        sync_status = excluded.sync_status,
        updated_at = excluded.updated_at
    `,
    [
      incident.id,
      incident.user_id,
      incident.trip_id ?? null,
      incident.scenario_key,
      incident.occurred_at,
      incident.gps_lat ?? null,
      incident.gps_lng ?? null,
      incident.notes ?? null,
      incident.severity ?? null,
      incident.sync_status ?? "pending",
      timestamp,
      timestamp,
    ]
  );
}

export async function listPendingIncidents() {
  const db = await getDb();
  return db.getAllAsync<LocalIncident>(
    `
      SELECT id, user_id, trip_id, scenario_key, occurred_at, gps_lat, gps_lng, notes, severity, sync_status
      FROM incidents
      WHERE sync_status IN ('pending', 'failed')
      ORDER BY occurred_at ASC
    `
  );
}

export async function markIncidentSynced(incidentId: string) {
  const db = await getDb();
  await db.runAsync("UPDATE incidents SET sync_status = 'synced', updated_at = ? WHERE id = ?", [nowIso(), incidentId]);
}

export async function enqueueSyncJob(params: {
  entityType: string;
  entityId: string;
  operation: "upsert" | "delete" | "sync";
  payload: Record<string, unknown>;
}) {
  const db = await getDb();
  await db.runAsync(
    `
      INSERT INTO sync_queue (entity_type, entity_id, operation, payload_json, attempts, status, next_retry_at, created_at)
      VALUES (?, ?, ?, ?, 0, 'pending', NULL, ?)
    `,
    [params.entityType, params.entityId, params.operation, JSON.stringify(params.payload), nowIso()]
  );
}

export async function getPendingSyncJobs(limit = 50) {
  const db = await getDb();
  return db.getAllAsync<SyncQueueJob>(
    `
      SELECT id, entity_type, entity_id, operation, payload_json, attempts, status, next_retry_at, created_at
      FROM sync_queue
      WHERE status IN ('pending', 'failed')
      ORDER BY created_at ASC
      LIMIT ?
    `,
    [limit]
  );
}

export async function markSyncJobDone(jobId: number) {
  const db = await getDb();
  await db.runAsync("UPDATE sync_queue SET status = 'done' WHERE id = ?", [jobId]);
}

export async function markSyncJobFailed(jobId: number, attempts: number) {
  const db = await getDb();
  const retryAt = new Date(Date.now() + Math.min(300000, attempts * 15000)).toISOString();
  await db.runAsync(
    "UPDATE sync_queue SET status = 'failed', attempts = ?, next_retry_at = ? WHERE id = ?",
    [attempts, retryAt, jobId]
  );
}
