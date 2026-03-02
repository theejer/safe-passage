import { View, TextInput, Button, Text, Modal, ScrollView, TouchableOpacity } from "react-native";
import { useRouter } from "expo-router";
import { useUserProfile } from "@/features/user/hooks/useUserProfile";
import { useState } from "react";
import { isLikelyPhone } from "@/shared/utils/validators";

interface CountryCodeOption {
  code: string;
  label: string;
}

type UserInfoFormProps = {
  onSaved?: () => void;
  onSkip?: () => void;
};

export function UserInfoForm({ onSaved, onSkip }: UserInfoFormProps) {
  // Minimal onboarding form for name + emergency contact phone.
  const router = useRouter();
  const { profile, setProfile, saveProfile, isSaving, error: saveError } = useUserProfile();
  const [userCountryCode, setUserCountryCode] = useState("+91");
  const [emergencyCountryCode, setEmergencyCountryCode] = useState("+91");
  const [error, setError] = useState("");
  const [showUserCountryModal, setShowUserCountryModal] = useState(false);
  const [showEmergencyCountryModal, setShowEmergencyCountryModal] = useState(false);

  // Minimal country code list for offline fallback
  const countryCodes: CountryCodeOption[] = [
    { code: "+91", label: "India (+91)" },
    { code: "+977", label: "Nepal (+977)" },
    { code: "+880", label: "Bangladesh (+880)" },
    { code: "+1", label: "USA (+1)" },
    { code: "+44", label: "UK (+44)" },
    { code: "+86", label: "China (+86)" },
  ];

  const handleSave = async () => {
    setError("");
    const userFullPhone = userCountryCode + (profile.phone || "").trim();
    const emergencyFullPhone = emergencyCountryCode + (profile.emergencyContact?.phone || "").trim();

    // Prevent saving if both phones are the same
    if (
      userFullPhone === emergencyFullPhone &&
      profile.phone?.trim() &&
      profile.emergencyContact?.phone?.trim() &&
      isLikelyPhone(profile.phone) &&
      isLikelyPhone(profile.emergencyContact.phone)
    ) {
      setError("Your phone and emergency contact phone must not be the same.");
      return;
    }

    try {
      console.log("[UserInfoForm] Starting profile save...");
      const result = await saveProfile();
      console.log("[UserInfoForm] Profile saved successfully:", result);
      if (onSaved) {
        onSaved();
      } else {
        router.replace("/complete");
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to save profile";
      console.error("[UserInfoForm] Error saving profile:", errorMessage);
      setError(errorMessage);
    }
  };

  const CountryCodePicker = ({
    visible,
    onClose,
    value,
    onChange,
  }: {
    visible: boolean;
    onClose: () => void;
    value: string;
    onChange: (code: string) => void;
  }) => (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <View style={{ flex: 1, backgroundColor: "rgba(0, 0, 0, 0.5)", justifyContent: "flex-end" }}>
        <View style={{ backgroundColor: "white", paddingTop: 16, paddingBottom: 32 }}>
          <ScrollView style={{ maxHeight: 300 }}>
            {countryCodes.map((country) => (
              <TouchableOpacity
                key={country.code}
                style={{
                  paddingVertical: 12,
                  paddingHorizontal: 16,
                  backgroundColor: value === country.code ? "#e3f2fd" : "white",
                  borderBottomWidth: 1,
                  borderBottomColor: "#f0f0f0",
                }}
                onPress={() => {
                  onChange(country.code);
                  onClose();
                }}
              >
                <Text style={{ fontSize: 16, color: value === country.code ? "#1976d2" : "#000" }}>
                  {country.label}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
          <TouchableOpacity
            style={{ paddingVertical: 12, paddingHorizontal: 16, alignItems: "center" }}
            onPress={onClose}
          >
            <Text style={{ fontSize: 16, color: "#666" }}>Close</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );

  return (
    <View style={{ gap: 8 }}>
      <TextInput
        placeholder="Full name"
        value={profile.fullName}
        onChangeText={(value) => setProfile({ ...profile, fullName: value })}
        style={{ borderWidth: 1, borderColor: "#ccc", padding: 10, borderRadius: 8 }}
      />
      <View style={{ gap: 8 }}>
        <View style={{ flexDirection: "row", gap: 8 }}>
          <TouchableOpacity
            style={{
              borderWidth: 1,
              borderColor: "#ccc",
              padding: 10,
              borderRadius: 8,
              justifyContent: "center",
              paddingHorizontal: 12,
            }}
            onPress={() => setShowUserCountryModal(true)}
          >
            <Text style={{ fontSize: 14, fontWeight: "500" }}>{userCountryCode}</Text>
          </TouchableOpacity>
          <TextInput
            placeholder="Your phone"
            value={profile.phone}
            onChangeText={(value) => setProfile({ ...profile, phone: value })}
            style={{ flex: 1, borderWidth: 1, borderColor: "#ccc", padding: 10, borderRadius: 8 }}
            keyboardType="phone-pad"
          />
        </View>
        <CountryCodePicker
          visible={showUserCountryModal}
          onClose={() => setShowUserCountryModal(false)}
          value={userCountryCode}
          onChange={setUserCountryCode}
        />
      </View>

      <TextInput
        placeholder="Emergency contact name"
        value={profile.emergencyContact?.name ?? ""}
        onChangeText={(value) =>
          setProfile({
            ...profile,
            emergencyContact: { ...(profile.emergencyContact ?? { phone: "" }), name: value },
          })
        }
        style={{ borderWidth: 1, borderColor: "#ccc", padding: 10, borderRadius: 8 }}
      />

      <View style={{ gap: 8 }}>
        <View style={{ flexDirection: "row", gap: 8 }}>
          <TouchableOpacity
            style={{
              borderWidth: 1,
              borderColor: "#ccc",
              padding: 10,
              borderRadius: 8,
              justifyContent: "center",
              paddingHorizontal: 12,
            }}
            onPress={() => setShowEmergencyCountryModal(true)}
          >
            <Text style={{ fontSize: 14, fontWeight: "500" }}>{emergencyCountryCode}</Text>
          </TouchableOpacity>
          <TextInput
            placeholder="Emergency contact phone"
            value={profile.emergencyContact?.phone ?? ""}
            onChangeText={(value) =>
              setProfile({
                ...profile,
                emergencyContact: { ...(profile.emergencyContact ?? { name: "" }), phone: value },
              })
            }
            style={{ flex: 1, borderWidth: 1, borderColor: "#ccc", padding: 10, borderRadius: 8 }}
            keyboardType="phone-pad"
          />
        </View>
        <CountryCodePicker
          visible={showEmergencyCountryModal}
          onClose={() => setShowEmergencyCountryModal(false)}
          value={emergencyCountryCode}
          onChange={setEmergencyCountryCode}
        />
      </View>

      {error || saveError ? (
        <View style={{ backgroundColor: "#ffebee", borderRadius: 8, padding: 12, borderLeftWidth: 4, borderLeftColor: "#f44336" }}>
          <Text style={{ color: "#c62828", fontSize: 14, fontWeight: "500" }}>
            ⚠️ Error
          </Text>
          <Text style={{ color: "#d32f2f", fontSize: 12, marginTop: 4 }}>
            {error || saveError}
          </Text>
        </View>
      ) : null}

      {isSaving && (
        <Text style={{ color: "#1976d2", fontSize: 12 }}>
          ⏳ Saving profile...
        </Text>
      )}

      <View style={{ gap: 8 }}>
        <Button 
          title={isSaving ? "Saving..." : "Save Profile"} 
          onPress={handleSave}
          disabled={isSaving || !profile.fullName || !profile.phone}
        />
        <TouchableOpacity 
          style={{ 
            paddingVertical: 12, 
            paddingHorizontal: 16, 
            borderWidth: 1, 
            borderColor: "#999",
            borderRadius: 8,
            alignItems: "center"
          }}
          onPress={() => {
            if (onSkip) {
              onSkip();
              return;
            }
            router.replace("/dashboard");
          }}
        >
          <Text style={{ color: "#666", fontSize: 16, fontWeight: "500" }}>Skip for now</Text>
        </TouchableOpacity>
      </View>
      <Text style={{ color: "#666", fontSize: 12 }}>Profile is used for alerts and trip ownership.</Text>
    </View>
  );
}
