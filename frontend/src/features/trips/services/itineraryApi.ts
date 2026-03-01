import { apiClient } from "@/lib/apiClient";
import type { Day } from "@/features/trips/types";

// Routes itinerary JSON to backend and fetches latest snapshot.
export function upsertItinerary(tripId: string, days: Day[]) {
  return apiClient.put(`/trips/${tripId}/itinerary`, { days, meta: {} });
}

export function getLatestItinerary(tripId: string) {
  return apiClient.get(`/trips/${tripId}/itinerary`);
}
