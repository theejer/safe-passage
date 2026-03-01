# SafePassage (DLW Track)

This repository hosts the SafePassage hackathon build: an offline-first safety companion for solo travelers.

## Project Direction
- Primary app surface: Expo-managed React Native in `my-app`.
- Frontend scaffold: Expo Router React Native app in `frontend` (agentic implementation workspace).
- Styling: NativeWind (Tailwind utility classes).
- Priority capabilities: itinerary risk prep (online), emergency guidance (offline), offline maps, and phrase helper.

## Contributor and Agent Guidance
- Authoritative instructions live in `AGENTS.md`.
- Use `skills/react-native-tailwind-builder` for default feature work.
- Apply `skills/security-best-practices` for emergency, GPS/location, storage, and on-device AI related changes.
- Use `skills/react-feature-builder` only for explicit legacy web maintenance.

## Verification Baseline
Run commands from `frontend` for the new Expo scaffold, and from `my-app` only for legacy surfaces:
- `npm start`
- `npm run typecheck` (if present)
- `npx expo-doctor` (if Expo CLI/deps are installed)

Legacy/compatibility commands in `my-app`:
- `npm start`
- `npm test`
- `npm run lint` (if present)
- `npm run typecheck` (if present)
- `npx expo-doctor`

## Environment Setup

Use the provided example files as templates:
- Frontend: `frontend/.env.example`
- Backend: `backend/.env.example`

PowerShell quick copy commands:
- `Copy-Item frontend/.env.example frontend/.env`
- `Copy-Item backend/.env.example backend/.env`

Then fill in real values (especially backend keys like `SUPABASE_URL` and `SUPABASE_KEY`).