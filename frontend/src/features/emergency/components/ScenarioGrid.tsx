import { View, Text } from "react-native";
import { Link } from "expo-router";
import { useEmergencyScenarios } from "@/features/emergency/hooks/useEmergencyScenarios";

export function ScenarioGrid() {
  // Simple list now; can evolve into grid cards with icons.
  const { scenarios } = useEmergencyScenarios();

  return (
    <View style={{ gap: 8 }}>
      {scenarios.map((scenario) => (
        <Link key={scenario.key} href={`/emergency/${scenario.key}`} asChild>
          <Text style={{ padding: 10, borderWidth: 1, borderColor: "#ddd", borderRadius: 8 }}>{scenario.title}</Text>
        </Link>
      ))}
    </View>
  );
}
