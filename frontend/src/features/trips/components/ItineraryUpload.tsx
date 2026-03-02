import { useState } from "react";
import { View, Text, ActivityIndicator, Platform, ScrollView } from "react-native";
import * as DocumentPicker from "expo-document-picker";
import { uploadItineraryPDF } from "@/features/trips/services/itineraryApi";
import { Day } from "../types";
import { Button } from "@/shared/components/Button";

type ItineraryUploadProps = {
  tripId: string;
  onItineraryExtracted: (itinerary: { days: Day[] }) => void;
  onCancel: () => void;
};

export function ItineraryUpload({ tripId, onItineraryExtracted, onCancel }: ItineraryUploadProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function pickPDF() {
    try {
      setError(null);
      const result = await DocumentPicker.getDocumentAsync({
        type: [
          "application/pdf",
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          "application/msword",
          "text/plain",
        ],
      });

      if (result.canceled) {
        return;
      }

      const file = result.assets[0];
      if (!file.uri) {
        setError("Failed to get file URI");
        return;
      }

      setLoading(true);

      // Create FormData and upload
      const formData = new FormData();
      formData.append("trip_id", tripId);

      if (Platform.OS === "web") {
        const webFile = (file as any).file as File | undefined;
        if (webFile) {
          formData.append("file", webFile, webFile.name || file.name || "itinerary-document");
        } else {
          const blobResponse = await fetch(file.uri);
          const blob = await blobResponse.blob();
          formData.append("file", blob, file.name || "itinerary-document");
        }
      } else {
        formData.append("file", {
          uri: file.uri,
          type: file.mimeType || "application/octet-stream",
          name: file.name || "itinerary-document",
        } as any);
      }

      console.log("[ItineraryUpload] Uploading PDF for trip:", tripId);
      const days = await uploadItineraryPDF(formData);
      setLoading(false);

      console.log("[ItineraryUpload] Extracted days:", days);
      if (days && days.length > 0) {
        console.log("[ItineraryUpload] Successfully extracted itinerary with", days.length, "days");
        onItineraryExtracted({ days });
      } else {
        setError("Could not extract any itinerary data from PDF. Please ensure the PDF contains travel dates and locations.");
      }
    } catch (err: any) {
      setLoading(false);
      const errorMessage = err.message || "Failed to process PDF";
      console.error("[ItineraryUpload] Error:", errorMessage);
      setError(errorMessage);
    }
  }

  return (
    <ScrollView contentContainerStyle={{ flexGrow: 1, padding: 16, justifyContent: "center", alignItems: "center", gap: 16 }}>
      <Text style={{ fontSize: 18, fontWeight: "700", textAlign: "center" }}>Upload Itinerary File</Text>
      <Text style={{ fontSize: 14, color: "#666", textAlign: "center" }}>
        Select a PDF or document containing your trip itinerary. We&apos;ll extract the details automatically.
      </Text>

      {error && (
        <View style={{ backgroundColor: "#ffebee", padding: 12, borderRadius: 8, width: "100%" }}>
          <Text style={{ color: "#c62828", fontSize: 14 }}>{error}</Text>
        </View>
      )}

      {loading && (
        <View style={{ alignItems: "center", gap: 12 }}>
          <ActivityIndicator size="large" color="#1976d2" />
            <Text style={{ color: "#666" }}>Processing itinerary document...</Text>
        </View>
      )}

      {!loading && (
        <>
          <Button onPress={() => void pickPDF()}>Choose File</Button>
          <Button variant="outline" onPress={onCancel}>
            Cancel
          </Button>
        </>
      )}
    </ScrollView>
  );
}
