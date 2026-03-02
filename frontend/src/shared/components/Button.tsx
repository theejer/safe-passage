import type { PropsWithChildren } from "react";
import { Pressable, StyleSheet, Text, View, Animated, ActivityIndicator, type TextStyle, type ViewStyle } from "react-native";
import { useRef } from "react";

type ButtonVariant = "primary" | "secondary" | "outline" | "danger";
type ButtonSize = "md" | "sm";

type ButtonProps = PropsWithChildren<{
  onPress?: () => void;
  disabled?: boolean;
  variant?: ButtonVariant;
  size?: ButtonSize;
  block?: boolean;
  loading?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
  accessibilityLabel?: string;
}>;

const VARIANT_STYLES: Record<ButtonVariant, { container: ViewStyle; text: TextStyle; pressedBg: string }> = {
  primary: {
    container: {
      backgroundColor: "#1976d2",
      borderColor: "#1565c0",
    },
    text: {
      color: "#ffffff",
    },
    pressedBg: "#1565c0",
  },
  secondary: {
    container: {
      backgroundColor: "#e3f2fd",
      borderColor: "#1565c0",
    },
    text: {
      color: "#1565c0",
    },
    pressedBg: "#bbdefb",
  },
  outline: {
    container: {
      backgroundColor: "#ffffff",
      borderColor: "#1565c0",
    },
    text: {
      color: "#1565c0",
    },
    pressedBg: "#e3f2fd",
  },
  danger: {
    container: {
      backgroundColor: "#ffebee",
      borderColor: "#c62828",
    },
    text: {
      color: "#b71c1c",
    },
    pressedBg: "#ffcdd2",
  },
};

const SIZE_STYLES: Record<ButtonSize, { container: ViewStyle; text: TextStyle }> = {
  md: {
    container: {
      paddingVertical: 14,
      paddingHorizontal: 16,
      minHeight: 48,
    },
    text: {
      fontSize: 16,
    },
  },
  sm: {
    container: {
      paddingVertical: 10,
      paddingHorizontal: 14,
      minHeight: 40,
    },
    text: {
      fontSize: 14,
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
  loading = false,
  style,
  textStyle,
  accessibilityLabel,
}: ButtonProps) {
  const variantStyle = VARIANT_STYLES[variant];
  const sizeStyle = SIZE_STYLES[size];
  const scaleAnim = useRef(new Animated.Value(1)).current;

  function handlePressIn() {
    if (disabled) return;
    Animated.spring(scaleAnim, {
      toValue: 0.96,
      useNativeDriver: true,
      speed: 50,
      bounciness: 4,
    }).start();
  }

  function handlePressOut() {
    if (disabled) return;
    Animated.spring(scaleAnim, {
      toValue: 1,
      useNativeDriver: true,
      speed: 50,
      bounciness: 4,
    }).start();
  }

  const isDisabled = disabled || loading;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      disabled={isDisabled}
      onPress={onPress}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
    >
      {({ pressed }) => (
        <Animated.View
          style={[
            styles.base,
            variantStyle.container,
            sizeStyle.container,
            block ? styles.block : styles.inline,
            pressed && !isDisabled ? { backgroundColor: variantStyle.pressedBg } : null,
            isDisabled ? styles.disabled : null,
            style,
            { transform: [{ scale: scaleAnim }] },
          ]}
        >
          {loading ? (
            <View style={styles.loadingRow}>
              <ActivityIndicator size="small" color={variantStyle.text.color ?? "#ffffff"} />
              <Text style={[styles.textBase, variantStyle.text, sizeStyle.text, styles.disabledText, textStyle]}>{children}</Text>
            </View>
          ) : (
            <Text style={[styles.textBase, variantStyle.text, sizeStyle.text, isDisabled ? styles.disabledText : null, textStyle]}>
              {children}
            </Text>
          )}
        </Animated.View>
      )}
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
  loadingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  disabled: {
    opacity: 0.5,
  },
  disabledText: {
    opacity: 0.95,
  },
});
