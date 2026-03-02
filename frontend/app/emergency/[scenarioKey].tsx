import { useLocalSearchParams } from "expo-router";
import { View, Text } from "react-native";
import { ProtocolSteps } from "@/features/emergency/components/ProtocolSteps";

export default function ScenarioProtocolScreen() {
  const { scenarioKey } = useLocalSearchParams<{ scenarioKey: string }>();

  return (
    <View style={{ flex: 1, padding: 16, gap: 12 }}>
      <Text style={{ fontSize: 20, fontWeight: "700" }}>{scenarioKey}</Text>
      <ProtocolSteps scenarioKey={String(scenarioKey ?? "lost")} />
    </View>
  );
}
