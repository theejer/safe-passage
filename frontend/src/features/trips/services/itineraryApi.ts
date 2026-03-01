import { apiClient } from "@/lib/apiClient";
import type { Day } from "@/features/trips/types";
import {
  enqueueSyncJob,
  getItinerary,
  initializeOfflineDb,
  upsertItinerary as upsertLocalItinerary,
} from "@/features/storage/services/offlineDb";

type DayWire = {
  date: string;
  locations: Array<{
    name: string;
    district?: string;
    block?: string;
    connectivity_zone?: string;
    assumed_location_risk?: string;
  }>;
  accommodation?: string;
};

function toWireDays(days: Day[]): DayWire[] {
  return days.map((day) => ({
    date: day.date,
    accommodation: day.accommodation,
    locations: day.locations.map((location) => ({
      name: location.name,
      district: location.district,
      block: location.block,
      connectivity_zone: location.connectivityZone,
    })),
  }));
}

function fromWireDays(days: DayWire[]): Day[] {
  return days.map((day) => ({
    date: day.date,
    accommodation: day.accommodation,
    locations: day.locations.map((location) => ({
      name: location.name,
      district: location.district,
      block: location.block,
      connectivityZone: location.connectivity_zone as Day["locations"][number]["connectivityZone"],
    })),
  }));
}

// Routes itinerary JSON to backend and fetches latest snapshot.
export async function upsertItinerary(tripId: string, days: Day[]) {
  await initializeOfflineDb();
  await upsertLocalItinerary(tripId, days);

  const wireDays = toWireDays(days);
  try {
    return await apiClient.put(`/trips/${tripId}/itinerary`, { days: wireDays, meta: {} });
  } catch {
    await enqueueSyncJob({
      entityType: "itinerary",
      entityId: tripId,
      operation: "upsert",
      payload: { trip_id: tripId, days: wireDays, meta: {} },
    });
    return { trip_id: tripId, days: wireDays, meta: {} };
  }
}

export async function getLatestItinerary(tripId: string) {
  await initializeOfflineDb();

  try {
    const response = (await apiClient.get(`/trips/${tripId}/itinerary`)) as { days?: DayWire[] };
    const normalizedDays = fromWireDays(response.days ?? []);
    await upsertLocalItinerary(tripId, normalizedDays);
    return normalizedDays;
  } catch {
    return getItinerary(tripId);
  }
}
