# ADR-001 — Frontend Architecture Reconciliation

| Item | Value |
|---|---|
| ADR ID | FRONTEND-ADR-001 |
| Title | Frontend Architecture Reconciliation (Phase 5/7 → Phase 8/9) |
| Status | **APPROVED** |
| Date Proposed | 2026-08-07 |
| Date Approved | 2026-08-07 |
| Approved By | Owner |
| Supersedes Status | PROPOSED |
| Authority | Phase 3 Domain Architecture (FROZEN) · Phase 4 UX Blueprint v1.1 (FROZEN) · Phase 6 Design System v1.0 (FROZEN) · Phase 5 Wireframes v1.1 (IMPLEMENTATION READY) · Phase 7 Technical Architecture v1.1 (IMPLEMENTATION READY) |
| Supersedes | Framework and sequencing assumptions embedded in `PHASE_8_FRONTEND_ENGINEERING_PLAN_v1.0.md` and `PHASE_9_FRONTEND_IMPLEMENTATION_v1.0.md` |
| Affects | Phase 8, Phase 9, and all downstream implementation |

---

# 1. Context

`PHASE_5_WIREFRAMES_v1.1_IMPLEMENTATION_READY.md` and
`PHASE_7_FRONTEND_TECHNICAL_ARCHITECTURE_v1.1_IMPLEMENTATION_READY.md` replaced their v1.0
predecessors, which were a table of contents and a section outline respectively.

The v1.1 documents make concrete architectural decisions. Phase 8 and Phase 9 — both authored
against the v1.0 outlines and both carrying freeze statements — now contradict them.

A frontend architecture inventory identified the following divergences requiring formal resolution:

| # | Divergence | Documents in conflict |
|---|---|---|
| A | Framework: Next.js vs React + Vite | Phase 8 §B, Phase 9 §A vs Phase 7 v1.1 §3 |
| B | State layer model: Resource State dropped, Server State added | Phase 4 P4-12 §3 (FROZEN) vs Phase 7 v1.1 §7 |
| C | Domain dependency diagram omits PORT, WATCH, USER | Domain Model §6 (FROZEN) vs Phase 7 v1.1 §5 |
| D | Ticker: 9 screens vs 5 permitted `?tab=` values | Phase 5 v1.1 §7 vs Phase 4 P4-13 §7 (FROZEN) |
| E | `IMPLEMENTATION READY` undefined in the governance vocabulary | Phase 5 v1.1, Phase 7 v1.1 vs Phase 4 P4-10 §3 |

This ADR resolves A, B, C, and E. It **documents** D and presents options without selecting one.

---

# 2. Decision A — Framework

## Resolution

**React + TypeScript + Vite + React Router.**

Next.js is withdrawn.

## Rationale

Phase 7 is the document that owns the technology decision. Phase 8 and Phase 9 are downstream
consumers; per Phase 4 P4-16 §15, no downstream phase may redefine architectural ownership.
The Next.js references in Phase 8/9 predate any Phase 7 technology decision and were therefore
assumptions, not decisions. When Phase 7 v1.1 made the decision, those assumptions became stale.

Phase 7 v1.1 §3 justifies the selection on the basis that the product is an authenticated
analytical workspace whose primary requirements are browser state, deep linking, workspace
navigation, and persistent context — satisfied by an SPA and not requiring server-side rendering.

## Resulting stack (binding)

| Concern | Decision | Source |
|---|---|---|
| Framework | React + TypeScript | Phase 7 v1.1 §3 |
| Build tool | Vite | Phase 7 v1.1 §3 |
| Application type | Single Page Application | Phase 7 v1.1 §3 |
| Routing | React Router | Phase 7 v1.1 §6 |
| Styling | CSS Variables + CSS Modules | Phase 7 v1.1 §11 |
| Visualization | Apache ECharts | Phase 7 v1.1 §12 |
| Tables | TanStack Table | Phase 7 v1.1 §13 |
| Forms | React Hook Form + Zod | Phase 7 v1.1 §14 |
| Testing | Vitest · React Testing Library · Playwright · axe-core | Phase 7 v1.1 §17 |
| Location | `frontend/` | Phase 7 v1.1 §4 |

## Consequences

