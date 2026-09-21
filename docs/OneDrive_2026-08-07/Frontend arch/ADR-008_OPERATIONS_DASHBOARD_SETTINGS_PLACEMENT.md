# ADR-008 — Operations Dashboard Information-Ownership Placement

| Item | Value |
|---|---|
| ADR ID | FRONTEND-ADR-008 |
| Title | Operations Dashboard placement — scheduler/job-history and system-status information belongs to the Settings workspace, not a new primary workspace |
| Status | **APPROVED — 2026-08-20, by Owner.** See "Ratification Note" after §17 below: implementation (commit `67537e6d475f229575c9668c534f95339ff3b3bb`) landed before formal ratification; verified on ratification to match this decision unchanged. |
| Date | 2026-08-20 |
| Depends On | `PHASE_4_UX_BLUEPRINT_v1.1.md` §P4-02 (FROZEN), §P4-16.14 (FROZEN) · `SETTINGS_DESIGN_SPEC_v1.0_FROZEN.md` (FROZEN) · `FRONTEND_ARCHITECTURE_RECONCILIATION_ADR_001.md` (APPROVED) |
| Authority | P4-16 §14 Change Control names "workspace additions," "navigation hierarchy changes," "context ownership changes," and "state ownership changes" as requiring an ADR. This document is that ADR for the Operations Dashboard's placement. |
| Closes | The open question raised but not answered in `ADR-006_LEGACY_UI_DISPOSITION.md` §7 Q-2 ("does `/internal/operations` set a usable precedent for how other in-progress workspaces should be exposed?") — answered here: no, it does not set a precedent; it was a temporary, ungoverned placement, now resolved by assigning the information to its correct owner. |
| Freeze effect | On approval, the ownership assignment in §8 (Decision) becomes **FROZEN** for Operations/scheduler/job-history information. It does not freeze anything about Settings' remaining unbuilt regions, and does not reopen or amend the seven-workspace list itself. |
| ADR number note | ADR-007 is already reserved (`FRONTEND_ARCHITECTURE_RECONCILIATION_ADR_001.md` line 387, `PHASE_9_FRONTEND_IMPLEMENTATION_v1.1_RESET.md` line 239/382) for the unrelated Candidate-vs-Recommendation terminology decision (U-11). This document is numbered ADR-008 to avoid collision with that reservation. |

---

# 1. Context

The Operations Dashboard (`frontend/src/domains/operations/`) — scheduler liveness, job execution
history, per-job drill-down — is fully implemented, tested, and verified against live production
data (`docs/superpowers/specs/2026-08-15-operations-dashboard-job-history-design.md`, its own
design brief, Status: Draft, never formally approved as a design document, but its Job History half
was built and works). It is mounted today as a standalone route, `/internal/operations`
(`frontend/src/app/router/app-router.tsx`), reachable only by direct URL or bookmark — it appears in
neither Zone A (sidebar, `workspaces.ts`) nor Zone B (header) navigation.

This placement was never governed by an ADR. It was a pragmatic engineering choice made under
`P4-16` §14's constraint that workspace additions and navigation-hierarchy changes require an ADR,
by a session that had no ADR to invoke and needed the page reachable by *some* URL. Its own
docstring is candid about this: it was built to avoid a *different*, incorrect placement (an early
design brief proposed reusing `domains/decision/` for Operations-adjacent content, which conflicted
with `workspaces.ts`'s actual "Decide" semantics), not chosen because a standalone route is an
architecturally sanctioned category. No frozen document in this corpus defines an "internal
route" or "utility route" tier as a legitimate alternative to the seven workspaces.

The prior session's diagnostic report (this ADR's immediate predecessor artifact, produced
2026-08-20) evaluated two ways to resolve this permanently — an eighth primary workspace, or folding
the information into an existing one — and recommended the latter, specifically into Settings, on
the strength of `SETTINGS_DESIGN_SPEC_v1.0_FROZEN.md`'s pre-existing, already-frozen scope. This ADR
formalizes that recommendation into a decision record, as P4-16 §14 requires before any
implementation proceeds.

---

# 2. Problem

