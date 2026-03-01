import { View, Text } from "react-native";
import { useEmergencyScenarios } from "@/features/emergency/hooks/useEmergencyScenarios";

type ProtocolStepsProps = { scenarioKey: string };

export function ProtocolSteps({ scenarioKey }: ProtocolStepsProps) {
  // Renders local protocol steps; LLM personalization can be layered on top.
  const { scenarios } = useEmergencyScenarios();
  const scenario = scenarios.find((item) => item.key === scenarioKey) ?? scenarios[0];

  return (
    <View style={{ gap: 6 }}>
      <Text style={{ fontWeight: "700" }}>{scenario.title}</Text>
      {scenario.steps.map((step, index) => (
        <Text key={`${scenario.key}-${index}`}>{index + 1}. {step}</Text>
      ))}
    </View>
  );
}
