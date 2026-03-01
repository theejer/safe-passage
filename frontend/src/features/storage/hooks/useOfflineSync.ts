import { useState } from "react";

export function useOfflineSync() {
  // Coordinates queue replay when online state returns.
  const [syncing, setSyncing] = useState(false);

  async function runSync() {
    setSyncing(true);
    try {
      // TODO: read pending queue, POST to backend, mark as synced.
    } finally {
      setSyncing(false);
    }
  }

  return { syncing, runSync };
}
