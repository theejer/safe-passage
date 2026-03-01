import { useState } from "react";
import {
  getPendingSyncJobs,
  initializeOfflineDb,
  markSyncJobDone,
  markSyncJobFailed,
  type SyncQueueJob,
} from "@/features/storage/services/offlineDb";

type SyncProcessor = (job: SyncQueueJob) => Promise<void>;

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
          if (processor) {
            await processor(job);
          }
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
