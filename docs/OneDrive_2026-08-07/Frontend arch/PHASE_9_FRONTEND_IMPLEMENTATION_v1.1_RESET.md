# PHASE_9_FRONTEND_IMPLEMENTATION_v1.1_RESET.md

# Phase 9 — Frontend Implementation Execution

## Document Status

| Item | Value |
|---|---|
| Version | v1.1 RESET |
| Status | **NOT STARTED** |
| Phase Type | **Implementation Execution** |
| Previous Document | `PHASE_9_FRONTEND_IMPLEMENTATION_v1.0.md` |
| Previous Status | FROZEN, reported complete — now **SUPERSEDED** |
| Reset By | `FRONTEND_ARCHITECTURE_RECONCILIATION_ADR_001.md` |
| Governed By | `PHASE_8_FRONTEND_ENGINEERING_PLAN_v1.1_RECONCILED.md` |
| Authority | Phase 3 (FROZEN) · Phase 4 v1.1 (FROZEN) · Phase 5 v1.1 · Phase 6 v1.0 (FROZEN) · Phase 7 v1.1 |
| Lines of frontend code written | **0** |

---

# 1. Reset Notice

Phase 9 v1.0 recorded the frontend implementation as delivered and frozen. It contained a program
completion table marking Phases 4 through 9 complete, and a handoff to "Maintenance, Feature
expansion, Backend integration refinement, Production operation."

**No frontend implementation exists.** Verified against the repository on 2026-08-07:

| Check | Result |
|---|---|
| `frontend/` directory | absent |
| `package.json` | absent |
| Vite / React / TypeScript configuration | absent |
| Any React source file | absent |
| Frontend test suite | absent |

Phase 9 v1.0 was written prospectively — a template describing intended work in the past tense —
and was then frozen in that state. Its completion record is withdrawn.

## 1.1 Vocabulary correction

| v1.0 term | v1.1 term |
|---|---|
| Delivered | **NOT STARTED** |
| Completed | **NOT STARTED** |
| Maintenance | **Implementation Execution** |
| ✅ Frozen (Phases 7–9) | Phase 7 → IMPLEMENTATION READY · Phase 8 → IMPLEMENTATION READY · Phase 9 → NOT STARTED |
| "Frontend implementation is ready for production operation" | *withdrawn* |

## 1.2 Corrected program state

| Phase | Artifact | Actual status |
|---|---|---|
| Phase 3 | Decision OS Architecture v2.0 | FROZEN |
| Phase 4 | UX Blueprint v1.1 | FROZEN |
| Phase 5 | Wireframes v1.1 | IMPLEMENTATION READY |
| Phase 6 | Design System v1.0 | FROZEN |
| Phase 7 | Technical Architecture v1.1 | IMPLEMENTATION READY |
| Phase 8 | Engineering Plan v1.1 RECONCILED | IMPLEMENTATION READY |
| **Phase 9** | **Implementation** | **NOT STARTED** |

---

# 2. Purpose

Phase 9 is the execution phase. This document is the **execution record**: it tracks what is
actually built, against what acceptance criteria, in what order.

It is not a specification. Every requirement it references is owned upstream. Phase 9 adds no
architecture.

---

# 3. Technology Baseline

Per Phase 7 v1.1 and ADR-001 §2. Next.js is withdrawn.

| Concern | Decision |
|---|---|
| Framework | React + TypeScript |
| Build tool | Vite |
| Application type | Single Page Application |
| Routing | React Router |
| Styling | CSS Variables + CSS Modules |
| Visualization | Apache ECharts |
| Tables | TanStack Table |
| Forms | React Hook Form + Zod |
| Testing | Vitest · React Testing Library · Playwright · axe-core |
| Location | `frontend/` |
| Server State library | **NOT SELECTED — ADR-003** |

---

# 4. Universal Acceptance Criteria

**Every** workstream, and every task within it, must satisfy all five before it may be marked done.

| # | Criterion | Verification |
|---|---|---|
| **AC-1** | **Tests passing** | `npm test` exits 0. No skipped tests in the delivered scope |
| **AC-2** | **Lint passing** | `npm run lint` exits 0, including import-boundary rules per ADR-001 §4 |
| **AC-3** | **Typecheck passing** | `npm run typecheck` exits 0. No `any` in delivered public interfaces |
| **AC-4** | **Build passing** | `npm run build` exits 0 |
| **AC-5** | **Architecture compliance verified** | See §4.1 |

