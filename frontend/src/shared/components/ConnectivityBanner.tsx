import { Text, View } from "react-native";
import { theme } from "@/lib/theme";
import { useBackendConnectivity } from "@/shared/hooks/useBackendConnectivity";

export function ConnectivityBanner() {
  const { isOnline, offlineCaption } = useBackendConnectivity();

  return (
    <View
      style={{
        backgroundColor: isOnline ? theme.colors.success : theme.colors.muted,
        paddingHorizontal: 12,
        paddingVertical: 8,
      }}
    >
      <Text style={{ color: "#ffffff", fontWeight: "600", textAlign: "center" }}>
        {isOnline ? "Online" : "Offline"}
      </Text>
      {!isOnline && offlineCaption ? (
        <Text style={{ color: "#ffffff", fontSize: 12, textAlign: "center", marginTop: 2 }}>
          {offlineCaption}
        </Text>
      ) : null}
    </View>
  );
}
