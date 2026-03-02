-- SafePassage Schema Outline (PostgreSQL / Supabase)
-- Contract version: 2.0.0
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

-- =====================================
-- PREVENTION
-- =====================================
create table if not exists trips (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  title text not null,
  trip_planned boolean not null default true,
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

create table if not exists itinerary_days (
  id uuid primary key,
  trip_id uuid not null references trips(id) on delete cascade,
  day_id text,
  day_order integer not null,
  day_date date,
  label text,
  day_notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists itinerary_locations (
  id uuid primary key,
  day_id uuid not null references itinerary_days(id) on delete cascade,
  location_id text,
  location_order integer not null,
  location_type text not null,
  name text,
  raw_text text,
  address_city text,
  address_state text,
  address_country text,
  geo_lat double precision,
  geo_lng double precision,
  geo_source text,
  start_local timestamptz,
  end_local timestamptz,
  timezone text,
  transport_mode text,
  transport_from_name text,
  transport_to_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists itinerary_accommodations (
  id uuid primary key,
  day_id uuid not null unique references itinerary_days(id) on delete cascade,
  accom_id text,
  name text,
  raw_text text,
  address_line1 text,
  address_line2 text,
  address_city text,
  address_state text,
  address_country text,
  address_postal_code text,
  geo_lat double precision,
  geo_lng double precision,
  geo_source text,
  checkin_local timestamptz,
  checkout_local timestamptz,
  timezone text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists itinerary_risk_queries (
  id uuid primary key,
  trip_id uuid not null references trips(id) on delete cascade,
  day_id uuid references itinerary_days(id) on delete cascade,
  location_ref_id uuid references itinerary_locations(id) on delete cascade,
  accommodation_ref_id uuid references itinerary_accommodations(id) on delete cascade,
  place_keywords jsonb not null default '[]'::jsonb,
  country_code text,
  state text,
  district text,
  nearest_city text,
  lat double precision,
  lng double precision,
  is_overnight boolean not null default false,
  created_at timestamptz not null default now(),
  check (
    (location_ref_id is not null and accommodation_ref_id is null)
    or (location_ref_id is null and accommodation_ref_id is not null)
  )
);

create table if not exists itinerary_risks (
  id uuid primary key,
  trip_id uuid not null references trips(id) on delete cascade,
  day_id uuid references itinerary_days(id) on delete cascade,
  location_ref_id uuid references itinerary_locations(id) on delete cascade,
  accommodation_ref_id uuid references itinerary_accommodations(id) on delete cascade,
  category text not null,
  risk_level text,
  recommendation text not null,
  source text,
  confidence numeric(5,2),
  connectivity_risk text,
  expected_offline_minutes integer check (expected_offline_minutes >= 0),
  connectivity_confidence numeric(5,2),
  connectivity_notes text,
  created_at timestamptz not null default now(),
  check (
    (location_ref_id is not null and accommodation_ref_id is null)
    or (location_ref_id is null and accommodation_ref_id is not null)
    or (location_ref_id is null and accommodation_ref_id is null)
  )
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
  current_location_ref_id uuid references itinerary_locations(id) on delete set null,
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
create index if not exists idx_trips_planned on trips(trip_planned);
create index if not exists idx_trips_destination_country on trips(destination_country);
create index if not exists idx_itinerary_days_trip_order on itinerary_days(trip_id, day_order);
create index if not exists idx_itinerary_locations_day_order on itinerary_locations(day_id, location_order);
create index if not exists idx_itinerary_risk_queries_trip on itinerary_risk_queries(trip_id, day_id);
create index if not exists idx_itinerary_risks_trip_category on itinerary_risks(trip_id, category);
create index if not exists idx_heartbeats_user_time on heartbeats(user_id, timestamp desc);
create index if not exists idx_traveler_status_trip_stage on traveler_status(trip_id, current_stage);
create index if not exists idx_incidents_user_sync_status on incidents(user_id, sync_status);