## 4.1 Architecture compliance — what AC-5 means

A task satisfies AC-5 when all of the following hold for the code it delivers:

| # | Check | Authority |
|---|---|---|
| AC-5.1 | No business logic in the frontend — no score calculation, ranking, recommendation generation, signal evaluation, or portfolio metric computation | FOUND-006 · Phase 4 Principle 2 · Phase 7 v1.1 §2 |
| AC-5.2 | Domain imports satisfy the ADR-001 §4 edge list | Domain Model §6 |
| AC-5.3 | Backend DTOs do not escape the mapper layer | Phase 7 v1.1 §9 |
| AC-5.4 | Data flows Component → View Model → Domain Adapter → Repository → API Client | Phase 7 v1.1 §8 |
| AC-5.5 | All seven state layers respected; Resource State owned by URL/Router; workspace filters are Workspace State | ADR-001 §3 |
| AC-5.6 | No Server State written to a URL | ADR-001 §3 |
| AC-5.7 | No temporary UI state in URLs; canonical URLs only; normalization enforced | Phase 4 RM-01, RU-08, P4-13 §12 |
| AC-5.8 | No hardcoded HEX, no arbitrary spacing — tokens only | Phase 6 P6-09 · Phase 7 v1.1 §10 |
| AC-5.9 | Component states match the Phase 6 Appendix G coverage matrix | Phase 6 Appendix G |
| AC-5.10 | WCAG 2.2 AA — axe-core clean; one H1; semantic landmarks; visible focus; no keyboard traps; no color-only communication | Phase 6 P6-42…P6-45 |
| AC-5.11 | Responsive behavior matches the Phase 6 Appendix H adaptation matrix; navigation hierarchy, terminology and workflows identical across devices | Phase 6 P6-41 |
| AC-5.12 | Browser Back / Forward / Refresh / Bookmark / Copy URL / New Tab / Duplicate Tab all behave natively | Phase 4 NP-12 |
| AC-5.13 | Every screen has an entry path and an exit path; no dead ends | Phase 4 SF-02, SF-03, SF-07 |
| AC-5.14 | Only the twelve legal cross-workspace transitions exist | Phase 4 Appendix E |
| AC-5.15 | Only Decision Center exposes actions | The seven workspace design specs, SHALL-NOT blocks |

---

# 5. Workstreams

Status legend: **NOT STARTED** · IN PROGRESS · BLOCKED · COMPLETE

---

## Workstream A — Project Foundation

**Status: NOT STARTED**

| # | Task | Status |
|---|---|---|
| A1 | Initialize `frontend/` with Vite + React + TypeScript | NOT STARTED |
| A2 | Create the `src/` tree per Phase 7 v1.1 §4 | NOT STARTED |
| A3 | Configure ESLint + Prettier | NOT STARTED |
| A4 | Configure import-boundary lint rules enforcing ADR-001 §4 | NOT STARTED |
| A5 | Configure Vitest + React Testing Library | NOT STARTED |
| A6 | Configure Playwright | NOT STARTED |
| A7 | Configure axe-core | NOT STARTED |
| A8 | Implement the five quality gates in CI | NOT STARTED |

**Entry criteria:** ADR-001 accepted — ✅ **SATISFIED 2026-08-07**. Workstream A is unblocked and
awaiting execution authorization.

**Exit criteria:** AC-1…AC-5 pass on an empty application. Import-boundary lint demonstrably fails
a deliberate violation.

**Blockers:** ADR-005 (deployment strategy) — affects the CI deploy stage only, not build or test.

---

## Workstream B — Application Shell

**Status: NOT STARTED**

