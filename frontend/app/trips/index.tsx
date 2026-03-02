import { useState } from "react";
import { useLocalSearchParams, useRouter } from "expo-router";
import { View, Text, ScrollView, TextInput } from "react-native";
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
            <TextInput
              placeholder="Start date (YYYY-MM-DD)"
              value={tripMetadata.startDate}
              onChangeText={(value) => updateTripMetadata({ startDate: value })}
              style={{ flex: 1, borderWidth: 1, borderColor: "#d1d5db", borderRadius: 10, padding: 12, fontSize: 14, backgroundColor: "#ffffff" }}
            />
            <TextInput
              placeholder="End date (YYYY-MM-DD)"
              value={tripMetadata.endDate}
              onChangeText={(value) => updateTripMetadata({ endDate: value })}
              style={{ flex: 1, borderWidth: 1, borderColor: "#d1d5db", borderRadius: 10, padding: 12, fontSize: 14, backgroundColor: "#ffffff" }}
            />
          </View>
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
