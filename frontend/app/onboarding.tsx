import { View, Text } from "react-native";
import { UserInfoForm } from "@/features/user/components/UserInfoForm";

export default function OnboardingScreen() {
  // Collect minimal profile and emergency contact, then persist via useUserProfile.
  return (
    <View style={{ flex: 1, padding: 16, gap: 12 }}>
      <Text style={{ fontSize: 20, fontWeight: "700" }}>Welcome to SafePassage</Text>
      <UserInfoForm />
    </View>
  );
}