| # | Task | Status |
|---|---|---|
| B1 | Global providers — theme, error boundary, auth context | NOT STARTED |
| B2 | Server State provider | BLOCKED — ADR-003 |
| B3 | React Router configuration for the Phase 4 Appendix B route registry | NOT STARTED |
| B4 | URL normalization — uppercase symbol, trailing-slash strip | NOT STARTED |
| B5 | Route validation and error mapping (400/401/403/404/408/429/500/maintenance) | NOT STARTED |
| B6 | Seven-layer state architecture per ADR-001 §3 | BLOCKED — ADR-003 |
| B7 | Global Header | NOT STARTED |
| B8 | Global Sidebar — fixed order: Decision Center, Portfolio │ Watchlist, Ticker, Market, Search │ Settings | NOT STARTED |
| B9 | Active Workspace container | NOT STARTED |
| B10 | Status Footer | NOT STARTED |
| B11 | Responsive navigation — drawer, bottom navigation | NOT STARTED |
| B12 | Breadcrumb | NOT STARTED |
| B13 | Context capture and restoration in Appendix F priority order | NOT STARTED |
| B14 | Workspace memory | NOT STARTED |
| B15 | Focus management — route change moves focus to primary heading | NOT STARTED |
| B16 | Keyboard shortcuts — Ctrl/Cmd+K, Ctrl/Cmd+F, Ctrl/Cmd+R, Esc | NOT STARTED |
| B17 | Route guards and auth boundary — shape only | BLOCKED — U-4 |
| B18 | Error, empty, loading and skeleton scaffolding | NOT STARTED |

**Entry criteria:** Workstream A complete.

**Exit criteria:** AC-1…AC-5 pass, **and** the shell passes the full Phase 4 P4-09 validation
checklist — navigation, information architecture, user journeys, screen flow, routing, deep
linking, cross-workspace navigation, context ownership, accessibility, responsive behavior,
browser compatibility, engineering readiness. All twelve must pass.

**Blockers:** ADR-003 · U-4.

---

## Workstream C — Design System

**Status: NOT STARTED — BLOCKED**

| # | Task | Status |
|---|---|---|
| C1 | Core token layer | BLOCKED — U-1 |
| C2 | Semantic token layer | BLOCKED — U-1 |
| C3 | Component token layer | BLOCKED — U-1 |
| C4 | Theme system — light and dark | BLOCKED — U-1 |
| C5 | Core components — Button, Input, Dropdown, Table, Card, Chart, Tabs, Breadcrumb, Toolbar, Navigation | NOT STARTED |
| C6 | Advanced components — Dialog, Drawer, Notification, Toast, Progress, Empty State, Error State, Skeleton | NOT STARTED |
| C7 | Data visualization — KPI Card, Analytical Table, Heatmap | NOT STARTED |
| C8 | Dashboard composition pattern per Phase 6 P6-37 | NOT STARTED |
| C9 | Per-component accessibility to WCAG 2.2 AA | NOT STARTED |
| C10 | Component documentation | NOT STARTED |

**Entry criteria:** Workstream B complete **and** blocker U-1 resolved — the Design Token registry
must exist with real values, light and dark, WCAG 2.2 AA contrast verified.

**Exit criteria:** AC-1…AC-5 pass. All 18 components implement their Phase 6 Appendix G required
states. axe-core clean on every component. No hardcoded HEX anywhere in `design-system/`.

**Blockers:** **U-1 — design token values do not exist.** C1–C4 cannot begin. C5–C8 can be
scaffolded structurally but cannot pass AC-5.8 and therefore cannot be accepted.

---

## Workstream D — Workspace Features

**Status: NOT STARTED**

Delivered strictly in the Phase 8 v1.1 §6 sequence. Each workspace is accepted against its own
FROZEN design specification.

| # | Workspace | Stage | Acceptance spec | Status | Blockers |
|---|---|---|---|---|---|
| D1 | Feature module template | — | Phase 7 v1.1 §4, §8–9 | NOT STARTED | — |
| D2 | **Watchlist** | 4 | `WATCHLIST_DESIGN_SPEC_v1.0_FROZEN` | NOT STARTED | none — API exists |
| D3 | **Market** | 5 | `MARKET_DESIGN_SPEC_v1.0_FROZEN` | BLOCKED | U-2 |
| D4 | **Ticker** | 6 | `TICKER_DESIGN_SPEC_v1.0_FROZEN` | BLOCKED | U-2, U-6 / ADR-002 |
| D5 | **Portfolio** | 7 | `PORTFOLIO_DESIGN_SPEC_v1.0_FROZEN` | BLOCKED | U-2, U-4 |
| D6 | **Decision Center** | 8 | `DECISION_CENTER_DESIGN_SPEC_v1.0_FROZEN` | BLOCKED | U-2, U-3, U-4, U-11 / ADR-007 |
| D7 | **Search** | 9 | `SEARCH_DESIGN_SPEC_v1.0_FROZEN` | BLOCKED | U-2 |
| D8 | **Settings** | 10 | `SETTINGS_DESIGN_SPEC_v1.0_FROZEN` | BLOCKED | U-2, U-3, U-4 |

