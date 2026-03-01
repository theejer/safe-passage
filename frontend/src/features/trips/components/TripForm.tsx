import { useState } from "react";
import { View, TextInput, Button } from "react-native";
import { createTrip } from "@/features/trips/services/tripsApi";

type TripFormProps = { mode: "create" | "edit" };

export function TripForm({ mode }: TripFormProps) {
  // Minimal create/edit form scaffold for trip metadata.
  const [title, setTitle] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  async function onSubmit() {
    if (mode === "create") {
      await createTrip({ userId: "demo-user", title, startDate, endDate });
    }
  }

  return (
    <View style={{ gap: 8 }}>
      <TextInput placeholder="Trip title" value={title} onChangeText={setTitle} style={{ borderWidth: 1, borderColor: "#ccc", padding: 10, borderRadius: 8 }} />
      <TextInput placeholder="Start date (YYYY-MM-DD)" value={startDate} onChangeText={setStartDate} style={{ borderWidth: 1, borderColor: "#ccc", padding: 10, borderRadius: 8 }} />
      <TextInput placeholder="End date (YYYY-MM-DD)" value={endDate} onChangeText={setEndDate} style={{ borderWidth: 1, borderColor: "#ccc", padding: 10, borderRadius: 8 }} />
      <Button title={mode === "create" ? "Create trip" : "Save changes"} onPress={() => void onSubmit()} />
    </View>
  );
}
