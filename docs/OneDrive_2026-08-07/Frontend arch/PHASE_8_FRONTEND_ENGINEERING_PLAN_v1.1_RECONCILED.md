# PHASE_8_FRONTEND_ENGINEERING_PLAN_v1.1_RECONCILED.md

# Phase 8 — Frontend Engineering Plan

## Document Status

| Item | Value |
|---|---|
| Version | v1.1 RECONCILED |
| Status | **IMPLEMENTATION READY** |
| Previous Document | `PHASE_8_FRONTEND_ENGINEERING_PLAN_v1.0.md` |
| Previous Status | FROZEN — now **SUPERSEDED** |
| Reconciled By | `FRONTEND_ARCHITECTURE_RECONCILIATION_ADR_001.md` |
| Authority | Phase 3 Domain Architecture (FROZEN) · Phase 4 UX Blueprint **v1.1** (FROZEN) · Phase 5 Wireframes **v1.1** · Phase 6 Design System v1.0 (FROZEN) · Phase 7 Technical Architecture **v1.1** |
| Downstream | `PHASE_9_FRONTEND_IMPLEMENTATION_v1.1_RESET.md` |

---

# 1. Purpose

This document converts the approved frontend architecture into an implementation roadmap.

It supersedes Phase 8 v1.0, which was authored against the Phase 5 and Phase 7 **outlines** and
embedded technology assumptions that the subsequent Phase 7 v1.1 technology decision contradicts.

Phase 8 defines **sequence, scope, and readiness**. It does not define architecture. Where this
document and an upstream artifact appear to conflict, the upstream artifact governs and the
conflict is a defect to be reported.

---

# 2. Reconciliation Summary

| Area | v1.0 (superseded) | v1.1 (this document) | Authority |
|---|---|---|---|
| Framework | Next.js | **React + TypeScript + Vite + React Router** | Phase 7 v1.1 §3, §6 · ADR-001 §2 |
| Routing | Next.js App Router | **React Router**, declarative | Phase 7 v1.1 §6 |
| Rendering | Server-side / App Router | **SPA** | Phase 7 v1.1 §3 |
| Location | *(unspecified)* | **`frontend/`** | Phase 7 v1.1 §4 |
| Structure | *(unspecified)* | **`src/{app,domains,design-system,api,models,state,hooks,utils,tests}`** | Phase 7 v1.1 §4 |
| Feature order | Dashboard → Watchlist → Research Workspace → Portfolio & Monitoring | **Watchlist → Market → Ticker → Portfolio → Decision Center → Search → Settings** | Phase 4 P4-02 · Domain Model §6 |
| Workspace count | 4 named, 2 unarchitected | **7 frozen workspaces** | Phase 4 P4-02 §3 |
| Sprint model | 5 sprints | **11 sequenced stages** | ADR-001 |
| Status | FROZEN | IMPLEMENTATION READY | ADR-001 §6 |

## 2.1 Removed scope

The following appeared in Phase 8 v1.0 and Phase 9 v1.0. **All three are removed.**

| Removed | Reason |
|---|---|
| **Dashboard workspace** | Not a workspace. Phase 4 P4-02 §3 defines exactly seven workspaces; Dashboard is not among them. "Dashboard" is a *screen* owned by Decision Center (`DEC-001`) and Portfolio (`PORT-001`), and a *composition pattern* (Phase 6 P6-37). Treating it as a workspace would violate NP-01 (single responsibility) and IA-01 (single ownership). |
| **Research workspace** | Not architected. `/research` is a **reserved namespace** (Phase 4 P4-02 §14, Appendix B) explicitly held "outside the current architecture." It has no IA entry, no screens in Appendix A, no design spec, and no route owner. It is also out of scope per Domain Model §7, which excludes Research Engine internals. |
| **Alerts workspace** | Not architected. `/alerts` is a **reserved namespace**. Alerts exist only as `WAT-003`, a screen inside the Watchlist workspace (Phase 4 Appendix A). Promoting it to a workspace would duplicate ownership with Watchlist. |

Reserved namespaces remain reserved. Adding any of them as a workspace requires an ADR under
Phase 4 P4-16 §14.

---

# 3. Technology Baseline

Inherited from Phase 7 v1.1. Not open for revision in Phase 8.

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
| Unit / component test | Vitest + React Testing Library |
| End-to-end test | Playwright |
| Accessibility test | axe-core |
| Server State library | **NOT SELECTED** — ADR-003 required before Stage 2 |

## 3.1 Quality gates

Required before merge, per Phase 7 v1.1 §18:

