import { useLocalSearchParams } from "expo-router";
import { ScrollView, Text } from "react-native";
import { RiskCategoryList } from "@/features/risk/components/RiskCategoryList";

export default function TripRiskScreen() {
  const { tripId } = useLocalSearchParams<{ tripId: string }>();

  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>

      <Text style={{ fontSize: 20, fontWeight: "700" }}>Risk Breakdown</Text>
      <RiskCategoryList tripId={String(tripId)} />
    </ScrollView>
  );
}
