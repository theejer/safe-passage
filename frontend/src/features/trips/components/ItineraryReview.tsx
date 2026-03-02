import { useEffect, useState } from "react";
import { View, Text, TouchableOpacity, ScrollView } from "react-native";
import { Day } from "../types";
import { DayEditor } from "./DayEditor";
import { Button } from "@/shared/components/Button";

type ItineraryReviewProps = {
  itinerary: { days: Day[] };
  onConfirm: (days: Day[]) => void;
  onCheckRisk: (days: Day[]) => void;
  onEdit: () => void;
  saving?: boolean;
  checkingRisk?: boolean;
};

export function ItineraryReview({ itinerary, onConfirm, onCheckRisk, onEdit, saving = false, checkingRisk = false }: ItineraryReviewProps) {
  const [days, setDays] = useState<Day[]>(itinerary.days);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<"table" | "cards">("table");

  useEffect(() => {
    setDays(itinerary.days);
  }, [itinerary.days]);

  function addDay() {
    const nextIndex = days.length + 1;
    const nextDayNumber = String(nextIndex).padStart(2, "0");
    setDays((prev) => [
      ...prev,
      {
        date: `2026-01-${nextDayNumber}`,
        accommodation: "",
        locations: [{ name: "", district: "", block: "" }],
      },
    ]);
  }

  if (editingIndex !== null) {
    return (
      <ScrollView contentContainerStyle={{ flexGrow: 1, padding: 16 }}>
        <Text style={{ fontSize: 18, fontWeight: "700", marginBottom: 16 }}>Edit Day {editingIndex + 1}</Text>
        <DayEditor
          dayIndex={editingIndex}
          day={days[editingIndex]}
          onChange={(updatedDay: Day) => {
            const newDays = [...days];
            newDays[editingIndex] = updatedDay;
            setDays(newDays);
            setEditingIndex(null);
          }}
          onRemove={() => {
            const newDays = days.filter((_, idx) => idx !== editingIndex);
            setDays(newDays);
            setEditingIndex(null);
          }}
        />
      </ScrollView>
    );
  }

  return (
    <ScrollView contentContainerStyle={{ flexGrow: 1, padding: 16 }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Text style={{ fontSize: 18, fontWeight: "700" }}>Extracted Itinerary ({days.length} days)</Text>
        <View style={{ flexDirection: "row", gap: 8 }}>
          <Button block={false} size="sm" variant="outline" onPress={addDay} disabled={saving || checkingRisk}>
            Add Day
          </Button>
          <TouchableOpacity
            style={{
              paddingHorizontal: 12,
              paddingVertical: 6,
              borderRadius: 6,
              backgroundColor: viewMode === "table" ? "#1976d2" : "#e0e0e0",
            }}
            onPress={() => setViewMode("table")}
          >
            <Text style={{ fontSize: 12, color: viewMode === "table" ? "white" : "#666", fontWeight: "600" }}>
              Table
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={{
              paddingHorizontal: 12,
              paddingVertical: 6,
              borderRadius: 6,
              backgroundColor: viewMode === "cards" ? "#1976d2" : "#e0e0e0",
            }}
            onPress={() => setViewMode("cards")}
          >
            <Text style={{ fontSize: 12, color: viewMode === "cards" ? "white" : "#666", fontWeight: "600" }}>
              Cards
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      <View style={{ marginBottom: 16 }}>
        {viewMode === "table" ? (
          // TABLE VIEW
          <View style={{ borderWidth: 1, borderColor: "#ddd", borderRadius: 8, overflow: "hidden" }}>
            {/* Table Header */}
            <View
              style={{
                flexDirection: "row",
                backgroundColor: "#1976d2",
                paddingVertical: 12,
                paddingHorizontal: 8,
                gap: 8,
              }}
            >
              <Text style={{ flex: 0.5, color: "white", fontWeight: "700", fontSize: 12 }}>Day</Text>
              <Text style={{ flex: 1, color: "white", fontWeight: "700", fontSize: 12 }}>Date</Text>
              <Text style={{ flex: 2, color: "white", fontWeight: "700", fontSize: 12 }}>Locations</Text>
              <Text style={{ flex: 1, color: "white", fontWeight: "700", fontSize: 12 }}>Stay</Text>
              <Text style={{ flex: 0.6, color: "white", fontWeight: "700", fontSize: 12 }}>Edit</Text>
            </View>

            {/* Table Rows */}
            {days.map((day, index) => (
              <View
                key={index}
                style={{
                  flexDirection: "row",
                  paddingVertical: 12,
                  paddingHorizontal: 8,
                  gap: 8,
                  borderBottomWidth: index < days.length - 1 ? 1 : 0,
                  borderBottomColor: "#f0f0f0",
                  backgroundColor: index % 2 === 0 ? "#fafafa" : "white",
                }}
              >
                <Text style={{ flex: 0.5, fontWeight: "700", fontSize: 12 }}>{index + 1}</Text>
                <Text style={{ flex: 1, fontSize: 11, color: "#333" }}>{day.date}</Text>
                <Text style={{ flex: 2, fontSize: 11, color: "#666" }}>
                  {day.locations.map((loc) => `${loc.name}${loc.district ? ` (${loc.district})` : ""}`).join(", ")}
                </Text>
                <Text style={{ flex: 1, fontSize: 11, color: "#666" }}>
                  {day.accommodation ? day.accommodation.substring(0, 20) + (day.accommodation.length > 20 ? "..." : "") : "-"}
                </Text>
                <TouchableOpacity
                  style={{ flex: 0.6, padding: 4 }}
                  onPress={() => setEditingIndex(index)}
                >
                  <Text style={{ color: "#1976d2", fontSize: 11, fontWeight: "600" }}>Edit</Text>
                </TouchableOpacity>
              </View>
            ))}
          </View>
        ) : (
          // CARD VIEW
          <>
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
          </>
        )}
      </View>

      <View style={{ gap: 8, flexDirection: "row" }}>
        <Button block={false} variant="outline" style={{ flex: 1 }} onPress={onEdit} disabled={saving || checkingRisk}>
          Edit File
        </Button>
        <Button block={false} style={{ flex: 1 }} onPress={() => onConfirm(days)} loading={saving} disabled={checkingRisk}>
          Save
        </Button>
        <Button block={false} variant="secondary" style={{ flex: 1 }} onPress={() => onCheckRisk(days)} loading={checkingRisk} disabled={saving}>
          Check Risk
        </Button>
      </View>
    </ScrollView>
  );
}
