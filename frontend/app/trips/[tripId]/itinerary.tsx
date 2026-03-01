import { useLocalSearchParams } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import { Text, ScrollView, Alert } from "react-native";
import { DayList } from "@/features/trips/components/DayList";
import { Button } from "@/shared/components/Button";
import { getLatestItinerary, upsertItinerary } from "@/features/trips/services/itineraryApi";
import type { Day } from "@/features/trips/types";

function createEmptyDay(): Day {
  return {
    date: "2026-01-01",
    accommodation: "",
    locations: [{ name: "", district: "", block: "" }],
  };
}

function validateDays(days: Day[]) {
  for (let dayIndex = 0; dayIndex < days.length; dayIndex += 1) {
    const day = days[dayIndex];
    if (!day.date || day.date.length < 10) {
      throw new Error(`Day ${dayIndex + 1}: date is required (YYYY-MM-DD)`);
    }

    if (!day.locations.length) {
      throw new Error(`Day ${dayIndex + 1}: at least one location is required`);
    }

    for (let locationIndex = 0; locationIndex < day.locations.length; locationIndex += 1) {
      if (!day.locations[locationIndex].name.trim()) {
        throw new Error(`Day ${dayIndex + 1}, location ${locationIndex + 1}: location name is required`);
      }
    }
  }
}

export default function ItineraryEditorScreen() {
  // View/edit itinerary day entries and save offline-first to backend sync queue.
  const { tripId } = useLocalSearchParams<{ tripId: string }>();
  const normalizedTripId = useMemo(() => String(tripId ?? ""), [tripId]);
  const [days, setDays] = useState<Day[]>([createEmptyDay()]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    async function load() {
      if (!normalizedTripId) {
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const latest = await getLatestItinerary(normalizedTripId);
        setDays(latest.length ? latest : [createEmptyDay()]);
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [normalizedTripId]);

  async function onSavePress() {
    if (!normalizedTripId) {
      Alert.alert("Missing trip", "Trip ID is missing.");
      return;
    }

    try {
      validateDays(days);
      setSaving(true);
      await upsertItinerary(normalizedTripId, days);
      Alert.alert("Saved", "Itinerary saved. If offline, it will sync when connected.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to save itinerary";
      Alert.alert("Save failed", message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>
      <Text style={{ fontSize: 20, fontWeight: "700" }}>Itinerary</Text>
      <Text>Trip ID: {normalizedTripId || "N/A"}</Text>
      {loading ? <Text>Loading itinerary...</Text> : null}
      {!loading ? <DayList tripId={normalizedTripId} days={days} onChangeDays={setDays} /> : null}
      <Button onPress={() => void onSavePress()}>{saving ? "Saving..." : "Save itinerary"}</Button>
      <Text>Offline fallback: changes are cached locally and queued for sync if backend is unavailable.</Text>
    </ScrollView>
  );
}
