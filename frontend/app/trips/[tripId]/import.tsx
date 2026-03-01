import { useLocalSearchParams } from "expo-router";
import { useMemo, useState } from "react";
import { Alert, ScrollView, Text } from "react-native";
import { Button } from "@/shared/components/Button";
import { TextInput } from "@/shared/components/TextInput";
import { upsertItinerary } from "@/features/trips/services/itineraryApi";
import type { Day } from "@/features/trips/types";

function normalizeDays(value: unknown): Day[] {
  const root = value as { days?: unknown } | Day[];
  const rawDays = Array.isArray(root) ? root : Array.isArray(root?.days) ? root.days : null;

  if (!rawDays) {
    throw new Error("JSON must be an array of days or an object with a days array");
  }

  return rawDays.map((day, index) => {
    const item = day as {
      date?: unknown;
      accommodation?: unknown;
      locations?: unknown;
    };

    if (typeof item.date !== "string" || item.date.length < 10) {
      throw new Error(`Day ${index + 1}: date is required (YYYY-MM-DD)`);
    }

    const rawLocations = Array.isArray(item.locations) ? item.locations : [];
    if (rawLocations.length === 0) {
      throw new Error(`Day ${index + 1}: at least one location is required`);
    }

    return {
      date: item.date,
      accommodation: typeof item.accommodation === "string" ? item.accommodation : undefined,
      locations: rawLocations.map((location, locationIndex) => {
        const row = location as {
          name?: unknown;
          district?: unknown;
          block?: unknown;
          connectivity_zone?: unknown;
          connectivityZone?: unknown;
        };

        if (typeof row.name !== "string" || row.name.trim().length === 0) {
          throw new Error(`Day ${index + 1}, location ${locationIndex + 1}: name is required`);
        }

        const zone = typeof row.connectivity_zone === "string" ? row.connectivity_zone : row.connectivityZone;

        return {
          name: row.name,
          district: typeof row.district === "string" ? row.district : undefined,
          block: typeof row.block === "string" ? row.block : undefined,
          connectivityZone:
            zone === "low" || zone === "moderate" || zone === "high" || zone === "severe" ? zone : undefined,
        };
      }),
    };
  });
}

export default function ItineraryImportScreen() {
  const { tripId } = useLocalSearchParams<{ tripId: string }>();
  const normalizedTripId = useMemo(() => String(tripId ?? ""), [tripId]);
  const [jsonInput, setJsonInput] = useState(`{
  "days": [
    {
      "date": "2026-04-02",
      "locations": [{ "name": "Bodh Gaya", "district": "Gaya", "block": "Bodh Gaya" }],
      "accommodation": "Monastery Road Guest House"
    }
  ]
}`);
  const [submitting, setSubmitting] = useState(false);

  async function onImportPress() {
    if (!normalizedTripId) {
      Alert.alert("Missing trip", "Trip ID is missing.");
      return;
    }

    try {
      setSubmitting(true);
      const parsed = JSON.parse(jsonInput) as unknown;
      const days = normalizeDays(parsed);
      await upsertItinerary(normalizedTripId, days);
      Alert.alert("Imported", "Itinerary uploaded. Open Edit Itinerary to review and adjust days.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to import itinerary JSON";
      Alert.alert("Import failed", message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 10 }}>
      <Text style={{ fontSize: 20, fontWeight: "700" }}>Import Itinerary</Text>
      <Text>Trip ID: {normalizedTripId || "N/A"}</Text>
      <Text>Paste itinerary JSON (array of days or object with days).</Text>
      <TextInput
        multiline
        value={jsonInput}
        onChangeText={setJsonInput}
        autoCapitalize="none"
        autoCorrect={false}
        style={{ minHeight: 260, textAlignVertical: "top" }}
      />
      <Button onPress={() => void onImportPress()}>{submitting ? "Importing..." : "Import itinerary"}</Button>
      <Text>
        Assumptions: dates are ISO (YYYY-MM-DD), location names are required, and connectivity uses low/moderate/high/severe.
      </Text>
    </ScrollView>
  );
}
