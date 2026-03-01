import { apiClient } from "@/lib/apiClient";
import type { RiskReport } from "@/features/risk/types";
import {
  cacheRiskReport,
  getLatestRiskReport,
  initializeOfflineDb,
} from "@/features/storage/services/offlineDb";

// Fetches risk analysis data for PREVENTION screens.
export async function getRiskReport(tripId: string): Promise<RiskReport | null> {
  await initializeOfflineDb();

  // Backend may expose a dedicated /trips/{id}/risk in later iterations.
  try {
    const report = (await apiClient.get(`/trips/${tripId}/risk`)) as RiskReport;
    await cacheRiskReport(tripId, report);
    return report;
  } catch {
    return getLatestRiskReport(tripId);
  }
}
