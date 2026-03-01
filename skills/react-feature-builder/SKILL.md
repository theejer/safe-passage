---
name: react-feature-builder
description: Implement and verify web React features in Create React App style projects. Use for browser-focused React component/UI tasks, frontend bug fixes, and web test/build validation. Do not use for React Native mobile tasks.
---

# React Feature Builder

Implement web React feature work in a predictable sequence that minimizes regressions and keeps edits scoped.

In this repository, this is a secondary skill for legacy/transitional web surfaces only. The primary product target is React Native mobile for SafePassage Bihar Travel Safety Edition.

## Workflow
1. Inspect impacted React files and existing tests before editing.
2. Implement the smallest change that satisfies the request.
3. Run targeted test verification first.
4. Run a production build check.
5. Summarize modified files, assumptions, and verification outcomes.

## Constraints
- Avoid broad refactors unless explicitly requested.
- Preserve existing project conventions and file structure.
- Document assumptions before making risky or ambiguous changes.
- Do not change unrelated files during feature delivery.
- In this repository, use this skill only for explicitly requested legacy web maintenance.
- Do not move core safety logic into web-only paths unless explicitly requested.
- Keep behavior contracts aligned with mobile-first pillars when touching shared docs/logic (PREVENTION/CURE/MITIGATION).

## Verification
- Use `scripts/run-react-checks.ps1` for deterministic checks.
- Default execution runs tests and build from the app directory.
- Use `-WhatIf` to preview commands without execution.

## References
- For detailed CRA-oriented implementation and verification guidance, read `references/react-cra-workflow.md`.
