import { Stack, usePathname, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { View } from "react-native";
import { ConnectivityBanner } from "@/shared/components/ConnectivityBanner";
import { ProfileHeader } from "@/shared/components/ProfileHeader";
import { useOnlineStatus } from "@/shared/hooks/useOnlineStatus";
import { getProfileSession, type ProfileSession } from "@/features/user/services/profileSession";
import {
  registerHeartbeatTask,
  replayQueuedHeartbeats,
  startForegroundHeartbeatLoop,
  stopForegroundHeartbeatLoop,
} from "@/features/heartbeat/services/heartbeatScheduler";

export default function RootLayout() {
  const router = useRouter();
  const pathname = usePathname();
  const { isOnline } = useOnlineStatus();
  const [session, setSession] = useState<ProfileSession | null>(null);
  const [sessionLoading, setSessionLoading] = useState(true);

  useEffect(() => {
    void registerHeartbeatTask();
    startForegroundHeartbeatLoop();
    return () => {
      stopForegroundHeartbeatLoop();
    };
  }, []);

  useEffect(() => {
    if (!isOnline) return;
    void replayQueuedHeartbeats();
  }, [isOnline]);

  useEffect(() => {
    let cancelled = false;

    async function loadSession() {
      setSessionLoading(true);
      const resolvedSession = await getProfileSession();
      if (cancelled) return;
      setSession(resolvedSession);
      setSessionLoading(false);
    }

    void loadSession();

    return () => {
      cancelled = true;
    };
  }, [pathname]);

  useEffect(() => {
    if (sessionLoading) return;

    const onOnboardingRoute = pathname === "/onboarding";
    if (!session && !onOnboardingRoute) {
      router.replace("/onboarding");
      return;
    }

    if (session && (pathname === "/" || onOnboardingRoute)) {
      router.replace("/dashboard");
    }
  }, [pathname, router, session, sessionLoading]);

  return (
    <View style={{ flex: 1 }}>
      <ConnectivityBanner />
      {session ? <ProfileHeader session={session} /> : null}
      <View style={{ flex: 1 }}>
        <Stack screenOptions={{ headerShown: false }} />
      </View>
    </View>
  );
}
