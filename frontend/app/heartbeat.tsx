import { View, Text } from "react-native";
import { useHeartbeatDebug } from "@/features/heartbeat/hooks/useHeartbeatDebug";

export default function HeartbeatDebugScreen() {
  // Optional debug UI for manual heartbeat trigger and status inspection.
  const { statusText } = useHeartbeatDebug();

  return (
    <View style={{ flex: 1, padding: 16, gap: 8 }}>
      <Text style={{ fontSize: 18, fontWeight: "700" }}>Heartbeat Debug</Text>
      <Text>{statusText}</Text>
    </View>
  );
}
