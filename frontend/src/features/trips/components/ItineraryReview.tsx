import { useState } from "react";
import { View, Text, TouchableOpacity, ScrollView, TextInput, Button } from "react-native";
import { Day } from "../types";
import { DayEditor } from "./DayEditor";

type ItineraryReviewProps = {
  itinerary: { days: Day[] };
  onConfirm: (days: Day[]) => void;
  onEdit: () => void;
};

export function ItineraryReview({ itinerary, onConfirm, onEdit }: ItineraryReviewProps) {
  const [days, setDays] = useState<Day[]>(itinerary.days);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  if (editingIndex !== null) {
    return (
      <View style={{ flex: 1, padding: 16 }}>
        <Text style={{ fontSize: 18, fontWeight: "700", marginBottom: 16 }}>Edit Day {editingIndex + 1}</Text>
        <DayEditor
          day={days[editingIndex]}
          onSave={(updatedDay) => {
            const newDays = [...days];
            newDays[editingIndex] = updatedDay;
            setDays(newDays);
            setEditingIndex(null);
          }}
          onCancel={() => setEditingIndex(null)}
        />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, padding: 16 }}>
      <Text style={{ fontSize: 18, fontWeight: "700", marginBottom: 16 }}>Review Extracted Itinerary</Text>

      <ScrollView style={{ flex: 1, marginBottom: 16 }}>
        {days.map((day, index) => (
          <View
            key={index}
            style={{
              backgroundColor: "#f5f5f5",
              padding: 12,
              borderRadius: 8,
              marginBottom: 12,
            }}
          >
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
              <Text style={{ fontSize: 14, fontWeight: "600" }}>Day {index + 1}: {day.date}</Text>
              <TouchableOpacity
                style={{ padding: 8 }}
                onPress={() => setEditingIndex(index)}
              >
                <Text style={{ color: "#1976d2", fontSize: 12, fontWeight: "600" }}>Edit</Text>
              </TouchableOpacity>
            </View>

            {day.locations.map((loc, locIndex) => (
              <Text key={locIndex} style={{ fontSize: 12, color: "#666", marginTop: 4 }}>
                • {loc.name} {loc.district ? `(${loc.district})` : ""}
              </Text>
            ))}

            {day.accommodation && (
              <Text style={{ fontSize: 12, color: "#666", marginTop: 4, fontWeight: "500" }}>
                📍 Stay: {day.accommodation}
              </Text>
            )}
          </View>
        ))}
      </ScrollView>

      <View style={{ gap: 8, flexDirection: "row" }}>
        <Button
          title="Edit"
          color="#999"
          onPress={onEdit}
        />
        <Button
          title="Confirm"
          onPress={() => onConfirm(days)}
        />
      </View>
    </View>
  );
}
