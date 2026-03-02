import { Link, useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { ScrollView, Text, View } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { useTrips } from "@/features/trips/hooks/useTrips";
import { getItem } from "@/features/storage/services/localStore";
import { Button } from "@/shared/components/Button";

const ACTIVE_USER_ID_KEY = "active_user_id";

export default function DashboardScreen() {
  const router = useRouter();
  const [userId, setUserId] = useState("demo-user");
  const { items, loading, reload } = useTrips(userId);

  useEffect(() => {
    async function loadUserId() {
      const saved = await getItem(ACTIVE_USER_ID_KEY);
      if (saved) {
        setUserId(saved);
      }
    }

    void loadUserId();
  }, []);

  useFocusEffect(
    useCallback(() => {
      let canceled = false;

      async function refreshOnFocus() {
        const saved = await getItem(ACTIVE_USER_ID_KEY);
        if (canceled) return;

        if (saved && saved !== userId) {
          setUserId(saved);
          return;
        }

        await reload();
      }

      void refreshOnFocus();

      return () => {
        canceled = true;
      };
    }, [reload, userId])
  );

  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>
      <Text style={{ fontSize: 24, fontWeight: "700" }}>Dashboard</Text>
      <Text style={{ color: "#4b5563" }}>Manage your trips, view saved trips, and start a trip.</Text>

      <Button onPress={() => router.push("/trips")}>Create New Trip</Button>

      <View style={{ borderWidth: 1, borderColor: "#d1d5db", borderRadius: 12, padding: 12, gap: 8, backgroundColor: "white" }}>
        <Text style={{ fontSize: 18, fontWeight: "700" }}>Saved Trips</Text>

        {loading ? <Text>Loading trips...</Text> : null}

        {!loading && items.length === 0 ? (
          <Text style={{ color: "#6b7280" }}>
            No trips yet. Create your first trip to start itinerary upload and risk analysis.
          </Text>
        ) : null}

        {!loading
          ? items.map((trip) => (
              <View
                key={trip.id}
                style={{ borderWidth: 1, borderColor: "#e5e7eb", borderRadius: 10, padding: 10, gap: 8, backgroundColor: "#f9fafb" }}
              >
                <Text style={{ fontWeight: "700", fontSize: 16 }}>{trip.title}</Text>
                <Text style={{ color: "#4b5563" }}>
                  {trip.startDate} → {trip.endDate}
                </Text>
                <View style={{ flexDirection: "row", gap: 12 }}>
                  <Link href={`/trips/${trip.id}`}>View Trip</Link>
                  <Link href={`/trips/${trip.id}/start`}>Start Trip</Link>
                  <Link href={`/trips/${trip.id}/risk`}>Open Risk</Link>
                </View>
              </View>
            ))
          : null}
      </View>
    </ScrollView>
  );
}
