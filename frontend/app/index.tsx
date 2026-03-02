import { Redirect } from "expo-router";
import { useEffect, useState } from "react";
import { getProfileSession } from "@/features/user/services/profileSession";

export default function IndexScreen() {
  const [targetHref, setTargetHref] = useState<"/dashboard" | "/onboarding" | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function resolveInitialRoute() {
      const session = await getProfileSession();
      if (cancelled) return;
      setTargetHref(session ? "/dashboard" : "/onboarding");
    }

    void resolveInitialRoute();

    return () => {
      cancelled = true;
    };
  }, []);

  if (!targetHref) {
    return null;
  }

  return <Redirect href={targetHref} />;
}
