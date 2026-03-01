import { Text, View } from "react-native";
import { useRiskReport } from "@/features/risk/hooks/useRiskReport";

type RiskSummaryProps = { tripId: string };

export function RiskSummary({ tripId }: RiskSummaryProps) {
  // Compact summary card for dashboard view.
  const { report, loading } = useRiskReport(tripId);
  if (loading) return <Text>Loading risk...</Text>;

  return (
    <View style={{ borderWidth: 1, borderColor: "#ddd", padding: 10, borderRadius: 8 }}>
      <Text style={{ fontWeight: "700" }}>Risk Summary</Text>
      <Text>{report?.summary ?? "No risk report available yet."}</Text>
    </View>
  );
}
