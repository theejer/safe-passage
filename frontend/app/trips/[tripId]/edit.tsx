import { Link, useLocalSearchParams } from "expo-router";
import { ScrollView, Text } from "react-native";

export default function EditTripScreen() {
  const { tripId } = useLocalSearchParams<{ tripId: string }>();

  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>
      <Text style={{ fontSize: 20, fontWeight: "700" }}>Edit Trip</Text>
      <Text>Trip ID: {String(tripId ?? "")}</Text>
      <Text>Manage itinerary details or re-import from a file.</Text>
      <Link href={`/trips/${tripId}/itinerary`}>Edit Itinerary</Link>
      <Link href={`/trips/${tripId}/import`}>Import Itinerary File</Link>
      <Link href={`/trips/${tripId}`}>Back to View Trip</Link>
      <Link href="/dashboard">Back to Dashboard</Link>
    </ScrollView>
  );
}
