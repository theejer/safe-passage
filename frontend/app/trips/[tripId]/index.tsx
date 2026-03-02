import { useLocalSearchParams, useRouter } from "expo-router";
import { useState, useEffect } from "react";
import { View, Text, Alert, ScrollView, TextInput } from "react-native";
import { getTripById } from "@/features/storage/services/offlineDb";
import { upsertTripWithSync } from "@/features/trips/services/tripsApi";
import { getLatestItinerary, upsertItinerary } from "@/features/trips/services/itineraryApi";
import { RiskSummary } from "@/features/risk/components/RiskSummary";
import { analyzeTripRisk } from "@/features/risk/services/riskApi";
import { DayList } from "@/features/trips/components/DayList";
import { Button } from "@/shared/components/Button";
import { LoadingModal } from "@/shared/components/LoadingModal";
import { tripUiColors } from "@/features/trips/styles/tripUi";
import type { Trip, Day } from "@/features/trips/types";

function parseIsoDate(value: string) {
  const parsed = new Date(`${value}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatIsoDate(value: Date) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function shiftDaysFromStart(days: Day[], startDate: string) {
  const start = parseIsoDate(startDate);
  if (!start) return days;

  return days.map((day, index) => {
    const next = new Date(start);
    next.setDate(start.getDate() + index);
    return { ...day, date: formatIsoDate(next) };
  });
}

function shiftDaysFromEnd(days: Day[], endDate: string) {
  const end = parseIsoDate(endDate);
  if (!end) return days;

  return days.map((day, index) => {
    const reversedIndex = days.length - 1 - index;
    const next = new Date(end);
    next.setDate(end.getDate() - reversedIndex);
    return { ...day, date: formatIsoDate(next) };
  });
}

function validateTripFields(title: string, startDate: string, endDate: string) {
  if (!title.trim()) {
    throw new Error("Trip title is required");
  }

  if (!startDate.trim()) {
    throw new Error("Start date is required");
  }

  if (!endDate.trim()) {
    throw new Error("End date is required");
  }
}

export default function TripDetailScreen() {
  const { tripId } = useLocalSearchParams<{ tripId: string }>();
  const router = useRouter();
  const normalizedTripId = String(tripId ?? "");

  const [trip, setTrip] = useState<Trip | null>(null);
  const [title, setTitle] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [itinerary, setItinerary] = useState<Day[]>([]);
  const [savingTrip, setSavingTrip] = useState(false);
  const [savingItinerary, setSavingItinerary] = useState(false);
  const [generatingRisk, setGeneratingRisk] = useState(false);
  const [openingImport, setOpeningImport] = useState(false);
  const [editingItinerary, setEditingItinerary] = useState(false);

  useEffect(() => {
    async function load() {
      if (!normalizedTripId) return;
      
      try {
        const tripData = await getTripById(normalizedTripId);
        if (tripData) {
          setTrip(tripData);
          setTitle(tripData.title);
          setStartDate(tripData.startDate);
          setEndDate(tripData.endDate);
        }

        const days = await getLatestItinerary(normalizedTripId);
        setItinerary(days);
      } catch (error) {
        console.error("[TripDetail] Load error:", error);
      }
    }

    void load();
  }, [normalizedTripId]);

  function onStartDateChange(value: string) {
    setStartDate(value);
    setItinerary((current) => shiftDaysFromStart(current, value));
  }

  function onEndDateChange(value: string) {
    setEndDate(value);
    setItinerary((current) => shiftDaysFromEnd(current, value));
  }

  async function persistTripAndItinerary(showSuccessMessage = true) {
    if (!trip) {
      throw new Error("Trip data not loaded");
    }

    validateTripFields(title, startDate, endDate);

    const savedTrip = await upsertTripWithSync({
      ...trip,
      title,
      startDate,
      endDate,
      heartbeatEnabled: trip.heartbeatEnabled,
    });

    await upsertItinerary(savedTrip.id, itinerary);
    setTrip(savedTrip);

    if (showSuccessMessage) {
      Alert.alert("Saved", "Trip details updated");
    }

    return savedTrip;
  }

  async function onSaveTripMetadata() {
    try {
      setSavingTrip(true);
      await persistTripAndItinerary(true);
      setEditingItinerary(false);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to save trip";
      Alert.alert("Save failed", message);
    } finally {
      setSavingTrip(false);
    }
  }

  async function onSaveItinerary() {
    try {
      setSavingItinerary(true);
      await persistTripAndItinerary(true);
      setEditingItinerary(false);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to save itinerary";
      Alert.alert("Save failed", message);
    } finally {
      setSavingItinerary(false);
    }
  }

  async function onGenerateRisk() {
    try {
      setGeneratingRisk(true);
      if (!itinerary.length) {
        Alert.alert("No itinerary", "Add or import itinerary first, then generate risk.");
        return;
      }

      const savedTrip = await persistTripAndItinerary(false);
      await analyzeTripRisk(savedTrip.id, itinerary);
      router.replace(`/trips/${savedTrip.id}/risk`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to generate risk";
      Alert.alert("Risk generation failed", message);
    } finally {
      setGeneratingRisk(false);
    }
  }

  async function onImportFilePress() {
    try {
      setOpeningImport(true);
      await persistTripAndItinerary(false);
      router.push(`/trips/${normalizedTripId}/import`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to open import";
      Alert.alert("Unable to open import", message);
    } finally {
      setOpeningImport(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 16 }}>
      {/* Trip Metadata Section */}
      <View style={{ gap: 8 }}>
        <Text style={{ fontSize: 12, fontWeight: "700", color: tripUiColors.mutedLabel, letterSpacing: 0.6 }}>
          TRIP DETAILS
        </Text>
        <TextInput
          placeholder="Trip title"
          value={title}
          onChangeText={setTitle}
          style={{
            borderWidth: 1,
            borderColor: "#d1d5db",
            borderRadius: 10,
            padding: 12,
            fontSize: 16,
            backgroundColor: "#ffffff",
          }}
        />
        <View style={{ flexDirection: "row", gap: 8 }}>
          <TextInput
            placeholder="Start date (YYYY-MM-DD)"
            value={startDate}
            onChangeText={onStartDateChange}
            style={{
              flex: 1,
              borderWidth: 1,
              borderColor: "#d1d5db",
              borderRadius: 10,
              padding: 12,
              fontSize: 14,
              backgroundColor: "#ffffff",
            }}
          />
          <TextInput
            placeholder="End date (YYYY-MM-DD)"
            value={endDate}
            onChangeText={onEndDateChange}
            style={{
              flex: 1,
              borderWidth: 1,
              borderColor: "#d1d5db",
              borderRadius: 10,
              padding: 12,
              fontSize: 14,
              backgroundColor: "#ffffff",
            }}
          />
        </View>
        <Button onPress={() => void onSaveTripMetadata()} loading={savingTrip} size="sm">
          Save Trip Details
        </Button>
      </View>

      {/* Risk Summary Section */}
      <View style={{ gap: 8 }}>
        <Text style={{ fontSize: 12, fontWeight: "700", color: tripUiColors.mutedLabel, letterSpacing: 0.6 }}>
          RISK ANALYSIS
        </Text>
        <View style={{ borderWidth: 1, borderColor: tripUiColors.cardBorder, borderRadius: 12, padding: 12, backgroundColor: tripUiColors.white }}>
          <RiskSummary tripId={normalizedTripId} />
        </View>
        <View style={{ flexDirection: "row", gap: 8 }}>
          <Button variant="outline" size="sm" block={false} onPress={() => void onGenerateRisk()} loading={generatingRisk}>
            Generate Risk
          </Button>
          <Button variant="outline" size="sm" block={false} onPress={() => router.replace(`/trips/${normalizedTripId}/risk`)}>
            View Full Risk
          </Button>
        </View>
      </View>

      {/* Itinerary Section */}
      <View style={{ gap: 8 }}>
        <Text style={{ fontSize: 12, fontWeight: "700", color: tripUiColors.mutedLabel, letterSpacing: 0.6 }}>
          ITINERARY
        </Text>
        {itinerary.length === 0 ? (
          <View style={{ padding: 12, backgroundColor: "#f9fafb", borderRadius: 10, borderWidth: 1, borderColor: "#e5e7eb" }}>
            <Text style={{ color: "#6b7280", textAlign: "center" }}>No itinerary yet</Text>
          </View>
        ) : editingItinerary ? (
          <DayList tripId={normalizedTripId} days={itinerary} onChangeDays={setItinerary} />
        ) : (
          <View style={{ gap: 6 }}>
            {itinerary.map((day, idx) => (
              <View key={idx} style={{ padding: 10, backgroundColor: "#f9fafb", borderRadius: 8, borderWidth: 1, borderColor: "#e5e7eb" }}>
                <Text style={{ fontWeight: "600", fontSize: 14 }}>Day {idx + 1}: {day.date}</Text>
                <Text style={{ fontSize: 13, color: "#4b5563" }}>
                  {day.locations.map((loc) => loc.name).filter(Boolean).join(", ") || "No locations"}
                </Text>
                {day.accommodation ? (
                  <Text style={{ fontSize: 12, color: "#6b7280" }}>Stay: {day.accommodation}</Text>
                ) : null}
              </View>
            ))}
          </View>
        )}

        {editingItinerary ? (
          <View style={{ flexDirection: "row", gap: 8 }}>
            <Button variant="secondary" size="sm" block={false} onPress={() => void onSaveItinerary()} loading={savingItinerary}>
              Save Itinerary
            </Button>
            <Button variant="outline" size="sm" block={false} onPress={() => setEditingItinerary(false)}>
              Cancel
            </Button>
          </View>
        ) : (
          <View style={{ flexDirection: "row", gap: 8, flexWrap: "wrap" }}>
            <Button variant="secondary" size="sm" block={false} onPress={() => setEditingItinerary(true)}>
              {itinerary.length > 0 ? "Edit Itinerary" : "Add Itinerary"}
            </Button>
            <Button variant="secondary" size="sm" block={false} onPress={() => void onImportFilePress()} loading={openingImport}>
              Import from PDF
            </Button>
          </View>
        )}
      </View>

      {/* Actions Section */}
      <View style={{ gap: 8 }}>
        <Button onPress={() => void onSaveTripMetadata()} loading={savingTrip}>Save Trip Details</Button>
      </View>

      <LoadingModal
        visible={generatingRisk}
        title="Analyzing Trip Risk"
        message="Saving latest trip changes and generating risk report..."
      />
    </ScrollView>
  );
}
