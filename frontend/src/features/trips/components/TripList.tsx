import { View, Text } from "react-native";
import { useTrips } from "@/features/trips/hooks/useTrips";

export function TripList() {
  // TODO: wire current userId from profile/auth context.
  const { items, loading } = useTrips("demo-user");

  if (loading) return <Text>Loading trips...</Text>;

  return (
    <View style={{ gap: 8 }}>
      {items.map((trip) => (
        <Text key={trip.id}>{trip.title}</Text>
      ))}
      {items.length === 0 ? <Text>No trips yet.</Text> : null}
    </View>
  );
}
