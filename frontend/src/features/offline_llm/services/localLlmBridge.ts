// Bridge contract for on-device LLM runtime.
// Keep this as an abstraction so fallback template logic remains available.
export async function generateLocalGuidance(prompt: string): Promise<string | null> {
  // TODO: wire native bridge (TFLite/ONNX/CoreML). Return null when unavailable.
  void prompt;
  return null;
}
