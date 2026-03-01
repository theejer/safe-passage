# Agent Instructions for dlweek

## Scope and Structure
- Repository root: `dlweek`
- SafePassage is a mobile-first safety product for low-connectivity travel in Bihar, India.
- Product shape follows three pillars: **PREVENTION** (itinerary risk analysis), **CURE** (connectivity-aware offline anomaly alerts), **MITIGATION** (offline emergency guidance).
- Primary target implementation is Expo-managed React Native; backend services may be Node/Express or Flask REST based on the active implementation slice.
- Styling direction: Tailwind utility classes through NativeWind.
- `my-app` is the active app folder and should be treated as the primary mobile app surface.
- Treat this file as the authoritative instruction source for this repository unless a deeper `AGENTS.md` is intentionally added later.

## SafePassage Operating Mode
- Default to offline-first design and degraded-mode behavior for all user-critical flows.
- Treat emergency workflows (Lost/Theft/Medical/Harassment/Breakdown/Flood/Detained/Witness) as high-risk UX paths: fail safe, keep steps explicit, and avoid fragile dependencies.
- For incident logs, retain data until user deletion. Keep retention transparent and user-controlled.
- Encrypt sensitive local data whenever the platform stack supports it (incident details, emergency contacts, identifiers, and precise location history).
- Keep Bihar context explicit in safety logic: district/block/place names, local emergency numbers, and low-tower assumptions for rural segments.
- Offline mode must remain operational for days/weeks without network and recover with deterministic sync once reconnected.

## Agentic Delivery Contract
- Start each substantial task by mapping requested work to one or more pillars (PREVENTION/CURE/MITIGATION).
- Define acceptance criteria before edits: user-visible behavior, offline behavior, fallback behavior, and escalation behavior.
- Prefer vertical slices over broad refactors: UI + state + storage + alerts for one user path at a time.
- For each implemented behavior, document assumptions for GPS quality, connectivity freshness, and map/data-pack availability.
- If a dependency or script is missing, report and continue with available verification paths; do not invent scripts.
- Preserve explainability in safety logic: no opaque thresholds without rationale in code/docs.

## Bihar Safety-Specific Engineering Guardrails
- Risk analysis output must separate location risk from connectivity risk and include actionable recommendations.
- Connectivity anomaly alerts should be risk-adaptive and minimize false positives; use expected-offline windows from itinerary context.
- Emergency UI must always expose a deterministic offline path with large, explicit actions and no hidden branching.
- Incident evidence capture (photos/audio/text + timestamp/GPS) should queue locally and sync safely after reconnect.
- Phrase-helper and crisis guidance must fail gracefully when on-device model is unavailable (template fallback).

## Command Contract
Run app commands from the active app folder (`my-app`):
- `npm start`
- `npm test`
- `npm run lint` (when available)
- `npm run typecheck` (when available)
- `npx expo-doctor` (Expo-managed app contexts only)

If a script is missing from `package.json`, report and skip it. Do not invent scripts.

## Editing and Review Expectations
- Keep changes minimal and localized to the requested task.
- Include or update tests when behavior changes.
- Do not modify unrelated files.
- Prefer preserving existing project patterns unless the task requires a change.
- Prefer React Native + NativeWind patterns over web-only React patterns.
- For offline features, define behavior for both connected and disconnected states.
- Call out assumptions for GPS accuracy, cached data freshness, and map/data-pack availability.
- For CURE alerting changes, call out trigger thresholds, escalation rules, and anti-spam/false-positive controls.
- For MITIGATION changes, verify offline emergency entry remains available in all major app states.

## Skill Usage Policy
- `react-native-tailwind-builder`: default for React Native features, screens, navigation, state, and NativeWind styling.
- `security-best-practices`: mandatory by default for tasks involving emergency workflows, GPS/location, offline storage, incident logging, contacts, auth/session, on-device AI context handling, or alert escalation integrations.
- `react-feature-builder`: use only for explicit legacy web maintenance tasks.
- `playwright`: use only when a browser surface exists and browser automation is explicitly needed.
- `doc`: use for structured documentation and task artifacts.

## Skill Routing Matrix
- React Native UI/feature work -> `react-native-tailwind-builder`
- Emergency or location-sensitive changes -> `react-native-tailwind-builder` + `security-best-practices`
- Data retention/storage/offline packs -> `react-native-tailwind-builder` + `security-best-practices`
- Alert thresholds/escalation/monitoring logic -> `react-native-tailwind-builder` + `security-best-practices`
- Itinerary parsing and risk-analysis integration -> `react-native-tailwind-builder` (+ backend skill guidance as applicable) + `security-best-practices`
- Legacy CRA web fix -> `react-feature-builder`
- Browser flow automation -> `playwright`
- Formal project docs/artifacts -> `doc`

## Output Expectations
- Always report modified files.
- Always report verification commands run and their outcomes.
- For security-sensitive tasks, report which security guidance was applied and any residual risk/tradeoff.
- For safety-feature tasks, explicitly report offline behavior, escalation behavior, and fallback behavior.