```
npm run lint
npm run typecheck
npm test
npm run build
npm run e2e
```

## 3.2 Performance requirements

Per Phase 7 v1.1 §19 and Phase 4 P4-04 §15:

| Metric | Target |
|---|---|
| Workspace switch | < 300 ms, excluding network |
| Search open | < 100 ms |
| Deep link open | one navigation step |
| Context restoration | immediate |
| Browser history | preserved |

---

# 4. Application Structure

Per Phase 7 v1.1 §4. Binding.

```
frontend/

src/

├── app/
│   ├── router/
│   ├── providers/
│   └── shell/

├── domains/
│   ├── decision/
│   ├── portfolio/
│   ├── watchlist/
│   ├── ticker/
│   ├── market/
│   ├── search/
│   └── settings/

├── design-system/
│   ├── tokens/
│   ├── components/
│   └── charts/

├── api/

├── models/

├── state/

├── hooks/

├── utils/

└── tests/
```

## 4.1 Structural rules

- `domains/` is a **workspace** decomposition. Domain ownership per the Domain Model is enforced in
  `models/` and `api/`, not by folder adjacency (ADR-001 §4).
- Import direction must satisfy the ADR-001 §4 edge list. Enforced by lint from Stage 1.
- `design-system/` consumes tokens only. No hardcoded HEX, no arbitrary spacing (Phase 7 v1.1 §10).
- `api/` holds the API client and repositories. Backend DTOs must not escape the mapper layer.
- `state/` implements the seven state layers of ADR-001 §3.

## 4.2 Data flow

Per Phase 7 v1.1 §8–9. Binding.

```
Component → View Model → Domain Adapter → Repository → API Client → Backend API

Backend DTO → Mapper → Domain Model → View Model → Component
```

Backend DTOs never enter UI components.

---

# 5. Workstreams

## Workstream A — Engineering Foundation

| # | Task |
|---|---|
| A1 | Repository initialization at `frontend/` |
| A2 | Vite + React + TypeScript configuration |
| A3 | Code quality foundation — ESLint, Prettier, import-boundary rules per ADR-001 §4 |
| A4 | Test harness — Vitest, React Testing Library, Playwright, axe-core |
| A5 | CI pipeline wiring the five quality gates |

**Objectives:** prepare the repository, establish the developer workflow, configure quality
standards, create automated validation.

**Blocked by:** U-8 (deployment/environment strategy) for the CI deploy stage only. Build and test
stages are unblocked.

---

## Workstream B — Core Application Shell

| # | Task |
|---|---|
| B1 | Global providers — theme, auth context, error boundary, server-state provider |
| B2 | Routing implementation — Phase 4 Appendix B registry via React Router |
| B3 | Seven-layer state architecture per ADR-001 §3 |
| B4 | Application shell — Global Header, Global Sidebar, Active Workspace, Status Footer (Phase 5 v1.1 §2) |
| B5 | Navigation components — sidebar, drawer, bottom navigation, breadcrumb, tabs |
| B6 | Context capture and restoration in Appendix F priority order |
| B7 | Error, empty, loading and skeleton scaffolding |
| B8 | Route guards and authentication boundary (shape only; backend pending) |

**Objectives:** establish the runtime, implement the route architecture, prepare authentication
boundaries, build the workspace foundation.

**Blocked by:** ADR-003 (Server State library) for B1/B3. U-4 (identity) for B8 beyond shape.

---

## Workstream C — Design System Implementation

| # | Task |
|---|---|
| C1 | Token pipeline — Core → Semantic → Component (Phase 6 P6-08) |
| C2 | Theme system — light and dark (Phase 6 P6-14) |
| C3 | Core components — Button, Input, Dropdown, Table, Card, Chart, Tabs, Breadcrumb, Toolbar, Navigation |
| C4 | Advanced components — Dialog, Drawer, Notification, Toast, Progress, Empty State, Error State, Skeleton |
| C5 | Data visualization — KPI Card, Analytical Table, Heatmap, Dashboard composition |
| C6 | Accessibility baseline per component (WCAG 2.2 AA) |
| C7 | Component documentation |

**Objectives:** convert Phase 6 into code, implement reusable components, establish the
documentation workflow.

**Blocked by:** **U-1 — design token values do not exist.** C1 cannot begin without them. C3–C5
can be structurally scaffolded against placeholder tokens but cannot be accepted.

---

## Workstream D — Workspace Feature Development

