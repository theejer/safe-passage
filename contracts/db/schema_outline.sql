-- SafePassage Schema Outline (PostgreSQL / Supabase)
-- Contract version: 1.1.0
-- NOTE: This is a blueprint for integration planning, not a production migration.

-- =====================================
-- Shared / Identity
-- =====================================
create table if not exists users (
  id uuid primary key,
  full_name text not null,
  phone text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists emergency_contacts (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  name text not null,
  phone text not null,
  telegram_chat_id text,
  telegram_bot_active boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists devices (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  platform text not null,
  app_version text not null,
  push_token text,
  locale text,
  last_seen_at timestamptz
);

-- =====================================
-- PREVENTION
-- =====================================
create table if not exists trips (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  title text not null,
  start_date date not null,
  end_date date not null,
  destination_country text,
  heartbeat_enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists itineraries (
  id uuid primary key,
  trip_id uuid not null unique references trips(id) on delete cascade,
  itinerary_json jsonb not null,
  source text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists itinerary_segments (
  id uuid primary key,
  trip_id uuid not null references trips(id) on delete cascade,
  segment_order integer not null,
  segment_label text,
  start_place text,
  end_place text,
  expected_offline_minutes integer not null check (expected_offline_minutes >= 0),
  connectivity_risk text,
  day_of_week integer,
  start_time_local time,
  end_time_local time,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists risk_reports (
  id uuid primary key,
  trip_id uuid not null references trips(id) on delete cascade,
  report jsonb not null,
  summary text,
  created_at timestamptz not null default now()
);

create table if not exists connectivity_forecasts (
  id uuid primary key,
  trip_id uuid not null references trips(id) on delete cascade,
  day_date date not null,
  location_name text not null,
  expected_offline_minutes integer not null check (expected_offline_minutes >= 0),
  confidence numeric(5,2),
  created_at timestamptz not null default now()
);

create table if not exists risk_recommendations (
  id uuid primary key,
  trip_id uuid not null references trips(id) on delete cascade,
  recommendation text not null,
  priority text not null,
  created_at timestamptz not null default now()
);

-- =====================================
-- CURE
-- =====================================
create table if not exists heartbeats (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  trip_id uuid references trips(id) on delete set null,
  timestamp timestamptz not null,
  gps_lat double precision,
  gps_lng double precision,
  accuracy_meters numeric(8,2),
  battery_percent integer,
  network_status text,
  offline_minutes integer,
  source text,
  emergency_phone text,
  created_at timestamptz not null default now()
);

create table if not exists traveler_status (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  trip_id uuid not null references trips(id) on delete cascade,
  last_seen_at timestamptz,
  last_seen_lat double precision,
  last_seen_lng double precision,
  last_battery_percent integer,
  last_network_status text,
  location_risk text,
  connectivity_risk text,
  current_segment_id uuid,
  current_stage text not null default 'none',
  monitoring_state text not null default 'active',
  last_stage_change_at timestamptz,
  last_evaluated_at timestamptz,
  updated_at timestamptz not null default now(),
  unique (user_id, trip_id)
);

create table if not exists monitoring_expectations (
  id uuid primary key,
  trip_id uuid not null references trips(id) on delete cascade,
  location_name text,
  expected_offline_minutes integer not null,
  threshold_multiplier numeric(5,2) not null default 1.50,
  created_at timestamptz not null default now()
);

create table if not exists alert_events (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  trip_id uuid references trips(id) on delete set null,
  stage text not null,
  message text not null,
  channels jsonb not null,
  recipients jsonb not null,
  escalation_context jsonb,
  created_at timestamptz not null default now()
);

create table if not exists alert_deliveries (
  id uuid primary key,
  alert_id uuid not null references alert_events(id) on delete cascade,
  channel text not null,
  destination text not null,
  status text not null,
  provider_message_id text,
  delivered_at timestamptz,
  created_at timestamptz not null default now()
);

-- =====================================
-- MITIGATION
-- =====================================
create table if not exists emergency_protocol_versions (
  id uuid primary key,
  scenario_key text not null,
  version text not null,
  protocol_json jsonb not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists phrase_packs (
  id uuid primary key,
  locale text not null,
  pack_name text not null,
  phrases_json jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists incidents (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  trip_id uuid references trips(id) on delete set null,
  scenario_key text not null,
  occurred_at timestamptz not null,
  gps_lat double precision,
  gps_lng double precision,
  notes text,
  severity text,
  sync_status text not null default 'pending',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists incident_attachments (
  id uuid primary key,
  incident_id uuid not null references incidents(id) on delete cascade,
  attachment_type text not null,
  storage_uri text,
  captured_at timestamptz,
  metadata jsonb,
  created_at timestamptz not null default now()
);

create table if not exists incident_sync_jobs (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  idempotency_key text not null unique,
  payload jsonb not null,
  status text not null,
  retry_count integer not null default 0,
  next_retry_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- =====================================
-- Index Suggestions
-- =====================================
create index if not exists idx_trips_user_id on trips(user_id);
create index if not exists idx_trips_destination_country on trips(destination_country);
create index if not exists idx_itinerary_segments_trip_order on itinerary_segments(trip_id, segment_order);
create index if not exists idx_heartbeats_user_time on heartbeats(user_id, timestamp desc);
create index if not exists idx_traveler_status_trip_stage on traveler_status(trip_id, current_stage);
create index if not exists idx_risk_reports_trip_time on risk_reports(trip_id, created_at desc);
create index if not exists idx_incidents_user_sync_status on incidents(user_id, sync_status);
