// Centralized environment access for runtime configuration.
export const env = {
  BACKEND_URL: process.env.EXPO_PUBLIC_BACKEND_URL ?? "http://localhost:5000",
  FEATURE_OFFLINE_LLM: (process.env.EXPO_PUBLIC_FEATURE_OFFLINE_LLM ?? "false") === "true",
};