`/internal/operations` is real, live, tested, operationally useful information — and undiscoverable.
A user of the Decision Operating System has no navigable path to "is the scheduler alive, did
today's jobs run" short of already knowing the URL. This is not a UI bug to patch; it is an
information-architecture gap. IA-01 ("every information entity shall have exactly one owner")
implies every information entity has *an* owner — Operations/scheduler/job-history information
currently has none, in the frozen sense: a standalone route is not a workspace and therefore cannot
be an IA-01 owner as the term is used throughout `PHASE_4_UX_BLUEPRINT_v1.1.md`.

The problem is narrowly: **which of the seven frozen workspaces — or a new eighth — owns
scheduler/job-history and system-status information, and what does that ownership assignment
require of navigation, routing, and state?**

---

# 3. Architectural Constraints

These are given, not decided here:

- **P4-02 §3**: "The Decision Operating System contains seven primary workspaces" (Settings,
  Search, Market, Watchlist, Ticker, Decision Center, Portfolio), "these workspaces exist at the
  same hierarchical level... no workspace is subordinate to another."
- **P4-02 §4**: Workspace responsibilities "are mutually exclusive" (Settings = Configuration,
  Search = Discovery, Market = Market Intelligence, Watchlist = Monitoring, Ticker = Security
  Analysis, Decision Center = Decision Synthesis, Portfolio = Portfolio Evaluation).
- **IA-01 (Single Ownership)**: "Every information entity shall have exactly one owner... No
  information may belong to multiple workspaces."
- **P4-16 §14 (Change Control)**: workspace additions, workspace removals, navigation-hierarchy
  changes, route changes, context-ownership changes, and state-ownership changes all require an
  ADR. Colors/typography/icons/spacing/copy/component-implementation-details do not.
- **`SETTINGS_DESIGN_SPEC_v1.0_FROZEN.md`** already declares, as frozen scope, regions **"System
  Information"** and **"Support & Diagnostics"**, business outcome **"Review application and system
  status,"** scenario **"Review System Information,"** and persona **"System Administrator
  (Future)."**
- This ADR may not reopen, amend, or narrow the seven-workspace list itself (P4-02 §3) — it may
  only assign one already-unowned information entity to one of the seven.

---

# 4. Options Considered

## Option A — Operations as an eighth primary workspace

Register `operations` as a full sibling of the existing seven in `workspaces.ts`, with its own
sidebar entry, its own `ROUTE_PATHS` slot, its own responsibility verb.

- **Governance**: Requires an ADR under P4-16 §14 (workspace addition) — this document could serve
  that purpose for Option A, but does not, per §8 below.
- **Semantic fit**: Poor. P4-02 §4's seven responsibilities (Configuration, Discovery, Market
  Intelligence, Monitoring, Security Analysis, Decision Synthesis, Portfolio Evaluation) are all
  analytical or trading verbs. "Is the scheduler alive and did today's jobs run" is an operational/
  engineering-health responsibility with no member of that set to belong to on its own terms —
  it would require inventing an eighth responsibility category (e.g. "Operational Health"), which
  P4-02 §4 does not currently contain and this ADR has no authority to add.
- **Cost**: Touches the frozen `workspaces.ts` data file (`WorkspaceId`, `ROUTE_PATHS`, `WORKSPACES`,
  `WORKSPACE_GROUPS`), `global-header.tsx`/`global-sidebar.tsx`'s enumerated content lists, the
  `eslint` architecture-boundary `WORKSPACES` array and `PERMITTED_WORKSPACE_EDGES` map, and every
  test that enumerates the seven workspaces (`workspaces.test.ts`, `app-router.test.tsx`).

## Option B — Operations information owned by the existing Settings workspace

Assign scheduler/job-history/system-status information to Settings, under its already-frozen
"System Information" / "Support & Diagnostics" regions. No new workspace; no change to the
seven-workspace list; no change to P4-02 §4's responsibility set.

- **Governance**: Still requires an ADR under P4-16 §14 — not because it adds a workspace, but
  because it is a **context-ownership change** and a **state-ownership change**: it assigns a
  previously-unowned information entity (scheduler/job-history) to a workspace's owned state for
  the first time. This document serves that purpose.
