import { useLocalSearchParams } from "expo-router";
import { View, Text } from "react-native";
import { DayList } from "@/features/trips/components/DayList";

export default function ItineraryEditorScreen() {
  // View/edit itinerary day entries and per-location details.
  const { tripId } = useLocalSearchParams<{ tripId: string }>();

  return (
    <View style={{ flex: 1, padding: 16, gap: 12 }}>
      <Text style={{ fontSize: 20, fontWeight: "700" }}>Itinerary</Text>
      <DayList tripId={String(tripId)} />
    </View>
  );
}
