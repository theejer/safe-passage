import { apiClient } from "@/lib/apiClient";
import type { NetInfoStateType } from "@react-native-community/netinfo";
import { enqueueSyncJob, type SyncQueueJob } from "@/features/storage/services/offlineDb";

export type HeartbeatSource = "foreground" | "background_fetch" | "manual_debug";

export type HeartbeatPayload = {
  user_id: string;
  trip_id: string;
  timestamp: string;
  gps?: {
    lat: number;
    lng: number;
    accuracy_meters?: number;
  };
  battery_percent?: number;
  network_status: "online" | "offline" | "unknown";
  offline_minutes?: number;
  source: HeartbeatSource;
  network_type?: NetInfoStateType | "unknown";
  app_state?: "active" | "background" | "inactive";
};

function normalizeError(error: unknown) {
  return error instanceof Error ? error.message : "unknown-error";
}

function isHeartbeatAuthFailure(error: unknown) {
  const message = normalizeError(error);
  return /\b401\b|\b403\b|missing bearer token|invalid bearer token|token subject/i.test(message);
}

export async function sendHeartbeat(payload: HeartbeatPayload) {
  return apiClient.post("/heartbeat", payload);
}

export async function queueHeartbeat(payload: HeartbeatPayload) {
  const entityId = `${payload.trip_id}_${payload.timestamp}`;
  await enqueueSyncJob({
    entityType: "heartbeat",
    entityId,
    operation: "upsert",
    payload: payload as unknown as Record<string, unknown>,
  });
}

export async function sendOrQueueHeartbeat(payload: HeartbeatPayload) {
  try {
    await sendHeartbeat(payload);
    return { status: "sent" as const };
  } catch (error) {
    if (isHeartbeatAuthFailure(error)) {
      return { status: "dropped" as const, reason: normalizeError(error) };
    }

    await queueHeartbeat(payload);
    return { status: "queued" as const, reason: normalizeError(error) };
  }
}

export async function replayHeartbeatSyncJob(job: SyncQueueJob) {
  if (job.entity_type !== "heartbeat") {
    throw new Error(`unsupported sync job entity type: ${job.entity_type}`);
  }

  const payload = JSON.parse(job.payload_json) as HeartbeatPayload;
  await sendHeartbeat(payload);
}

export function isHeartbeatPermanentFailure(error: unknown) {
  return isHeartbeatAuthFailure(error);
}
