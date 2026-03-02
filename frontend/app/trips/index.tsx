import { useState } from "react";
import { useLocalSearchParams, useRouter } from "expo-router";
import { View, Text, ScrollView } from "react-native";
import { TripForm } from "@/features/trips/components/TripForm";
import { ItineraryUpload } from "@/features/trips/components/ItineraryUpload";
import { ItineraryReview } from "@/features/trips/components/ItineraryReview";
import { upsertItinerary } from "@/features/trips/services/itineraryApi";
import { analyzeTripRisk } from "@/features/risk/services/riskApi";
import { Day } from "@/features/trips/types";

type TripStep = "tripinfo" | "upload" | "review" | "complete";

export default function TripFlowScreen() {
  const router = useRouter();
  const { tripId: initialTripId } = useLocalSearchParams<{ tripId: string }>();

  const [step, setStep] = useState<TripStep>(initialTripId ? "upload" : "tripinfo");
  const [tripId, setTripId] = useState<string | null>(initialTripId || null);
  const [extractedItinerary, setExtractedItinerary] = useState<{ days: Day[] } | null>(null);
  const [saving, setSaving] = useState(false);
  const [checkingRisk, setCheckingRisk] = useState(false);

  function handleTripCreated(id: string) {
    setTripId(id);
    setStep("upload");
  }


  async function handleConfirmItinerary(days: Day[]) {
    if (!tripId) {
      alert("Missing trip ID. Please create or select a trip first.");
      return;
    }
    try {
      setSaving(true);
      await upsertItinerary(tripId, days);
      setExtractedItinerary({ days });
      setStep("complete");
      setTimeout(() => {
        router.replace("/dashboard");
      }, 1200);
    } catch (error) {
      console.error("Failed to save itinerary:", error);
      alert("Failed to save itinerary. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function handleCheckRisk(days: Day[]) {
    if (!tripId) {
      alert("Missing trip ID. Please create or select a trip first.");
      return;
    }
    try {
      setCheckingRisk(true);
      console.log("[TripFlow] Check Risk clicked", { tripId, itineraryDays: days.length });
      try {
        await upsertItinerary(tripId, days);
      } catch (persistError) {
        console.warn("[TripFlow CheckRisk] Continuing without itinerary persistence:", persistError);
      }

      const report = await analyzeTripRisk(tripId, days);
      alert(report.summary || "Risk analysis completed.");
      router.push(`/trips/${tripId}/risk`);
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
          <TripForm mode="create" onSuccess={handleTripCreated} />
        </ScrollView>
      )}

      {step === "upload" && tripId && (
        <ItineraryUpload
          tripId={tripId}
          onItineraryExtracted={(itinerary) => {
            setExtractedItinerary(itinerary);
            setStep("review");
          }}
          onCancel={() => (initialTripId ? router.back() : setStep("tripinfo"))}
        />
      )}

      {step === "review" && extractedItinerary && (
        <ItineraryReview
          itinerary={extractedItinerary}
          onConfirm={handleConfirmItinerary}
          onCheckRisk={handleCheckRisk}
          onEdit={() => setStep("upload")}
          saving={saving}
          checkingRisk={checkingRisk}
        />
      )}

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
