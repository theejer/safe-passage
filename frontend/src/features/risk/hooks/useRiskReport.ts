import { useEffect, useState } from "react";
import { getRiskReport } from "@/features/risk/services/riskApi";
import type { RiskReport } from "@/features/risk/types";

export function useRiskReport(tripId: string) {
  const [report, setReport] = useState<RiskReport | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function load() {
      if (!tripId) return;
      setLoading(true);
      try {
        const data = await getRiskReport(tripId);
        setReport(data ?? null);
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [tripId]);

  return { report, loading };
}
