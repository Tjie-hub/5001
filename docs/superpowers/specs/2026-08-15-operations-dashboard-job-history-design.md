# Operations Dashboard / Job History — Design

**Status:** Draft, pending approval (P1-8, `Audit/PRODUCTION_ENGINE_BACKLOG.md`). Scopes the
milestone named in `Audit/PRODUCTION_ENGINE_RELEASE_CERTIFICATION.md` §"Recommended Next Phase"
and reaffirmed in `Audit/PRODUCTION_ENGINE_NEXT_MILESTONE.md` — this document is that milestone's
own stated prerequisite ("a design document scoping exactly what 'Operations Dashboard / Job
History' means... should be the first deliverable of the milestone itself"), not a proposal to
change the milestone or its sequencing. Builds on the frozen API v1 layer
(`docs/superpowers/specs/2026-08-06-api-v1-foundation-design.md`) and the shipped frontend app
shell (Workstream B, commit `48b2d4a`) — no changes to either's conventions.

---

## 1. What this is, in one sentence

A read-only frontend page over API surface that (mostly) already exists: **"is the scheduler
alive and did today's jobs run"** (Job History) plus **"what is the Agent Firm doing and is it
healthy"** (Operations), replacing the current practice of checking this by hand via Telegram
messages and ad hoc SQL (`docs/OPERATIONS.md`'s existing `provider_events` query convention).

## 2. Data inventory — what exists vs. what's new

The milestone's own framing risked scope creep ("build a dashboard") without first checking what's
already there. It's mostly there:

| Panel | Backing endpoint(s) | Status |
|---|---|---|
| Scheduler state + job list | `GET /api/v1/scheduler`, `GET /api/v1/scheduler/jobs`, `GET /api/v1/scheduler/jobs/<id>` | **Exists** (Task 2B-1, frozen) |
| Job execution history / metrics rollup | `GET /api/v1/metrics/jobs`, `GET /api/v1/metrics/engine`, `GET /api/v1/metrics` | **Exists** (Task 2B-2, frozen) |
| Agent Firm decision cohorts, inter-provider agreement, recent decision log | `GET /api/agent/audit` (`cohorts`/`agreement`/`log`) | **Exists** (legacy, non-`/v1`-prefixed route, `routes/backtest.py:874`) |
| Agent Firm mode (off/shadow/enforce) | `GET /api/agent/status`, `POST /api/agent/config` | **Exists** |
| Health / scheduler liveness | `GET /health` | **Exists**, extended this session (P1-6) with a `scheduler` liveness field |
| Provider failover health (Z.ai/Claude circuit breaker, quota state) | `provider_events` table, queried by hand per `docs/OPERATIONS.md` | **No API** — new endpoint needed (§4) |
| AF2 metric §1 Candidate Throughput, §3 Decision Distribution, §6 Decision Latency, §7 Risk Veto Rate, §8 Paper-Trade Acceptance | Partially covered by `/api/agent/audit`'s `cohorts`/`agreement`; exact query-to-metric mapping not yet verified 1:1 | **Needs a mapping pass** (§4) — likely thin new queries in `engine/agent_firm/analytics.py`, not new infrastructure |
| AF2 metric §2 Context Completeness, §4 Specialist Failures | Not yet queried anywhere | **New query**, same file |
| AF2 metric §5 Cache Hit Rate, §9 Unexpected Fail-Soft Activations | Explicitly blocked on `Audit/PRODUCTION_ENGINE_BACKLOG.md` P2-4/P2-5 (instrumentation not yet built) | **Out of scope for v1** — see §6 |

This confirms `Audit/AF2_POST_DEPLOYMENT_MONITORING_PLAN.md`'s own framing: "no new dashboarding
technology... some [metrics] are one `SELECT` away today." The real net-new backend work is one
new endpoint (provider failover health) plus a handful of new query functions in
`engine/agent_firm/analytics.py` — not a new data layer.

## 3. Frontend scope

Two new pages under `frontend/src/domains/`, following the existing domain-per-feature layout
(`decision/`, `market/`, `portfolio/`, `search/`, `settings/`, `ticker/`, `watchlist/` —
`decision/` currently exists as an empty scaffold, `.gitkeep` only, ready for this):

- **`domains/decision/`** (reused, not renamed — the empty scaffold already matches this content):
  Agent Firm operational view. Panels, per `AF2_POST_DEPLOYMENT_MONITORING_PLAN.md`'s own
  "Recommended Dashboard Layout" (§198 of that doc), reused verbatim rather than re-designed:
  1. Top row: candidate throughput + decision distribution, by strategy, 30-day trend.
  2. Second row: context completeness + specialist failure rate, with alert thresholds as
     reference lines.
  3. Third row: decision latency + risk veto rate breakdown.
  4. Fourth row: paper-trade acceptance rate (auto-entry-relevant strategies only).
  5. Sidebar: provider failover health (new, §4) — circuit-breaker state per provider, current
     quota-window usage. Cache hit rate and fail-soft count sidebar entries are placeholders
     ("instrumentation pending — see backlog P2-4/P2-5") for v1, not omitted entirely, so the
     panel doesn't need restructuring once those land.
- **New `domains/operations/`**: Job History view. Scheduler state banner (running/paused/
  stopped, from `/api/v1/scheduler`), sortable job table (id, trigger, next run, last run,
  paused) from `/api/v1/scheduler/jobs`, row click → job detail
  (`/api/v1/scheduler/jobs/<id>`). This is the direct "Job History" half of the milestone name
  and has zero backend gaps — pure frontend work over already-frozen API.

Both consume `frontend/src/api/` (existing API client layer). Verified before writing this: every
`domains/*` folder (`decision/`, `market/`, `portfolio/`, `search/`, `settings/`, `ticker/`,
`watchlist/`) and `design-system/charts/` are empty scaffolds (`.gitkeep` only) — Workstream A/B
built the shell, routing, and architecture guards, not feature components. So a sortable table and
a trend-line chart primitive are genuinely new `design-system/` work, shared by this dashboard and
whichever domain builds a chart first (likely `market`/`ticker`, given their names) — worth
sequencing so this isn't the first page forced to invent that primitive ad hoc.

## 4. New backend work (the only net-new implementation)

1. **`GET /api/v1/operations/providers`** (or under `/api/v1/metrics/` — naming TBD at
   implementation time, not a design blocker): thin controller over a new
   `engine/agent_firm/providers` query reading `provider_events` — current circuit-breaker state
   per provider, last failover event, quota-window usage. Mirrors the `routes/v1/metrics.py`
   pattern (§8 of `2026-08-06-2b2-metrics-api-design.md`): read-only, `VIEWER`-classified, no new
   computation — just exposing what `provider_events` (per `engine/agent_firm/`'s existing
   `docs/OPERATIONS.md` documentation) already records on every router decision.
2. **AF2 metric query mapping**: a short audit task (not a design decision) — for each of §1, §3,
   §4, §6, §7, §8 in `AF2_POST_DEPLOYMENT_MONITORING_PLAN.md`, confirm whether `cohort_summary()`/
   `agent_agreement()`/`decision_log()` already compute it, or write the "one `SELECT` away" query
   that plan promised. Output is new functions in `engine/agent_firm/analytics.py`, exposed via
   the existing `/api/agent/audit` route (extend its response shape) rather than a parallel
   endpoint.

No new tables, no new write paths, no change to `AUTH_MODE`/route classification conventions
beyond classifying the one new route in `security/route_policy.py` (mandatory per
`tests/security/test_route_policy.py` — every registered route must be classified or CI fails).

## 5. Explicitly out of scope (v1)

- **Any write/control action** (pause/resume/trigger a job, change Agent Firm mode from this
  page) — `2026-08-06-2b1-scheduler-api-design.md` already drew this line for the scheduler API
  itself ("Pausing/resuming/triggering a job... not requested, this workstream is read-only") and
  this dashboard inherits it. `POST /api/agent/config` already exists for mode changes and stays
  a separate, deliberate action outside a monitoring view.
- **Cache hit rate (§5) and unexpected fail-soft count (§9)** — blocked on P2-4/P2-5
  instrumentation, tracked separately, not re-scoped here.
- **Real-time push/websocket updates** — polling on page load / manual refresh is sufficient for
  an operator-facing internal tool; no live-tailing requirement was stated anywhere in the
  milestone's source documents.
- **Research-pipeline visibility** (gatekeeper decisions, hypothesis registry, wf-refresh status)
  — a different governance domain (research/production separation, per `CLAUDE.md`), not part of
  "Operations Dashboard / Job History" as named in the certification trail this milestone traces
  to.
- **Historical retention/archival of dashboard data** — every panel reads live from existing
  tables (`agent_decisions`, `provider_events`, `job_execution_log`); no new retention policy is
  introduced by adding a read-only view over them.

## 6. Exit criteria for this milestone

1. `domains/operations/` (Job History) shipped and wired to the 3 existing scheduler endpoints.
2. `domains/decision/` (Agent Firm operations) shipped with the 4-row + sidebar layout from §3,
   the 6 already-backed AF2 metrics wired, and the 2 blocked metrics shown as explicit
   "instrumentation pending" placeholders rather than omitted.
3. New provider-failover endpoint (§4.1) shipped, tested, classified in `security/route_policy.py`.
4. AF2 metric query mapping (§4.2) complete — every one of the 6 in-scope metrics has a real,
   tested query behind it, not a stub.
5. Per this repo's testing convention: each piece lands with its own passing tests before the
   next starts, not one untested batch.

Per `Audit/PRODUCTION_ENGINE_NEXT_MILESTONE.md`'s own entry-criteria finding, this milestone's
*start* was gated on tracking the 11 RC follow-up items "ahead of or alongside" it — as of this
document's date, `Audit/PRODUCTION_ENGINE_BACKLOG.md` shows those resolved except the deliberately
deferred local-DB-repair item (P1-11) and the still-unwritten `frontend/README.md` update
(P2-11), neither of which blocks this milestone's own scope.
