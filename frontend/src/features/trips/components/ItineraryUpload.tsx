import { useState } from "react";
import { View, Text, TouchableOpacity, ActivityIndicator } from "react-native";
import * as DocumentPicker from "expo-document-picker";
import { uploadItineraryPDF } from "@/features/trips/services/itineraryApi";
import { Day } from "../types";

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
        type: "application/pdf",
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
      formData.append("file", {
        uri: file.uri,
        type: "application/pdf",
        name: file.name || "itinerary.pdf",
      } as any);

      const response = await uploadItineraryPDF(formData);
      setLoading(false);

      if (response.days && response.days.length > 0) {
        onItineraryExtracted(response);
      } else {
        setError("Could not extract itinerary data from PDF");
      }
    } catch (err: any) {
      setLoading(false);
      setError(err.message || "Failed to process PDF");
    }
  }

  return (
    <View style={{ flex: 1, padding: 16, justifyContent: "center", alignItems: "center", gap: 16 }}>
      <Text style={{ fontSize: 18, fontWeight: "700", textAlign: "center" }}>Upload Itinerary PDF</Text>
      <Text style={{ fontSize: 14, color: "#666", textAlign: "center" }}>
        Select a PDF file containing your trip itinerary. We'll extract the details automatically.
      </Text>

      {error && (
        <View style={{ backgroundColor: "#ffebee", padding: 12, borderRadius: 8, width: "100%" }}>
          <Text style={{ color: "#c62828", fontSize: 14 }}>{error}</Text>
        </View>
      )}

      {loading && (
        <View style={{ alignItems: "center", gap: 12 }}>
          <ActivityIndicator size="large" color="#1976d2" />
          <Text style={{ color: "#666" }}>Processing PDF...</Text>
        </View>
      )}

      {!loading && (
        <>
          <TouchableOpacity
            style={{
              backgroundColor: "#1976d2",
              paddingVertical: 12,
              paddingHorizontal: 24,
              borderRadius: 8,
              width: "100%",
              alignItems: "center",
            }}
            onPress={pickPDF}
          >
            <Text style={{ color: "white", fontSize: 16, fontWeight: "600" }}>Choose PDF File</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={{
              paddingVertical: 12,
              paddingHorizontal: 24,
              borderRadius: 8,
              borderWidth: 1,
              borderColor: "#999",
              width: "100%",
              alignItems: "center",
            }}
            onPress={onCancel}
          >
            <Text style={{ color: "#333", fontSize: 16, fontWeight: "600" }}>Cancel</Text>
          </TouchableOpacity>
        </>
      )}
    </View>
  );
}
