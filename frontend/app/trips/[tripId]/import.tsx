import { useLocalSearchParams } from "expo-router";
import { View, Text } from "react-native";

export default function ItineraryImportScreen() {
  // Placeholder for PDF/Excel picker upload and backend import call.
  const { tripId } = useLocalSearchParams<{ tripId: string }>();

  return (
    <View style={{ flex: 1, padding: 16, gap: 10 }}>
      <Text style={{ fontSize: 20, fontWeight: "700" }}>Import Itinerary</Text>
      <Text>Trip ID: {tripId}</Text>
      <Text>TODO: wire file picker and upload action.</Text>
    </View>
  );
}