| # | Task | Workspace |
|---|---|---|
| D1 | Feature module template | — |
| D2 | Watchlist implementation | Watchlist |
| D3 | Market implementation | Market |
| D4 | Ticker implementation | Ticker |
| D5 | Portfolio implementation | Portfolio |
| D6 | Decision Center implementation | Decision Center |
| D7 | Search implementation | Search |
| D8 | Settings implementation | Settings |

**Objectives:** define feature delivery order, establish ownership, execute the roadmap.

**Blocked by:** U-2 (API coverage) for D3–D8. U-3 (write endpoints) for D6, D8. U-6 (Ticker route
model) for D4. U-11 (terminology) for D6.

---

## Workstream E — Quality & Production Readiness

| # | Task |
|---|---|
| E1 | Test coverage — unit, integration, end-to-end |
| E2 | Performance validation against §3.2 targets |
| E3 | Security review — route guards, token handling, URL hygiene per P4-13 §16 |
| E4 | Accessibility audit — full WCAG 2.2 AA |
| E5 | Observability and error reporting |

**Objectives:** ensure production readiness, enforce quality gates, establish monitoring.

---

## Workstream F — Release Planning

| # | Task |
|---|---|
| F1 | Deployment and environment strategy (ADR-005) |
| F2 | Legacy Flask UI disposition (ADR-006) |
| F3 | Implementation readiness review |
| F4 | Phase 8 promotion to FROZEN |

**Objectives:** finalize the release path, validate readiness, close the plan.

---

# 6. Implementation Sequence

Eleven stages. Ordered by architectural dependency and API readiness.

| Stage | Deliverable | Workstream | Rationale |
|---|---|---|---|
| **1** | **Foundation** | A | Nothing can be built or validated without it |
| **2** | **Application Shell** | B | Every workspace mounts inside it. Must pass the P4-09 validation checklist before feature work |
| **3** | **Design System Implementation** | C | Every workspace consumes it. Blocked on token values |
| **4** | **Watchlist** | D2 | **Only workspace with live backing endpoints** (`/api/v1/watchlists/*`, `/api/v1/candidates/*`). Proves the full vertical slice against a real API |
| **5** | **Market** | D3 | Shared market context consumed by every other workspace (FOUND-004). MI is a shared domain with no personalized dependencies — buildable earliest of the remaining |
| **6** | **Ticker** | D4 | The analytical hub; five of the twelve legal transitions terminate here. Largest API surface |
| **7** | **Portfolio** | D5 | PORT depends on USER. Requires identity |
| **8** | **Decision Center** | D6 | DEC depends on MI + INV + PORT + USER — every upstream domain. Architecturally last despite being the primary workspace |
| **9** | **Search** | D7 | Cross-cutting; needs destinations 4–8 to exist to be useful |
| **10** | **Settings** | D8 | Requires identity and write endpoints |
| **11** | **Hardening** | E, F | Coverage, performance, security, accessibility, observability, release |

## 6.1 Sequence rationale

The order is derived from the frozen dependency edges in `FRONTEND_DOMAIN_MODEL_v1.0` §6, filtered
by current API availability:

```
Shared, no personalization:      MI, INV        → Market, Ticker
Personalized, USER only:         PORT           → Portfolio
Personalized, MI+INV+USER:       WATCH          → Watchlist
Personalized, all upstream:      DEC            → Decision Center
```

Watchlist is promoted ahead of Market despite a heavier dependency set because it is the only
workspace with a live backend today. This is a deliberate deviation from pure dependency order,
made to obtain a working vertical slice early and to validate the Phase 7 §8 data-flow pattern
against a real API before six more workspaces are built on it.

Decision Center is deliberately last. It consumes every other domain, and building it early would
require stubbing MI, INV, PORT and USER simultaneously.

## 6.2 Dependency flow

```
Foundation
   ↓
Application Shell
   ↓
Design System
   ↓
Watchlist → Market → Ticker → Portfolio → Decision Center → Search → Settings
   ↓
Hardening
   ↓
Production Release
```

---

# 7. Stage Gates

No stage begins until the previous stage's gate passes.

| Gate | Condition |
|---|---|
| G1 → Stage 2 | Repo builds; five quality gates green on an empty app; import-boundary lint active |
| G2 → Stage 3 | Shell passes the Phase 4 P4-09 validation checklist: navigation, IA, routing, journeys, context, accessibility, responsive, engineering readiness |
| G3 → Stage 4 | Token pipeline live; all 18 components implemented with their Appendix G required states; axe-core clean |
| G4 → Stage 5 | Watchlist passes its design-spec acceptance criteria; vertical slice validated end to end |
| G5..G10 | Each workspace passes its own frozen design-spec acceptance criteria |
| G11 → Release | Workstream E complete; ADR-004, 005, 006 accepted |

