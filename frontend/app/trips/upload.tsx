import { useState } from "react";
import { useLocalSearchParams, useRouter } from "expo-router";
import { View, Text } from "react-native";
import { ItineraryUpload } from "@/features/trips/components/ItineraryUpload";
import { ItineraryReview } from "@/features/trips/components/ItineraryReview";
import { UserInfoForm, UserInfo } from "@/features/trips/components/UserInfoForm";
import { upsertItinerary } from "@/features/trips/services/itineraryApi";
import { Day } from "@/features/trips/types";

type UploadStep = "upload" | "review" | "userinfo" | "complete";

export default function ItineraryUploadScreen() {
  const router = useRouter();
  const { tripId } = useLocalSearchParams<{ tripId: string }>();

  const [step, setStep] = useState<UploadStep>("upload");
  const [extractedItinerary, setExtractedItinerary] = useState<{ days: Day[] } | null>(null);
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(false);

  if (!tripId) {
    return <View style={{ flex: 1, justifyContent: "center", alignItems: "center" }}>
      <Text>Trip ID is required</Text>
    </View>;
  }

  async function handleConfirmItinerary(days: Day[]) {
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

  function handleUserInfoSubmit(info: UserInfo) {
    setUserInfo(info);
    setStep("complete");
    // The user info would typically be saved to the user profile/trip
    setTimeout(() => {
      router.push(`/trips/${tripId}`);
    }, 1500);
  }

  return (
    <View style={{ flex: 1, backgroundColor: "white" }}>
      {step === "upload" && (
        <ItineraryUpload
          tripId={tripId}
          onItineraryExtracted={(itinerary) => {
            setExtractedItinerary(itinerary);
            setStep("review");
          }}
          onCancel={() => router.back()}
        />
      )}

      {step === "review" && extractedItinerary && (
        <ItineraryReview
          itinerary={extractedItinerary}
          onConfirm={handleConfirmItinerary}
          onEdit={() => setStep("upload")}
        />
      )}

      {step === "userinfo" && (
        <UserInfoForm onSubmit={handleUserInfoSubmit} />
      )}

      {step === "complete" && (
        <View style={{ flex: 1, justifyContent: "center", alignItems: "center", padding: 16 }}>
          <Text style={{ fontSize: 18, fontWeight: "700", textAlign: "center" }}>
            ✓ Itinerary Saved
          </Text>
          <Text style={{ fontSize: 14, color: "#666", marginTop: 12, textAlign: "center" }}>
            Your itinerary and information have been saved successfully.
          </Text>
        </View>
      )}
    </View>
  );
}
