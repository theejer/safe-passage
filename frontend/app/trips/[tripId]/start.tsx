import { useEffect } from "react";
import { useLocalSearchParams, useRouter } from "expo-router";
import { ScrollView, Text } from "react-native";
import { setItem } from "@/features/storage/services/localStore";

const ACTIVE_TRIP_ID_KEY = "active_trip_id";

export default function StartTripScreen() {
  const router = useRouter();
  const { tripId } = useLocalSearchParams<{ tripId: string }>();
  const normalizedTripId = String(tripId ?? "");

  useEffect(() => {
    if (!normalizedTripId) return;

    async function activateTrip() {
      await setItem(ACTIVE_TRIP_ID_KEY, normalizedTripId);
      router.replace(`/trips/${normalizedTripId}`);
    }

    void activateTrip();
  }, [normalizedTripId, router]);

  return (
    <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: "center", alignItems: "center", padding: 16, gap: 10 }}>
      <Text style={{ fontSize: 22, fontWeight: "700", textAlign: "center" }}>Starting Trip</Text>
      <Text style={{ fontSize: 14, color: "#4b5563", textAlign: "center" }}>
        Activating this trip for heartbeat and safety monitoring...
      </Text>
    </ScrollView>
  );
}
