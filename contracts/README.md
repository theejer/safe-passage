# SafePassage Integration Contracts

This folder is the shared source of truth for data contracts between `frontend` and `backend`.

## Purpose
- Prevent frontend/backend payload drift.
- Standardize JSON structures for PREVENTION, CURE, and MITIGATION.
- Define stable database table outlines and shared interfaces for agentic implementation.

## Contract Rules
- Wire payloads use `snake_case` for backend alignment.
- Frontend maps payloads to `camelCase` at service boundaries.
- All payloads should include `contract_version` and `request_id` where applicable.
- Critical writes (alerts, incident sync) use idempotency keys.
- Sensitive fields (GPS traces, contacts, incident evidence) must be treated as encrypted-at-rest in implementation.

## Structure
- `api/shared/` : common API envelope and device/sync contracts
- `api/prevention/` : itinerary/trip/risk payloads
- `api/cure/` : heartbeat/anomaly/alert payloads
- `api/mitigation/` : emergency protocol, phrase packs, incident sync payloads
- `db/schema_outline.sql` : table blueprint with constraints/index notes
- `interfaces/contracts.ts` : shared TypeScript interfaces and enums

## Versioning
- Breaking schema changes: create a new major version folder (for example `v2/`).
- Additive fields: backward-compatible update in current major version.
- Keep changelog entries in `contracts/changelog.md`.
