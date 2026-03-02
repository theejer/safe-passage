import { useCallback, useEffect, useState } from "react";
import { listRecentHeartbeatJournal, type LocalHeartbeatJournal } from "@/features/storage/services/offlineDb";
import { getItem } from "@/features/storage/services/localStore";

const ACTIVE_TRIP_ID_KEY = "active_trip_id";

export function useRecentHeartbeats(userId: string, limit = 5) {
  const [heartbeats, setHeartbeats] = useState<LocalHeartbeatJournal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Get active trip ID from storage
      const activeTripId = await getItem(ACTIVE_TRIP_ID_KEY);
      
      if (!activeTripId) {
        setHeartbeats([]);
        setLoading(false);
        return;
      }

      const recent = await listRecentHeartbeatJournal(userId, activeTripId, limit);
      setHeartbeats(recent);
    } catch (err) {
      console.error("[useRecentHeartbeats] error:", err);
      setError(err instanceof Error ? err.message : "Failed to load heartbeats");
    } finally {
      setLoading(false);
    }
  }, [userId, limit]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { heartbeats, loading, error, reload };
}