- **Semantic fit**: Strong, and — critically — not invented for this decision. `SETTINGS_DESIGN_
  SPEC_v1.0_FROZEN.md` already names "System Information," "Support & Diagnostics," "Review
  application and system status," and a "System Administrator (Future)" persona as in-scope,
  independently of and prior to this ADR. Assigning Operations information here instantiates
  already-frozen scope; it does not expand Settings' responsibility (still "Configuration" under
  P4-02 §4 — system-status *visibility* is a natural instrument of configuring/administering the
  system, not a new responsibility category).
- **Cost**: Smaller. No change to `workspaces.ts`'s schema, `WorkspaceId` union, or
  `WORKSPACE_GROUPS` sidebar structure. No new eslint `WORKSPACES` entry. The existing `/settings`
  route (currently `WorkspaceShellPage`, unbuilt) gains a real region; `/internal/operations` is
  retired as a route once Settings' Support & Diagnostics region supersedes it.
- **Risk**: Settings' frozen widget list (Profile Summary, Account Actions, Authentication
  Settings, Privacy Settings, Notification Channels, Appearance Controls, Localization Controls,
  Workspace Preferences, System Information, Configuration Metadata, Support & Diagnostics) does
  not currently enumerate a sortable job table or a per-job drill-down detail panel as named
  widgets. Instantiating Operations' existing UI under "System Information" / "Support &
  Diagnostics" is a reasonable reading of those two named-but-unspecified regions, not a verbatim
  match to an existing widget spec line item — flagged honestly in §15 Risks, not glossed over.

---

# 5. Decision

**Operations Dashboard is not a new primary workspace. Its scheduler/job-history and system-status
functionality belongs under the existing Settings workspace, as an instantiation of Settings'
already-frozen "System Information" and "Support & Diagnostics" regions.**

The seven-workspace model (P4-02 §3) is preserved unchanged. No eighth workspace is authorized by
this document, now or by implication for any future information entity — this decision is scoped
to Operations/scheduler/job-history information specifically, not a general precedent that
"anything unowned defaults to Settings."

---

# 6. Rationale

1. **IA-01 is satisfied, not bypassed.** Scheduler/job-history/system-status information gets
   exactly one owner — Settings — for the first time. It previously had no IA-01-conformant owner
   (a standalone route is not a workspace). This ADR does not create a competing responsibility:
   Settings' P4-02 §4 responsibility remains "Configuration," and system-status visibility is
   read-only administrative information consistent with that responsibility, not a rival
   "Operational Health" workspace responsibility competing with Decision Center's "Decision
   Synthesis" or any other of the seven.
