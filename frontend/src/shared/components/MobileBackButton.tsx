import { useNavigation } from "@react-navigation/native";
import { type Href, useRouter } from "expo-router";
import { Button } from "@/shared/components/Button";

type MobileBackButtonProps = {
  fallbackHref: Href;
  label?: string;
};

export function MobileBackButton({ fallbackHref, label = "Back" }: MobileBackButtonProps) {
  const navigation = useNavigation();
  const router = useRouter();

  function handleBack() {
    if (navigation.canGoBack()) {
      router.back();
      return;
    }

    router.replace(fallbackHref);
  }

  return (
    <Button variant="outline" size="sm" block={false} onPress={handleBack}>
      {label}
    </Button>
  );
}
