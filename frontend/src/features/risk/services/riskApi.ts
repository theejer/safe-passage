import { apiClient } from "@/lib/apiClient";
import type { RiskReport } from "@/features/risk/types";
import type { Day } from "@/features/trips/types";
import {
  cacheRiskReport,
  getTripById,
  getLatestRiskReport,
  initializeOfflineDb,
} from "@/features/storage/services/offlineDb";
import { canSyncItineraryOnline } from "@/shared/utils/syncGuards";

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
  status?: string;
  stage?: string;
  details?: Record<string, unknown>;
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
  saved?: Record<string, unknown>;
};

type FinalRiskWire = {
  severity?: string;
};

type FinalActivityWire = {
  location?: string;
  RISK?: FinalRiskWire[];
};

type FinalDayWire = {
  day_label?: string;
  day_id?: string;
  ACTIVITY?: FinalActivityWire[];
};

function pipelineFinalReportToRiskDays(finalReport: Record<string, unknown> | undefined): RiskDayWire[] {
  const finalDays = (finalReport?.DAY ?? finalReport?.["DAY"]) as FinalDayWire[] | undefined;
  if (!Array.isArray(finalDays)) return [];

  return finalDays.map((day) => {
    const activities = Array.isArray(day.ACTIVITY) ? day.ACTIVITY : [];
    const locationAgg = new Map<string, { high: number; medium: number; low: number }>();

    for (const activity of activities) {
      if (!activity || typeof activity !== "object") continue;
      const locationName = String(activity.location || "General");
      const stats = locationAgg.get(locationName) ?? { high: 0, medium: 0, low: 0 };
      const risks = Array.isArray(activity.RISK) ? activity.RISK : [];

      for (const risk of risks) {
        const severity = String(risk?.severity || "low").toLowerCase();
        if (severity === "high" || severity === "severe") stats.high += 1;
        else if (severity === "medium" || severity === "moderate") stats.medium += 1;
        else stats.low += 1;
      }

      locationAgg.set(locationName, stats);
    }

    const locations: RiskLocationWire[] = [...locationAgg.entries()].map(([name, stats]) => {
      const location_risk =
        stats.high > 0 ? "HIGH" : stats.medium > 0 ? "MODERATE" : stats.low > 0 ? "LOW" : "LOW";
      return {
        name,
        location_risk,
        connectivity_risk: "MODERATE",
        expected_offline_minutes: 0,
      };
    });

    return {
      date: String(day.day_label || day.day_id || "Unknown"),
      locations,
    };
  });
}

function resolvePipelineSummary(report: RiskReportWire): string {
  if (report.summary) return report.summary;
  const score = (report.final_report as { SCORE?: { value?: number } } | undefined)?.SCORE?.value;
  if (typeof score === "number") {
    return `Pipeline risk analysis completed. Score: ${score}/100.`;
  }
  return "Pipeline risk analysis completed.";
}

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
  const finalReport = report.final_report as Record<string, unknown> | undefined;
  const finalScore = (finalReport as { SCORE?: { value?: number; justification?: string } } | undefined)?.SCORE;
  const wireDays = (report.days ?? []).length ? (report.days ?? []) : pipelineFinalReportToRiskDays(finalReport);

  return {
    summary: resolvePipelineSummary(report),
    days: wireDays.map((day) => ({
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
      : finalScore
      ? {
          value: Number(finalScore.value ?? 0),
          justification: String(finalScore.justification ?? ""),
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
    finalReport: finalReport,
  };
}

export async function analyzeTripRisk(tripId: string, days: Day[]): Promise<RiskReport> {
  await initializeOfflineDb();

  const onlineTrip = canSyncItineraryOnline(tripId);

  const trip = await getTripById(tripId);

  const response = (await apiClient.post("/itinerary/analyze-pipeline", {
    trip_id: onlineTrip ? tripId : undefined,
    trip_name: trip?.title,
    start_date: trip?.startDate,
    end_date: trip?.endDate,
    itinerary: JSON.stringify({
      days: toWireDays(days),
      meta: { source: "user-reviewed-itinerary" },
    }),
    metadata: {
      source: "user-reviewed-itinerary",
      trip_name: trip?.title,
      start_date: trip?.startDate,
      end_date: trip?.endDate,
    },
  })) as RiskReportWire;

  console.log("[analyzeTripRisk] pipeline response meta", {
    status: response.status,
    stage: response.stage,
    saved: response.saved,
  });

  if (response.status === "failed") {
    const details = response.details ? JSON.stringify(response.details) : "Unknown pipeline error";
    throw new Error(`Pipeline analysis failed (${response.stage || "unknown"}): ${details}`);
  }

  const normalized = fromWireReport(response);
  await cacheRiskReport(tripId, normalized);
  return normalized;
}

// Fetches risk analysis data for PREVENTION screens.
export async function getRiskReport(tripId: string): Promise<RiskReport | null> {
  await initializeOfflineDb();

  if (!canSyncItineraryOnline(tripId)) {
    return getLatestRiskReport(tripId);
  }

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