2. **No invented scope.** Unlike Option A, which would require adding a responsibility category
   P4-02 §4 does not contain, Option B assigns Operations information to regions
   (`SETTINGS_DESIGN_SPEC_v1.0_FROZEN.md`'s "System Information" / "Support & Diagnostics") that
   were already frozen before this ADR existed. The ADR's job is to ratify an instantiation of
   existing frozen scope, not to expand it.
3. **Smaller, reversible footprint.** Option B touches no frozen data-schema file (`workspaces.ts`,
   the eslint `WORKSPACES` array). If this decision is later superseded, undoing it means moving a
   folder and a route, not restructuring the seven-workspace enumeration and every test that
   depends on it.
4. **Resolves ADR-006 §7 Q-2 honestly.** The standalone-route pattern is not endorsed as a
   reusable precedent for other in-progress workspaces (Portfolio, Watchlist, etc.) — those remain
   governed by their own frozen design specs and Workstream D sequencing, not by this ADR.

---

# 7. Information Ownership

Per IA-01, this ADR assigns:

| Information entity | Prior owner | New owner (on approval) |
|---|---|---|
| Scheduler state (running/paused/stopped, job count, timezone) | None (standalone route, not a workspace) | Settings — System Information |
| Job execution history (per-job runs, status, duration, errors) | None | Settings — Support & Diagnostics |
| Per-job drill-down detail | None | Settings — Support & Diagnostics |

No information owned by any other workspace (Decision Center's registry-admission summary, Market,
Watchlist, Ticker, Portfolio, Search) changes owner. No information currently owned by Settings'
other already-frozen regions (Account, Security, Notifications, Appearance, Workspace Preferences,
Support) changes owner.

---

# 8. Navigation Implications

- Settings gains its first real navigable content (it is currently an unbuilt `WorkspaceShellPage`
  placeholder, same as five of the other six workspaces).
- `/internal/operations` is retired as a *reachable concept* once Settings' Support & Diagnostics
  region supersedes it — its content does not disappear, it relocates under Settings' existing
  sidebar entry. (Whether the literal URL redirects or 404s is an implementation detail for the
  follow-up task, not decided here.)
- Zone A (sidebar) and Zone B (header) enumerated content lists are **unchanged in membership** —
  Settings was already one of the seven sidebar entries; nothing is added to or removed from either
  frozen list.
- No change to any other workspace's navigation entry, order, or grouping
  (`WORKSPACE_GROUPS` in `workspaces.ts` stays as-is).

---

# 9. Route Implications

- `ROUTE_PATHS.settings` (`/settings`) already exists and already resolves to the Settings
  workspace route in `app-router.tsx` — no new canonical route is created.
- `/internal/operations` (the standalone route) is retired once the Settings implementation ships;
  this ADR does not itself remove the route, only authorizes its eventual removal as part of the
  follow-up implementation task.
- No change to `ROUTE_PATHS.home` (`/`), `ROUTE_PATHS.portfolio` (`/portfolio`), or any Flask-served
  legacy route — see §19.

---

# 10. State/Data Ownership Implications

- Backend data sources are unchanged: `GET /api/v1/scheduler`, `GET /api/v1/scheduler/jobs`,
  `GET /api/v1/scheduler/jobs/<job_id>`, `GET /api/v1/status/jobs/history` remain the same
  already-frozen v1 endpoints Operations already reads. No backend route, schema, or classification
  changes as a result of this ADR.
- Frontend-side, per ADR-003's Server State architecture and the `eslint` boundary rules, moving
  `domains/operations/hooks.ts` and its API calls under `domains/settings/` does not cross a
  Server State boundary — neither location uses `@tanstack/react-query` today (ADR-003 is still
  PROPOSED, not installed), so no Repository-seam relocation is implied.
- Cross-workspace import rules (`ADR-001` §4, `tools/eslint/architecture-boundaries.js`
  `PERMITTED_WORKSPACE_EDGES`) are unaffected: Settings has no permitted outbound workspace edges
  today and none are introduced by this decision.

---

# 11. Implementation Consequences

(Described here for completeness per the requested ADR outline; **not performed by this
document** — see "Implementation After Approval" below.)

- `frontend/src/domains/operations/*` content is relocated under `frontend/src/domains/settings/`.
- The Settings workspace's route in `app-router.tsx` renders real content (a "System Information /
  Support & Diagnostics" region) instead of the generic `WorkspaceShellPage`, following the same
  override pattern Decision Center already established for its Executive Summary region.
- The standalone `/internal/operations` route is removed once superseded.
- Existing Operations tests (`operations-page.test.tsx`, `hooks.ts` coverage) move and are updated
  to assert against the new location/heading, not rewritten in substance.

---

# 12. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Settings' frozen widget list doesn't name "sortable job table" or "drill-down detail panel" verbatim (§4 Option B cost) | Implemented as an instantiation of "Support & Diagnostics," which is a named-but-unspecified region — consistent with how "System Information" already leaves widget-level detail open. If the owner judges this a stretch beyond the frozen spec's intent, that is grounds to reject this ADR, not to silently narrow scope during implementation. |
| Settings workspace itself is still an unbuilt placeholder (same Workstream D gap as five other workspaces) | This ADR authorizes the ownership assignment only. It does not schedule or guarantee when Settings' implementation happens — that remains ordinary Workstream D sequencing, unblocked by (but not accelerated by) this decision. |
| Retiring `/internal/operations` could break an existing bookmark | Acceptable and already flagged as an explicit, non-hidden consequence (§9) — the information is not deleted, only relocated; this is the same category of change ADR-006 already anticipates for legacy-page retirement, applied here to an internal, unadvertised route rather than a public one. |
| Scope creep during implementation (rebuilding Settings' other regions while "in there") | Explicitly excluded — see §13 Non-Goals. |

---

# 13. Non-Goals

This ADR does **not** authorize:

- An eighth primary workspace, now or as a future default for other unowned information.
- Any change to the seven-workspace list in `workspaces.ts` (`P4-02 §3`).
- Any change to `/` or `/portfolio`, Flask legacy routing, or `ADR-006`'s undecided options.
- Any change to Decision Center (`domains/decision/`) or its Executive Summary region.
- Any change to `engine/registry_loader.py`, `/api/v1/registry/status`, or any production-admission
  logic. Registry state remains exactly as-is: **0 approved, 1 shadow (NR7_BULL), no strategy
  eligible for live capital.**
- Implementation of any of the other five still-placeholder workspaces (Watchlist, Ticker, Market,
  Search, Portfolio) beyond Settings.
- A redesign of the Operations UI. The existing scheduler banner, job table, and detail panel move
  as-is; visual/interaction changes beyond what relocation requires are out of scope.
- Any write/control capability (pause/resume/trigger a job) — Operations remains read-only, per its
  original design brief's own scope line, unchanged by this ADR.

---

# 14. Compatibility / Migration Considerations

- No backend contract changes — the same v1 endpoints, same auth classification (`VIEWER`).
- No data migration — nothing is persisted client-side that needs to move.
- The relocation is additive-then-subtractive: Settings' region ships and is verified before
  `/internal/operations` is removed, so there is no window where the information is unreachable
  from both locations at once (ordinary safe-migration sequencing, not a new rule this ADR invents).
- No change to `AUTH_MODE`, route classification conventions, or any test outside the frontend
  route/workspace test files named in §11.

---

# 15. Verification Requirements

Before this ADR's decision is considered implemented (not verified here — for the follow-up task):

1. Settings workspace route renders real System Information / Support & Diagnostics content,
   sourced from the same live `/api/v1/scheduler*` and `/api/v1/status/jobs/*` endpoints Operations
   already used.
2. `/internal/operations` either redirects to the new location or is removed, not left as a second,
   diverging copy (would violate IA-01's "no information may belong to multiple workspaces" if both
   stayed live simultaneously).
3. `frontend/tools/eslint/architecture-boundaries.js` and its test
   (`architecture-boundaries.test.ts`) still pass unmodified in structure — this decision does not
   require touching `WORKSPACES` or `PERMITTED_WORKSPACE_EDGES`.
4. `workspaces.test.ts` / `app-router.test.tsx` continue to assert exactly seven workspaces.
5. Full frontend suite (vitest, lint, typecheck, build) and the relevant backend suite remain green,
   matching the verification standard already established for the Decision Center milestone.
6. Registry admission state unchanged: `GET /api/v1/registry/status` still reports 0 approved / 1
   shadow (NR7_BULL) after this work — a regression check, not a new capability.

---

# 16. Relationship to ADR-006

**This ADR does not modify, resolve, or depend on ADR-006 being decided.** ADR-006 governs the
retirement path for the legacy Flask `/` and `/portfolio` Jinja templates — a disjoint concern from
Operations' placement. The only connection is textual: ADR-006 §7 Q-2 asked whether
`/internal/operations`'s standalone-route pattern should generalize as a precedent for other
in-progress workspaces. This ADR answers that question **no** — the standalone route was a
temporary, ungoverned placement now given a real IA-01 owner, not a pattern to repeat. ADR-006
remains **PROPOSED**, exactly as it was before this document, with all three of its options still
open and undecided.

---

# 17. Explicit Approval Requirement

**This ADR requires Tjie's explicit approval before any implementation step in §11 or
"Implementation After Approval" below is performed.** Per `P4-16` §16 Governance Workflow
(`Proposal → Architecture Review → ADR → Approval → Implementation → Verification → Release`), this
document is the ADR stage.

---

# 18. Ratification Note (2026-08-20)

**Approved by Tjie, 2026-08-20**, as part of Production OS Slice 1 (governance cleanup).

Recorded honestly, out of the §16/§17 workflow's normal sequence: the §11 implementation steps
were already carried out and committed (`67537e6d475f229575c9668c534f95339ff3b3bb`) **before** this
ADR was formally approved — the decision this document records was correct and the code already
matches it, but the paperwork trailed the implementation rather than gating it. On ratification,
the implementation was re-verified against this ADR's own decision and requirements:

- `frontend/src/domains/operations/` no longer exists as a separate directory; its former contents
  (`hooks.ts`, `scheduler-banner.tsx`, `job-table.tsx`, `job-detail-panel.tsx`, `status-badge.tsx`,
  `format.ts`, and their `.module.css` files) live under `frontend/src/domains/settings/`, matching
  §7's ownership assignment and §11's relocation plan.
- `frontend/src/app/router/app-router.tsx` has no `/internal/operations` route; `ROUTE_PATHS.settings`
  renders `SettingsPage`, a real implementation (not the generic `WorkspaceShellPage`), matching §9.
- `frontend/src/domains/settings/settings-page.tsx`'s own docstring cites this ADR by file path and
  restates §5's decision and §7's information-ownership split (scheduler state → System Information,
  job history/drill-down → Support & Diagnostics) — the code is self-documenting against this ADR.
- No change to any other workspace, to `workspaces.ts`'s seven-workspace list, to the eslint
  architecture-boundary `WORKSPACES`/`PERMITTED_WORKSPACE_EDGES` configuration, or to registry
  admission state (`GET /api/v1/registry/status`: 0 approved, 1 shadow — unaffected, as §13 requires).

This note ratifies what was already built; it does not authorize any new implementation step, and
§13's Non-Goals remain in force unchanged.

---

**Status: APPROVED — 2026-08-20, by Owner.**

# End of ADR

---

# Implementation After Approval

Listed for planning purposes only. **None of these steps have been performed.** They would follow,
in this order, only after explicit approval of §5 above:

1. Create `frontend/src/domains/settings/` content (currently `.gitkeep` only): a Settings page
   component analogous to `decision-page.tsx`'s role for Decision Center, with a "System
   Information" and a "Support & Diagnostics" region.
2. Move `frontend/src/domains/operations/{hooks.ts,format.ts,scheduler-banner.tsx,status-badge.tsx,
   job-table.tsx,job-detail-panel.tsx}` and their `.module.css` files under
   `frontend/src/domains/settings/` (or a clearly-scoped subpath such as
   `domains/settings/diagnostics/`), preserving their existing tested behavior — TDD: move the
   existing tests first, watch them fail on the old import path, then move the implementation.
3. Update `frontend/src/app/router/app-router.tsx`: point `ROUTE_PATHS.settings` at the real
   Settings page instead of `WorkspaceRoute id="settings"`; remove (or redirect) the standalone
   `/internal/operations` route once the new location is verified live.
4. Update `frontend/src/domains/operations/operations-page.test.tsx` (moved/renamed) to assert the
   new heading/route context.
5. Confirm `frontend/tools/eslint/architecture-boundaries.js` needs **no edits** (Settings already
   has a `WORKSPACES` entry and an empty `PERMITTED_WORKSPACE_EDGES` list); run
   `architecture-boundaries.test.ts` to prove it.
6. Confirm `frontend/src/app/router/workspaces.test.ts` and `app-router.test.tsx` still pass
   unmodified (they assert the seven-workspace set generically, by iterating `WORKSPACES`).
7. Full verification pass: `npm run test`, `npm run lint`, `npm run typecheck`, `npm run build`,
   plus a live Playwright check against the running service (same standard used for the Decision
   Center milestone) confirming Settings renders real scheduler/job data and `/internal/operations`
   no longer strands the information.
8. Re-verify `GET /api/v1/registry/status` still reports 0 approved / 1 shadow (NR7_BULL) —
   regression check only, no logic in this area is touched.
9. Only after all of the above is green: present for review before any commit, per this session's
   standing instruction not to commit without being asked.
