import type { ScenarioKey } from "@/features/emergency/types";
import type { RiskReport } from "@/features/risk/types";
import type { Day, Trip } from "@/features/trips/types";

const SCHEMA_VERSION = "1";
const WEB_STORE_KEY = "safepassage.web.offline.store.v1";

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

type MemoryTripRecord = {
  id: string;
  user_id: string;
  title: string;
  start_date: string;
  end_date: string;
  heartbeat_enabled: number;
};

type MemoryStore = {
  initialized: boolean;
  metadata: Map<string, string>;
  trips: Map<string, MemoryTripRecord>;
  itineraries: Map<string, Day[]>;
  riskReports: Map<string, RiskReport>;
  incidents: Map<string, LocalIncident>;
  syncQueue: SyncQueueJob[];
  nextSyncQueueId: number;
};

declare global {
  // eslint-disable-next-line no-var
  var __safepassageWebMemoryStore__: MemoryStore | undefined;
}

function isStorageAvailable() {
  try {
  } catch {
    return false;
  }
}

function hydrateStoreFromLocalStorage(): MemoryStore | null {
  if (!isStorageAvailable()) return null;

  try {
    const raw = globalThis.localStorage.getItem(WEB_STORE_KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw) as {
      initialized?: boolean;
      metadata?: Record<string, string>;
      trips?: MemoryTripRecord[];
      itineraries?: Record<string, Day[]>;
      riskReports?: Record<string, RiskReport>;
      incidents?: LocalIncident[];
      syncQueue?: SyncQueueJob[];
      nextSyncQueueId?: number;
    };

    return {
      initialized: Boolean(parsed.initialized),
      metadata: new Map<string, string>(Object.entries(parsed.metadata ?? {})),
      trips: new Map<string, MemoryTripRecord>((parsed.trips ?? []).map((trip) => [trip.id, trip])),
      itineraries: new Map<string, Day[]>(Object.entries(parsed.itineraries ?? {})),
      riskReports: new Map<string, RiskReport>(Object.entries(parsed.riskReports ?? {})),
      incidents: new Map<string, LocalIncident>((parsed.incidents ?? []).map((incident) => [incident.id, incident])),
      syncQueue: parsed.syncQueue ?? [],
      nextSyncQueueId: parsed.nextSyncQueueId ?? 1,
    };
  } catch {
    return null;
  }
}

function persistStoreToLocalStorage(store: MemoryStore) {
  if (!isStorageAvailable()) return;

  try {
    const serialized = JSON.stringify({
      initialized: store.initialized,
      metadata: Object.fromEntries(store.metadata),
      trips: [...store.trips.values()],
      itineraries: Object.fromEntries(store.itineraries),
      riskReports: Object.fromEntries(store.riskReports),
      incidents: [...store.incidents.values()],
      syncQueue: store.syncQueue,
      nextSyncQueueId: store.nextSyncQueueId,
    });
    globalThis.localStorage.setItem(WEB_STORE_KEY, serialized);
  } catch {
    // Best-effort persistence only.
  }
}

function getStore(): MemoryStore {
  if (!globalThis.__safepassageWebMemoryStore__) {
    globalThis.__safepassageWebMemoryStore__ = hydrateStoreFromLocalStorage() ?? {
      initialized: false,
      metadata: new Map<string, string>(),
      trips: new Map<string, MemoryTripRecord>(),
      itineraries: new Map<string, Day[]>(),
      riskReports: new Map<string, RiskReport>(),
      incidents: new Map<string, LocalIncident>(),
      syncQueue: [],
      nextSyncQueueId: 1,
    };
  }
  return globalThis.__safepassageWebMemoryStore__;
}

