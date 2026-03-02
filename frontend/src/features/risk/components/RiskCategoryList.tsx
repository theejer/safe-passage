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
      {report?.score ? (
        <View style={{ borderWidth: 1, borderColor: "#ddd", borderRadius: 8, padding: 10, gap: 4 }}>
          <Text style={{ fontWeight: "700" }}>Score: {report.score.value}/100</Text>
          <Text>{report.score.justification}</Text>
        </View>
      ) : null}

      {(report?.days ?? []).map((day) => (
        <DayRiskCard key={day.date} dayRisk={day} />
      ))}

      {(report?.recommendations ?? []).length ? (
        <View style={{ borderWidth: 1, borderColor: "#ddd", borderRadius: 8, padding: 10, gap: 4 }}>
          <Text style={{ fontWeight: "700" }}>Recommendations</Text>
          {(report?.recommendations ?? []).map((recommendation, index) => (
            <Text key={`${index}-${recommendation}`}>• {recommendation}</Text>
          ))}
        </View>
      ) : null}

      {report?.judge ? (
        <View style={{ borderWidth: 1, borderColor: "#ddd", borderRadius: 8, padding: 10, gap: 4 }}>
          <Text style={{ fontWeight: "700" }}>Judge</Text>
          <Text>
            Applied: {String(report.judge.applied)} | Before: {report.judge.before} | After: {report.judge.after} | Removed: {report.judge.removed}
          </Text>
          {report.judge.reason ? <Text>Reason: {report.judge.reason}</Text> : null}
        </View>
      ) : null}

      {(report?.days ?? []).length === 0 ? <Text>No day-level risk entries yet.</Text> : null}
    </View>
  );
}
