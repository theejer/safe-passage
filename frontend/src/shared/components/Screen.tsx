import type { PropsWithChildren } from "react";
import { View } from "react-native";

export function Screen({ children }: PropsWithChildren) {
  // Basic screen container to centralize spacing/padding conventions.
  return <View style={{ flex: 1, padding: 16 }}>{children}</View>;
}
