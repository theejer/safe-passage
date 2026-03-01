import { View, TextInput, Button, Text } from "react-native";
import { useUserProfile } from "@/features/user/hooks/useUserProfile";

export function UserInfoForm() {
  // Minimal onboarding form for name + emergency contact phone.
  const { profile, setProfile, saveProfile, isSaving } = useUserProfile();

  return (
    <View style={{ gap: 8 }}>
      <TextInput
        placeholder="Full name"
        value={profile.fullName}
        onChangeText={(value) => setProfile({ ...profile, fullName: value })}
        style={{ borderWidth: 1, borderColor: "#ccc", padding: 10, borderRadius: 8 }}
      />
      <TextInput
        placeholder="Your phone"
        value={profile.phone}
        onChangeText={(value) => setProfile({ ...profile, phone: value })}
        style={{ borderWidth: 1, borderColor: "#ccc", padding: 10, borderRadius: 8 }}
      />
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
      <TextInput
        placeholder="Emergency contact phone"
        value={profile.emergencyContact?.phone ?? ""}
        onChangeText={(value) =>
          setProfile({
            ...profile,
            emergencyContact: { ...(profile.emergencyContact ?? { name: "" }), phone: value },
          })
        }
        style={{ borderWidth: 1, borderColor: "#ccc", padding: 10, borderRadius: 8 }}
      />
      <Button title={isSaving ? "Saving..." : "Save"} onPress={() => void saveProfile()} />
      <Text style={{ color: "#666" }}>Profile is used for alerts and trip ownership.</Text>
    </View>
  );
}
