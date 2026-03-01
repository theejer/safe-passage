export type DayRisk = {
  date: string;
  locations: Array<{
    name: string;
    locationRisk: string;
    connectivityRisk: string;
    expectedOfflineMinutes: number;
  }>;
};

export type RiskReport = {
  days: DayRisk[];
  summary: string;
};
