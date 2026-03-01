import { Stack } from "expo-router";

export default function RootLayout() {
  // Keeps route-level wiring thin; feature logic lives in src/features.
  return <Stack screenOptions={{ headerTitleAlign: "center" }} />;
}
