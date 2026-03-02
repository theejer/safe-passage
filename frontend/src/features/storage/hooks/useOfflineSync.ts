import { useState } from "react";
import {
  getPendingSyncJobs,
  initializeOfflineDb,
  markSyncJobDone,
  markSyncJobFailed,
  type SyncQueueJob,
} from "@/features/storage/services/offlineDb";
import { replayHeartbeatSyncJob } from "@/features/heartbeat/services/heartbeatApi";
import { replayTripSyncJob } from "@/features/trips/services/tripsApi";
import { replayItinerarySyncJob } from "@/features/trips/services/itineraryApi";
import { replayIncidentSyncJob } from "@/features/emergency/services/emergencyApi";
import { replayEmergencyContactSyncJob, replayUserSyncJob } from "@/features/user/services/userApi";

type SyncProcessor = (job: SyncQueueJob) => Promise<void>;

async function processSyncJob(job: SyncQueueJob) {
  if (job.entity_type === "heartbeat") {
    await replayHeartbeatSyncJob(job);
    return;
  }

  if (job.entity_type === "trip") {
    await replayTripSyncJob(job);
    return;
  }

  if (job.entity_type === "itinerary") {
    await replayItinerarySyncJob(job);
    return;
  }

  if (job.entity_type === "incident_sync") {
    await replayIncidentSyncJob(job);
    return;
  }

  if (job.entity_type === "user") {
    await replayUserSyncJob(job);
    return;
  }

  if (job.entity_type === "emergency_contact") {
    await replayEmergencyContactSyncJob(job);
    return;
  }

  throw new Error(`unsupported sync job entity type: ${job.entity_type}`);
}

export function useOfflineSync() {
  // Coordinates queue replay when online state returns.
  const [syncing, setSyncing] = useState(false);
  const [lastRunSummary, setLastRunSummary] = useState<{
    total: number;
    succeeded: number;
    failed: number;
  } | null>(null);

  async function runSync(processor?: SyncProcessor) {
    setSyncing(true);
    try {
      await initializeOfflineDb();
      const jobs = await getPendingSyncJobs();

      let succeeded = 0;
      let failed = 0;

      for (const job of jobs) {
        try {
          await (processor ?? processSyncJob)(job);
          await markSyncJobDone(job.id);
          succeeded += 1;
        } catch {
          await markSyncJobFailed(job.id, job.attempts + 1);
          failed += 1;
        }
      }

      setLastRunSummary({ total: jobs.length, succeeded, failed });
      return { total: jobs.length, succeeded, failed };
    } finally {
      setSyncing(false);
    }
  }

  return { syncing, runSync, lastRunSummary };
}
