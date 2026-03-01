import { useEffect, useState } from "react";
import { listTrips } from "@/features/trips/services/tripsApi";
import type { Trip } from "@/features/trips/types";

export function useTrips(userId: string) {
  // Simple read hook; replace with react-query once data layer matures.
  const [items, setItems] = useState<Trip[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function load() {
      if (!userId) return;
      setLoading(true);
      try {
        const response = await listTrips(userId);
        setItems(response?.items ?? []);
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [userId]);

  return { items, loading };
}
