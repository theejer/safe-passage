import { apiClient } from "@/lib/apiClient";
import type { Trip } from "@/features/trips/types";
import {
  enqueueSyncJob,
  initializeOfflineDb,
  listTrips as listLocalTrips,
  upsertTrip,
  type SyncQueueJob,
} from "@/features/storage/services/offlineDb";
import { setItem } from "@/features/storage/services/localStore";
import { canSyncTripOnline } from "@/shared/utils/syncGuards";
import { generateUuidV4 } from "@/shared/utils/ids";

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

// CRUD-ish API wrappers for trip metadata.
export async function createTrip(payload: TripCreateInput) {
  await initializeOfflineDb();

  const tripId = generateUuidV4();
  const wirePayload = {
    id: tripId,
    user_id: payload.userId,
    title: payload.title,
    start_date: payload.startDate,
    end_date: payload.endDate,
    heartbeat_enabled: payload.heartbeatEnabled ?? true,
  };

  const localTrip: Trip = {
    id: tripId,
    userId: payload.userId,
    title: payload.title,
    startDate: payload.startDate,
    endDate: payload.endDate,
    heartbeatEnabled: payload.heartbeatEnabled ?? true,
  };

  if (!canSyncTripOnline(payload.userId)) {
    await upsertTrip(localTrip);
    await enqueueSyncJob({
      entityType: "trip",
      entityId: localTrip.id,
      operation: "upsert",
      payload: wirePayload,
    });
    await setItem(ACTIVE_TRIP_ID_KEY, localTrip.id);
    return localTrip;
  }

  try {
    const response = await apiClient.post("/trips", wirePayload);
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
      payload: wirePayload,
    });
    return localTrip;
  }
}

export async function listTrips(userId: string) {
  await initializeOfflineDb();
  const localItems = await listLocalTrips(userId);

  if (!canSyncTripOnline(userId)) {
    return { items: localItems };
  }

  try {
    const response = (await apiClient.get(`/trips?user_id=${encodeURIComponent(userId)}`)) as {
      items?: TripWire[];
    };
    const normalizedItems = (response?.items ?? []).map(fromWireTrip);
    for (const trip of normalizedItems) {
      await upsertTrip(trip);
    }

    const mergedById = new Map<string, Trip>();
    for (const localTrip of localItems) {
      mergedById.set(localTrip.id, localTrip);
    }
    for (const remoteTrip of normalizedItems) {
      mergedById.set(remoteTrip.id, remoteTrip);
    }

    const merged = [...mergedById.values()].sort((a, b) => b.startDate.localeCompare(a.startDate));
    return { items: merged };
  } catch {
    return { items: localItems };
  }
}

export function getTrip(tripId: string) {
  // Placeholder; backend currently provides list and itinerary endpoints.
  return apiClient.get(`/trips/${tripId}/itinerary`);
}

export async function replayTripSyncJob(job: SyncQueueJob) {
  if (job.entity_type !== "trip") {
    throw new Error(`unsupported sync job entity type: ${job.entity_type}`);
  }

  const payload = JSON.parse(job.payload_json) as Record<string, unknown>;
  const response = (await apiClient.post("/trips", payload)) as TripWire;
  await upsertTrip(fromWireTrip(response));
}
