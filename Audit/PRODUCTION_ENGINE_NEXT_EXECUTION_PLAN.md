# Production Engine — Next Execution Plan

**Date:** 2026-07-29
**Companion to:** `Audit/PRODUCTION_ENGINE_ROADMAP_RECONCILIATION.md` and
`Audit/PRODUCTION_ENGINE_BACKLOG.md`. This document does not implement anything — it is the
governance/planning synthesis this session was asked to produce.

---

## Current Repository State

- Branch `ops/hardening-2026-07-10`, 36 tracked-modified files (all from the ADR-AF-002 closure
  sequence), zero new modifications from this session (governance/planning only, no code touched).
- `CLAUDE.md` (the current status source, per this task's own instruction) accurately states
  ADR-AF-002 is complete as of its 2026-07-29 amendment.
- The working tree contains fully-implemented ADR-AF-001 and ADR-AF-002; a **decided-but-unimplemented**
  ADR-AF-003 (a live code defect — see below); a policy-only ADR-AF-004 already adhered to; RC1
  (Telegram Reporting v2) and the whole-repository "Final Gate" certification both merged and
  certified GO as of 2026-07-28 (assumed still true — this session found no evidence to the contrary,
  but also had no live-host access to re-verify operational state such as `EDGE_SCORE_MODE`'s or
  `TELEGRAM_WEBHOOK_SECRET`'s actual current production values).

---

## Closed Milestones

| Milestone | Evidence |
|---|---|
| ADR-AF-001 (Deterministic Ownership) | Implemented by construction in `engine/agent_firm_context.py`; confirmed by direct code read |
| ADR-AF-002 (Context Ownership) | WP1–WP4 + independent architecture audit + simulated production validation, all internally consistent; `Audit/ADR-AF-002_CLOSURE_REPORT.md` |
| ADR-AF-004 (Versioning Contract) | Policy decision, self-enforcing, already followed in practice by WP1-3's own additive-field approach |
| RC1 — Telegram Reporting v2 | Both certification conditions closed with evidence; CI-green on real GitHub Actions; features confirmed live in the current checkout |
| Production Engine Release Certification ("Final Gate") | 6 defects fixed and validated; sole blocking condition (webhook secret) confirmed live via SSH; upgraded to unconditional GO |
| `PLAN.md` — Agent Firm Optimization (2-stage evaluation) | Shipped 2026-06-05/09, historical, confirmed still the live architecture |

---

## Outstanding Mandatory Work

The single most important finding of this reconciliation: **ADR-AF-003 (Sizing Ownership) is
architecturally decided but not implemented, and describes a confirmed, currently-shipped defect** —
`scheduler/scanner.py` has two write sites for `r["agent_size_hint"]` (line 962, gated on
`EDGE_SCORE_MODE=enforce`; line 1038, unconditional whenever Agent Firm is active) with no precedence
rule between them. The second unconditionally overwrites the first, silently discarding a computed,
validated edge score in favor of the LLM's own hint or a blind, information-free default of `1.0`.
Verified this session by direct code read: `engine/position_sizing.py` does not exist, both write
sites are unchanged, and the Risk agent still does not emit `size_tier`. This predates ADR-AF-002
entirely and is untouched by any of WP1–WP4.

Alongside this, 11 Production Engine follow-up items from the 2026-07-28 Final Gate certification
remain unaddressed — verified via `git log` showing zero commits touching any of the files they name
since that date. Full detail and per-item status: `Audit/PRODUCTION_ENGINE_ROADMAP_RECONCILIATION.md`
Part 2; prioritized list: `Audit/PRODUCTION_ENGINE_BACKLOG.md` P0/P1.

---

## Recommended Next Milestone

# Implement ADR-AF-003 (Sizing Ownership)

### Why This Milestone Is Next

The standing sequence agreed on 2026-07-28 (Operations Dashboard / Job History, then Agent Firm
repository split) was decided **before** ADR-AF-003 existed — ADR-AF-003 is dated 2026-07-29, a full
day later, produced by the same architecture-certification pass that also certified ADR-AF-002
(`AF2_ARCHITECTURE_CERTIFICATION.md`). Those 2026-07-28 planning documents could not have accounted
for a defect that had not yet been identified. Updating the plan in light of new evidence is not the
same as reordering priorities without justification — it is exactly what this task asked for:
resolving contradictions and reconciling sources, not mechanically executing the oldest instruction
found.

Weighed against Operations Dashboard / Job History specifically:
- ADR-AF-003 fixes a **confirmed, live correctness defect** in production trading logic (position
  sizing can silently receive an uninformative value instead of a computed one). Operations
  Dashboard is a pure observability/tooling addition with no live defect behind it.
- ADR-AF-003's **architecture is already decided** (`ADR-AF-003-SIZING_OWNERSHIP.md`, Status:
  DECIDED, permanent) — implementation is the only remaining step, following the exact same
  producer-wiring pattern ADR-AF-002's own WP1–WP4 already proved out in this codebase. This is
  lower-risk, better-scoped work than Operations Dashboard, which has no design document yet.
- Fixing it does not conflict with this session's "no new Agent Firm features" constraint — removing
  a silent overwrite and routing sizing through one function is a defect correction, not a capability
  addition, consistent with how every certification in this trail has drawn that same line.

### Dependencies

- No dependency on Operations Dashboard / Job History or the Agent Firm repository split — those
  remain correctly sequenced afterward, per `AGENT_FIRM_GOVERNANCE.md`'s own stated timing (repo
  split happens only after Operations Dashboard **and** AF-7).
