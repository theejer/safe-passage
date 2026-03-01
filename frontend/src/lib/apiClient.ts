import { env } from "@/shared/config/env";

async function request(method: string, path: string, body?: unknown) {
  const response = await fetch(`${env.BACKEND_URL}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API ${method} ${path} failed: ${response.status} ${text}`);
  }

  return response.status === 204 ? null : response.json();
}

export const apiClient = {
  get: (path: string) => request("GET", path),
  post: (path: string, body?: unknown) => request("POST", path, body),
  put: (path: string, body?: unknown) => request("PUT", path, body),
  patch: (path: string, body?: unknown) => request("PATCH", path, body),
};
