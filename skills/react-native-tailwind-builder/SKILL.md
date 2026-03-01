---
name: react-native-tailwind-builder
description: Build and verify React Native features styled with Tailwind utility classes through NativeWind. Use when tasks involve React Native screens/components, navigation flows, mobile bug fixes, NativeWind class updates, or validation of mobile app behavior with tests and build checks.
---

# React Native Tailwind Builder

Implement mobile feature work in a strict, low-regression workflow for React Native projects using Tailwind-style utility classes via NativeWind.

This repository's primary product design is SafePassage Bihar Travel Safety Edition, with three core pillars:
- PREVENTION: itinerary risk + connectivity analysis
- CURE: connectivity-aware emergency anomaly detection and escalation
- MITIGATION: offline emergency guidance and incident capture

## Workflow
1. Classify the request by pillar (PREVENTION, CURE, MITIGATION, or shared infrastructure).
2. Inspect impacted screens/components, navigation paths, local storage, and related tests.
3. Define behavior contract before editing:
	- online behavior
	- offline/degraded behavior
	- fallback behavior (missing map/model/data)
	- escalation behavior (if alerting is involved)
4. Implement the smallest React Native change that satisfies the request.
5. Apply or adjust NativeWind utility classes for styling updates.
6. For SafePassage-critical flows (emergency, GPS/location, local storage, contacts, on-device AI context, alerting), invoke `security-best-practices` guidance by default.
7. Run verification checks (tests, lint/type checks, and build health checks when available).
8. Summarize modified files, assumptions, and command outcomes.

## Constraints
- Avoid broad refactors unless explicitly requested.
- Preserve existing project conventions and folder structure.
- Prefer reusable UI primitives and shared style tokens when available.
- Document assumptions before risky changes, especially around navigation and platform behavior.
- Define degraded-mode behavior for offline or missing-data conditions.
- For emergency workflows, keep user steps deterministic, clear, and fail-safe.
- Keep Bihar context explicit where relevant (district names, local emergency services, connectivity-poor routes).
- Never block emergency UX on network availability.
- Maintain durable local queue behavior for events/logs that sync on reconnect.
- Do not change unrelated files.

## Styling Rules
- Use NativeWind utility classes via `className` for styling.
- Prefer shared utility patterns and design tokens over one-off inline styles.
- Use `StyleSheet` only when utility classes are insufficient (for dynamic or platform-specific cases).
- Keep spacing/typography scales consistent across screens.

## Verification
- Use `scripts/run-rn-checks.ps1` for deterministic non-interactive checks.
- Run with `-WhatIf` to preview commands.
- When scripts are missing in `package.json`, the checker reports and skips them.
- `expo-doctor` should run only for Expo projects.

## Agentic Coding Checklist
- Trace each change to a user scenario (for example, offline breakdown guidance, missed check-ins, itinerary import).
- Verify one happy path plus one degraded path per changed feature.
- Validate storage and retry behavior if writing emergency/incident data.
- For CURE logic, include threshold rationale and false-positive controls in notes/tests.
- For MITIGATION logic, verify emergency entry works while offline and under low battery/device constraints when possible.

## References
- Read `references/react-native-nativewind-workflow.md` for setup assumptions, implementation order, and failure handling.
