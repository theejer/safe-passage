import { Stack } from "expo-router";
import { useEffect } from "react";
import { useOnlineStatus } from "@/shared/hooks/useOnlineStatus";
import {
  registerHeartbeatTask,
  replayQueuedHeartbeats,
  startForegroundHeartbeatLoop,
  stopForegroundHeartbeatLoop,
} from "@/features/heartbeat/services/heartbeatScheduler";

export default function RootLayout() {
  // Keeps route-level wiring thin; feature logic lives in src/features.
  const { isOnline } = useOnlineStatus();

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

  return <Stack screenOptions={{ headerTitleAlign: "center" }} />;
}
