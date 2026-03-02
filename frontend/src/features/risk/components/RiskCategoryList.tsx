import { useState } from "react";
import { View, Text, TouchableOpacity, LayoutAnimation, Platform, UIManager } from "react-native";
import { useRiskReport } from "@/features/risk/hooks/useRiskReport";
import { DayRiskCard } from "@/features/risk/components/DayRiskCard";

if (Platform.OS === "android" && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

type RiskCategoryListProps = { tripId: string };

type FinalRiskItem = {
  domain?: string;
  risk?: string;
  severity?: string;
  mitigation?: string;
  details?: string;
};

type FinalActivity = {
  activity?: string;
  location?: string;
  RISK?: FinalRiskItem[];
};

type FinalDay = {
  day_id?: string;
  day_label?: string;
  ACTIVITY?: FinalActivity[];
};

function scoreColor(score?: number) {
  if (typeof score !== "number") return "#374151";
  if (score >= 75) return "#15803d";
  if (score >= 50) return "#a16207";
  return "#b91c1c";
}

function severityStyle(severity?: string) {
  const value = String(severity || "").toLowerCase();
  if (value === "severe" || value === "high") {
    return { bg: "#fee2e2", text: "#991b1b" };
  }
  if (value === "moderate" || value === "medium") {
    return { bg: "#fef3c7", text: "#92400e" };
  }
  return { bg: "#dcfce7", text: "#166534" };
}

export function RiskCategoryList({ tripId }: RiskCategoryListProps) {
  // Lists day-level risk cards by itinerary date.
  const { report, loading } = useRiskReport(tripId);
  const [expandedDayKeys, setExpandedDayKeys] = useState<Record<string, boolean>>({});
  const [hasManualToggle, setHasManualToggle] = useState(false);

  const toggleDay = (dayKey: string) => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setHasManualToggle(true);
    setExpandedDayKeys((current) => ({ ...current, [dayKey]: !current[dayKey] }));
  };

  if (loading) return <Text>Loading risk...</Text>;

  const finalReport = report?.finalReport as { DAY?: FinalDay[] } | undefined;
  const finalDays = Array.isArray(finalReport?.DAY) ? finalReport?.DAY : [];

  return (
    <View style={{ gap: 12 }}>
      {report?.summary || report?.score ? (
        <View style={{ borderWidth: 1, borderColor: "#d1d5db", borderRadius: 12, padding: 12, gap: 8, backgroundColor: "#f8fafc" }}>
          <Text style={{ fontWeight: "800", fontSize: 16 }}>Risk Summary</Text>
          {report?.score ? (
            <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
              <Text style={{ fontWeight: "800", fontSize: 28, color: scoreColor(report.score.value) }}>{report.score.value}</Text>
              <Text style={{ color: "#4b5563" }}>/ 100</Text>
            </View>
          ) : null}
          {report?.summary ? <Text style={{ color: "#111827" }}>{report.summary}</Text> : null}
          {report?.score?.justification ? <Text style={{ color: "#374151" }}>{report.score.justification}</Text> : null}
        </View>
      ) : null}

      {(report?.recommendations ?? []).length ? (
        <View style={{ borderWidth: 1, borderColor: "#d1d5db", borderRadius: 12, padding: 12, gap: 6, backgroundColor: "#f9fafb" }}>
          <Text style={{ fontWeight: "800" }}>Recommendations</Text>
          {(report?.recommendations ?? []).map((recommendation, index) => (
            <Text key={`${index}-${recommendation}`} style={{ color: "#1f2937" }}>• {recommendation}</Text>
          ))}
        </View>
      ) : null}

      {finalDays.length > 0
        ? finalDays.map((day, dayIndex) => {
            const label = day.day_label || day.day_id || `Day ${dayIndex + 1}`;
            const dayKey = `${day.day_id ?? label}-${dayIndex}`;
            const activities = Array.isArray(day.ACTIVITY) ? day.ACTIVITY : [];
            const isExpanded = hasManualToggle ? !!expandedDayKeys[dayKey] : dayIndex === 0;

            return (
              <View key={dayKey} style={{ borderWidth: 1, borderColor: "#d1d5db", borderRadius: 12, backgroundColor: "white" }}>
                <TouchableOpacity
                  style={{ paddingHorizontal: 12, paddingVertical: 12, flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}
                  onPress={() => toggleDay(dayKey)}
                >
                  <Text style={{ fontWeight: "800", fontSize: 16 }}>{label}</Text>
                  <Text style={{ fontWeight: "700", color: "#374151" }}>{isExpanded ? "▲" : "▼"}</Text>
                </TouchableOpacity>

                {isExpanded ? <View style={{ borderTopWidth: 1, borderTopColor: "#e5e7eb" }} /> : null}

                {isExpanded ? (
                  <View style={{ padding: 12, gap: 10 }}>
                    {activities.map((activity, activityIndex) => {
                      const risks = Array.isArray(activity.RISK) ? activity.RISK : [];
                      return (
                        <View
                          key={`${label}-activity-${activityIndex}`}
                          style={{ borderWidth: 1, borderColor: "#e5e7eb", borderRadius: 10, padding: 10, gap: 6, backgroundColor: "#fafafa" }}
                        >
                          <Text style={{ fontWeight: "700" }}>{activity.activity || "Activity"}</Text>
                          {activity.location ? <Text style={{ color: "#374151" }}>Location: {activity.location}</Text> : null}

                          {risks.length > 0 ? (
                            risks.map((risk, riskIndex) => (
                              <View key={`${label}-risk-${activityIndex}-${riskIndex}`} style={{ borderWidth: 1, borderColor: "#e5e7eb", borderRadius: 8, padding: 8, gap: 4, backgroundColor: "white" }}>
                                <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                                  <Text style={{ fontWeight: "700", color: "#1f2937" }}>{(risk.domain || "domain").toUpperCase()}</Text>
                                  <Text
                                    style={{
                                      backgroundColor: severityStyle(risk.severity).bg,
                                      color: severityStyle(risk.severity).text,
                                      fontWeight: "700",
                                      fontSize: 12,
                                      paddingHorizontal: 8,
                                      paddingVertical: 3,
                                      borderRadius: 999,
                                      overflow: "hidden",
                                    }}
                                  >
                                    {(risk.severity || "unknown").toUpperCase()}
                                  </Text>
                                </View>
                                <Text style={{ fontWeight: "600" }}>{risk.risk || "Unspecified risk"}</Text>
                                {risk.details ? <Text style={{ color: "#374151" }}>Details: {risk.details}</Text> : null}
                                {risk.mitigation ? <Text style={{ color: "#111827" }}>Mitigation: {risk.mitigation}</Text> : null}
                              </View>
                            ))
                          ) : (
                            <Text style={{ color: "#6b7280" }}>No reportable risks for this activity.</Text>
                          )}
                        </View>
                      );
                    })}

                    {activities.length === 0 ? <Text style={{ color: "#6b7280" }}>No activity analysis available for this day.</Text> : null}
                  </View>
                ) : null}
              </View>
            );
          })
        : (report?.days ?? []).map((day) => <DayRiskCard key={day.date} dayRisk={day} />)}

      {finalDays.length === 0 && (report?.days ?? []).length === 0 ? <Text style={{ color: "#6b7280" }}>No day-level risk entries yet.</Text> : null}
    </View>
  );
}
