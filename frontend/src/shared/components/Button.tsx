import type { PropsWithChildren } from "react";
import { Pressable, Text } from "react-native";

type ButtonProps = PropsWithChildren<{ onPress?: () => void }>;

export function Button({ onPress, children }: ButtonProps) {
  return (
    <Pressable onPress={onPress} style={{ backgroundColor: "#222", paddingVertical: 10, paddingHorizontal: 14, borderRadius: 8 }}>
      <Text style={{ color: "white", fontWeight: "600" }}>{children}</Text>
    </Pressable>
  );
}
