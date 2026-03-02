import { useState } from "react";
import { View, TextInput, Button, TouchableOpacity, Text, Modal, ScrollView } from "react-native";
import { createTrip } from "@/features/trips/services/tripsApi";
import { getItem } from "@/features/storage/services/localStore";

const ACTIVE_USER_ID_KEY = "active_user_id";

type TripFormProps = { 
  mode: "create" | "edit";
  onSuccess?: (tripId: string) => void;
};

export function TripForm({ mode, onSuccess }: TripFormProps) {
  // Minimal create/edit form scaffold for trip metadata.
  const [title, setTitle] = useState("");
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);
  const [showStartDatePicker, setShowStartDatePicker] = useState(false);
  const [showEndDatePicker, setShowEndDatePicker] = useState(false);

  const formatDate = (date: Date | null) => {
    if (!date) return "Select date";
    return date.toISOString().split("T")[0];
  };

  const formatDateForAPI = (date: Date | null) => {
    if (!date) return "";
    return date.toISOString().split("T")[0];
  };

  const generateYears = () => {
    const current = new Date().getFullYear();
    return Array.from({ length: 10 }, (_, i) => current - 5 + i);
  };

  const generateDays = (year: number, month: number) => {
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    return Array.from({ length: daysInMonth }, (_, i) => i + 1);
  };

  const DatePickerModal = ({
    visible,
    onClose,
    date,
    onDateChange,
  }: {
    visible: boolean;
    onClose: () => void;
    date: Date | null;
    onDateChange: (date: Date) => void;
  }) => {
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

            <View style={{ flexDirection: "row", gap: 8 }}>
              <Button title="Cancel" color="#999" onPress={onClose} />
              <Button title="Confirm" onPress={handleConfirm} />
            </View>
          </View>
        </View>
      </Modal>
    );
  };

  async function onSubmit() {
    if (mode === "create") {
      const activeUserId = (await getItem(ACTIVE_USER_ID_KEY)) ?? "demo-user";
      const trip = await createTrip({
        userId: activeUserId,
        title,
        startDate: formatDateForAPI(startDate),
        endDate: formatDateForAPI(endDate),
      });
      onSuccess?.(trip.id);
    }
  }

  return (
    <ScrollView contentContainerStyle={{ gap: 8 }}>
      <TextInput
        placeholder="Trip title"
        value={title}
        onChangeText={setTitle}
        style={{ borderWidth: 1, borderColor: "#ccc", padding: 10, borderRadius: 8 }}
      />

      <TouchableOpacity
        style={{ borderWidth: 1, borderColor: "#ccc", padding: 10, borderRadius: 8, justifyContent: "center" }}
        onPress={() => setShowStartDatePicker(true)}
      >
        <Text style={{ fontSize: 16, color: startDate ? "#000" : "#999" }}>Start date: {formatDate(startDate)}</Text>
      </TouchableOpacity>

      <DatePickerModal
        visible={showStartDatePicker}
        onClose={() => setShowStartDatePicker(false)}
        date={startDate}
        onDateChange={setStartDate}
      />

      <TouchableOpacity
        style={{ borderWidth: 1, borderColor: "#ccc", padding: 10, borderRadius: 8, justifyContent: "center" }}
        onPress={() => setShowEndDatePicker(true)}
      >
        <Text style={{ fontSize: 16, color: endDate ? "#000" : "#999" }}>End date: {formatDate(endDate)}</Text>
      </TouchableOpacity>

      <DatePickerModal
        visible={showEndDatePicker}
        onClose={() => setShowEndDatePicker(false)}
        date={endDate}
        onDateChange={setEndDate}
      />

      <Button title={mode === "create" ? "Create trip" : "Save changes"} onPress={() => void onSubmit()} />
    </ScrollView>
  );
}