function nowIso() {
  return new Date().toISOString();
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function toTrip(record: MemoryTripRecord): Trip {
  return {
    id: record.id,
    userId: record.user_id,
    title: record.title,
    startDate: record.start_date,
    endDate: record.end_date,
    heartbeatEnabled: record.heartbeat_enabled === 1,
  };
}

export async function initializeOfflineDb() {
  const store = getStore();
  if (!store.initialized) {
    store.metadata.set("schema_version", SCHEMA_VERSION);
    store.initialized = true;
    persistStoreToLocalStorage(store);
    console.log("[offlineDb:web] initialized in-memory storage adapter");
  }

  return { initialized: true as const, dbName: "web-memory", schemaVersion: SCHEMA_VERSION };
}

export async function setMetadata(key: string, value: string) {
  const store = getStore();
  store.metadata.set(key, value);
  persistStoreToLocalStorage(store);
}

export async function getMetadata(key: string) {
  const store = getStore();
  return store.metadata.get(key) ?? null;
}

export async function deleteMetadata(key: string) {
  const store = getStore();
  store.metadata.delete(key);
  persistStoreToLocalStorage(store);
}

export async function upsertTrip(trip: Trip) {
  const store = getStore();
  store.trips.set(trip.id, {
    id: trip.id,
    user_id: trip.userId,
    title: trip.title,
    start_date: trip.startDate,
    end_date: trip.endDate,
    heartbeat_enabled: trip.heartbeatEnabled ? 1 : 0,
  });
  persistStoreToLocalStorage(store);
}

export async function listTrips(userId: string) {
  const store = getStore();
  return [...store.trips.values()]
    .filter((trip) => trip.user_id === userId)
    .sort((a, b) => b.start_date.localeCompare(a.start_date))
    .map(toTrip);
}

export async function getTripById(tripId: string) {
  const store = getStore();
  const record = store.trips.get(tripId);
  return record ? toTrip(record) : null;
}

export async function upsertItinerary(tripId: string, days: Day[]) {
  const store = getStore();
  store.itineraries.set(tripId, clone(days));
  persistStoreToLocalStorage(store);
}

export async function getItinerary(tripId: string) {
  const store = getStore();
  return clone(store.itineraries.get(tripId) ?? []);
}

export async function cacheRiskReport(tripId: string, report: RiskReport) {
  const store = getStore();
  store.riskReports.set(tripId, clone(report));
  persistStoreToLocalStorage(store);
}

export async function getLatestRiskReport(tripId: string) {
  const store = getStore();
  const report = store.riskReports.get(tripId);
  return report ? clone(report) : null;
}

export async function upsertIncident(incident: LocalIncident) {
  const store = getStore();
  store.incidents.set(incident.id, { ...incident, sync_status: incident.sync_status ?? "pending" });
  persistStoreToLocalStorage(store);
}

export async function listPendingIncidents() {
  const store = getStore();
  return [...store.incidents.values()]
    .filter((incident) => incident.sync_status === "pending" || incident.sync_status === "failed")
    .sort((a, b) => a.occurred_at.localeCompare(b.occurred_at));
}

export async function markIncidentSynced(incidentId: string) {
  const store = getStore();
  const existing = store.incidents.get(incidentId);
  if (!existing) return;
  store.incidents.set(incidentId, { ...existing, sync_status: "synced" });
  persistStoreToLocalStorage(store);
}

export async function enqueueSyncJob(params: {
  entityType: string;
  entityId: string;
  operation: "upsert" | "delete" | "sync";
  payload: Record<string, unknown>;
}) {
  const store = getStore();
  const job: SyncQueueJob = {
    id: store.nextSyncQueueId,
    entity_type: params.entityType,
    entity_id: params.entityId,
    operation: params.operation,
    payload_json: JSON.stringify(params.payload),
    attempts: 0,
    status: "pending",
    next_retry_at: null,
    created_at: nowIso(),
  };
  store.nextSyncQueueId += 1;
  store.syncQueue.push(job);
  persistStoreToLocalStorage(store);
}

export async function getPendingSyncJobs(limit = 50) {
  const store = getStore();
  return store.syncQueue
    .filter((job) => job.status === "pending" || job.status === "failed")
    .sort((a, b) => a.created_at.localeCompare(b.created_at))
    .slice(0, limit)
    .map((job) => ({ ...job }));
}

export async function markSyncJobDone(jobId: number) {
  const store = getStore();
  const index = store.syncQueue.findIndex((job) => job.id === jobId);
  if (index === -1) return;
  store.syncQueue[index] = { ...store.syncQueue[index], status: "done" };
  persistStoreToLocalStorage(store);
}

export async function markSyncJobFailed(jobId: number, attempts: number) {
  const store = getStore();
  const index = store.syncQueue.findIndex((job) => job.id === jobId);
  if (index === -1) return;

  const retryAt = new Date(Date.now() + Math.min(300000, attempts * 15000)).toISOString();
  store.syncQueue[index] = {
    ...store.syncQueue[index],
    status: "failed",
    attempts,
    next_retry_at: retryAt,
  };
  persistStoreToLocalStorage(store);
}
