import { useLocalSearchParams, useRouter } from "expo-router";
import { View, Text, ScrollView } from "react-native";
import { useTripDetail } from "@/features/trips/hooks/useTripDetail";
import { RiskSummary } from "@/features/risk/components/RiskSummary";
import { Button } from "@/shared/components/Button";
import { tripUiColors } from "@/features/trips/styles/tripUi";

export default function TripDashboardScreen() {
  // Dashboard summary for one trip + links to itinerary/import/risk screens.
  const { tripId } = useLocalSearchParams<{ tripId: string }>();
  const router = useRouter();
  const { trip } = useTripDetail(String(tripId));

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