**Removed from scope:** Dashboard workspace, Research workspace, Alerts workspace. None is a frozen
workspace — see Phase 8 v1.1 §2.1.

**Per-workspace exit criteria.** In addition to AC-1…AC-5, each workspace must satisfy:

- its design spec's §11 state model, implemented exactly
- its design spec's §11 error states — NETWORK_ERROR, API_ERROR, PARTIAL_DATA, STALE_DATA, UNAUTHORIZED
- its design spec's §11 acceptance criteria
- its design spec's §12 SHALL / SHALL NOT / MAY constraints
- its Phase 5 v1.1 screen composition
- the Phase 5 v1.1 §12 seven-state coverage — Default, Loading, Empty, Success, Warning, Error, Disabled
- its Phase 4 Appendix A screen inventory
- its Phase 4 Appendix E legal transitions, and no others

---

## Workstream E — Integration

**Status: NOT STARTED**

| # | Task | Status |
|---|---|---|
| E1 | API client — envelope handling, error mapping, retry policy | NOT STARTED |
| E2 | Repository layer per Phase 7 v1.1 §8 | NOT STARTED |
| E3 | DTO → Domain Model → View Model mappers per Phase 7 v1.1 §9 | NOT STARTED |
| E4 | Server State cache and invalidation policy | BLOCKED — ADR-003 |
| E5 | Event-driven refresh per DEC-006 | BLOCKED — U-2 |
| E6 | Background refresh — no navigation, scroll, workspace or focus reset | NOT STARTED |
| E7 | Authentication integration | BLOCKED — U-4 |
| E8 | Write path — `submitDecisionResponse`, settings save, watchlist/portfolio import | BLOCKED — U-3 |
| E9 | Performance optimization against the §3.2 targets | NOT STARTED |

**Entry criteria:** Workstream D2 complete — the Watchlist vertical slice validates the pattern
before it is generalized.

**Exit criteria:** AC-1…AC-5 pass. Performance targets met. No business logic in any adapter or
mapper.

**Blockers:** ADR-003 · U-2 · U-3 · U-4.

---

## Workstream F — Production Validation

**Status: NOT STARTED**

| # | Task | Status |
|---|---|---|
| F1 | Full test coverage review against agreed thresholds | NOT STARTED |
| F2 | Full WCAG 2.2 AA audit — keyboard, screen reader, contrast, responsive, focus | NOT STARTED |
| F3 | Performance validation — workspace switch < 300 ms, search open < 100 ms | NOT STARTED |
| F4 | Security review — route guards, token handling, URL hygiene per P4-13 §16 | NOT STARTED |
| F5 | Observability and error reporting | NOT STARTED |
| F6 | Architecture compliance audit — full AC-5 sweep | NOT STARTED |
| F7 | Deployment execution | BLOCKED — ADR-005 |
| F8 | Legacy Flask UI cutover | BLOCKED — ADR-006 |
| F9 | Phase 9 completion sign-off | NOT STARTED |

**Entry criteria:** Workstreams A–E complete.

**Exit criteria:** the §6 validation checklist fully green, with evidence.

---

# 6. Production Validation Checklist

Reset to unchecked. To be completed with evidence, not assertion.

## Architecture
- [ ] Application structure matches Phase 7 v1.1 §4
- [ ] Module boundaries enforced by lint
- [ ] Domain dependency rules satisfied per ADR-001 §4
- [ ] No business logic in the frontend

## Routing
- [ ] All Phase 4 Appendix B routes registered, including bare `/decision`
- [ ] URL normalization enforced
- [ ] Protected routes validated
- [ ] Browser history semantics correct — push vs replace
- [ ] Session restoration correct
- [ ] Deep links restore context in Appendix F priority order

