# SafePassage Frontend Scaffold

This is an Expo Router + TypeScript scaffold for agentic implementation of SafePassage.

## Design Intent
- Thin route files in `app/`
- Feature logic in `src/features/*`
- Shared UI/hooks/config in `src/shared/*`
- Infrastructure wrappers in `src/lib/*`

## Quick Start
```powershell
cd frontend
npm install
npm run start
```

## Environment
Create a local env file from the template:

```powershell
copy .env.example .env
```

Supported public variables:
- `EXPO_PUBLIC_BACKEND_URL` (default: `http://localhost:5000`)
- `EXPO_PUBLIC_FEATURE_OFFLINE_LLM` (`true`/`false`, default: `false`)

## Useful Commands
```powershell
npm run start
npm run android
npm run ios
npm run web
npm run typecheck
```

## Agentic Coding Notes
- Route screens should orchestrate hooks/services, not embed heavy logic.
- Feature hooks own data orchestration and offline fallback behavior.
- Services are the boundary for backend API and local persistence integrations.

## SQLite Storage Docs
- Collaborator guide: `src/features/storage/README.md`
- Runtime smoke test docs: `tests/README.md`
