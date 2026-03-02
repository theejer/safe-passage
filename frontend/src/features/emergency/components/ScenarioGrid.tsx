import { View } from "react-native";
import { useRouter } from "expo-router";
import { useEmergencyScenarios } from "@/features/emergency/hooks/useEmergencyScenarios";
import { Button } from "@/shared/components/Button";

export function ScenarioGrid() {
  const router = useRouter();
  const { scenarios } = useEmergencyScenarios();

  return (
    <View style={{ gap: 8 }}>
      {scenarios.map((scenario) => (
        <Button key={scenario.key} variant="outline" onPress={() => router.push(`/emergency/${scenario.key}`)}>
          {scenario.title}
        </Button>
      ))}
    </View>
  );
}