- Phase 8 and Phase 9 must be reissued. Superseded by `_v1.1_RECONCILED` and `_v1.1_RESET`.
- No server-side rendering, no React Server Components, no Next.js file-system routing.
- Routing is declarative and code-owned; the Phase 4 Appendix B route registry maps directly to
  React Router route definitions.
- The PRD's "Mobile-first PWA" non-functional requirement (PRD §11) is **not** satisfied by an SPA
  alone. See §7 Unresolved.

---

# 3. Decision B — State ownership

## Resolution

The frontend implements **seven** state layers: the six frozen layers from Phase 4 P4-12,
**plus** Server State.

```
1. Application State
2. Workspace State
3. Resource State
4. Page State
5. Component State
6. Overlay State
        +
7. Server State
```

**Server State does not replace Resource State.** The two are orthogonal.

## Rationale

Phase 7 v1.1 §7 enumerated six layers that dropped Resource State and added Server State. Phase 4
P4-12 declares state ownership frozen, and P4-16 §14 lists state-ownership changes as
ADR-requiring. Removing Resource State would break three frozen guarantees:

- **RM-04 / RU-04** — the same URL always produces the same application state.
- **P4-12 §14** — context restoration priority begins at Resource.
- **Appendix D** — Active Resource is owned by the URL.

Resource State answers *which analytical object is in view*, is owned by the URL and Router, and is
addressable and bookmarkable. Server State answers *what the backend returned for it*, is owned by
the data layer, and is cache-shaped and non-addressable. Conflating them would place cache
lifecycle into the URL, which P4-13 §19 prohibits.

## Ownership matrix (normative)

| Layer | Owns | Owner | Lifetime | Persisted in |
|---|---|---|---|---|
| Application | Authentication, theme, environment, feature flags, snapshot version, time zone | Application | Session | Application |
| Workspace | Selected sector/index, active tab, compare mode, timeframe, benchmark, grouping, **workspace filters** | Workspace | Workspace lifetime | Workspace + URL where addressable |
| **Resource** | The active analytical object (`:symbol`, `:index`, `:sector`, `:group`) | **URL / Router** | Resource lifetime | **URL** |
| Page | Pagination, expanded panels, local sorting, accordion state | Page | Page lifetime | Not persisted |
| Component | Dropdown open, input value, selected option, hover, focus | Component | Component lifetime | Not persisted |
| Overlay | Modal, drawer, tooltip, context menu, toast | Component | Temporary | Never persisted, never restored on refresh |
| **Server** | API responses, cache entries, fetch/refetch status, invalidation | **Data layer** | Cache policy | In-memory cache only |

## Correction to Phase 7 v1.1 §7

Phase 7 v1.1 §7 assigns `Filters → Page`. Phase 4 P4-12 §11 assigns `Workspace Filters → Workspace`.

**The frozen assignment governs: workspace filters are Workspace State.** Page State owns only
page-local presentation (pagination, expansion, local sort), per P4-12 §8.

## Consequences

- Server State requires a dedicated library. **Not yet selected** — see §7 Unresolved.
- Server State must never be written to the URL.
- Resource State must never be held in the server cache as the source of truth for identity.
- Phase 7 v1.1 §7 is amended by this ADR and should be corrected at its next revision.

---

# 4. Decision C — Domain dependency model

## Resolution

Phase 7 v1.1 §5 omits **PORT**, **WATCH**, and **USER**, and misstates DEC's dependencies. It is
corrected as follows.

### Layer view

```
FOUND
 |
REF
 |
+-----------------------+
|          |            |
MI        INV          USER
|          |            |
+----------+------------+
           |
          PORT
           |
          DEC
```

Additionally:

```
WATCH depends on:   MI + INV + USER

UI    depends on:   DEC + PORT + WATCH + USER

UX    depends on:   UI
```

### Normative edge list

The layer view above is a tier rendering. Where it and the edge list differ, **the edge list
governs**, because it reproduces `FRONTEND_DOMAIN_MODEL_v1.0_FROZEN.md` §6 verbatim:

| Domain | Depends on |
|---|---|
| FOUND | *(nothing)* |
| REF | FOUND |
| MI | FOUND, REF |
| INV | FOUND, REF |
| USER | FOUND, REF |
| PORT | **USER** |
| WATCH | MI, INV, USER |
| DEC | **MI, INV, PORT, USER** |
| UI | DEC, PORT, WATCH, USER *(view models)* |
| UX | UI *(components)* |

