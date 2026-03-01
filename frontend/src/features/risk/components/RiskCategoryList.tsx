import { View, Text } from "react-native";
import { useRiskReport } from "@/features/risk/hooks/useRiskReport";
import { DayRiskCard } from "@/features/risk/components/DayRiskCard";

type RiskCategoryListProps = { tripId: string };

export function RiskCategoryList({ tripId }: RiskCategoryListProps) {
  // Lists day-level risk cards by itinerary date.
  const { report, loading } = useRiskReport(tripId);
  if (loading) return <Text>Loading risk...</Text>;

  return (
    <View style={{ gap: 8 }}>
      {(report?.days ?? []).map((day) => (
        <DayRiskCard key={day.date} dayRisk={day} />
      ))}
      {(report?.days ?? []).length === 0 ? <Text>No day-level risk entries yet.</Text> : null}
    </View>
  );
}
