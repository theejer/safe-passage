import { apiClient } from "@/lib/apiClient";

// Fetches risk analysis data for PREVENTION screens.
export function getRiskReport(tripId: string) {
  // Backend may expose a dedicated /trips/{id}/risk in later iterations.
  return apiClient.get(`/trips/${tripId}/risk`);
}
