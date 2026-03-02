import { apiClient } from "@/lib/apiClient";
import type { RiskReport } from "@/features/risk/types";
import type { Day } from "@/features/trips/types";
import {
  cacheRiskReport,
  getLatestRiskReport,
  initializeOfflineDb,
} from "@/features/storage/services/offlineDb";

type RiskLocationWire = {
  name?: string;
  location_risk?: string;
  connectivity_risk?: string;
  expected_offline_minutes?: number;
};

type RiskDayWire = {
  date?: string;
  locations?: RiskLocationWire[];
};

type RiskReportWire = {
  days?: RiskDayWire[];
  summary?: string;
  recommendations?: string[];
  score?: {
    value?: number;
    justification?: string;
  };
  score_breakdown?: Record<string, unknown>;
  judge?: {
    applied?: boolean;
    before?: number;
    after?: number;
    removed?: number;
    error?: string | null;
    reason?: string | null;
  };
  analyst_reports?: Record<string, unknown>;
  final_report?: Record<string, unknown>;
};

function toWireDays(days: Day[]) {
  return days.map((day) => ({
    date: day.date,
    accommodation: day.accommodation,
    locations: day.locations.map((location) => ({
      name: location.name,
      district: location.district,
      block: location.block,
      connectivity_zone: location.connectivityZone,
    })),
  }));
}

function fromWireReport(report: RiskReportWire): RiskReport {
  return {
    summary: report.summary ?? "Risk analysis completed.",
    days: (report.days ?? []).map((day) => ({
      date: day.date ?? "Unknown",
      locations: (day.locations ?? []).map((location) => ({
        name: location.name ?? "Unknown",
        locationRisk: location.location_risk ?? "MODERATE",
        connectivityRisk: location.connectivity_risk ?? "MODERATE",
        expectedOfflineMinutes: location.expected_offline_minutes ?? 0,
      })),
    })),
    recommendations: report.recommendations ?? [],
    score: report.score
      ? {
          value: Number(report.score.value ?? 0),
          justification: String(report.score.justification ?? ""),
        }
      : undefined,
    scoreBreakdown: report.score_breakdown,
    judge: report.judge
      ? {
          applied: Boolean(report.judge.applied),
          before: Number(report.judge.before ?? 0),
          after: Number(report.judge.after ?? 0),
          removed: Number(report.judge.removed ?? 0),
          error: report.judge.error,
          reason: report.judge.reason,
        }
      : undefined,
    analystReports: report.analyst_reports as RiskReport["analystReports"],
    finalReport: report.final_report,
  };
}

export async function analyzeTripRisk(tripId: string, days: Day[]): Promise<RiskReport> {
  await initializeOfflineDb();

  const response = (await apiClient.post("/itinerary/analyze", {
    contract_version: "1.0.0",
    request_id: `req_${Date.now()}`,
    trip_id: tripId,
    itinerary: {
      days: toWireDays(days),
      meta: { source: "user-reviewed-itinerary" },
    },
  })) as { report?: RiskReportWire; request_id?: string; analyzer?: string; saved?: unknown };

  console.log("[analyzeTripRisk] response meta", {
    request_id: response.request_id,
    analyzer: response.analyzer,
    saved: response.saved,
  });

  const normalized = fromWireReport(response.report ?? {});
  await cacheRiskReport(tripId, normalized);
  return normalized;
}

// Fetches risk analysis data for PREVENTION screens.
export async function getRiskReport(tripId: string): Promise<RiskReport | null> {
  await initializeOfflineDb();

  try {
    const response = (await apiClient.get(`/api/reports?trip_id=${encodeURIComponent(tripId)}`)) as {
      items?: Array<{ report?: RiskReportWire }>;
    };
    const latest = response.items?.[0]?.report;
    if (!latest) {
      return getLatestRiskReport(tripId);
    }

    const normalized = fromWireReport(latest);
    await cacheRiskReport(tripId, normalized);
    return normalized;
  } catch {
    return getLatestRiskReport(tripId);
  }
}