- Depends on confirming `EDGE_SCORE_MODE`'s actual live production value first (P0-2 in the backlog)
  — this determines whether the collision is currently active in production or dormant, which should
  inform rollout caution (e.g., whether a shadow-mode-style staged rollout is warranted), but does
  not change whether the fix should be built.

### Estimated Scope

Small and well-bounded, per the ADR's own decision: one new module
(`engine/position_sizing.py::resolve_size_hint()`), removal of the write at `scanner.py:1038` and the
conditional write at `:962` in favor of a single call site, and (per the ADR's stated Risk-agent-side
half) wiring `size_tier` from the Risk prompt's output through to that resolver. This mirrors the
shape of ADR-AF-002's own WP1–WP2 (a Foundation step, then a wiring step) — expect a comparable,
proven implementation pattern, not a novel one.

### Risks

- **Silent behavior change for any deployment currently running `EDGE_SCORE_MODE=enforce` +
  Agent Firm active simultaneously** — exactly the collision being fixed, so a change is expected and
  correct, but should be watched post-deploy the same way ADR-AF-002's own certifications recommended
  monitoring its decision-distribution shift.
- **Unverified live configuration** — this plan cannot confirm from repository state alone whether
  the collision is currently dormant (`EDGE_SCORE_MODE=off`, the coded default) or live. Recommend
  confirming before implementation begins, not after.
- **Scope creep risk**: ADR-AF-003 also names `size_tier` (Risk agent's qualitative output) as part
  of the same decision — implementing only the `agent_size_hint` single-writer half while leaving
  `size_tier` unemitted would be a partial fix; the execution should treat both halves as one unit of
  work, per the ADR's own framing.

### Expected Deliverables

- `engine/position_sizing.py` (new module).
- `scheduler/scanner.py` changes removing the two-writer collision.
- Risk agent/prompt changes to emit `size_tier` (a prompt change — but justified as completing an
  already-decided architecture, not a redesign, consistent with this session's "no prompt redesign
  unless a genuine defect requires it" instruction from the immediately-preceding ADR-AF-002 sessions).
- Test coverage mirroring ADR-AF-002's own precedent (unit tests for the resolver, integration tests
  proving the collision is gone).
- A short implementation/audit report, following this repository's own established convention.

---

## Items Intentionally Deferred

- **Operations Dashboard / Job History** — remains the milestone after ADR-AF-003, not cancelled or
  deprioritized, simply resequenced behind a higher-severity, better-evidenced, better-scoped item.
  Its own entry criteria (the 11 follow-up items, per the prior session's `PRODUCTION_ENGINE_NEXT_MILESTONE.md`)
  remain unmet regardless of ADR-AF-003's insertion.
- **Agent Firm repository split (AF-1 through AF-7)** — unchanged, sequenced after Operations
  Dashboard per `AGENT_FIRM_GOVERNANCE.md`'s own stated timing.
- **`ConsensusContext`/`SessionContext`/`OpportunityContext`** — Tier 2 / no-attach-point items,
  explicitly out of scope for every work package in this trail; would need their own ADR amendment.
- **P1/P2/P3 backlog items** — all remain valid, tracked work; none block or are blocked by ADR-AF-003.
- **`docs/agent_firm/*.md` planning-corpus reconciliation** — still explicitly deferred, unchanged.

This session did not implement Operations Dashboard / Job History, per its own explicit constraint,
and does not implement ADR-AF-003 either — both are recommendations for future work, not actions
taken here.

---

## Overall Production Readiness

**The system is production-ready today** — nothing in this reconciliation found a reason to
withdraw or qualify the Final Gate certification's unconditional GO. The ADR-AF-003 finding is a
real, confirmed defect, but its blast radius is conditional on a non-default configuration
(`EDGE_SCORE_MODE=enforce`) this session could not confirm is actually set in production; it is a
priority correction, not evidence the system is currently unsafe to run as-is. Production readiness
should be qualified the same way `Audit/AF2_WP4_FINAL_CERTIFICATION.md` and
`Audit/AF2_PRODUCTION_VALIDATION_REPORT.md` already qualified ADR-AF-002's own closure: **ready, with
monitoring and a now-identified next engineering priority**, not blocked.

---

## Summary

- **Current milestone: COMPLETE** (ADR-AF-002, per `CLAUDE.md`'s 2026-07-29 amendment and its full
  supporting audit trail).
- **Next milestone: Implement ADR-AF-003 (Sizing Ownership).**
- **Ready to begin: YES** — architecture already decided, pattern already proven by ADR-AF-002's own
  implementation, no dependency on any unmet entry criteria (unlike Operations Dashboard / Job
  History, whose own entry criteria remain unmet per the prior session's findings).

---

**The next engineering milestone should be: Implement ADR-AF-003 (Sizing Ownership) — build
`engine/position_sizing.py::resolve_size_hint()` as the single writer of `agent_size_hint`, removing
the confirmed, currently-shipped silent-overwrite collision between `scheduler/scanner.py`'s edge-veto
and Agent-Firm-gate write sites.**

Supported by: `Audit/PRODUCTION_ENGINE_ROADMAP_RECONCILIATION.md` Part 3 (the defect, verified by
direct code read — `engine/position_sizing.py` absent, both write sites present and unchanged,
`size_tier` unemitted); Part 1 (ADR-AF-003 classified "still required — decided, not implemented,"
the only such classification in the entire reconciliation); and the dated-precedence argument that
the 2026-07-28 "Operations Dashboard next" sequencing could not have accounted for a defect first
documented 2026-07-29.
