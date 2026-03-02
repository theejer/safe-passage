import { useEffect } from "react";
import { useRouter } from "expo-router";
import { ScrollView, Text } from "react-native";

export default function OnboardingCompleteScreen() {
  const router = useRouter();

  useEffect(() => {
    const timer = setTimeout(() => {
      router.replace("/dashboard");
    }, 1200);

    return () => {
      clearTimeout(timer);
    };
  }, [router]);

  return (
    <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: "center", alignItems: "center", padding: 16, gap: 10 }}>
      <Text style={{ fontSize: 22, fontWeight: "700", textAlign: "center" }}>Profile Saved</Text>
      <Text style={{ fontSize: 14, color: "#4b5563", textAlign: "center" }}>
        You&apos;re all set. Taking you to your dashboard...
      </Text>
    </ScrollView>
  );
}
