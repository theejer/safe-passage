import { useState } from "react";
import { sendHeartbeat } from "@/features/heartbeat/services/heartbeatApi";

export function useHeartbeatDebug() {
  const [statusText, setStatusText] = useState("Idle");

  async function triggerHeartbeat() {
    setStatusText("Sending heartbeat...");
    await sendHeartbeat({ timestamp: Date.now(), source: "debug" });
    setStatusText("Heartbeat sent");
  }

  return { statusText, triggerHeartbeat };
}
