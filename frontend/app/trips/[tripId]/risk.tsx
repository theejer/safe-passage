import { Link, useLocalSearchParams } from "expo-router";
import { ScrollView, Text } from "react-native";
import { RiskCategoryList } from "@/features/risk/components/RiskCategoryList";

export default function TripRiskScreen() {
  // Full risk breakdown by day and category for PREVENTION planning.
  const { tripId } = useLocalSearchParams<{ tripId: string }>();

  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>
      <Text style={{ fontSize: 20, fontWeight: "700" }}>Risk Breakdown</Text>
      <Link href="/dashboard">Back to Dashboard</Link>
      <RiskCategoryList tripId={String(tripId)} />
    </ScrollView>
  );
}
