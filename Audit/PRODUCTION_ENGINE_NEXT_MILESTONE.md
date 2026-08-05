# Production Engine — Next Milestone Transition Report

**Date:** 2026-07-29
**Purpose:** transfer execution from the completed ADR-AF-002 (Agent Firm Tier 1 Context Ownership)
workstream back to the standing Production Engine roadmap, and assess readiness to begin the next
milestone in that roadmap's already-agreed sequence.

---

## Completed Milestone

**ADR-AF-002 — Agent Firm Tier 1 Context Ownership: COMPLETE.**

Every Tier 1 context object is assembled once by Production Engine (`engine/agent_firm_context.py`)
and attached to `SignalCandidate` at all five live construction sites before Agent Firm evaluation;
every specialist consumes only typed candidate fields; the legacy raw-SQL context path is fully
retired. Delivered across WP1 (Foundation) → WP2 (Producer Migration) → WP3 (Consumption Migration)
→ WP4 (Integration Completion), independently re-audited, and validated under 8 simulated production
scenarios. Full detail: `Audit/ADR-AF-002_CLOSURE_REPORT.md`. Handoff confirmation:
`Audit/ADR-AF-002_HANDOFF_CHECKLIST.md`.

This closure did not touch `research/`, change any schema, or expand Agent Firm's capabilities beyond
what ADR-AF-002 itself specified.

---

## How This Milestone Fits the Standing Roadmap

ADR-AF-002 was not itself a line item in the pre-existing Production Engine sequencing. The last
whole-repository Production Engine certification before ADR-AF-002 began
(`Audit/PRODUCTION_ENGINE_RELEASE_CERTIFICATION.md`, upgraded to unconditional **GO** in
`Audit/FINAL_RELEASE_DECISION.md`, both 2026-07-28) already named the standing next-milestone
sequence: **Operations Dashboard / Job History**, then **Agent Firm repository split** — gated on
first tracking/addressing 11 required follow-up items (`Audit/RELEASE_CONDITIONS_MATRIX.md`). ADR-AF-002's
own WP1-4 sequence ran instead of that follow-up work, as a separate, subsequently-prioritized
initiative (confirmed: `scheduler/jobs.py`, `monitor.py`, and `scheduler/scanner.py` all already
carried the RC1-certified Telegram-reporting features before WP1-4 began touching them for Tier 1
context wiring — the two workstreams are independent, not sequential dependencies of each other).

**This transition report's job is therefore to resume the roadmap exactly where it was left on
2026-07-28**, not to re-derive a new sequence — the next milestone was already decided; what needs
verifying is whether its entry criteria are now met.

---

## Outstanding Maintenance Items (not blockers)

Carried from `Audit/ADR-AF-002_HANDOFF_CHECKLIST.md`, restated here for completeness — none of these
block ADR-AF-002's own closure, and none are Production Engine roadmap blockers either, but they are
maintenance debt an incoming engineer should know about:

| Item | Category |
|---|---|
| `reset_market_ctx()` compatibility shim (blocked by 2 dev scripts) | Small, mechanical, low-priority |
| One stale test docstring (`tests/test_agent_firm_context_wiring.py` line 9) | Comment-only |
| Batch-context cache hit/miss instrumentation (proposed, not built) | Future observability enhancement |
| Fail-soft activation structured logging (proposed, not built) | Future observability enhancement |
| `docs/agent_firm/*.md` planning-corpus reconciliation (23 files) | Large, explicitly deferred documentation debt |

---

## Next Milestone

# Operations Dashboard / Job History

Per the standing sequence in `Audit/PRODUCTION_ENGINE_RELEASE_CERTIFICATION.md` §"Recommended Next
Phase" and reaffirmed in `Audit/FINAL_RELEASE_DECISION.md` §"Exact Rationale for GO" — this is the
next executable milestone by dependency order, **not** a new milestone this report is proposing.
The milestone after this one (unchanged) is the **Agent Firm repository split**, for which
`docs/agent_firm/AGENT_FIRM_IMPLEMENTATION_ROADMAP.md`'s AF-1 through AF-7 sequence is the existing
detailed execution plan — not yet relevant until Operations Dashboard / Job History is itself
complete.

---

## Entry Criteria

Per the standing sequencing's own explicit condition (`Audit/PRODUCTION_ENGINE_RELEASE_CERTIFICATION.md`
§"Conditions for full GO", item 3; `Audit/FINAL_RELEASE_DECISION.md` §"Required Follow-Up Actions"):
the 11 items in `Audit/RELEASE_CONDITIONS_MATRIX.md`'s required-follow-up list must be **tracked as
the next scheduled block of work, ahead of or alongside** this milestone.

**Verified this session, not assumed:** `git log` on every file the 11 follow-up items name
(`scripts/release.sh`, `scripts/cron_wrap.sh`, `auto_token.py`, `monitor.py`, `scheduler/__init__.py`,
`app.py`) shows **zero commits after 2026-07-28** touching any of them. The certification date itself
(2026-07-28) is the most recent commit on several of these files; nothing since. ADR-AF-002's WP1-4
commits touched `scheduler/jobs.py`/`monitor.py`/`scheduler/scanner.py` only for Tier 1 context
wiring, not for any of the 11 named items (confirmed by direct review across all four WP sessions —
none of them changed `validate_config()`, `start_scheduler()`'s job registration, `monitor.py`'s
SL/TP exception isolation, redaction coverage, `/health`, or either release script).

