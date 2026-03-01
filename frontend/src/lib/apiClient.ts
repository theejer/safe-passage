import { env, getBackendUrlCandidates } from "@/shared/config/env";

async function request(method: string, path: string, body?: unknown) {
  const urls = getBackendUrlCandidates();
  let lastError: unknown = null;

  for (let index = 0; index < urls.length; index += 1) {
    const baseUrl = urls[index];
    try {
      const response = await fetch(`${baseUrl}${path}`, {
        method,
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(`API ${method} ${path} failed: ${response.status} ${text}`);
      }

      return response.status === 204 ? null : response.json();
    } catch (error) {
      lastError = error;
      const isLastCandidate = index === urls.length - 1;
      if (!isLastCandidate) {
        continue;
      }
    }
  }

  if (lastError instanceof Error) {
    if (lastError.message.includes("Network request failed")) {
      throw new Error(
        `Network request failed. Checked backend URLs: ${urls.join(", ")}. Ensure backend is running and reachable from your device.`
      );
    }
    throw lastError;
  }

  throw new Error(`API ${method} ${path} failed at ${env.BACKEND_URL}`);
}

export const apiClient = {
  get: (path: string) => request("GET", path),
  post: (path: string, body?: unknown) => request("POST", path, body),
  put: (path: string, body?: unknown) => request("PUT", path, body),
  patch: (path: string, body?: unknown) => request("PATCH", path, body),
};
