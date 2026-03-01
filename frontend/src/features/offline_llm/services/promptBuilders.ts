export function buildEmergencyPrompt(input: {
  scenarioTitle: string;
  nearestSafePoint?: string;
  userName?: string;
}) {
  // Template prompt used for local/offline personalization.
  return `User: ${input.userName ?? "Traveler"}. Scenario: ${input.scenarioTitle}. Safe point: ${input.nearestSafePoint ?? "unknown"}. Provide concise safety steps.`;
}
