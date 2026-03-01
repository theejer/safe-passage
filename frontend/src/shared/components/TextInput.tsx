import { TextInput as RNTextInput, type TextInputProps } from "react-native";

export function TextInput(props: TextInputProps) {
  return <RNTextInput {...props} style={[{ borderWidth: 1, borderColor: "#ccc", padding: 10, borderRadius: 8 }, props.style]} />;
}
