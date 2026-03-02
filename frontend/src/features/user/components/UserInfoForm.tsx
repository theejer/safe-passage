import { View, TextInput, Button, Text } from "react-native";
import { useRouter } from "expo-router";
import { useUserProfile } from "@/features/user/hooks/useUserProfile";

export function UserInfoForm() {
  // Minimal onboarding form for name + emergency contact phone.
  const router = useRouter();
  const { profile, setProfile, saveProfile, saveError, isSaving } = useUserProfile();

  async function onSavePress() {
    try {
      await saveProfile({ requireRemote: true });
      router.replace("/trips");
    } catch {
      return;
    }
  }

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
      <Button title={isSaving ? "Saving..." : "Save"} onPress={() => void onSavePress()} />
      {saveError ? <Text style={{ color: "#b00020" }}>{saveError}</Text> : null}
      <Text style={{ color: "#666" }}>Profile is used for alerts and trip ownership.</Text>
    </View>
  );
}
