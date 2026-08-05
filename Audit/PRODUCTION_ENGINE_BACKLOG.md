# Production Engine — Canonical Execution Backlog

**Date:** 2026-07-29
**Companion to:** `Audit/PRODUCTION_ENGINE_ROADMAP_RECONCILIATION.md`.
**Basis:** every item below is traced to a specific finding in the reconciliation matrix — nothing
here is newly invented by this backlog document.

---

## P0 — Must Complete Before Next Production Release

*"Next production release" means the next time production code is deployed/restarted — not
necessarily ADR-AF-002-related, since ADR-AF-002 is already merged into the working tree.*

| # | Item | Why P0 | Source |
|---|---|---|---|
| P0-1 | **Implement ADR-AF-003 (Sizing Ownership)** — build `engine/position_sizing.py::resolve_size_hint()` as the single writer of `agent_size_hint`; remove the unconditional overwrite at `scheduler/scanner.py:1038`; retire the collision with `run_edge_veto_stage()`'s write at line 962 | Confirmed live code defect: a silent overwrite that can discard a computed, validated edge score in favor of an uninformative default. Architecture already decided — implementation only, no design risk | Reconciliation Part 3 |
| P0-2 | **Confirm `EDGE_SCORE_MODE`'s actual live production value** (via operator/host access this session did not have) | Determines whether P0-1's collision is *currently* firing in production today or dormant — materially changes urgency framing, does not change the need to fix it | Reconciliation Part 3 |
| P0-3 | **Confirm `TELEGRAM_WEBHOOK_SECRET` is still set in the live production `.env`** (re-verify — last confirmed 2026-07-28, not re-checked since) | A silent config drift since the last confirmation would reopen an unauthenticated-webhook exposure with zero automated detection | Reconciliation Part 2, item 1 |
| P0-4 | **Harden `validate_config()` to enforce `TELEGRAM_WEBHOOK_SECRET`** (Owner Decision 1, Option B) once P0-3 confirms it's safe to do so | Closes the enforcement gap permanently, independent of any single confirmation snapshot | Reconciliation Part 2/4 |

---

## P1 — High-Priority Engineering

| # | Item | Rationale | Source |
|---|---|---|---|
| P1-1 | Restructure `start_scheduler()`'s ~20 `add_job()` calls for per-job failure isolation | One bad job registration currently crashes the entire worker boot | Reconciliation Part 2, item 3 |
| P1-2 | Add a cron dead-man's-switch for backup/restore-drill cadence | A ~36h gap already occurred once (2026-07-25/26) and went undetected until manually noticed | Reconciliation Part 2, item 4 |
| P1-3 | Land the already-written `_write_token_atomic()` hardening | Ready, tested, was only excluded from RC1 for release-scope hygiene — real cost of leaving it uncommitted already documented | Reconciliation Part 2, item 5 |
| P1-4 | Add per-trade exception isolation + alert to `monitor.py`'s SL/TP evaluation loop | An unhandled exception on trade N currently aborts monitoring for every trade after N in that tick, silently | Reconciliation Part 2, item 6 |
| P1-5 | Extend redaction: fix the Stockbit-JWT structural gap and the truncate-before-redact ordering at 10+ call sites | A secret embedded in an exception message can still leak unredacted today; RC1-C2 already closed a *related* but narrower gap | Reconciliation Part 2, item 7 |
| P1-6 | Add a scheduler-liveness check to `/health` | A deploy where scheduler-start silently fails currently reports "ok" and passes the deploy gate | Reconciliation Part 2, item 8 |
| P1-7 | Redact `cron_wrap.sh`'s shell-based Telegram crash alert | The one outbound alert path never covered by the Python redaction mechanism | Reconciliation Part 2, item 11 |
| P1-8 | Write the Operations Dashboard / Job History design document | Standing-agreed next milestone has no scope document; per this repo's own convention (spec-then-plan-then-implement), this should exist before implementation starts. Should incorporate `Audit/AF2_POST_DEPLOYMENT_MONITORING_PLAN.md`'s 9 metrics so the dashboard's first version doesn't need a redesign | Reconciliation Part 1 |
| P1-9 | Fix `scripts/release.sh`'s `SHARED_PATHS` default to match the real `DB_PATH` default | Silently symlinks nothing on a stock configuration today | Reconciliation Part 2, item 9 |
| P1-10 | Exercise `scripts/release.sh` end-to-end in CI, not just via unit tests of its logic | No integration-level coverage of the actual release mechanism exists today | Reconciliation Part 2, item 10 |

