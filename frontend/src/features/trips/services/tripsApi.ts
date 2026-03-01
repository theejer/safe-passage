import { apiClient } from "@/lib/apiClient";
import type { Trip } from "@/features/trips/types";

// CRUD-ish API wrappers for trip metadata.
export function createTrip(payload: Pick<Trip, "userId" | "title" | "startDate" | "endDate">) {
  return apiClient.post("/trips", payload);
}

export function listTrips(userId: string) {
  return apiClient.get(`/trips?user_id=${encodeURIComponent(userId)}`);
}

export function getTrip(tripId: string) {
  // Placeholder; backend currently provides list and itinerary endpoints.
  return apiClient.get(`/trips/${tripId}/itinerary`);
}
