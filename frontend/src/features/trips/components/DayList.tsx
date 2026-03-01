import { View, Text } from "react-native";
import { DayEditor } from "@/features/trips/components/DayEditor";

type DayListProps = { tripId: string };

export function DayList({ tripId }: DayListProps) {
  // Placeholder list; eventual source is itinerary hook or API fetch.
  return (
    <View style={{ gap: 8 }}>
      <Text>Trip: {tripId}</Text>
      <DayEditor dayIndex={0} />
    </View>
  );
}
