import { View, Text } from "react-native";
import { TripList } from "@/features/trips/components/TripList";

export default function TripsScreen() {
  // Thin route: list trips via feature hooks/components.
  return (
    <View style={{ flex: 1, padding: 16, gap: 12 }}>
      <Text style={{ fontSize: 20, fontWeight: "700" }}>Trips</Text>
      <TripList />
    </View>
  );
}
