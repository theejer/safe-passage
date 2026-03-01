import { Pressable, Text } from "react-native";

export function EmergencyButton() {
  // Always-visible primary emergency action entry.
  return (
    <Pressable
      accessibilityRole="button"
      style={{ backgroundColor: "#c00", paddingVertical: 16, borderRadius: 10, alignItems: "center" }}
    >
      <Text style={{ color: "white", fontWeight: "700" }}>Emergency Mode</Text>
    </Pressable>
  );
}
