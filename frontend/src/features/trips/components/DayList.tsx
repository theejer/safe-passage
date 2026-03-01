import { View, Text } from "react-native";
import { DayEditor } from "@/features/trips/components/DayEditor";
import { Button } from "@/shared/components/Button";
import type { Day } from "@/features/trips/types";

type DayListProps = {
  tripId: string;
  days: Day[];
  onChangeDays: (days: Day[]) => void;
};

function emptyDay(nextIndex: number): Day {
  const dayNumber = String(nextIndex + 1).padStart(2, "0");
  return {
    date: `2026-01-${dayNumber}`,
    accommodation: "",
    locations: [{ name: "", district: "", block: "" }],
  };
}

export function DayList({ tripId, days, onChangeDays }: DayListProps) {
  // Renders editable itinerary days and location rows.
  function updateDay(index: number, day: Day) {
    onChangeDays(days.map((item, itemIndex) => (itemIndex === index ? day : item)));
  }

  function removeDay(index: number) {
    const nextDays = days.filter((_, itemIndex) => itemIndex !== index);
    onChangeDays(nextDays.length ? nextDays : [emptyDay(0)]);
  }

  function addDay() {
    onChangeDays([...days, emptyDay(days.length)]);
  }

  return (
    <View style={{ gap: 8 }}>
      <Text>Trip: {tripId}</Text>
      {days.map((day, dayIndex) => (
        <DayEditor
          key={`${tripId}-${dayIndex}`}
          dayIndex={dayIndex}
          day={day}
          onChange={(next) => updateDay(dayIndex, next)}
          onRemove={() => removeDay(dayIndex)}
        />
      ))}
      <Button onPress={addDay}>Add day</Button>
    </View>
  );
}