---

# 8. Readiness Checklist

## Architecture

- [x] Application architecture defined — Phase 7 v1.1 §2–4
- [x] Module boundaries defined — Phase 7 v1.1 §4, ADR-001 §4
- [x] Dependency rules defined — Domain Model §6, ADR-001 §4
- [x] Domain dependency diagram corrected — ADR-001 §4

## Application

- [x] Routing defined — Phase 4 Appendix B, Phase 7 v1.1 §6
- [x] Layout hierarchy defined — Phase 5 v1.1 §2–3
- [x] State ownership defined — ADR-001 §3
- [ ] Authentication model defined — **backend blocker U-4**
- [ ] Server State library selected — **ADR-003**

## UI

- [ ] Design tokens defined — **blocker U-1: values do not exist**
- [x] Component strategy defined — Phase 6 P6-15…P6-32
- [x] Component states defined — Phase 6 Appendix G
- [x] Responsive strategy defined — Phase 6 Appendix H
- [x] Accessibility target defined — WCAG 2.2 AA

## Features

- [x] Feature template scope defined — Workstream D1
- [x] Development order defined — §6
- [x] Screen composition defined — Phase 5 v1.1 §4–10
- [x] Data flow defined — Phase 7 v1.1 §8–9
- [ ] API contract complete — **blocker U-2, U-3**
- [ ] Ticker route model resolved — **ADR-002**

## Quality

- [x] Testing strategy defined — Phase 7 v1.1 §17
- [x] Quality gates defined — Phase 7 v1.1 §18
- [x] Performance targets defined — §3.2
- [ ] Coverage thresholds defined — **open**
- [ ] Observability strategy defined — **open**
- [ ] Deployment strategy defined — **ADR-005**

---

# 9. Open Dependencies

Carried from ADR-001 §7. Phase 8 cannot promote to FROZEN while any blocker in the first group
remains open.

| # | Blocker | Blocks stage |
|---|---|---|
| U-1 | Design Token values | 3 and everything after |
| U-2 | Backend API coverage | 5–10 |
| U-3 | Write endpoints | 8, 10 |
| U-4 | Identity layer | 2 (partial), 7, 8, 10 |
| U-5 | Server State library — ADR-003 | 2 |
| U-6 | Ticker route model — ADR-002 | 6 |
| U-7 | PWA posture — ADR-004 | 11 |
| U-8 | Deployment strategy — ADR-005 | 1 (partial), 11 |
| U-9 | Legacy Flask UI — ADR-006 | 11 |
| U-10 | Phase 4 freeze status | governance only |
| U-11 | Candidate vs Recommendation — ADR-007 | 8 |

**Stages 1 and 2 are startable today**, subject to ADR-003. Stage 3 is blocked on U-1. Stage 4 is
startable once Stages 1–3 complete, because its API already exists.

---

# 10. Change Control

This document is IMPLEMENTATION READY, not FROZEN (ADR-001 §6).

| Change | Process |
|---|---|
| Sequence reordering | Versioned revision + changelog |
| Task addition or refinement | Versioned revision |
| Adding a workspace | **ADR required** — Phase 4 P4-16 §14 |
| Technology substitution | **ADR required** — amends Phase 7 |
| Any change contradicting a FROZEN artifact | **Prohibited.** Report as a defect |

Promotion to FROZEN occurs at Workstream F4, after the sequence has been exercised through at least
Stage 4.

---

# 11. Traceability

| Section | Derived from |
|---|---|
| §2 Reconciliation | ADR-001 §2 |
| §2.1 Removed scope | Phase 4 P4-02 §3, §14; Appendix A, B |
| §3 Technology baseline | Phase 7 v1.1 §3, §6, §11–14, §17–19 |
| §4 Application structure | Phase 7 v1.1 §4, §8–10; ADR-001 §4 |
| §5 Workstreams | Phase 8 v1.0 (structure retained); Phase 5 v1.1; Phase 6 P6-15…P6-45 |
| §6 Sequence | Domain Model §6; Phase 4 P4-02; verified API inventory |
| §7 Stage gates | Phase 4 P4-09; the seven workspace design specs |
| §8 Readiness | Phase 8 v1.0 §Implementation Readiness Checklist (updated) |
| §9 Open dependencies | ADR-001 §7 |

---

# 12. Transition

Phase 8 v1.1 enables:

```
Phase 9 — Frontend Implementation
PHASE_9_FRONTEND_IMPLEMENTATION_v1.1_RESET.md
Status: NOT STARTED
```

# End of Document
