import { Text, View } from "react-native";

type SectionHeaderProps = { title: string; subtitle?: string };

export function SectionHeader({ title, subtitle }: SectionHeaderProps) {
  return (
    <View style={{ gap: 2 }}>
      <Text style={{ fontSize: 18, fontWeight: "700" }}>{title}</Text>
      {subtitle ? <Text style={{ color: "#666" }}>{subtitle}</Text> : null}
    </View>
  );
}
