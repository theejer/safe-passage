import { Redirect, useLocalSearchParams } from "expo-router";

export default function EditTripScreen() {
  const { tripId } = useLocalSearchParams<{ tripId: string }>();
  return <Redirect href={`/trips/${String(tripId ?? "")}`} />;
}
