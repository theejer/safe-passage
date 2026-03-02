export type DayRisk = {
  date: string;
  locations: Array<{
    name: string;
    locationRisk: string;
    connectivityRisk: string;
    expectedOfflineMinutes: number;
  }>;
};

export type RiskScore = {
  value: number;
  justification: string;
};

export type RiskJudge = {
  applied: boolean;
  before: number;
  after: number;
  removed: number;
  error?: string | null;
  reason?: string | null;
};

export type DomainAnalystReport = {
  domain: string;
  error?: string;
  items: Array<{
    date: string;
    location: string;
    risk: string;
    severity: string;
    connectivity_risk: string;
    expected_offline_minutes: number;
    recommendation: string;
    details: string;
    domain: string;
  }>;
};

export type RiskReport = {
  days: DayRisk[];
  summary: string;
  recommendations?: string[];
  score?: RiskScore;
  scoreBreakdown?: Record<string, unknown>;
  judge?: RiskJudge;
  analystReports?: Record<string, DomainAnalystReport>;
  finalReport?: Record<string, unknown>;
};