| Entry criterion | Status |
|---|---|
| RC-001 follow-up: harden `validate_config()` for `TELEGRAM_WEBHOOK_SECRET` (now confirmed safe to do, per `FINAL_RELEASE_DECISION.md`) | **Not done** — no commit found |
| Restructure `start_scheduler()`'s job registration for failure isolation | **Not done** |
| Cron dead-man's-switch for backup/restore-drill cadence | **Not done** (the restore-drill cron gap itself was flagged as needing a manual drill "this week" as of 2026-07-28 — no evidence of resolution) |
| Land `_write_token_atomic()` hardening (already written, uncommitted) | **Not done** — `auto_token.py`'s last commit (2026-07-28) is the reporting feature, not this hardening |
| `monitor.py` per-trade exception isolation + alert | **Not done** |
| Extend redaction to the Stockbit bearer JWT + fix truncate-before-redact ordering | **Not done** |
| `/health` scheduler-liveness check | **Not done** |
| `scripts/release.sh` `SHARED_PATHS` default fix | **Not done** — file unchanged since 2026-07-11 |
| Exercise `scripts/release.sh` end-to-end in CI | **Not done** |
| Redact `cron_wrap.sh`'s shell-based Telegram alert | **Not done** — file unchanged since 2026-07-10 |
| `validate_config()` DB_PATH-must-pre-exist contradiction — fix or explicit accept decision | **Not done / no explicit decision recorded** |

**None of these are Agent Firm/ADR-AF-002 items — they are pre-existing Production Engine debt,
untouched by any of the four work packages this closure concerns.** This report does not fix them
(that would be reopening/continuing a different, already-closed workstream, explicitly against this
task's own instruction) — it verifies their status, which is: outstanding.

---

## Exit Criteria (for the Operations Dashboard / Job History milestone itself, once started)

Not yet defined in detail anywhere in the repository (searched: no design doc, spec, or ADR for this
milestone was found under `docs/` or `Audit/` beyond the one-line mentions in the RC1 certification
trail). Recommended, consistent with this repository's own established pattern (a `docs/superpowers/specs/*-design.md`
+ `docs/superpowers/plans/*.md` pair precedes implementation for comparable prior work, e.g. the
2026-07-08 firm-provider-abstraction and 2026-06-30 forward-test-scheduler-wiring efforts): a design
document scoping exactly what "Operations Dashboard / Job History" means (a UI over the existing
`engine/agent_firm/analytics.py` + `provider_events`/`agent_decisions` data already wired into
`routes/backtest.py`? A new route? Which of the 9 metrics in
`Audit/AF2_POST_DEPLOYMENT_MONITORING_PLAN.md` does it need to surface, given that plan was written
after this milestone was originally sequenced and is now available input to it?) should be the first
deliverable of the milestone itself, not assumed here.

---

## Risks

1. **Entry-criteria gap (primary risk).** The 11 required follow-up items were supposed to be
   "tracked... ahead of or alongside" this milestone; verified zero progress on any of them. Starting
   Operations Dashboard/Job History work now would mean beginning a new milestone while a previously
   agreed precondition sits completely unaddressed — exactly the situation ADR-AF-002 itself
   demonstrated the cost of (WP3 "finished" migrating consumption while a real producer-side gap sat
   undetected for an entire work package, per the Closure Report's Defect #2).
2. **Undefined scope.** "Operations Dashboard / Job History" has no design document — starting
   implementation without one risks the same category of silent gap.
3. **RC-001 (Telegram webhook fail-open) is "verified safe today," not fixed.** `FINAL_RELEASE_DECISION.md`
   confirmed the secret is currently set in production, but `validate_config()` still doesn't enforce
   it — a future configuration change (e.g., during dashboard/monitoring work touching the same
   routes) could silently reintroduce the exposure with no automated check to catch it.
4. **Restore-drill cron gap** — flagged as needing a manual drill "this week" as of 2026-07-28; no
   evidence of resolution found. Backups remain current, so this is not an active data-loss risk, but
   it is an unverified recovery capability.

---

## Estimated Implementation Order

1. **Resolve or explicitly re-scope the 11 entry-criteria items** (or obtain an explicit owner
   decision to proceed without full resolution, analogous to how Owner Decision Package items were
   handled in the 2026-07-28 certification) — this is not new work invented by this report, it is
   already-agreed prerequisite work that has simply not started.
2. **Write the Operations Dashboard / Job History design doc**, scoping it against the monitoring
   plan this closure already produced (`Audit/AF2_POST_DEPLOYMENT_MONITORING_PLAN.md`) so the
   dashboard's first version doesn't have to be redesigned once ADR-AF-002's own metrics need a home.
3. **Implement Operations Dashboard / Job History** per that design doc.
4. **Begin Agent Firm repository split**, using `docs/agent_firm/AGENT_FIRM_IMPLEMENTATION_ROADMAP.md`'s
   existing AF-1 through AF-7 sequence as the execution plan.

---

## Summary

- **Current milestone: COMPLETE**
- **Next milestone: Operations Dashboard / Job History**
- **Ready to begin: NO** — the milestone's own explicitly-agreed entry criteria (tracking/addressing
  11 pre-existing Production Engine follow-up items) have zero verified progress. This is a finding,
  not a recommendation to do that work now — per this task's own instruction not to continue any
  workstream the roadmap doesn't explicitly require, resolving the 11 items is a decision for
  whoever owns the Production Engine roadmap next, not an action this transition report takes
  unilaterally.
