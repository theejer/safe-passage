import Constants from "expo-constants";

const DEFAULT_BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL ?? "http://localhost:5000";

function parseDevHostUrl() {
  const hostUri = Constants.expoConfig?.hostUri ?? null;
  if (!hostUri) return null;

  const host = hostUri.split(":")[0];
  if (!host) return null;
  return `http://${host}:5000`;
}

export function isLocalhostUrl(url: string) {
  return (
    url.includes("localhost") ||
    url.includes("127.0.0.1") ||
    url.includes("0.0.0.0")
  );
}

export function getBackendUrlCandidates() {
  const candidates = [DEFAULT_BACKEND_URL];

  if (isLocalhostUrl(DEFAULT_BACKEND_URL)) {
    candidates.push(DEFAULT_BACKEND_URL.replace("localhost", "10.0.2.2"));
    candidates.push(DEFAULT_BACKEND_URL.replace("127.0.0.1", "10.0.2.2"));

    const devHostUrl = parseDevHostUrl();
    if (devHostUrl) {
      candidates.push(devHostUrl);
    }
  }

  return Array.from(new Set(candidates));
}

// Centralized environment access for runtime configuration.
export const env = {
  BACKEND_URL: DEFAULT_BACKEND_URL,
  FEATURE_OFFLINE_LLM: (process.env.EXPO_PUBLIC_FEATURE_OFFLINE_LLM ?? "false") === "true",
};
