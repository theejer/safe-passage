import { View, Text } from "react-native";
import { TripForm } from "@/features/trips/components/TripForm";

export default function NewTripScreen() {
  // Creates a new trip (title + date range), then navigates to detail dashboard.
  return (
    <View style={{ flex: 1, padding: 16, gap: 12 }}>
      <Text style={{ fontSize: 20, fontWeight: "700" }}>Create Trip</Text>
      <TripForm mode="create" />
    </View>
  );
}
