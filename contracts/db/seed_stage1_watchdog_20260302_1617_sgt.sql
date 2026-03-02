-- Seed data to trigger Stage 1 watchdog alert at 2026-03-02 16:17 SGT
-- SGT (UTC+8) reference: 2026-03-02 16:17:00+08 = 2026-03-02 08:17:00+00
-- Target behavior:
-- 1) Trip is watchdog-eligible (heartbeat_enabled + trip_planned + date window)
-- 2) Traveler status is open and current_stage='none'
-- 3) Offline duration is large enough to exceed Stage 1 trigger (> 1.5x expected)
-- 4) Emergency contact has Telegram activated
-- 5) No recent Stage 1 alert dedupe conflict

begin;

-- Clean previous rows for this named scenario so reruns stay tidy.
delete from alert_events
where trip_id in (
  select id from trips where title = 'Bihar Route Simulation'
)
and stage = 'stage_1_initial_alert';

delete from traveler_status
where trip_id in (
  select id from trips where title = 'Bihar Route Simulation'
);

delete from monitoring_expectations
where trip_id in (
  select id from trips where title = 'Bihar Route Simulation'
);

delete from emergency_contacts
where phone = '+6598765432';

delete from trips
where title = 'Bihar Route Simulation';

delete from users
where phone = '+6591234567';

with new_user as (
  insert into users (id, full_name, phone)
  values (
    gen_random_uuid(),
    'Aarti Kumari',
    '+6591234567'
  )
  returning id
), new_trip as (
  insert into trips (
    id,
    user_id,
    title,
    trip_planned,
    start_date,
    end_date,
    destination_country,
    heartbeat_enabled
  )
  select
    gen_random_uuid(),
    u.id,
    'Bihar Route Simulation',
    true,
    '2026-03-01',
    '2026-03-05',
    'India',
    true
  from new_user u
  returning id, user_id
), new_contact as (
  insert into emergency_contacts (id, user_id, name, phone, telegram_chat_id, telegram_bot_active)
  select
    gen_random_uuid(),
    u.id,
    'Ravi Kumar',
    '+6598765432',
    '123456789',
    true
  from new_user u
  returning id
), new_expectation as (
  insert into monitoring_expectations (
    id,
    trip_id,
    location_name,
    expected_offline_minutes,
    threshold_multiplier,
    created_at
  )
  select
    gen_random_uuid(),
    t.id,
    'dynamic_window',
    90,
    1.50,
    now()
  from new_trip t
  returning id
)
insert into traveler_status (
  id,
  user_id,
  trip_id,
  last_seen_at,
  last_seen_lat,
  last_seen_lng,
  last_battery_percent,
  last_network_status,
  location_risk,
  connectivity_risk,
  current_stage,
  monitoring_state,
  last_stage_change_at,
  last_evaluated_at,
  updated_at
)
select
  gen_random_uuid(),
  t.user_id,
  t.id,
  '2026-03-01 20:00:00+00', -- 12h17m offline at 2026-03-02 08:17:00+00
  24.7541,
  84.3795,
  18,
  'offline',
  'high',
  'severe',
  'none',
  'active',
  '2026-03-01 20:00:00+00',
  '2026-03-02 08:16:00+00',
  now()
from new_trip t;

commit;

-- Optional: if watchdog baseline should be seeded explicitly, add a row into itinerary_risks:
-- insert into itinerary_risks (id, trip_id, category, expected_offline_minutes, recommendation)
-- select gen_random_uuid(), id, 'connectivity', 90, 'Seeded for watchdog simulation'
-- from trips where title = 'Bihar Route Simulation' order by created_at desc limit 1;
