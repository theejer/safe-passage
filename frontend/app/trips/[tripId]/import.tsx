import { useLocalSearchParams } from "expo-router";
import { useMemo, useState } from "react";
import { Alert, ScrollView, Text } from "react-native";
import { upsertItinerary } from "@/features/trips/services/itineraryApi";
import { analyzeTripRisk } from "@/features/risk/services/riskApi";
import { ItineraryUpload } from "@/features/trips/components/ItineraryUpload";
import { ItineraryReview } from "@/features/trips/components/ItineraryReview";
import type { Day } from "@/features/trips/types";

export default function ItineraryImportScreen() {
  const { tripId } = useLocalSearchParams<{ tripId: string }>();
  const normalizedTripId = useMemo(() => String(tripId ?? ""), [tripId]);
  const [extracted, setExtracted] = useState<{ days: Day[] } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  async function onSavePress(days: Day[]) {
    if (!normalizedTripId) {
      Alert.alert("Missing trip", "Trip ID is missing.");
      return;
    }

    try {
      setSubmitting(true);
      await upsertItinerary(normalizedTripId, days);
      Alert.alert("Saved", "Itinerary saved. You can now run risk analysis.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to save itinerary";
      Alert.alert("Save failed", message);
    } finally {
      setSubmitting(false);
    }
  }

  async function onCheckRiskPress(days: Day[]) {
    if (!normalizedTripId) {
      Alert.alert("Missing trip", "Trip ID is missing.");
      return;
    }

    try {
      setAnalyzing(true);
      try {
        await upsertItinerary(normalizedTripId, days);
      } catch (persistError) {
        console.warn("[CheckRisk] Continuing without itinerary persistence:", persistError);
      }
      const report = await analyzeTripRisk(normalizedTripId, days);
      Alert.alert("Risk ready", report.summary || "Risk analysis completed.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to run risk analysis";
      Alert.alert("Risk analysis failed", message);
    } finally {
      setAnalyzing(false);
    }
  }

  if (!extracted) {
    return (
      <ItineraryUpload
        tripId={normalizedTripId}
        onItineraryExtracted={setExtracted}
        onCancel={() => {
          Alert.alert("Canceled", "File upload canceled.");
        }}
      />
    );
  }

  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 10 }}>
      <Text style={{ fontSize: 20, fontWeight: "700" }}>Review Extracted Itinerary</Text>
      <Text>Trip ID: {normalizedTripId || "N/A"}</Text>
      <Text>
        Update missing fields in the extracted itinerary, then save and run risk analysis.
      </Text>
      <ItineraryReview
        itinerary={extracted}
        onConfirm={(days) => void onSavePress(days)}
        onCheckRisk={(days) => void onCheckRiskPress(days)}
        onEdit={() => setExtracted(null)}
      />
      {submitting ? <Text>Saving itinerary...</Text> : null}
      {analyzing ? <Text>Running risk analysis...</Text> : null}
    </ScrollView>
  );
}
