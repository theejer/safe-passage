import { useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Alert, ScrollView, Text, View } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { useTrips } from "@/features/trips/hooks/useTrips";
import { getItem } from "@/features/storage/services/localStore";
import { useRiskReport } from "@/features/risk/hooks/useRiskReport";
import { analyzeTripRisk } from "@/features/risk/services/riskApi";
import { getLatestItinerary } from "@/features/trips/services/itineraryApi";
import type { Trip } from "@/features/trips/types";
import { Button } from "@/shared/components/Button";

const ACTIVE_USER_ID_KEY = "active_user_id";

function DashboardTripScore({ tripId }: { tripId: string }) {
  const { report, loading } = useRiskReport(tripId);

  if (loading) return <Text style={{ color: "#6b7280" }}>Score: ...</Text>;
  if (!report?.score) return <Text style={{ color: "#6b7280" }}>Score: Not generated</Text>;

  return (
    <Text style={{ color: "#111827", fontWeight: "600" }}>
      Score: {report.score.value}/100
    </Text>
  );
}

function DashboardTripActions({ trip, onSaved }: { trip: Trip; onSaved: () => Promise<void> | void }) {
  const router = useRouter();
  const tripId = trip.id;
  const [generatingScore, setGeneratingScore] = useState(false);

  async function onGenerateScore() {
    if (!tripId) {
      Alert.alert("Missing trip", "Trip ID is missing.");
      return;
    }

    try {
      setGeneratingScore(true);
      const days = await getLatestItinerary(tripId);
      if (!days.length) {
        Alert.alert("No itinerary yet", "Add or import itinerary first, then generate score.");
        return;
      }

      const report = await analyzeTripRisk(tripId, days);
      Alert.alert("Score ready", report.summary || "Risk analysis completed.");
      router.replace(`/trips/${tripId}/risk`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to generate score";
      Alert.alert("Score generation failed", message);
    } finally {
      setGeneratingScore(false);
    }
  }

  return (
    <View style={{ flexDirection: "row", gap: 12, flexWrap: "wrap" }}>
      <Button variant="secondary" size="sm" block={false} onPress={() => router.push(`/trips/${tripId}`)}>
        View / Edit Trip
      </Button>
      <Button variant="outline" size="sm" block={false} onPress={() => void onGenerateScore()} disabled={generatingScore}>
        {generatingScore ? "Generating score..." : "Generate Score"}
      </Button>
      <Button variant="outline" size="sm" block={false} onPress={() => router.replace(`/trips/${tripId}/risk`)}>
        Open Risk
      </Button>
    </View>
  );
}

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
                <DashboardTripScore tripId={trip.id} />
                <DashboardTripActions trip={trip} onSaved={reload} />
              </View>
            ))
          : null}
      </View>
    </ScrollView>
  );
}
