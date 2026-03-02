import type { PropsWithChildren } from "react";
import { Pressable, StyleSheet, Text, type TextStyle, type ViewStyle } from "react-native";

type ButtonVariant = "primary" | "secondary" | "outline" | "danger";
type ButtonSize = "md" | "sm";

type ButtonProps = PropsWithChildren<{
  onPress?: () => void;
  disabled?: boolean;
  variant?: ButtonVariant;
  size?: ButtonSize;
  block?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
  accessibilityLabel?: string;
}>;

const VARIANT_STYLES: Record<ButtonVariant, { container: ViewStyle; text: TextStyle }> = {
  primary: {
    container: {
      backgroundColor: "#1976d2",
      borderColor: "#1565c0",
    },
    text: {
      color: "#ffffff",
    },
  },
  secondary: {
    container: {
      backgroundColor: "#e3f2fd",
      borderColor: "#1565c0",
    },
    text: {
      color: "#1565c0",
    },
  },
  outline: {
    container: {
      backgroundColor: "#ffffff",
      borderColor: "#1565c0",
    },
    text: {
      color: "#1565c0",
    },
  },
  danger: {
    container: {
      backgroundColor: "#ffebee",
      borderColor: "#c62828",
    },
    text: {
      color: "#b71c1c",
    },
  },
};

const SIZE_STYLES: Record<ButtonSize, { container: ViewStyle; text: TextStyle }> = {
  md: {
    container: {
      paddingVertical: 12,
      paddingHorizontal: 14,
    },
    text: {
      fontSize: 16,
    },
  },
  sm: {
    container: {
      paddingVertical: 8,
      paddingHorizontal: 12,
    },
    text: {
      fontSize: 13,
    },
  },
};

export function Button({
  onPress,
  children,
  disabled = false,
  variant = "primary",
  size = "md",
  block = true,
  style,
  textStyle,
  accessibilityLabel,
}: ButtonProps) {
  const variantStyle = VARIANT_STYLES[variant];
  const sizeStyle = SIZE_STYLES[size];

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.base,
        variantStyle.container,
        sizeStyle.container,
        block ? styles.block : styles.inline,
        pressed && !disabled ? styles.pressed : null,
        disabled ? styles.disabled : null,
        style,
      ]}
    >
      <Text style={[styles.textBase, variantStyle.text, sizeStyle.text, disabled ? styles.disabledText : null, textStyle]}>
        {children}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    borderWidth: 2,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  textBase: {
    fontWeight: "800",
    textAlign: "center",
  },
  block: {
    width: "100%",
  },
  inline: {
    alignSelf: "flex-start",
  },
  pressed: {
    opacity: 0.9,
  },
  disabled: {
    opacity: 0.55,
  },
  disabledText: {
    opacity: 0.95,
  },
});
