import { buildEmergencyPrompt } from "@/features/offline_llm/services/promptBuilders";
import { generateLocalGuidance } from "@/features/offline_llm/services/localLlmBridge";

export async function useEmergencyLlm(scenarioTitle: string) {
  // Hook-like async utility to prefer local model then fallback templates.
  const prompt = buildEmergencyPrompt({ scenarioTitle });
  const generated = await generateLocalGuidance(prompt);
  if (generated) return generated;

  return "Follow offline protocol steps and move toward the nearest safe location.";
}
