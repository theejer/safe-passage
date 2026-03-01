import { useLocalSearchParams } from "expo-router";
import { View, Text } from "react-native";
import { RiskCategoryList } from "@/features/risk/components/RiskCategoryList";

export default function TripRiskScreen() {
  // Full risk breakdown by day and category for PREVENTION planning.
  const { tripId } = useLocalSearchParams<{ tripId: string }>();

  return (
    <View style={{ flex: 1, padding: 16, gap: 12 }}>
      <Text style={{ fontSize: 20, fontWeight: "700" }}>Risk Breakdown</Text>
      <RiskCategoryList tripId={String(tripId)} />
    </View>
  );
}
