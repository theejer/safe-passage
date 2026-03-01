export type ContractVersion = "1.0.0";

export type ScenarioKey =
  | "lost"
  | "theft"
  | "harassment"
  | "medical"
  | "flood"
  | "breakdown"
  | "detained"
  | "witness";

export type RiskLevel = "low" | "guarded" | "elevated" | "high" | "severe";

export type ConnectivityZone =
  | "urban_stable"
  | "semi_urban_patchy"
  | "rural_weak"
  | "remote_no_signal"
  | "transit_intermittent";

export type AlertStage =
  | "stage_1_initial_alert"
  | "stage_2_escalation"
  | "stage_3_auto_reconnection";

export type ApiSuccess<T> = {
  contract_version: ContractVersion;
  request_id: string;
  data: T;
  meta?: Record<string, unknown>;
};

export type ApiError = {
  contract_version: ContractVersion;
  request_id: string;
  error: {
    code: string;
    message: string;
    retryable: boolean;
    details?: Array<Record<string, unknown>>;
  };
  meta?: Record<string, unknown>;
};

export type GeoPoint = {
  lat: number;
  lng: number;
  accuracy_meters?: number;
};

export type EmergencyContact = {
  name: string;
  phone: string;
  email?: string;
};

export type UserProfile = {
  id?: string;
  full_name: string;
  phone: string;
  emergency_contact?: EmergencyContact;
};

export type ItineraryLocation = {
  name: string;
  district?: string;
  block?: string;
  connectivity_zone?: ConnectivityZone;
  assumed_location_risk?: RiskLevel;
};

export type ItineraryDay = {
  date: string;
  locations: ItineraryLocation[];
  accommodation?: string;
};

export type Trip = {
  id: string;
  user_id: string;
  title: string;
  start_date: string;
  end_date: string;
  days?: ItineraryDay[];
};

export type LocationRiskAssessment = {
  name: string;
  location_risk: RiskLevel;
  connectivity_risk: RiskLevel;
  expected_offline_minutes: number;
};

export type DayRisk = {
  date: string;
  locations: LocationRiskAssessment[];
};

export type RiskReport = {
  summary: string;
  days: DayRisk[];
  recommendations?: string[];
};

export type HeartbeatEvent = {
  user_id: string;
  trip_id?: string;
  timestamp: string;
  gps?: GeoPoint;
  battery_percent?: number;
  network_status?: "online" | "offline" | "unknown";
  offline_minutes?: number;
  source?: "background_fetch" | "manual_debug" | "foreground";
  emergency_phone?: string;
};

export type AnomalyDecision = {
  expected_offline_minutes: number;
  actual_offline_minutes: number;
  threshold_rule: string;
  triggered: boolean;
  trigger_stage?: AlertStage;
};

export type AlertMessage = {
  alert_id: string;
  stage: AlertStage;
  user_id: string;
  trip_id?: string;
  channels: Array<"sms" | "push" | "email">;
  message: string;
  recipients: Array<{ type: string; name?: string; phone?: string; email?: string }>;
  escalation_context?: Record<string, unknown>;
};

export type EmergencyProtocol = {
  scenario_key: ScenarioKey;
  title: string;
  steps: string[];
  fallback_templates?: {
    calm_message?: string;
    next_action?: string;
  };
  local_numbers?: Record<string, string>;
};

export type IncidentAttachment = {
  attachment_id: string;
  incident_id: string;
  type: "photo" | "audio" | "text";
  local_uri?: string;
  captured_at?: string;
  metadata?: Record<string, unknown>;
};

export type IncidentLog = {
  incident_id: string;
  user_id: string;
  trip_id?: string;
  scenario_key: ScenarioKey;
  occurred_at: string;
  gps_lat?: number;
  gps_lng?: number;
  notes?: string;
  severity?: "low" | "moderate" | "high" | "severe";
  sync_status?: "pending" | "synced" | "failed";
};

export type SyncEnvelope = {
  idempotency_key: string;
  user_id: string;
  trip_id?: string;
  incidents: IncidentLog[];
  attachments: IncidentAttachment[];
  retry_count: number;
};

export type SyncResult = {
  accepted_ids: string[];
  rejected_ids: string[];
  conflict_ids: string[];
  next_retry_at: string | null;
  sync_status: "complete" | "partial" | "failed";
};
