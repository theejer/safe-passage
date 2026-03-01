import { View, Text, TextInput } from "react-native";
import { LocationEditor } from "@/features/trips/components/LocationEditor";

type DayEditorProps = { dayIndex: number };

export function DayEditor({ dayIndex }: DayEditorProps) {
  // Edits one day's itinerary: locations + accommodation.
  return (
    <View style={{ borderWidth: 1, borderColor: "#ddd", borderRadius: 8, padding: 10, gap: 8 }}>
      <Text style={{ fontWeight: "700" }}>Day {dayIndex + 1}</Text>
      <TextInput placeholder="Accommodation" style={{ borderWidth: 1, borderColor: "#ccc", padding: 8, borderRadius: 8 }} />
      <LocationEditor />
    </View>
  );
}
