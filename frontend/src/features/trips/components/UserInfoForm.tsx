import { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, ScrollView } from "react-native";

export type UserInfo = {
  name: string;
  email: string;
  phone: string;
  emergencyContact?: string;
  emergencyContactPhone?: string;
};

type UserInfoFormProps = {
  onSubmit: (userInfo: UserInfo) => void;
};

export function UserInfoForm({ onSubmit }: UserInfoFormProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [emergencyContact, setEmergencyContact] = useState("");
  const [emergencyContactPhone, setEmergencyContactPhone] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!name.trim()) {
      newErrors.name = "Name is required";
    }

    if (!email.trim()) {
      newErrors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = "Invalid email format";
    }

    if (!phone.trim()) {
      newErrors.phone = "Phone number is required";
    } else if (!/^\d{10}$/.test(phone.replace(/\D/g, ""))) {
      newErrors.phone = "Phone must be 10 digits";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  function handleSubmit() {
    if (validateForm()) {
      onSubmit({
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim(),
        emergencyContact: emergencyContact.trim() || undefined,
        emergencyContactPhone: emergencyContactPhone.trim() || undefined,
      });
    }
  }

  return (
    <ScrollView style={{ flex: 1, padding: 16 }}>
      <Text style={{ fontSize: 18, fontWeight: "700", marginBottom: 16 }}>Your Information</Text>

      <View style={{ marginBottom: 16 }}>
        <Text style={{ fontSize: 14, fontWeight: "600", marginBottom: 4 }}>Full Name *</Text>
        <TextInput
          style={{
            borderWidth: 1,
            borderColor: errors.name ? "#c62828" : "#ccc",
            borderRadius: 8,
            padding: 10,
            fontSize: 14,
          }}
          placeholder="Your full name"
          value={name}
          onChangeText={setName}
        />
        {errors.name && <Text style={{ color: "#c62828", fontSize: 12, marginTop: 4 }}>{errors.name}</Text>}
      </View>

      <View style={{ marginBottom: 16 }}>
        <Text style={{ fontSize: 14, fontWeight: "600", marginBottom: 4 }}>Email *</Text>
        <TextInput
          style={{
            borderWidth: 1,
            borderColor: errors.email ? "#c62828" : "#ccc",
            borderRadius: 8,
            padding: 10,
            fontSize: 14,
          }}
          placeholder="your.email@example.com"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
        />
        {errors.email && <Text style={{ color: "#c62828", fontSize: 12, marginTop: 4 }}>{errors.email}</Text>}
      </View>

      <View style={{ marginBottom: 16 }}>
        <Text style={{ fontSize: 14, fontWeight: "600", marginBottom: 4 }}>Phone Number *</Text>
        <TextInput
          style={{
            borderWidth: 1,
            borderColor: errors.phone ? "#c62828" : "#ccc",
            borderRadius: 8,
            padding: 10,
            fontSize: 14,
          }}
          placeholder="10-digit phone number"
          value={phone}
          onChangeText={setPhone}
          keyboardType="phone-pad"
        />
        {errors.phone && <Text style={{ color: "#c62828", fontSize: 12, marginTop: 4 }}>{errors.phone}</Text>}
      </View>

      <Text style={{ fontSize: 14, fontWeight: "600", color: "#666", marginVertical: 12 }}>Emergency Contact (Optional)</Text>

      <View style={{ marginBottom: 16 }}>
        <Text style={{ fontSize: 12, color: "#999", marginBottom: 4 }}>Contact Name</Text>
        <TextInput
          style={{
            borderWidth: 1,
            borderColor: "#ccc",
            borderRadius: 8,
            padding: 10,
            fontSize: 14,
          }}
          placeholder="Emergency contact name"
          value={emergencyContact}
          onChangeText={setEmergencyContact}
        />
      </View>

      <View style={{ marginBottom: 16 }}>
        <Text style={{ fontSize: 12, color: "#999", marginBottom: 4 }}>Contact Phone</Text>
        <TextInput
          style={{
            borderWidth: 1,
            borderColor: "#ccc",
            borderRadius: 8,
            padding: 10,
            fontSize: 14,
          }}
          placeholder="Emergency contact phone"
          value={emergencyContactPhone}
          onChangeText={setEmergencyContactPhone}
          keyboardType="phone-pad"
        />
      </View>

      <TouchableOpacity
        style={{
          backgroundColor: "#1976d2",
          paddingVertical: 12,
          borderRadius: 8,
          alignItems: "center",
          marginBottom: 8,
        }}
        onPress={handleSubmit}
      >
        <Text style={{ color: "white", fontSize: 16, fontWeight: "600" }}>Save & Continue</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}
