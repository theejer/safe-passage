import { apiClient } from "@/lib/apiClient";
import type { Trip } from "@/features/trips/types";
import {
  enqueueSyncJob,
  initializeOfflineDb,
  listTrips as listLocalTrips,
  upsertTrip,
} from "@/features/storage/services/offlineDb";
import { setItem } from "@/features/storage/services/localStore";

const ACTIVE_TRIP_ID_KEY = "active_trip_id";

type TripWire = {
  id: string;
  user_id: string;
  title: string;
  start_date: string;
  end_date: string;
  heartbeat_enabled?: boolean;
};

type TripCreateInput = Pick<Trip, "userId" | "title" | "startDate" | "endDate"> & {
  heartbeatEnabled?: boolean;
};

function fromWireTrip(value: TripWire): Trip {
  return {
    id: value.id,
    userId: value.user_id,
    title: value.title,
    startDate: value.start_date,
    endDate: value.end_date,
    heartbeatEnabled: value.heartbeat_enabled ?? true,
  };
}

function toWireTrip(payload: TripCreateInput) {
  return {
    user_id: payload.userId,
    title: payload.title,
    start_date: payload.startDate,
    end_date: payload.endDate,
    heartbeat_enabled: payload.heartbeatEnabled ?? true,
  };
}

// CRUD-ish API wrappers for trip metadata.
export async function createTrip(payload: TripCreateInput) {
  await initializeOfflineDb();

  const localTrip: Trip = {
    id: `local_${Date.now()}`,
    userId: payload.userId,
    title: payload.title,
    startDate: payload.startDate,
    endDate: payload.endDate,
    heartbeatEnabled: payload.heartbeatEnabled ?? true,
  };

  try {
    const response = await apiClient.post("/trips", toWireTrip(payload));
    const wireTrip = response as TripWire;
    const normalized = fromWireTrip(wireTrip);
    await upsertTrip(normalized);
    await setItem(ACTIVE_TRIP_ID_KEY, normalized.id);
    return normalized;
  } catch {
    await upsertTrip(localTrip);
    await setItem(ACTIVE_TRIP_ID_KEY, localTrip.id);
    await enqueueSyncJob({
      entityType: "trip",
      entityId: localTrip.id,
      operation: "upsert",
      payload: toWireTrip(payload),
    });
    return localTrip;
  }
}

export async function listTrips(userId: string) {
  await initializeOfflineDb();

  try {
    const response = (await apiClient.get(`/trips?user_id=${encodeURIComponent(userId)}`)) as {
      items?: TripWire[];
    };
    const normalizedItems = (response?.items ?? []).map(fromWireTrip);
    for (const trip of normalizedItems) {
      await upsertTrip(trip);
    }
    return { items: normalizedItems };
  } catch {
    const localItems = await listLocalTrips(userId);
    return { items: localItems };
  }
}

export function getTrip(tripId: string) {
  // Placeholder; backend currently provides list and itinerary endpoints.
  return apiClient.get(`/trips/${tripId}/itinerary`);
}
