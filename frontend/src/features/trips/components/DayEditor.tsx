import { View, Text } from "react-native";
import { LocationEditor } from "@/features/trips/components/LocationEditor";
import { Button } from "@/shared/components/Button";
import { TextInput } from "@/shared/components/TextInput";
import type { Day, Location } from "@/features/trips/types";

type DayEditorProps = {
  dayIndex: number;
  day: Day;
  onChange: (next: Day) => void;
  onRemove: () => void;
};

function emptyLocation(): Location {
  return {
    name: "",
    district: "",
    block: "",
  };
}

export function DayEditor({ dayIndex, day, onChange, onRemove }: DayEditorProps) {
  // Edits one itinerary day and nested locations.
  function updateLocation(index: number, location: Location) {
    const nextLocations = day.locations.map((item, itemIndex) => (itemIndex === index ? location : item));
    onChange({ ...day, locations: nextLocations });
  }

  function removeLocation(index: number) {
    const nextLocations = day.locations.filter((_, itemIndex) => itemIndex !== index);
    onChange({ ...day, locations: nextLocations.length ? nextLocations : [emptyLocation()] });
  }

  function addLocation() {
    onChange({ ...day, locations: [...day.locations, emptyLocation()] });
  }

  return (
    <View style={{ borderWidth: 1, borderColor: "#ddd", borderRadius: 8, padding: 10, gap: 8 }}>
      <Text style={{ fontWeight: "700" }}>Day {dayIndex + 1}</Text>
      <TextInput
        placeholder="Date (YYYY-MM-DD)"
        value={day.date}
        autoCapitalize="none"
        onChangeText={(value) => onChange({ ...day, date: value })}
      />
      <TextInput
        placeholder="Accommodation"
        value={day.accommodation ?? ""}
        onChangeText={(value) => onChange({ ...day, accommodation: value || undefined })}
      />
      {day.locations.map((location, locationIndex) => (
        <LocationEditor
          key={`${dayIndex}-${locationIndex}`}
          location={location}
          onChange={(next) => updateLocation(locationIndex, next)}
          onRemove={() => removeLocation(locationIndex)}
        />
      ))}
      <Button onPress={addLocation}>Add location</Button>
      <Button onPress={onRemove}>Remove day</Button>
    </View>
  );
}
