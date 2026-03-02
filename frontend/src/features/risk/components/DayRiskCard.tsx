import { View, Text } from "react-native";
import type { DayRisk } from "@/features/risk/types";

type DayRiskCardProps = { dayRisk: DayRisk };

function severityStyle(severity: string) {
  const value = severity.toLowerCase();
  if (value === "severe" || value === "high") return { bg: "#fee2e2", text: "#991b1b" };
  if (value === "moderate" || value === "medium") return { bg: "#fef3c7", text: "#92400e" };
  return { bg: "#dcfce7", text: "#166534" };
}

export function DayRiskCard({ dayRisk }: DayRiskCardProps) {
  // Shows location + connectivity risk per day segment.
  return (
    <View style={{ borderWidth: 1, borderColor: "#d1d5db", borderRadius: 12, padding: 12, gap: 8, backgroundColor: "white" }}>
      <Text style={{ fontWeight: "800" }}>{dayRisk.date}</Text>
      {dayRisk.locations.map((location) => (
        <View key={`${dayRisk.date}-${location.name}`} style={{ borderWidth: 1, borderColor: "#e5e7eb", borderRadius: 10, padding: 10, gap: 6, backgroundColor: "#fafafa" }}>
          <Text style={{ fontWeight: "600" }}>{location.name}</Text>
          <View style={{ flexDirection: "row", gap: 8 }}>
            <Text
              style={{
                backgroundColor: severityStyle(location.locationRisk).bg,
                color: severityStyle(location.locationRisk).text,
                fontWeight: "700",
                fontSize: 12,
                paddingHorizontal: 8,
                paddingVertical: 3,
                borderRadius: 999,
                overflow: "hidden",
              }}
            >
              LOC {location.locationRisk.toUpperCase()}
            </Text>
            <Text
              style={{
                backgroundColor: severityStyle(location.connectivityRisk).bg,
                color: severityStyle(location.connectivityRisk).text,
                fontWeight: "700",
                fontSize: 12,
                paddingHorizontal: 8,
                paddingVertical: 3,
                borderRadius: 999,
                overflow: "hidden",
              }}
            >
              NET {location.connectivityRisk.toUpperCase()}
            </Text>
          </View>
          <Text style={{ color: "#374151" }}>Expected offline: {location.expectedOfflineMinutes} min</Text>
        </View>
      ))}
    </View>
  );
}
