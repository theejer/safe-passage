import { apiClient } from "@/lib/apiClient";
import type { Day } from "@/features/trips/types";
import {
  enqueueSyncJob,
  getItinerary,
  initializeOfflineDb,
  upsertItinerary as upsertLocalItinerary,
} from "@/features/storage/services/offlineDb";
import { canSyncItineraryOnline } from "@/shared/utils/syncGuards";

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

type DayWireFlexible = {
  date?: string;
  day_label?: string;
  accommodation?: string;
  stay?: string;
  hotel?: string;
  locations?: Array<{
    name?: string;
    location?: string;
    place?: string;
    activity?: string;
    district?: string;
    block?: string;
    connectivity_zone?: string;
    connectivityZone?: string;
  }>;
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

function fromWireDays(days: DayWireFlexible[]): Day[] {
  return days.map((day) => ({
    date: day.date ?? day.day_label ?? "",
    accommodation: day.accommodation ?? day.stay ?? day.hotel,
    locations: (day.locations ?? [])
      .map((location) => {
        const locationName = location.name ?? location.location ?? location.place ?? location.activity ?? "";
        return {
          name: locationName,
          district: location.district,
          block: location.block,
          connectivityZone: (location.connectivity_zone ?? location.connectivityZone) as Day["locations"][number]["connectivityZone"],
        };
      })
      .filter((location) => location.name.trim().length > 0),
  }));
}

// Routes itinerary JSON to backend and fetches latest snapshot.
export async function upsertItinerary(tripId: string, days: Day[]) {
  await initializeOfflineDb();
  await upsertLocalItinerary(tripId, days);

  const wireDays = toWireDays(days);

  if (!canSyncItineraryOnline(tripId)) {
    return { trip_id: tripId, days: wireDays, meta: { saved: false, local_only: true } };
  }

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

  if (!canSyncItineraryOnline(tripId)) {
    return getItinerary(tripId);
  }

  try {
    const response = (await apiClient.get(`/trips/${tripId}/itinerary`)) as { days?: DayWire[] };
    const normalizedDays = fromWireDays(response.days ?? []);
    await upsertLocalItinerary(tripId, normalizedDays);
    return normalizedDays;
  } catch {
    return getItinerary(tripId);
  }
}

// Upload itinerary document and extract structured itinerary.
export async function uploadItineraryPDF(formData: FormData) {
  const env = await import("@/shared/config/env").then(m => m.env);
  
  const response = await fetch(`${env.BACKEND_URL}/trips/upload-pdf`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to upload itinerary file: ${response.status} ${error}`);
  }

  const result = (await response.json()) as { days?: DayWireFlexible[] };
  return fromWireDays(result.days ?? []);
}
