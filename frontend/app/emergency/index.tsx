import { View, Text } from "react-native";
import { EmergencyButton } from "@/features/emergency/components/EmergencyButton";
import { ScenarioGrid } from "@/features/emergency/components/ScenarioGrid";

export default function EmergencyHomeScreen() {
  // MITIGATION home: large emergency button plus scenario selection grid.
  return (
    <View style={{ flex: 1, padding: 16, gap: 12 }}>
      <Text style={{ fontSize: 20, fontWeight: "700" }}>Emergency</Text>
      <EmergencyButton />
      <ScenarioGrid />
    </View>
  );
}
