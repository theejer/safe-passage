import { useState } from "react";
import { useLocalSearchParams, useRouter } from "expo-router";
import { View, Text, ScrollView, TextInput, TouchableOpacity, Modal, Alert } from "react-native";
import { TripForm } from "@/features/trips/components/TripForm";
import { ItineraryUpload } from "@/features/trips/components/ItineraryUpload";
import { ItineraryReview } from "@/features/trips/components/ItineraryReview";
import { createTrip } from "@/features/trips/services/tripsApi";
import { upsertItinerary } from "@/features/trips/services/itineraryApi";
import { analyzeTripRisk } from "@/features/risk/services/riskApi";
import { generateUuidV4 } from "@/shared/utils/ids";
import { LoadingModal } from "@/shared/components/LoadingModal";
import { Day } from "@/features/trips/types";

type TripStep = "tripinfo" | "upload" | "review" | "complete";
type TripMetadata = { userId: string; title: string; startDate: string; endDate: string };

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

function withShiftedDatesFromStart(days: Day[], startDate: string) {
  const start = parseIsoDate(startDate);
  if (!start) return days;

  return days.map((day, index) => {
    const next = new Date(start);
    next.setDate(start.getDate() + index);
    return { ...day, date: formatIsoDate(next) };
  });
}

function withShiftedDatesFromEnd(days: Day[], endDate: string) {
  const end = parseIsoDate(endDate);
  if (!end) return days;

  return days.map((day, index) => {
    const reversedIndex = days.length - 1 - index;
    const next = new Date(end);
    next.setDate(end.getDate() - reversedIndex);
    return { ...day, date: formatIsoDate(next) };
  });
}

function validateMetadata(metadata: TripMetadata) {
  if (!metadata.title.trim()) {
    throw new Error("Trip title is required");
  }

  if (!metadata.startDate.trim()) {
    throw new Error("Start date is required");
  }

  if (!metadata.endDate.trim()) {
    throw new Error("End date is required");
  }

  const start = parseIsoDate(metadata.startDate);
  const end = parseIsoDate(metadata.endDate);
  if (!start || !end) {
    throw new Error("Start date and end date must be valid dates.");
  }

  if (start.getTime() > end.getTime()) {
    throw new Error("End date cannot be earlier than the start date.");
  }
}

