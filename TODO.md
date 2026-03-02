## Demo Goal (Must Work)

- User can create a trip and itinerary.
- User can see a risk output for the trip.
- Heartbeat can be sent/queued/replayed with staged watchdog behavior.
- User can open offline emergency protocol and submit incident data that syncs on reconnect.

## Done ✅ (keep as-is; already demoable foundation)

### PREVENTION base

- [x] Trip creation with heartbeat toggle (`heartbeat_enabled`)
  - Implemented: `frontend/src/features/trips/services/tripsApi.ts`, `backend/app/routes/trips.py`, `backend/app/schemas/trip_schema.py`
  - Verify: create via `/trips/new`, then list trips API includes `heartbeat_enabled`.

- [x] Itinerary import/upsert + offline fallback
  - Implemented: `frontend/app/trips/[tripId]/import.tsx`, `frontend/src/features/trips/services/itineraryApi.ts`, `frontend/src/features/storage/services/offlineDb.ts`, `backend/app/routes/trips.py`
  - Verify: import JSON; disconnect backend; itinerary still available from local storage.

- [x] Risk report rendering shell + backend analysis scaffold
  - Implemented: `backend/app/routes/itinerary_analysis.py`, `backend/app/services/risk_engine.py`, `frontend/src/features/risk/components/RiskCategoryList.tsx`
  - Verify: run analysis endpoint and view `/trips/[tripId]/risk`.

### CURE base

- [x] Heartbeat ingest + watchdog stage logic
  - Implemented: `backend/app/routes/heartbeats.py`, `backend/app/services/heartbeat_monitor.py`, `backend/tests/test_heartbeat_monitor.py`
  - Verify: `py -3 -m pytest tests/test_heartbeat_monitor.py -q`; manual `POST /heartbeats/watchdog/run`.

- [x] Frontend heartbeat schedule + queue + replay
  - Implemented: `frontend/src/features/heartbeat/services/heartbeatScheduler.ts`, `frontend/src/features/heartbeat/services/heartbeatApi.ts`, `frontend/app/_layout.tsx`
  - Verify: `/dev/heartbeat-test` + offline/online replay behavior.

### MITIGATION base

- [x] Offline emergency protocol UI
  - Implemented: `frontend/app/emergency/index.tsx`, `frontend/app/emergency/[scenarioKey].tsx`, `frontend/src/features/emergency/components/ProtocolSteps.tsx`
  - Verify: open emergency routes without network.

- [x] Local incident + sync queue primitives
  - Implemented: `frontend/src/features/storage/services/offlineDb.ts`, `frontend/src/features/emergency/services/emergencyApi.ts`
  - Verify: `/dev/storage-test`; incident sync queues when backend unavailable.

---

## Must-Do Next ⏭️ (Hackathon Priority P0)

These are the minimum remaining tasks to deliver the full user story demo.

### P0-1: Fix risk API endpoint mismatch (PREVENTION blocker)

- [ ] Make frontend and backend agree on one risk read path.
  - Current mismatch:
    - Frontend calls `GET /trips/{tripId}/risk` in `frontend/src/features/risk/services/riskApi.ts`.
    - Backend currently uses `backend/app/routes/itinerary_analysis.py` and `backend/app/routes/reports.py`.
  - Integration with done features:
    - Keeps existing `RiskCategoryList` and local risk cache working.
  - Done when:
    - `/trips/[tripId]/risk` shows real backend response consistently.

### P0-2: Add `/incidents/sync` backend endpoint (MITIGATION blocker)

- [ ] Implement `POST /incidents/sync` and return stable sync response.
  - Needed because frontend already sends this from `frontend/src/features/emergency/services/emergencyApi.ts`.
  - Integration with done features:
    - Existing `incident_sync` queued jobs can transition to synced.
  - Done when:
    - Incident created offline is marked synced after reconnect.

### P0-3: Demo-grade alert dispatch path (CURE blocker)

- [ ] Implement one concrete alert output path for demo (Twilio SMS **or** deterministic log sink shown in UI).
  - Current placeholder: `backend/app/services/notifications.py`.
  - Integration with done features:
    - Reuses watchdog stage events from `heartbeat_monitor.py`.
  - Done when:
    - Stage 1/2 visibly generates external alert evidence.

---

## Should-Do If Time Permits (P1)

- [ ] Show heartbeat status on trip dashboard (`last seen`, `current stage`).
  - Integrates with CURE stage logic already implemented.

- [ ] Improve risk scoring content quality (Bihar-specific heuristics/data mappings).
  - Integrates with existing analyzer + risk UI.

- [ ] Add file-based itinerary import polish (PDF/CSV input path) while keeping JSON import as fallback.
  - Integrates with current `/trips/[tripId]/import` flow.

---

## Explicitly Deprioritized for Hackathon (P2 / post-demo)

- [ ] Full auth hardening across all routes.
- [ ] Production-grade key management and RBAC.
- [ ] Full notification multi-channel resiliency (FCM/email retries, provider failover).
- [ ] Comprehensive observability, SLO dashboards, and deep telemetry.
- [ ] Long-term schema migrations and data governance workflows.

Reason: these are important for production but not required to prove the core user story in a one-day event.

---

## Hackathon Implementation Sequence (clear execution order)

- [ ] Step 1: Complete P0-1 (risk endpoint alignment)
- [ ] Step 2: Complete P0-2 (incident sync backend)
- [ ] Step 3: Complete P0-3 (alert output path)
- [ ] Step 4: Run full smoke verification pass

Dependency notes:

- Step 2 depends on existing local incident queue/storage (already done).
- Step 3 depends on existing heartbeat watchdog stage triggers (already done).
- Full story demo depends on all three P0 items being complete.

---

## Final Demo Verification Checklist

- [ ] Backend tests pass: `py -3 -m pytest tests -q`
- [ ] Frontend typecheck passes: `npm run typecheck` (from `frontend`)
- [ ] Storage smoke route passes: `/dev/storage-test`
- [ ] Heartbeat smoke route passes: `/dev/heartbeat-test`

End-to-end user story run:

- [ ] Onboard (minimal profile) and create trip with heartbeat enabled.
- [ ] Import itinerary and view risk output.
- [ ] Simulate offline heartbeat delay, trigger watchdog, verify stage alert evidence.
- [ ] Open emergency protocol offline, create incident, reconnect, confirm sync success.