Two points where the layer diagram simplifies and the edge list is authoritative:

1. **DEC depends on MI and INV directly**, not transitively through PORT.
2. **PORT depends on USER only.** It does not depend on MI or INV.

> **Open for owner ruling.** If the intent was to change the frozen model — routing MI/INV to DEC
> through PORT, or adding MI/INV as PORT dependencies — that is an amendment to a FROZEN document
> and requires its own ADR. This ADR assumes no such change was intended and preserves the frozen
> edges.

## Invariants

- Shared domains (FOUND, REF, MI, INV) never depend on personalized domains (DEC, PORT, WATCH, USER).
- One business concept has exactly one owner domain.
- Cross-domain access is by reference only.
- Reverse dependencies are prohibited.

## Consequences

- The `frontend/src/domains/` tree — `decision`, `portfolio`, `watchlist`, `ticker`, `market`,
  `search`, `settings` — is a **workspace** decomposition, not a domain decomposition. Domain
  ownership is enforced within `models/` and `api/`, not by folder adjacency.
- `decision` may import from `market`, `portfolio`, and `watchlist` models. The reverse is prohibited.
- Import-boundary enforcement should be added to the lint configuration during Phase 9 Workstream A.

---

# 5. Decision D — Ticker route model *(DOCUMENTED, NOT RESOLVED)*

## Conflict

| Source | Statement |
|---|---|
| Phase 4 Appendix A | Ticker has **9** screens: Overview, Technical, Fundamentals, Ownership, Flow, Financial Statements, Corporate Actions, News, Compare |
| Phase 5 v1.1 §7 | Ticker exposes **9** tabs — the same nine |
| Phase 4 §7 / P4-13 §7 | `?tab=` permits **5** values: `overview`, `technical`, `ownership`, `flow`, `fundamentals` |
| Phase 4 Appendix B | One Ticker route: `/ticker/:symbol` |

Four screens — Financial Statements, Corporate Actions, News, Compare — have **no legal URL**.

This violates two frozen rules: P4-02 §13 (every Resource and Detail screen is deep-linkable) and
DL-01 / RU-01 (every analytical resource has exactly one canonical URL).

## Options

**Option 1 — Extend the tab allowlist**

```
?tab= overview | technical | fundamentals | ownership | flow
    | financials | corporate-actions | news | compare
```

Preserves one canonical route. Consistent with P4-07 §7, which classes tabs as detail links that
never change the underlying resource. Minimal change: one enum in a frozen document.

*Cost:* `compare` is arguably not a peer of the others — it already has a dedicated `?compare=`
parameter, creating an overlap between `?tab=compare` and `?compare=BMRI`.

**Option 2 — Dedicated sub-routes**

```
/ticker/:symbol
/ticker/:symbol/technical
/ticker/:symbol/fundamentals
...
```

Each screen becomes independently addressable. Aligns with P4-02 §7's Resource → Detail hierarchy.

*Cost:* Contradicts Phase 4 Appendix B, which registers exactly one Ticker route, and P4-06 §4's
"every workspace owns one canonical root." A larger frozen-document change than Option 1.

**Option 3 — Hybrid**

Extend the allowlist to eight analytical tabs (Option 1); promote Compare to `/ticker/:symbol/compare`
because it takes a second resource identifier and is therefore not pure presentation.

## Recommendation

**Option 1**, amended to exclude Compare — i.e. Option 3.

Rationale: eight of the nine screens are alternate views of one resource and belong in `?tab=`,
which is what P4-07 §7 describes. Compare binds a *second* symbol; under RM-02 and P4-13 §19
("resource identifiers in query parameters" are prohibited) a comparison of two securities is
arguably its own resource and warrants a path segment.

**No implementation shall proceed on the Ticker workspace until this is ruled on.** Ticker is
position 6 in the Phase 8 sequence, which provides scheduling slack.

---

# 6. Decision E — Governance status vocabulary

## Resolution

**IMPLEMENTATION READY** is added to the governance vocabulary and defined as:

> **IMPLEMENTATION READY** — A reviewed architecture artifact approved for execution but not yet
> frozen.