export default function TripFlowScreen() {
  const router = useRouter();
  const { tripId: initialTripId } = useLocalSearchParams<{ tripId: string }>();

  const [step, setStep] = useState<TripStep>(initialTripId ? "upload" : "tripinfo");
  const [tripId, setTripId] = useState<string | null>(initialTripId || null);
  const [tripMetadata, setTripMetadata] = useState<TripMetadata | null>(null);
  const [extractedItinerary, setExtractedItinerary] = useState<{ days: Day[] } | null>(null);
  const [saving, setSaving] = useState(false);
  const [checkingRisk, setCheckingRisk] = useState(false);
  const [showStartDatePicker, setShowStartDatePicker] = useState(false);
  const [showEndDatePicker, setShowEndDatePicker] = useState(false);

  function generateYears() {
    const current = new Date().getFullYear();
    return Array.from({ length: 10 }, (_, i) => current - 5 + i);
  }

  function generateDays(year: number, month: number) {
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    return Array.from({ length: daysInMonth }, (_, i) => i + 1);
  }

  function DatePickerModal({
    visible,
    onClose,
    date,
    onDateChange,
  }: {
    visible: boolean;
    onClose: () => void;
    date: Date | null;
    onDateChange: (date: Date) => void;
  }) {
    const currentDate = date || new Date();
    const [year, setYear] = useState(currentDate.getFullYear());
    const [month, setMonth] = useState(currentDate.getMonth());
    const [day, setDay] = useState(currentDate.getDate());

    const handleConfirm = () => {
      onDateChange(new Date(year, month, day));
      onClose();
    };

    return (
      <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
        <View
          style={{
            flex: 1,
            backgroundColor: "rgba(0, 0, 0, 0.5)",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <View style={{ backgroundColor: "white", borderRadius: 12, padding: 20, width: "80%" }}>
            <Text style={{ fontSize: 18, fontWeight: "700", marginBottom: 16 }}>Select Date</Text>

            <View style={{ flexDirection: "row", gap: 8, marginBottom: 16 }}>
              <ScrollView style={{ flex: 1, maxHeight: 150, borderWidth: 1, borderColor: "#ccc", borderRadius: 8 }}>
                {generateYears().map((y) => (
                  <TouchableOpacity
                    key={y}
                    style={{
                      paddingVertical: 10,
                      paddingHorizontal: 8,
                      backgroundColor: year === y ? "#e3f2fd" : "white",
                    }}
                    onPress={() => setYear(y)}
                  >
                    <Text style={{ textAlign: "center", color: year === y ? "#1976d2" : "#000" }}>
                      {y}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              <ScrollView style={{ flex: 1, maxHeight: 150, borderWidth: 1, borderColor: "#ccc", borderRadius: 8 }}>
                {Array.from({ length: 12 }, (_, i) => i).map((m) => (
                  <TouchableOpacity
                    key={m}
                    style={{
                      paddingVertical: 10,
                      paddingHorizontal: 8,
                      backgroundColor: month === m ? "#e3f2fd" : "white",
                    }}
                    onPress={() => setMonth(m)}
                  >
                    <Text
                      style={{
                        textAlign: "center",
                        color: month === m ? "#1976d2" : "#000",
                      }}
                    >
                      {String(m + 1).padStart(2, "0")}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              <ScrollView style={{ flex: 1, maxHeight: 150, borderWidth: 1, borderColor: "#ccc", borderRadius: 8 }}>
                {generateDays(year, month).map((d) => (
                  <TouchableOpacity
                    key={d}
                    style={{
                      paddingVertical: 10,
                      paddingHorizontal: 8,
                      backgroundColor: day === d ? "#e3f2fd" : "white",
                    }}
                    onPress={() => setDay(d)}
                  >
                    <Text
                      style={{
                        textAlign: "center",
                        color: day === d ? "#1976d2" : "#000",
                      }}
                    >
                      {String(d).padStart(2, "0")}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </View>

            <View style={{ flexDirection: "row", justifyContent: "flex-end", gap: 8 }}>
              <TouchableOpacity
                style={{ borderWidth: 1, borderColor: "#1565c0", borderRadius: 10, paddingVertical: 10, paddingHorizontal: 14 }}
                onPress={onClose}
              >
                <Text style={{ color: "#1565c0", fontWeight: "700" }}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={{ borderWidth: 1, borderColor: "#1565c0", borderRadius: 10, paddingVertical: 10, paddingHorizontal: 14, backgroundColor: "#1976d2" }}
                onPress={handleConfirm}
              >
                <Text style={{ color: "white", fontWeight: "700" }}>Confirm</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    );
  }

  function handleTripMetadataSubmit(metadata: TripMetadata) {
    // Generate a temporary tripId but DON'T create the trip in DB yet
    const tempTripId = generateUuidV4();
    setTripId(tempTripId);
    setTripMetadata(metadata);
    setStep("upload");
  }

  function updateTripMetadata(patch: Partial<TripMetadata>) {
    setTripMetadata((current) => {
      if (!current) return current;
      const next = { ...current, ...patch };
      const start = parseIsoDate(next.startDate);
      const end = parseIsoDate(next.endDate);
      if (start && end && start.getTime() > end.getTime()) {
        Alert.alert("Invalid end date", "End date cannot be earlier than the start date.");
        return current;
      }

      setExtractedItinerary((existing) => {
        if (!existing) return existing;
        if (patch.startDate && patch.startDate !== current.startDate) {
          return { days: withShiftedDatesFromStart(existing.days, patch.startDate) };
        }
        if (patch.endDate && patch.endDate !== current.endDate) {
          return { days: withShiftedDatesFromEnd(existing.days, patch.endDate) };
        }
        return existing;
      });

      return next;
    });
  }

  function applyDatesAfterExtraction(days: Day[]) {
    if (!tripMetadata) return days;
    const byStart = withShiftedDatesFromStart(days, tripMetadata.startDate);
    return withShiftedDatesFromEnd(byStart, tripMetadata.endDate);
  }

  async function handleConfirmItinerary(days: Day[]) {
    if (!tripId || !tripMetadata) {
      alert("Missing trip information. Please start over.");
      return;
    }
    try {
      validateMetadata(tripMetadata);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Invalid trip details.";
      alert(message);
      return;
    }

    try {
      setSaving(true);
      const persistedTrip = await createTrip({
        id: tripId,
        userId: tripMetadata.userId,
        title: tripMetadata.title,
        startDate: tripMetadata.startDate,
        endDate: tripMetadata.endDate,
        heartbeatEnabled: true,
      });
      await upsertItinerary(persistedTrip.id, days);
      
      setExtractedItinerary({ days });
      setStep("complete");
      setTimeout(() => {
        router.replace("/dashboard");
      }, 1200);
    } catch (error) {
      console.error("Failed to save trip and itinerary:", error);
      alert("Failed to save trip and itinerary. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function handleCheckRisk(days: Day[]) {
    if (!tripId || !tripMetadata) {
      alert("Missing trip information. Please start over.");
      return;
    }
    try {
      validateMetadata(tripMetadata);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Invalid trip details.";
      alert(message);
      return;
    }

    try {
      setCheckingRisk(true);
      console.log("[TripFlow] Check Risk clicked", { tripId, itineraryDays: days.length });
      const persistedTrip = await createTrip({
        id: tripId,
        userId: tripMetadata.userId,
        title: tripMetadata.title,
        startDate: tripMetadata.startDate,
        endDate: tripMetadata.endDate,
        heartbeatEnabled: true,
      });
      await upsertItinerary(persistedTrip.id, days);

      await analyzeTripRisk(persistedTrip.id, days);
      router.replace(`/trips/${persistedTrip.id}/risk`);
    } catch (error) {
      console.error("Failed to analyze risk:", error);
      alert("Failed to analyze risk. Please try again.");
    } finally {
      setCheckingRisk(false);
    }
  }

  return (
    <View style={{ flex: 1, backgroundColor: "white" }}>
      {step === "tripinfo" && (
        <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>
          <Text style={{ fontSize: 20, fontWeight: "700" }}>Create Trip</Text>
          <TripForm mode="create" onMetadataSubmit={handleTripMetadataSubmit} />
        </ScrollView>
      )}

      {step === "upload" && tripId && (
        <ItineraryUpload
          tripId={tripId}
          onItineraryExtracted={(itinerary) => {
            setExtractedItinerary({ days: applyDatesAfterExtraction(itinerary.days) });
            setStep("review");
          }}
          onCancel={() => {
            if (initialTripId) {
              router.back();
              return;
            }
            if (extractedItinerary) {
              setStep("review");
              return;
            }
            setStep("tripinfo");
          }}
        />
      )}

      {step === "review" && extractedItinerary && tripMetadata && (
        <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>
          <Text style={{ fontSize: 20, fontWeight: "700" }}>Review & Save Trip</Text>
          <TextInput
            placeholder="Trip title"
            value={tripMetadata.title}
            onChangeText={(value) => updateTripMetadata({ title: value })}
            style={{ borderWidth: 1, borderColor: "#d1d5db", borderRadius: 10, padding: 12, fontSize: 16, backgroundColor: "#ffffff" }}
          />
          <View style={{ flexDirection: "row", gap: 8 }}>
            <TouchableOpacity
              style={{ flex: 1, borderWidth: 1, borderColor: "#d1d5db", borderRadius: 10, padding: 12, justifyContent: "center", backgroundColor: "#ffffff" }}
              onPress={() => setShowStartDatePicker(true)}
            >
              <Text style={{ fontSize: 14, color: tripMetadata.startDate ? "#111827" : "#9ca3af" }}>
                Start date: {tripMetadata.startDate || "Select date"}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={{ flex: 1, borderWidth: 1, borderColor: "#d1d5db", borderRadius: 10, padding: 12, justifyContent: "center", backgroundColor: "#ffffff" }}
              onPress={() => setShowEndDatePicker(true)}
            >
              <Text style={{ fontSize: 14, color: tripMetadata.endDate ? "#111827" : "#9ca3af" }}>
                End date: {tripMetadata.endDate || "Select date"}
              </Text>
            </TouchableOpacity>
          </View>
          <DatePickerModal
            visible={showStartDatePicker}
            onClose={() => setShowStartDatePicker(false)}
            date={parseIsoDate(tripMetadata.startDate)}
            onDateChange={(value) => updateTripMetadata({ startDate: formatIsoDate(value) })}
          />
          <DatePickerModal
            visible={showEndDatePicker}
            onClose={() => setShowEndDatePicker(false)}
            date={parseIsoDate(tripMetadata.endDate)}
            onDateChange={(value) => updateTripMetadata({ endDate: formatIsoDate(value) })}
          />
          <ItineraryReview
            itinerary={extractedItinerary}
            onConfirm={handleConfirmItinerary}
            onCheckRisk={handleCheckRisk}
            onEdit={() => setStep("upload")}
            saving={saving}
            checkingRisk={checkingRisk}
          />
        </ScrollView>
      )}

      <LoadingModal
        visible={checkingRisk}
        title="Analyzing Trip Risk"
        message="Saving trip details and itinerary, then generating risk report..."
      />

      {step === "complete" && (
        <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: "center", alignItems: "center", padding: 16 }}>
          <Text style={{ fontSize: 18, fontWeight: "700", textAlign: "center" }}>
            ✓ Trip Created
          </Text>
          <Text style={{ fontSize: 14, color: "#666", marginTop: 12, textAlign: "center" }}>
            Your trip and itinerary have been saved successfully. Returning to dashboard...
          </Text>
        </ScrollView>
      )}
    </View>
  );
}
