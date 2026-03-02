import { useLocalSearchParams, Link, useRouter } from "expo-router";
import { useState } from "react";
import { View, Text, Alert, ScrollView } from "react-native";
import { useTripDetail } from "@/features/trips/hooks/useTripDetail";
import { RiskSummary } from "@/features/risk/components/RiskSummary";
import { analyzeTripRisk } from "@/features/risk/services/riskApi";
import { getLatestItinerary } from "@/features/trips/services/itineraryApi";
import { Button } from "@/shared/components/Button";
import { tripUiColors } from "@/features/trips/styles/tripUi";

export default function TripDashboardScreen() {
  // Dashboard summary for one trip + links to itinerary/import/risk screens.
  const { tripId } = useLocalSearchParams<{ tripId: string }>();
  const router = useRouter();
  const { trip } = useTripDetail(String(tripId));
  const [generatingRisk, setGeneratingRisk] = useState(false);

  async function onGenerateRiskNow() {
    const normalizedTripId = String(tripId ?? "");
    if (!normalizedTripId) {
      Alert.alert("Missing trip", "Trip ID is missing.");
      return;
    }

    try {
      setGeneratingRisk(true);
      const days = await getLatestItinerary(normalizedTripId);
      if (!days.length) {
        Alert.alert("No itinerary yet", "Add or import itinerary first, then generate risk.");
        return;
      }

      const report = await analyzeTripRisk(normalizedTripId, days);
      Alert.alert("Risk ready", report.summary || "Risk analysis completed.");
      router.push(`/trips/${normalizedTripId}/risk`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to generate risk";
      Alert.alert("Risk generation failed", message);
    } finally {
      setGeneratingRisk(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }}>
      <View style={{ gap: 6 }}>
        <Text style={{ fontSize: 12, fontWeight: "700", color: tripUiColors.mutedLabel, letterSpacing: 0.6 }}>TRIP OVERVIEW</Text>
        <Text style={{ fontSize: 24, fontWeight: "800", color: tripUiColors.title }}>{trip?.title ?? "Trip"}</Text>
      </View>

      <View style={{ borderWidth: 1, borderColor: tripUiColors.cardBorder, borderRadius: 12, padding: 12, backgroundColor: tripUiColors.white }}>
        <RiskSummary tripId={String(tripId)} />
      </View>

      <View style={{ gap: 10 }}>
        <Button onPress={() => router.push(`/trips/${tripId}/start`)}>Start Trip</Button>
        <Button variant="secondary" onPress={() => router.push(`/trips/${tripId}/itinerary`)}>
          Edit Itinerary
        </Button>
        <Button variant="secondary" onPress={() => router.push(`/trips/${tripId}/risk`)}>
          View Full Risk
        </Button>
        <Button variant="outline" onPress={() => router.push("/dashboard")}>
          Back to Dashboard
        </Button>
      </View>
    </ScrollView>
  );
}
