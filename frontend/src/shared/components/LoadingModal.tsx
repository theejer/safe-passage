import { ActivityIndicator, Modal, Text, View } from "react-native";

type LoadingModalProps = {
  visible: boolean;
  title: string;
  message?: string;
};

export function LoadingModal({ visible, title, message }: LoadingModalProps) {
  return (
    <Modal visible={visible} transparent animationType="fade" statusBarTranslucent>
      <View
        style={{
          flex: 1,
          backgroundColor: "rgba(0,0,0,0.45)",
          justifyContent: "center",
          alignItems: "center",
          padding: 24,
        }}
      >
        <View
          style={{
            width: "100%",
            maxWidth: 320,
            backgroundColor: "#ffffff",
            borderRadius: 14,
            paddingVertical: 18,
            paddingHorizontal: 16,
            alignItems: "center",
            gap: 10,
          }}
        >
          <ActivityIndicator size="large" color="#1976d2" />
          <Text style={{ fontSize: 17, fontWeight: "700", color: "#111827", textAlign: "center" }}>{title}</Text>
          {message ? <Text style={{ fontSize: 13, color: "#4b5563", textAlign: "center" }}>{message}</Text> : null}
        </View>
      </View>
    </Modal>
  );
}
