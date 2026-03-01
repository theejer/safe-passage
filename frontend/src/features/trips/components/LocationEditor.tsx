import { View, TextInput } from "react-native";

export function LocationEditor() {
  // Minimal location row; extend with district/block/connectivity metadata.
  return (
    <View style={{ gap: 6 }}>
      <TextInput placeholder="Location name" style={{ borderWidth: 1, borderColor: "#ccc", padding: 8, borderRadius: 8 }} />
      <TextInput placeholder="District (Bihar)" style={{ borderWidth: 1, borderColor: "#ccc", padding: 8, borderRadius: 8 }} />
    </View>
  );
}