## State
- [ ] All seven layers implemented per ADR-001 §3
- [ ] Resource State owned by URL/Router
- [ ] Workspace filters owned by Workspace State
- [ ] Server State never in a URL
- [ ] Multi-tab isolation correct

## Data Layer
- [ ] API client validated
- [ ] Repository pattern validated
- [ ] DTO mapping validated — no DTO reaches a component

## Design System
- [ ] Tokens implemented, no hardcoded values
- [ ] All 18 components implemented
- [ ] Appendix G state coverage complete
- [ ] Appendix H responsive adaptation verified

## Features
- [ ] Watchlist validated
- [ ] Market validated
- [ ] Ticker validated
- [ ] Portfolio validated
- [ ] Decision Center validated
- [ ] Search validated
- [ ] Settings validated

## Quality
- [ ] AC-1 tests passing
- [ ] AC-2 lint passing
- [ ] AC-3 typecheck passing
- [ ] AC-4 build passing
- [ ] AC-5 architecture compliance verified
- [ ] E2E journeys passing — login, navigation, search, workspace transitions
- [ ] WCAG 2.2 AA verified
- [ ] Performance targets met
- [ ] Security reviewed
- [ ] Monitoring enabled

---

# 7. Blockers

Phase 9 cannot start Workstream C, D3–D8, or E while these remain open.

| # | Blocker | Owner | Blocks |
|---|---|---|---|
| U-1 | Design Token values do not exist | Design | Workstream C |
| U-2 | Backend API covers ~1 of 8 domains | Backend | D3–D8, E5 |
| U-3 | Zero write endpoints | Backend | D6, D8, E8 |
| U-4 | No identity layer | Backend | B17, D5–D8, E7 |
| U-5 | Server State library — ADR-003 | Frontend | B2, B6, E4 |
| U-6 | Ticker route model — ADR-002 | Architecture | D4 |
| U-7 | PWA posture — ADR-004 | Product | F |
| U-8 | Deployment strategy — ADR-005 | Frontend + Ops | A8, F7 |
| U-9 | Legacy Flask UI — ADR-006 | Product + Ops | F8 |
| U-10 | Phase 4 freeze status contradiction | Architecture | governance |
| U-11 | Candidate vs Recommendation — ADR-007 | Architecture | D6 |

**ADR-001 approved 2026-08-07.** Remaining gate for start:

- **Workstream A — fully unblocked.** Awaiting execution authorization only.
- **Workstream B — unblocked except B2, B6 (ADR-003) and B17 (U-4).**
- All other workstreams remain blocked as tabulated above.

---

# 8. Progress Ledger

Updated only against verified evidence. No task is marked complete without its acceptance criteria
demonstrably passing.

| Workstream | Tasks | Complete | In progress | Blocked | Not started |
|---|---|---|---|---|---|
| A — Project Foundation | 8 | 0 | 0 | 0 | 8 |
| B — Application Shell | 18 | 0 | 0 | 3 | 15 |
| C — Design System | 10 | 0 | 0 | 4 | 6 |
| D — Workspace Features | 8 | 0 | 0 | 6 | 2 |
| E — Integration | 9 | 0 | 0 | 4 | 5 |
| F — Production Validation | 9 | 0 | 0 | 2 | 7 |
| **Total** | **62** | **0** | **0** | **19** | **43** |

**Overall Phase 9 completion: 0%.**

---

# 9. Change Control

| Change | Process |
|---|---|
| Task status update | Direct edit with evidence reference |
| Task addition or refinement | Versioned revision |
| Acceptance criteria change | **ADR required** |
| Sequence change | Amends Phase 8 v1.1 §6 — versioned revision there first |
| Any change contradicting a FROZEN artifact | **Prohibited.** Report as a defect |

Phase 9 promotes to COMPLETE only when §6 is fully green with evidence. It does not promote to
FROZEN — an execution record is superseded, not frozen.

---

# 10. Handoff

Phase 9 hands off to production operation only after §6 passes in full.

Until then the correct statement of program state is:

```
Architecture:     COMPLETE (with 11 open blockers)
Implementation:   NOT STARTED
Production:       NOT AVAILABLE
```

# End of Document
