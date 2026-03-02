import { Text, View, Pressable } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useRouter, usePathname } from "expo-router";
import type { ProfileSession } from "@/features/user/services/profileSession";

type ProfileHeaderProps = {
  session: ProfileSession;
};

const ROUTES_WITHOUT_BACK = ["/dashboard", "/onboarding", "/emergency"];

export function ProfileHeader({ session }: ProfileHeaderProps) {
  const navigation = useNavigation();
  const router = useRouter();
  const pathname = usePathname();

  const showBack = !ROUTES_WITHOUT_BACK.includes(pathname);

  function handleBack() {
    if (navigation.canGoBack()) {
      router.back();
      return;
    }

    // Fallback routing based on current path
    if (pathname.startsWith("/trips/")) {
      router.replace("/dashboard");
    } else if (pathname.startsWith("/emergency/")) {
      router.replace("/emergency");
    } else {
      router.replace("/dashboard");
    }
  }

  return (
    <View
      style={{
        backgroundColor: "#ffffff",
        borderBottomColor: "#e5e7eb",
        borderBottomWidth: 1,
        paddingHorizontal: 12,
        paddingVertical: 10,
        flexDirection: "row",
        alignItems: "center",
        gap: 12,
      }}
    >
      {showBack ? (
        <Pressable
          onPress={handleBack}
          style={({ pressed }) => ({
            paddingHorizontal: 8,
            paddingVertical: 4,
            borderRadius: 8,
            backgroundColor: pressed ? "#f3f4f6" : "transparent",
          })}
        >
          <Text style={{ fontSize: 24, color: "#1976d2" }}>←</Text>
        </Pressable>
      ) : null}
      <View style={{ flex: 1 }}>
        <Text style={{ color: "#111111", fontSize: 16, fontWeight: "700" }}>{session.fullName}</Text>
        <Text style={{ color: "#6b7280", fontSize: 12, marginTop: 2 }}>{session.userId}</Text>
      </View>
    </View>
  );
}