## Status ladder

| Status | Meaning | Change process |
|---|---|---|
| DRAFT | Authoring in progress | Free revision |
| **IMPLEMENTATION READY** | **Reviewed and approved for execution. Content is authoritative and may be built against. Not yet frozen — correction is permitted without an ADR, provided no FROZEN artifact is contradicted.** | **Versioned revision + changelog. No ADR required unless a FROZEN artifact is affected.** |
| FROZEN | Canonical and closed | ADR required for any architectural change |
| SUPERSEDED | Replaced by a newer artifact | Retained for history; never deleted |

## Rules

1. An IMPLEMENTATION READY artifact **may be built against**. It is not provisional.
2. It **may not contradict** a FROZEN artifact. Where it does, the FROZEN artifact governs and the
   contradiction is a defect to be reported — as exercised by Decisions B and C of this ADR.
3. It **should be promoted to FROZEN** once its subject matter has been exercised by implementation
   and found stable.
4. Downstream artifacts must cite the exact version they were derived from.

## Current classification

| Document | Status |
|---|---|
| Phase 3 Decision OS Architecture v2.0 | FROZEN |
| Frontend Domain Model v1.0 | FROZEN |
| Foundation Consolidation v1.0 | FROZEN |
| Decision Intelligence Consolidation v1.0 | FROZEN |
| Production Decision OS PRD v1.0 | FROZEN |
| Seven workspace design specs v1.0 | FROZEN |
| Phase 4 UX Blueprint v1.1 | FROZEN |
| **Phase 5 Wireframes v1.1** | **IMPLEMENTATION READY** |
| Phase 6 Design System v1.0 | FROZEN |
| **Phase 7 Technical Architecture v1.1** | **IMPLEMENTATION READY** |
| **Phase 8 Engineering Plan v1.1 RECONCILED** | **IMPLEMENTATION READY** |
| **Phase 9 Implementation v1.1 RESET** | **IMPLEMENTATION READY — NOT STARTED** |
| Phase 8 v1.0 · Phase 9 v1.0 | SUPERSEDED by this ADR |
| Frontend Decision Registry v0.1 | SUPERSEDED |

---

# 7. Unresolved — outside this ADR

These block implementation and are **not** resolved here.

| # | Blocker | Owner | Blocks |
|---|---|---|---|
| U-1 | **Design Token values do not exist.** Phase 6 defers to a "Design Token registry"; Phase 7 §10 defers to Phase 6. No hex, px, rem, font family, breakpoint, contrast ratio, motion duration, or z-index exists in the corpus. Phase 7 §10 forbids hardcoded HEX while providing no alternative | Design | All UI work (Stage 3+) |
| U-2 | **Backend API covers ~1 of 8 business domains.** `/api/v1` exposes 33 read-only GET endpoints (health, status, scheduler, metrics, config, platform, watchlists, snapshots, reports, candidates). Absent: Portfolio, Decision, Ticker detail, Market, Search, Settings | Backend | Workspaces 5–10 |
| U-3 | **Zero write endpoints.** Phase 7 §8 names `submitDecisionResponse()`; Phase 5 §10 specifies a Save Action; empty states offer Create/Import | Backend | Decision Center, Settings, Watchlist writes |
| U-4 | **No identity layer.** `AUTH_MODE` defaults `off` with static role tokens; no user concept. The domain model is built on USER and personalized DEC/PORT/WATCH. Phase 7 §17 mandates a `login` E2E journey | Backend | Auth, personalization, Settings, Portfolio |
| U-5 | **Server State library not selected.** Decision B mandates the layer; no library is named | Frontend | Data layer (Stage 2+) |
| U-6 | **Ticker route model** — Decision D, above | Architecture | Ticker (Stage 6) |
| U-7 | **PWA posture contradicted.** PRD §11 "Mobile-first PWA" vs Phase 6 P6-38 "Desktop is the primary analytical environment" vs Phase 7 §3 SPA. No service worker, manifest, offline model, or caching strategy anywhere | Product | Non-functional acceptance |
| U-8 | **Deployment and environment strategy absent.** Phase 7 v1.0 outline §57–58 were dropped rather than answered. No build target, hosting model, env config, or relationship to the existing gunicorn/systemd release pipeline | Frontend + Ops | Stage 1 CI, Stage 11 release |
| U-9 | **Existing Flask UI unaccounted for.** Seven Jinja templates plus `shell.css`/`shell.js` serve on :5001. No migration, coexistence, or retirement plan | Product + Ops | Release cutover |
| U-10 | **Phase 4 v1.1 freeze status is self-contradictory.** Front matter says `DRAFT FOR FREEZE` / `Pending Final Approval`; §21 and the final page say `FROZEN` | Architecture | Governance clarity |
| U-11 | **Terminology drift.** Phase 4 Appendix A says "Candidate Queue / Candidate Detail"; Phase 5 v1.1 and the Decision Center Design Spec say "Recommendation Queue / Recommendation Detail." NP-09 forbids alternation | Architecture | Decision Center (Stage 8) |

