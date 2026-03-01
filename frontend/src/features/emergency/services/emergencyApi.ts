import { apiClient } from "@/lib/apiClient";

// Sync queued incidents when device reconnects.
export function syncIncident(payload: Record<string, unknown>) {
  return apiClient.post("/incidents/sync", payload);
}
