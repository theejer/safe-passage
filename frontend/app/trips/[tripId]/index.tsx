import { useLocalSearchParams, Link, useRouter } from "expo-router";
import { useState } from "react";
import { View, Text, Alert } from "react-native";
import { useTripDetail } from "@/features/trips/hooks/useTripDetail";
import { RiskSummary } from "@/features/risk/components/RiskSummary";
import { analyzeTripRisk } from "@/features/risk/services/riskApi";
import { getLatestItinerary } from "@/features/trips/services/itineraryApi";
import { Button } from "@/shared/components/Button";

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
    <View style={{ flex: 1, padding: 16, gap: 10 }}>
      <Text style={{ fontSize: 20, fontWeight: "700" }}>{trip?.title ?? "Trip"}</Text>
      <RiskSummary tripId={String(tripId)} />
      <Button onPress={() => void onGenerateRiskNow()}>
        {generatingRisk ? "Generating score..." : "Generate Score"}
      </Button>
      <Link href="/dashboard">Back to Dashboard</Link>
      <Link href={`/trips/${tripId}/start`}>Start Trip</Link>
      <Link href={`/trips/${tripId}/edit`}>Edit Trip</Link>
      <Link href={`/trips/${tripId}/import`}>Import Itinerary File</Link>
      <Link href={`/trips/${tripId}/risk`}>View Full Risk</Link>
    </View>
  );
}
