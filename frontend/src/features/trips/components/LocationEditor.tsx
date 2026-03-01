import { View, Text } from "react-native";
import { TextInput } from "@/shared/components/TextInput";
import { Button } from "@/shared/components/Button";
import type { Location } from "@/features/trips/types";

type LocationEditorProps = {
  location: Location;
  onChange: (next: Location) => void;
  onRemove: () => void;
};

export function LocationEditor({ location, onChange, onRemove }: LocationEditorProps) {
  // Edits one location row for itinerary day.
  return (
    <View style={{ gap: 6, borderWidth: 1, borderColor: "#ddd", borderRadius: 8, padding: 8 }}>
      <TextInput
        placeholder="Location name"
        value={location.name}
        onChangeText={(value) => onChange({ ...location, name: value })}
      />
      <TextInput
        placeholder="District (Bihar)"
        value={location.district ?? ""}
        onChangeText={(value) => onChange({ ...location, district: value || undefined })}
      />
      <TextInput
        placeholder="Block"
        value={location.block ?? ""}
        onChangeText={(value) => onChange({ ...location, block: value || undefined })}
      />
      <TextInput
        placeholder="Connectivity zone (low/moderate/high/severe)"
        value={location.connectivityZone ?? ""}
        autoCapitalize="none"
        onChangeText={(value) => {
          const normalized = value.trim().toLowerCase();
          const zone =
            normalized === "low" || normalized === "moderate" || normalized === "high" || normalized === "severe"
              ? normalized
              : undefined;
          onChange({ ...location, connectivityZone: zone });
        }}
      />
      <Button onPress={onRemove}>Remove location</Button>
      <Text style={{ fontSize: 12 }}>Use Bihar district/block names when known.</Text>
    </View>
  );
}
