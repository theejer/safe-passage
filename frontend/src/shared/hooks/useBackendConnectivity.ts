import { useCallback, useEffect, useMemo, useState } from "react";
import { getBackendUrlCandidates } from "@/shared/config/env";
import { useOnlineStatus } from "@/shared/hooks/useOnlineStatus";

const BACKEND_CHECK_INTERVAL_MS = 15000;
const BACKEND_CHECK_TIMEOUT_MS = 5000;

type BackendOfflineReason = "no-internet" | "backend-unreachable" | "backend-error";

type BackendConnectivityState = {
  isBackendReachable: boolean;
  offlineReason: BackendOfflineReason | null;
  offlineCaption: string | null;
  lastErrorMessage: string | null;
};

async function fetchWithTimeout(url: string, timeoutMs: number) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, {
      method: "GET",
      signal: controller.signal,
      headers: { "Cache-Control": "no-cache" },
    });
  } finally {
    clearTimeout(timeoutId);
  }
}

async function probeBackendHealth() {
  const urls = getBackendUrlCandidates();
  let lastError: Error | null = null;

  for (let index = 0; index < urls.length; index += 1) {
    const baseUrl = urls[index];

    try {
      const response = await fetchWithTimeout(`${baseUrl}/health`, BACKEND_CHECK_TIMEOUT_MS);
      if (response.ok) {
        return;
      }

      const body = await response.text();
      lastError = new Error(`Backend error ${response.status}: ${body || "empty response"}`);
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        lastError = new Error(`Backend health check timed out for ${baseUrl}`);
      } else {
        lastError = error instanceof Error ? error : new Error(String(error));
      }
    }
  }

  throw lastError ?? new Error("Unable to reach backend health endpoint");
}

function mapOfflineCaption(reason: BackendOfflineReason, lastErrorMessage: string | null) {
  if (reason === "no-internet") {
    return "No internet connection on this device.";
  }

  if (reason === "backend-unreachable") {
    return "Internet is available, but backend is not reachable.";
  }

  return lastErrorMessage
    ? `Backend responded with an error: ${lastErrorMessage}`
    : "Backend is returning an error response.";
}

export function useBackendConnectivity() {
  const { isOnline } = useOnlineStatus();
  const [state, setState] = useState<BackendConnectivityState>({
    isBackendReachable: false,
    offlineReason: "no-internet",
    offlineCaption: "No internet connection on this device.",
    lastErrorMessage: null,
  });

  const runHealthCheck = useCallback(async () => {
    if (!isOnline) {
      setState({
        isBackendReachable: false,
        offlineReason: "no-internet",
        offlineCaption: mapOfflineCaption("no-internet", null),
        lastErrorMessage: null,
      });
      return;
    }

    try {
      await probeBackendHealth();
      setState({
        isBackendReachable: true,
        offlineReason: null,
        offlineCaption: null,
        lastErrorMessage: null,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const inferredReason: BackendOfflineReason =
        /Network request failed|timed out|Failed to fetch/i.test(message)
          ? "backend-unreachable"
          : "backend-error";

      setState({
        isBackendReachable: false,
        offlineReason: inferredReason,
        offlineCaption: mapOfflineCaption(inferredReason, message),
        lastErrorMessage: message,
      });
    }
  }, [isOnline]);

  useEffect(() => {
    void runHealthCheck();

    if (!isOnline) {
      return;
    }

    const intervalId = setInterval(() => {
      void runHealthCheck();
    }, BACKEND_CHECK_INTERVAL_MS);

    return () => {
      clearInterval(intervalId);
    };
  }, [isOnline, runHealthCheck]);

  return useMemo(
    () => ({
      ...state,
      isOnline: state.isBackendReachable,
    }),
    [state]
  );
}
