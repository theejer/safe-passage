import type { ScenarioProtocol } from "@/features/emergency/types";

export function useEmergencyScenarios() {
  // Local fallback protocols for deterministic offline guidance.
  const scenarios: ScenarioProtocol[] = [
    { key: "lost", title: "Lost / Disoriented", steps: ["Stay calm", "Do not leave marked path", "Move to known safe point"] },
    { key: "breakdown", title: "Vehicle Breakdown", steps: ["Stay with vehicle", "Signal visibly", "Log incident details"] },
  ];

  return { scenarios };
}
