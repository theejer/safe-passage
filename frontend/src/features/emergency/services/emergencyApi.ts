import { apiClient } from "@/lib/apiClient";
import {
  enqueueSyncJob,
  initializeOfflineDb,
  markIncidentSynced,
  upsertIncident,
  type SyncQueueJob,
} from "@/features/storage/services/offlineDb";
import type { ScenarioKey } from "@/features/emergency/types";

type IncidentInput = {
  incident_id: string;
  user_id: string;
  trip_id?: string;
  scenario_key: ScenarioKey;
  occurred_at: string;
  gps_lat?: number;
  gps_lng?: number;
  notes?: string;
  severity?: "low" | "moderate" | "high" | "severe";
};

function parseIncidentPayload(payload: Record<string, unknown>) {
  const incidents = Array.isArray(payload.incidents)
    ? (payload.incidents as IncidentInput[])
    : [];
  return incidents;
}

// Sync queued incidents when device reconnects.
export async function syncIncident(payload: Record<string, unknown>) {
  await initializeOfflineDb();

  const incidents = parseIncidentPayload(payload);
  for (const incident of incidents) {
    await upsertIncident({
      id: incident.incident_id,
      user_id: incident.user_id,
      trip_id: incident.trip_id,
      scenario_key: incident.scenario_key,
      occurred_at: incident.occurred_at,
      gps_lat: incident.gps_lat,
      gps_lng: incident.gps_lng,
      notes: incident.notes,
      severity: incident.severity,
      sync_status: "pending",
    });
  }

  try {
    const response = await apiClient.post("/incidents/sync", payload);
    for (const incident of incidents) {
      await markIncidentSynced(incident.incident_id);
    }
    return response;
  } catch {
    await enqueueSyncJob({
      entityType: "incident_sync",
      entityId: String(payload.idempotency_key ?? `incsync_${Date.now()}`),
      operation: "sync",
      payload,
    });

    return {
      sync_status: "queued",
      queued_count: incidents.length,
    };
  }
}

export async function replayIncidentSyncJob(job: SyncQueueJob) {
  if (job.entity_type !== "incident_sync") {
    throw new Error(`unsupported sync job entity type: ${job.entity_type}`);
  }

  const payload = JSON.parse(job.payload_json) as Record<string, unknown>;
  const incidents = parseIncidentPayload(payload);
  await apiClient.post("/incidents/sync", payload);

  for (const incident of incidents) {
    await markIncidentSynced(incident.incident_id);
  }
}
