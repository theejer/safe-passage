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
  };
}

export async function analyzeTripRisk(tripId: string, days: Day[]): Promise<RiskReport> {
  await initializeOfflineDb();

  const response = (await apiClient.post("/itinerary/analyze", {
    trip_id: tripId,
    itinerary: {
      days: toWireDays(days),
      meta: { source: "user-reviewed-itinerary" },
    },
  })) as { report?: RiskReportWire };

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