---

## P2 — Maintenance

| # | Item | Source |
|---|---|---|
| P2-1 | Resolve or explicitly accept the `validate_config()` DB_PATH-must-pre-exist contradiction (Owner Decision 2) | Reconciliation Part 4 |
| P2-2 | Remove `reset_market_ctx()` compatibility shim + update the two developer scripts that still call it | `Audit/AF2_WP4_TECHNICAL_DEBT_REPORT.md`, re-confirmed unchanged in `Audit/ADR-AF-002_HANDOFF_CHECKLIST.md` |
| P2-3 | Fix the stale docstring in `tests/test_agent_firm_context_wiring.py` (line 9, claims `_build_context()` "is untouched" — deleted in WP3) | `Audit/PRODUCTION_ENGINE_NEXT_MILESTONE.md` |
| P2-4 | Instrument batch-context cache hit/miss as a structured, queryable signal | `Audit/AF2_POST_DEPLOYMENT_MONITORING_PLAN.md` §5 |
| P2-5 | Promote "unexpected fail-soft" log lines to a structured event table | `Audit/AF2_POST_DEPLOYMENT_MONITORING_PLAN.md` §9 |
| P2-6 | Run a manual restore drill and investigate why the weekly cron entry stopped firing (Owner Decision 3) | Reconciliation Part 4 — cannot confirm from repo state alone whether already done |
| P2-7 | `redact_secrets()` pattern-based matching (currently exact-configured-value-match only) | `SECURITY_REVIEW_REPORT.md` P2 |
| P2-8 | Cover `.playwright_state/`'s live session cookies under the secret-permission check | `SECURITY_REVIEW_REPORT.md` P2 |
| P2-9 | Reconcile the `docs/agent_firm/*.md` planning corpus (≥3 mutually-inconsistent roadmap/sequence documents, 23 files total) against actual delivered state | Repeatedly deferred since WP2; still outstanding |
| P2-10 | Silent auth-token role downgrade on duplicate values in `security/auth.py::configured_tokens()` | `PRODUCTION_READINESS_REPORT.md` P1 (bounded to `AUTH_MODE=enforce`, confirmed `off` in production as of 2026-07-28) |

---

## P3 — Future Enhancements

| # | Item | Source |
|---|---|---|
| P3-1 | Build `ConsensusContext` (Tier 2) — `guardrails.py::build_consensus_summary()`, wired into `firm.py::_run_risk()` | `ADR-AF-002`; deliberately out of every prior work package's mandate |
| P3-2 | `SessionContext`/`OpportunityContext` — no `SignalCandidate` attach point exists; would need a dated ADR amendment | `ADR-AF-002` |
| P3-3 | Agent Firm repository split (AF-1 through AF-7 per `AGENT_FIRM_IMPLEMENTATION_ROADMAP.md`) | Explicitly sequenced after Operations Dashboard / Job History; zero milestones started |
| P3-4 | `PRAGMA integrity_check` at application startup (partially mitigated today by the nightly backup's own verify step) | `PRODUCTION_READINESS_REPORT.md` P1 |
| P3-5 | Alert on halted/delisted-ticker positions that silently stop being monitored | `PRODUCTION_READINESS_REPORT.md` P1 |
| P3-6 | External alert on a boot crash-loop (systemd `StartLimitBurst` exhaustion) | `PRODUCTION_READINESS_REPORT.md` P1 |
| P3-7 | Disaster-recovery runbook for total server loss / lost secrets / Stockbit lockout | `PRODUCTION_READINESS_REPORT.md` P3 |
| P3-8 | Release-directory retention/pruning (unbounded disk growth over time, not a correctness risk) | `PRODUCTION_READINESS_REPORT.md` P2 |
| P3-9 | `signal.signal()` handler for the `python app.py` dev-mode path | `PRODUCTION_READINESS_REPORT.md` P3 |

---

## Explicitly Not Backlogged (already complete, no action needed)

- ADR-AF-001, ADR-AF-002, ADR-AF-004 — complete, per the reconciliation matrix.
- RC1 (Telegram Reporting v2) and the Final Gate certification — complete, merged, CI-green.
- `PLAN.md`'s Agent Firm Optimization (2-stage evaluation) — shipped 2026-06-05/09, historical.
- General production-code technical debt (`_ROUTES_DEBT`, `_LIFECYCLE_DEBT`, etc.) — confirmed zero
  must-resolve items by `Audit/TECHNICAL_DEBT_RELEASE_REVIEW.md`, bounded and CI-enforced shrink-only.
