# Frontend Tests

This folder contains runtime test helpers for frontend features.

## SQLite CRUD smoke test

- File: `tests/storage/sqliteCrud.smoke.ts`
- Executes local SQLite storage checks for metadata, trips, itinerary, risk cache, and incidents.
- Intended runtime: Expo app on simulator/device (not plain Node.js).

### Run path

A dev route is available at `/dev/storage-test`.

1. Start app: `npm start`
2. Open route in Expo Router: `/dev/storage-test`
3. Tap **Run SQLite Smoke Test**
4. Review check-by-check pass/fail output on screen
