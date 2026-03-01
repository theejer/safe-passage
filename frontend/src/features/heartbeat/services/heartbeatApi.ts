import { apiClient } from "@/lib/apiClient";

// Backend ingestion endpoint for CURE heartbeat stream.
export function sendHeartbeat(payload: Record<string, unknown>) {
  return apiClient.post("/heartbeats", payload);
}
