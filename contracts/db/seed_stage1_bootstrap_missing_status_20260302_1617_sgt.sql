-- Seed variant: trigger Stage 1 via missing-status bootstrap path
-- When watchdog finds an eligible trip with no traveler_status row, it sends Stage 1.

begin;

-- Clean previous rows for this named scenario so reruns stay tidy.
delete from alert_events
where trip_id in (
  select id from trips where title = 'Bootstrap Alert Simulation'
)
and stage = 'stage_1_initial_alert';

delete from traveler_status
where trip_id in (
  select id from trips where title = 'Bootstrap Alert Simulation'
);

delete from emergency_contacts
where phone = '+6592000002';

delete from trips
where title = 'Bootstrap Alert Simulation';

delete from users
where phone = '+6592000001';

with new_user as (
  insert into users (id, full_name, phone)
  values (
    gen_random_uuid(),
    'Priya Sharma',
    '+6592000001'
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
    'Bootstrap Alert Simulation',
    true,
    '2026-03-01',
    '2026-03-05',
    'India',
    true
  from new_user u
  returning id, user_id
)
insert into emergency_contacts (id, user_id, name, phone, telegram_chat_id, telegram_bot_active)
select
  gen_random_uuid(),
  u.id,
  'Anil Sharma',
  '+6592000002',
  '123456789',
  true
from new_user u;

commit;
