import { useState } from "react";
import { useLocalSearchParams, useRouter } from "expo-router";
import { View, Text } from "react-native";
import { TripForm } from "@/features/trips/components/TripForm";
import { ItineraryUpload } from "@/features/trips/components/ItineraryUpload";
import { ItineraryReview } from "@/features/trips/components/ItineraryReview";
import { UserInfoForm, UserInfo } from "@/features/trips/components/UserInfoForm";
import { upsertItinerary } from "@/features/trips/services/itineraryApi";
import { analyzeTripRisk } from "@/features/risk/services/riskApi";
import { Day } from "@/features/trips/types";

type TripStep = "tripinfo" | "upload" | "review" | "userinfo" | "complete";

export default function TripFlowScreen() {
  const router = useRouter();
  const { tripId: initialTripId } = useLocalSearchParams<{ tripId: string }>();

  const [step, setStep] = useState<TripStep>(initialTripId ? "upload" : "tripinfo");
  const [tripId, setTripId] = useState<string | null>(initialTripId || null);
  const [extractedItinerary, setExtractedItinerary] = useState<{ days: Day[] } | null>(null);
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(false);

  function handleTripCreated(id: string) {
    setTripId(id);
    setStep("upload");
  }


  async function handleConfirmItinerary(days: Day[]) {
    if (!tripId) return;
    try {
      setLoading(true);
      await upsertItinerary(tripId, days);
      setExtractedItinerary({ days });
      setStep("userinfo");
    } catch (error) {
      console.error("Failed to save itinerary:", error);
      alert("Failed to save itinerary. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCheckRisk(days: Day[]) {
    if (!tripId) return;
    try {
      setLoading(true);
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
      setLoading(false);
    }
  }

  function handleUserInfoSubmit(info: UserInfo) {
    setUserInfo(info);
    setStep("complete");
    setTimeout(() => {
      router.push(`/trips/${tripId}`);
    }, 1500);
  }

  return (
    <View style={{ flex: 1, backgroundColor: "white" }}>
      {step === "tripinfo" && (
        <View style={{ flex: 1, padding: 16, gap: 12 }}>
          <Text style={{ fontSize: 20, fontWeight: "700" }}>Create Trip</Text>
          <TripForm mode="create" onSuccess={handleTripCreated} />
        </View>
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
        />
      )}

      {step === "userinfo" && (
        <UserInfoForm onSubmit={handleUserInfoSubmit} />
      )}

      {step === "complete" && (
        <View style={{ flex: 1, justifyContent: "center", alignItems: "center", padding: 16 }}>
          <Text style={{ fontSize: 18, fontWeight: "700", textAlign: "center" }}>
            ✓ Trip Created
          </Text>
          <Text style={{ fontSize: 14, color: "#666", marginTop: 12, textAlign: "center" }}>
            Your trip and itinerary have been saved successfully.
          </Text>
        </View>
      )}
    </View>
  );
}
