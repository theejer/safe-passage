# Agent Instructions for dlweek

## Scope and Structure
- Repository root: `dlweek`
- Active application: `my-app` (Create React App structure)
- Treat this file as the authoritative instruction source for this repository unless a deeper `AGENTS.md` is intentionally added later.

## Command Contract
Run app commands from `my-app`:
- `npm start`
- `npm test`
- `npm run build`

## Editing and Review Expectations
- Keep changes minimal and localized to the requested task.
- Include or update tests when behavior changes.
- Do not modify unrelated files.
- Prefer preserving existing project patterns unless the task requires a change.

## Skill Usage Policy
- Use `react-feature-builder` for React feature work in `my-app`.
- Use `playwright` for browser end-to-end checks when needed.
- Use `security-best-practices` for security-sensitive changes.
- Use `doc` for structured documentation and task artifacts.

## Output Expectations
- Always report modified files.
- Always report verification commands run and their outcomes.
