import { View, Text } from "react-native";
import type { DayRisk } from "@/features/risk/types";

type DayRiskCardProps = { dayRisk: DayRisk };

export function DayRiskCard({ dayRisk }: DayRiskCardProps) {
  // Shows location + connectivity risk per day segment.
  return (
    <View style={{ borderWidth: 1, borderColor: "#ddd", borderRadius: 8, padding: 10, gap: 4 }}>
      <Text style={{ fontWeight: "700" }}>{dayRisk.date}</Text>
      {dayRisk.locations.map((location) => (
        <View key={`${dayRisk.date}-${location.name}`} style={{ paddingVertical: 4 }}>
          <Text style={{ fontWeight: "600" }}>{location.name}</Text>
          <Text>
            Location risk: {location.locationRisk} | Connectivity risk: {location.connectivityRisk}
          </Text>
          <Text>Expected offline: {location.expectedOfflineMinutes} min</Text>
        </View>
      ))}
    </View>
  );
}
