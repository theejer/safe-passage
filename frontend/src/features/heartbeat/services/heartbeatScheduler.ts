import { AppState, Platform, type AppStateStatus } from "react-native";
import * as BackgroundFetch from "expo-background-fetch";
import * as Battery from "expo-battery";
import * as TaskManager from "expo-task-manager";
import NetInfo, { type NetInfoStateType } from "@react-native-community/netinfo";
import { HEARTBEAT_INTERVAL_MINUTES } from "@/shared/config/constants";
import {
  getPendingSyncJobs,
  getTripById,
  initializeOfflineDb,
  listTrips,
  markSyncJobDone,
  markSyncJobFailed,
} from "@/features/storage/services/offlineDb";
import { getItem, setItem } from "@/features/storage/services/localStore";
import {
  replayHeartbeatSyncJob,
  sendOrQueueHeartbeat,
  type HeartbeatPayload,
} from "@/features/heartbeat/services/heartbeatApi";

const HEARTBEAT_TASK_NAME = "safepassage-heartbeat-task";
const HEARTBEAT_INTERVAL_MS = HEARTBEAT_INTERVAL_MINUTES * 60 * 1000;

const ACTIVE_USER_ID_KEY = "active_user_id";
const ACTIVE_TRIP_ID_KEY = "active_trip_id";
const IS_WEB = Platform.OS === "web";

let foregroundIntervalRef: ReturnType<typeof setInterval> | null = null;
let appStateSubscription: { remove: () => void } | null = null;

type HeartbeatContext = {
  userId: string;
  tripId: string;
};

async function resolveHeartbeatContext(): Promise<HeartbeatContext | null> {
  await initializeOfflineDb();

  const userId = await getItem(ACTIVE_USER_ID_KEY);
  if (!userId) return null;

  let tripId = await getItem(ACTIVE_TRIP_ID_KEY);
  if (tripId) {
    const trip = await getTripById(tripId);
    if (trip?.heartbeatEnabled) {
      return { userId, tripId };
    }
  }

  const trips = await listTrips(userId);
  const candidate = trips.find((trip) => trip.heartbeatEnabled);
  if (!candidate) return null;

  tripId = candidate.id;
  await setItem(ACTIVE_TRIP_ID_KEY, tripId);
  return { userId, tripId };
}

async function buildHeartbeatPayload(source: "foreground" | "background_fetch" | "manual_debug") {
  const context = await resolveHeartbeatContext();
  if (!context) return null;

  const netInfo = await NetInfo.fetch();
  const batteryLevel = await Battery.getBatteryLevelAsync();

  const isConnected = Boolean(netInfo.isConnected) && Boolean(netInfo.isInternetReachable ?? true);
  const networkStatus: HeartbeatPayload["network_status"] = isConnected ? "online" : "offline";

  const appState = AppState.currentState as AppStateStatus;
  const normalizedAppState: HeartbeatPayload["app_state"] =
    appState === "active" || appState === "background" || appState === "inactive"
      ? appState
      : "inactive";
  const payload: HeartbeatPayload = {
    user_id: context.userId,
    trip_id: context.tripId,
    timestamp: new Date().toISOString(),
    battery_percent: batteryLevel >= 0 ? Math.round(batteryLevel * 100) : undefined,
    network_status: networkStatus,
    source,
    network_type: (netInfo.type ?? "unknown") as NetInfoStateType | "unknown",
    app_state: normalizedAppState,
  };

  return payload;
}

export async function sendScheduledHeartbeat(source: "foreground" | "background_fetch" | "manual_debug") {
  const payload = await buildHeartbeatPayload(source);
  if (!payload) {
    return { status: "skipped" as const, reason: "missing-active-user-or-heartbeat-enabled-trip" };
  }

  return sendOrQueueHeartbeat(payload);
}

if (!IS_WEB && !TaskManager.isTaskDefined(HEARTBEAT_TASK_NAME)) {
  TaskManager.defineTask(HEARTBEAT_TASK_NAME, async () => {
    try {
      const result = await sendScheduledHeartbeat("background_fetch");
      if (result.status === "sent" || result.status === "queued") {
        return BackgroundFetch.BackgroundFetchResult.NewData;
      }
      return BackgroundFetch.BackgroundFetchResult.NoData;
    } catch {
      return BackgroundFetch.BackgroundFetchResult.Failed;
    }
  });
}

export async function registerHeartbeatTask() {
  if (IS_WEB) {
    return { registered: false, reason: "background-task-not-supported-on-web" };
  }

  const isRegistered = await TaskManager.isTaskRegisteredAsync(HEARTBEAT_TASK_NAME);
  if (!isRegistered) {
    await BackgroundFetch.registerTaskAsync(HEARTBEAT_TASK_NAME, {
      minimumInterval: HEARTBEAT_INTERVAL_MINUTES * 60,
      stopOnTerminate: false,
      startOnBoot: true,
    });
  }
  return { registered: true };
}

export function startForegroundHeartbeatLoop() {
  if (foregroundIntervalRef) {
    return;
  }

  const runIfActive = async () => {
    if (AppState.currentState !== "active") {
      return;
    }
    await sendScheduledHeartbeat("foreground");
  };

  void runIfActive();
  foregroundIntervalRef = setInterval(() => {
    void runIfActive();
  }, HEARTBEAT_INTERVAL_MS);

  appStateSubscription = AppState.addEventListener("change", (state) => {
    if (state === "active") {
      void runIfActive();
    }
  });
}

export function stopForegroundHeartbeatLoop() {
  if (foregroundIntervalRef) {
    clearInterval(foregroundIntervalRef);
    foregroundIntervalRef = null;
  }

  if (appStateSubscription) {
    appStateSubscription.remove();
    appStateSubscription = null;
  }
}

export async function replayQueuedHeartbeats() {
  await initializeOfflineDb();
  const jobs = await getPendingSyncJobs();
  const heartbeatJobs = jobs.filter((job) => job.entity_type === "heartbeat");

  let replayed = 0;
  let failed = 0;

  for (const job of heartbeatJobs) {
    try {
      await replayHeartbeatSyncJob(job);
      await markSyncJobDone(job.id);
      replayed += 1;
    } catch {
      await markSyncJobFailed(job.id, job.attempts + 1);
      failed += 1;
    }
  }

  return { total: heartbeatJobs.length, replayed, failed };
}