---

# 8. Consequences of this ADR

## Accepted

- Phase 8 v1.0 and Phase 9 v1.0 are SUPERSEDED.
- `PHASE_8_FRONTEND_ENGINEERING_PLAN_v1.1_RECONCILED.md` and
  `PHASE_9_FRONTEND_IMPLEMENTATION_v1.1_RESET.md` become the operative plan and execution record.
- Phase 7 v1.1 §5 and §7 are amended by Decisions B and C. Corrections should be folded into
  Phase 7 at its next revision; until then, this ADR governs.
- The false completion state recorded in Phase 9 v1.0 is withdrawn.

## Rejected

- Retaining Next.js. It has no owning decision document.
- Dropping Resource State. It would break three frozen guarantees.
- Resolving the Ticker route model without owner approval.

## Follow-up ADRs required

| ADR | Subject | Trigger |
|---|---|---|
| ADR-002 | Ticker route model | Owner selects from Decision D options |
| ADR-003 | Server State library | Before Stage 2 |
| ADR-004 | PWA posture — reconcile PRD §11 with Phase 6 P6-38 and Phase 7 §3 | Before Stage 11 |
| ADR-005 | Deployment and environment strategy | Before Stage 1 CI completes |
| ADR-006 | Legacy Flask UI disposition | Before Stage 11 |
| ADR-007 | Candidate vs Recommendation terminology | Before Stage 8 |

---

# 9. Compliance

Implementation is compliant with this ADR when:

- [ ] No Next.js dependency exists in the frontend
- [ ] The stack matches §2 exactly
- [ ] All seven state layers of §3 are implemented, with Resource State owned by the URL/Router
- [ ] Workspace filters are Workspace State, not Page State
- [ ] Server State never appears in a URL
- [ ] Domain imports satisfy the §4 edge list, enforced by lint
- [ ] No implementation exists for Ticker tabs beyond the five currently-permitted values, pending ADR-002
- [ ] Every artifact cites the exact version it derives from

---

**Status:** **APPROVED** — 2026-08-07, by Owner.

Decisions A, B, C and E are **binding** as of this approval. Phase 8 v1.1 and Phase 9 v1.1 are the
operative plan and execution record. Phase 8 v1.0 and Phase 9 v1.0 are SUPERSEDED.

Standing constraints that survive approval:

- **No implementation shall begin on Ticker until ADR-002 is accepted** (Decision D remains open).
- **No implementation shall begin on Workstream B tasks B2, B6 until ADR-003 is accepted**
  (Server State library unselected).
- **Workstream C shall not begin until blocker U-1 is resolved** (Design Token values do not exist).
- Approval of this ADR does not authorize coding. Execution authorization is granted per
  workstream, against `PHASE_9_FRONTEND_IMPLEMENTATION_v1.1_RESET.md`.

---

# 10. Approval Record

| Field | Value |
|---|---|
| Decision | ADR-001 accepted in full |
| Scope accepted | A (framework) · B (state ownership) · C (domain dependency) · E (governance status) |
| Scope deferred | D (Ticker route model) → ADR-002 |
| Approved by | Owner |
| Date | 2026-08-07 |
| Effect | Phase 8 v1.0, Phase 9 v1.0 → SUPERSEDED. Phase 7 v1.1 §5 and §7 amended by Decisions C and B |
| Coding authorized | **No** — documentation state only |

# End of ADR
