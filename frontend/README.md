# Production Decision OS — Frontend

Phase 9 implementation of the frozen frontend architecture.

**Current state: Workstream A (Project Foundation) complete. The application is
intentionally empty** — there is no shell, no routing, no design system and no
workspace yet. Workstream A's exit criterion is that the quality gates pass on
an empty application.

**Decision Center update:** this claim is stale for Decision Center specifically
— Workstream B (Shell + Router) is also complete, and Decision Center's
Executive Summary region is real: it reads live scheduler, Edge Registry
admission, and current-watchlist state through `/api/v1/*`
(`src/domains/decision/decision-page.tsx`, `hooks.ts`), not a placeholder. The
other five still-placeholder workspaces (Portfolio, Watchlist, Ticker, Market,
Search) are unaffected by this milestone. See this repo's CLAUDE.md
Decision-Making Hierarchy on trusting running-system state over a document's
self-report.

**ADR-008 update:** scheduler/job-history/system-status information (formerly
a standalone, unreachable `/internal/operations` route) is now owned by the
Settings workspace, under its already-frozen "System Information" / "Support &
Diagnostics" regions — see
`docs/OneDrive_2026-08-07/Frontend arch/ADR-008_OPERATIONS_DASHBOARD_SETTINGS_PLACEMENT.md`
and `src/domains/settings/settings-page.tsx`. Not an eighth workspace; the
frozen seven-workspace list is unchanged.

## Governing documents

All under `docs/OneDrive_2026-08-07/Frontend arch/`. Read before changing
anything structural.

| Document                              | Status               | Owns                                    |
| ------------------------------------- | -------------------- | --------------------------------------- |
| Phase 3 Decision OS Architecture v2.0 | FROZEN               | Domain stack, ownership                 |
| Frontend Domain Model v1.0            | FROZEN               | Domain edges, dependency rules          |
| Phase 4 UX Blueprint v1.1             | FROZEN               | Navigation, IA, routes, state ownership |
| Phase 5 Wireframes v1.1               | IMPLEMENTATION READY | Screen composition                      |
| Phase 6 Design System v1.0            | FROZEN               | Components, tokens, a11y, responsive    |
| Phase 7 Technical Architecture v1.1   | IMPLEMENTATION READY | Stack, structure, layering              |
| Phase 8 Engineering Plan v1.1         | IMPLEMENTATION READY | Sequence, stage gates                   |
| Phase 9 Implementation v1.1           | NOT STARTED          | Execution record                        |
| ADR-001                               | APPROVED             | Framework, state layers, domain diagram |
| ADR-003                               | APPROVED (2026-08-20) | Server State architecture (TanStack Query) |
| ADR-005                               | PROPOSED             | Deployment strategy                     |
| ADR-006                               | PROPOSED             | Legacy Flask UI disposition             |

## Commands

```bash
npm run dev          # Vite dev server
npm run lint         # gate — AC-2
npm run typecheck    # gate — AC-3
npm run test         # gate — AC-1  (Vitest + RTL)
npm run build        # gate — AC-4
npm run format:check # Prettier
npm run e2e          # Playwright (not a required gate yet)
npm run e2e:install  # one-time browser download
```

The four gates must pass before merge (Phase 7 v1.1 §18).

## Structure

Fixed by Phase 7 v1.1 §4. Do not add top-level directories without an ADR.

```
src/
├── app/            composition root — router · providers · shell
├── domains/        the seven frozen workspaces
├── design-system/  tokens · components · charts
├── api/            API client, transport, typed errors
├── models/         domain models, DTO types, mappers
├── state/          QueryClient config, global defaults
├── hooks/          cross-cutting presentation hooks
├── utils/          leaf helpers, no layer imports
└── tests/          setup, shared test utilities
tests/e2e/          Playwright specs
tools/eslint/       architecture boundary rules
```

`domains/` is a **workspace** decomposition, not a domain one. Domain ownership
is enforced in `models/` and `api/` — see ADR-001 §4.

## Architecture guards

`tools/eslint/architecture-boundaries.js` enforces the machine-checkable subset
of the architecture, and `src/tests/architecture-boundaries.test.ts` proves the
guards actually fire by linting deliberate violations through the real config.

Enforced today:

- **ADR-001 §4** — cross-workspace imports. Only `decision → market, portfolio,
watchlist` is permitted, and only through the public surface. Everything else
  is denied; share through `models/`.
- **ADR-003 N-3** — `@tanstack/react-query` is confined to
  `domains/*/repository/**`, `state/**`, `app/providers/**` and `tests/**`.
  Components and adapters consume the hook surface a Repository exposes.
- **Phase 7 v1.1 §8** — layer direction. `design-system` imports no workspace or
  data layer; `api` and `models` import no workspace; `utils` is a leaf; nothing
  imports the composition root.

If you need to widen an edge, that is an architecture change and needs an ADR —
not an eslint-disable.

## Data flow

Fixed by Phase 7 v1.1 §8–9. Backend DTOs never reach components.

```
Component → ViewModel → Domain Adapter → Repository → Server State → API Client → Backend
Backend DTO → Mapper → Domain Model → View Model → Component
```

## Not yet decided

These block later workstreams and are tracked in Phase 9 v1.1 §7:

| Blocker                                   | Blocks                                     |
| ----------------------------------------- | ------------------------------------------ |
| U-1 design token values do not exist      | Workstream C entirely                      |
| U-2 backend API covers ~1 of 8 domains (stale 2026-08-06 claim — `/api/v1/*` now covers status/scheduler/watchlists/candidates/snapshots/reports/registry/metrics/config/health; still no write endpoints, see U-3) | Workspaces 5–10 |
| U-3 zero write endpoints                  | Decision Center, Settings                  |
| U-4 no identity layer                     | Auth, Portfolio, Decision Center, Settings |
| U-6 Ticker route model (ADR-002)          | Ticker                                     |
| U-8 deployment strategy (ADR-005)         | CI deploy stage, release                   |
| U-9 legacy Flask UI disposition (ADR-006) | Cutover                                    |
