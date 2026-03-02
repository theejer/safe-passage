import { env } from "@/shared/config/env";

async function request(method: string, path: string, body?: unknown) {
  try {
    console.log(`[API] ${method} ${env.BACKEND_URL}${path}`, body);
    
    const response = await fetch(`${env.BACKEND_URL}${path}`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });

    console.log(`[API] Response status:`, response.status);
    
    if (!response.ok) {
      const text = await response.text();
      console.error(`[API] Error response:`, text);
      throw new Error(`API ${method} ${path} failed: ${response.status} ${text}`);
    }

    return response.status === 204 ? null : response.json();
  } catch (error) {
    console.error(`[API] Fetch error:`, error);
    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw new Error(`Cannot reach backend at ${env.BACKEND_URL} - is the server running?`);
    }
    throw error;
  }
}

export const apiClient = {
  get: (path: string) => request("GET", path),
  post: (path: string, body?: unknown) => request("POST", path, body),
  put: (path: string, body?: unknown) => request("PUT", path, body),
  patch: (path: string, body?: unknown) => request("PATCH", path, body),
};
