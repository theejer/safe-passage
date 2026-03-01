import { useState } from "react";
import { sendScheduledHeartbeat } from "@/features/heartbeat/services/heartbeatScheduler";

export function useHeartbeatDebug() {
  const [statusText, setStatusText] = useState("Idle");

  async function triggerHeartbeat() {
    setStatusText("Sending heartbeat...");
    try {
      const result = await sendScheduledHeartbeat("manual_debug");
      if (result.status === "sent") {
        setStatusText("Heartbeat sent");
      } else if (result.status === "queued") {
        setStatusText(`Heartbeat queued (${result.reason})`);
      } else {
        setStatusText(`Heartbeat skipped (${result.reason})`);
      }
    } catch (error) {
      setStatusText(`Heartbeat failed: ${error instanceof Error ? error.message : "unknown-error"}`);
    }
  }

  return { statusText, triggerHeartbeat };
}
