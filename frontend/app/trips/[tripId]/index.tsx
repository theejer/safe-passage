import { useLocalSearchParams, Link } from "expo-router";
import { View, Text } from "react-native";
import { useTripDetail } from "@/features/trips/hooks/useTripDetail";
import { RiskSummary } from "@/features/risk/components/RiskSummary";

export default function TripDashboardScreen() {
  // Dashboard summary for one trip + links to itinerary/import/risk screens.
  const { tripId } = useLocalSearchParams<{ tripId: string }>();
  const { trip } = useTripDetail(String(tripId));

  return (
    <View style={{ flex: 1, padding: 16, gap: 10 }}>
      <Text style={{ fontSize: 20, fontWeight: "700" }}>{trip?.title ?? "Trip"}</Text>
      <RiskSummary tripId={String(tripId)} />
      <Link href={`/trips/${tripId}/itinerary`}>Edit Itinerary</Link>
      <Link href={`/trips/${tripId}/import`}>Import Itinerary File</Link>
      <Link href={`/trips/${tripId}/risk`}>View Full Risk</Link>
    </View>
  );
}
