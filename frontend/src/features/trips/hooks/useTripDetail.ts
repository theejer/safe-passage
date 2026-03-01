import { useEffect, useState } from "react";
import { getLatestItinerary } from "@/features/trips/services/itineraryApi";

export function useTripDetail(tripId: string) {
  // Combines trip metadata + itinerary in future iterations.
  const [trip, setTrip] = useState<{ title?: string } | null>(null);
  const [itinerary, setItinerary] = useState<unknown>(null);

  useEffect(() => {
    async function load() {
      if (!tripId) return;
      const data = await getLatestItinerary(tripId);
      setTrip({ title: `Trip ${tripId}` });
      setItinerary(data);
    }
    void load();
  }, [tripId]);

  return { trip, itinerary };
}
