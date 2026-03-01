# React Native + NativeWind Workflow

## Assumed Stack
- React Native app with Expo-managed workflow by default.
- Tailwind-style classes implemented through NativeWind.
- JavaScript or TypeScript project layouts are both supported.
- SafePassage flows are offline-first and include security-sensitive emergency scenarios.
- SafePassage is Bihar-focused and should preserve district/block and low-connectivity context when relevant.

## Implementation Order
1. Identify affected screen(s), component(s), route(s), and data layers for the relevant pillar:
	- PREVENTION (itinerary/risk display)
	- CURE (monitoring/alerts/escalation)
	- MITIGATION (offline emergency/protocol/evidence capture)
2. Review current UI state and existing tests for the changed behavior.
3. Define behavior contract before coding:
	- connected mode
	- offline mode
	- fallback mode (no map pack, stale cache, unavailable on-device model)
	- escalation behavior (if alerting/check-ins are touched)
4. Implement behavior changes first (state, props, handlers, data flow).
5. Apply NativeWind utility classes (`className`) for final visual structure.
6. Validate responsive behavior and platform-specific rendering.
7. For emergency/location/storage/model-context/alerting changes, include security best-practice checks.
8. Run checks and summarize outcomes.

## NativeWind Guidance
- Prefer utility classes for layout, spacing, colors, and typography.
- Consolidate repeated class sets into shared components when repetition appears.
- Keep class strings readable and grouped by purpose (layout, spacing, text, color).
- Avoid mixing many inline style objects with utility classes unless required.
- Keep emergency-state screens visually unambiguous (high contrast, obvious action hierarchy).

## Suggested Commands
From app directory:
- `npm test -- --watchAll=false`
- `npm run lint`
- `npm run typecheck`
- `npx expo-doctor` (Expo projects)

Run only commands that exist in the project. Missing scripts should be reported, not invented.

## Failure Handling
- Test failure: resolve assertions or implementation mismatches and rerun tests.
- Lint/type failure: fix violations and rerun checks before completion.
- Expo health failure: report actionable issues and impacted platform behavior.
- NativeWind mismatch (classes not applied): verify Babel plugin setup, content globs, and component wrappers.
- Offline data missing or stale: define and document fallback behavior before completion.

## Proposal-Specific Guardrails
- Risk analysis outputs should separate location risk and connectivity risk.
- Alert logic should be risk-adaptive and include anti-spam/false-positive controls.
- Emergency action entry should stay visible and deterministic in all major app states.
- Incident logs (photo/audio/text + GPS/timestamp) should queue locally and sync deterministically after reconnect.
- If on-device model guidance is unavailable, use template-based crisis steps and phrase helper fallback.
