import { Redirect } from "expo-router";

export default function IndexScreen() {
  // Entry point decision placeholder:
  // - if onboarding incomplete -> /onboarding
  // - else -> /trips
  return <Redirect href="/onboarding" />;
}
