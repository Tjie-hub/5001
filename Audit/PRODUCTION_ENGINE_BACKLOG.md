# Production Engine — Canonical Execution Backlog

**Date:** 2026-07-29
**Companion to:** `Audit/PRODUCTION_ENGINE_ROADMAP_RECONCILIATION.md`.
**Basis:** every item below is traced to a specific finding in the reconciliation matrix — nothing
here is newly invented by this backlog document.

**Amended 2026-08-15** — Session update following R-5 closure + an independent cross-check (zcode)
of live repo/production state. P0 is now fully resolved (verified live, not assumed — see below).
P1-3 is done; P1-5/P1-7/P1-9/P1-10/P1-1/P1-2/P1-4/P1-6 re-confirmed still open by direct code
inspection at HEAD `05038fa`. New items added: a local DB-corruption repair (P1-11), a regression
guard for the `.stignore` incident that recurred this session (P1-12), and frontend-doc staleness
(P2-11). See `Audit/R5_TIER1_DB_SPLIT_CLOSURE_REPORT.md` and this session's transcript for full
evidence trails.

---

## P0 — RESOLVED (verified live 2026-08-15)

*"Next production release" means the next time production code is deployed/restarted — not
necessarily ADR-AF-002-related, since ADR-AF-002 is already merged into the working tree.*

| # | Item | Resolution |
|---|---|---|
| P0-1 | Implement ADR-AF-003 (Sizing Ownership) | **DONE.** `engine/position_sizing.py::resolve_size_hint()` exists and is the sole writer, called from `scheduler/scanner.py:1091`; the old unconditional overwrite is gone. Verified by direct code inspection (independent cross-check), not just the ADR-AF-003 report's own claim. |
| P0-2 | Confirm `EDGE_SCORE_MODE`'s live production value | **CONFIRMED:** `shadow` (checked via SSH against production `.env`, 2026-08-15). Now moot regardless, since P0-1's collision is already fixed in code. |
| P0-3 | Confirm `TELEGRAM_WEBHOOK_SECRET` still set in production `.env` | **CONFIRMED SET** (non-empty; checked via SSH, presence only, value not read/logged). |
| P0-4 | Harden `validate_config()` to enforce `TELEGRAM_WEBHOOK_SECRET` | **DONE**, commit `e260b5c` (2026-08-05) — `config.py::validate_config()` now fails closed if unset. Verified present at HEAD. |

---

## P1 — High-Priority Engineering

| # | Item | Rationale | Source |
|---|---|---|---|
| P1-1 | Restructure `start_scheduler()`'s ~20 `add_job()` calls for per-job failure isolation | One bad job registration currently crashes the entire worker boot | Reconciliation Part 2, item 3 |
| P1-2 | Add a cron dead-man's-switch for backup/restore-drill cadence | A ~36h gap already occurred once (2026-07-25/26) and went undetected until manually noticed | Reconciliation Part 2, item 4 |
| ~~P1-3~~ | ~~Land the already-written `_write_token_atomic()` hardening~~ | **DONE**, commit `88165a6` (2026-08-04) — `auto_token.py:173-182` (tmpfile+rename+chmod 0600), called at `auto_token.py:604`. Verified present at HEAD. | Reconciliation Part 2, item 5 |
| P1-4 | Add per-trade exception isolation + alert to `monitor.py`'s SL/TP evaluation loop | An unhandled exception on trade N currently aborts monitoring for every trade after N in that tick, silently | Reconciliation Part 2, item 6 |
| P1-5 | Extend redaction: fix the Stockbit-JWT structural gap and the truncate-before-redact ordering at 10+ call sites | A secret embedded in an exception message can still leak unredacted today; RC1-C2 already closed a *related* but narrower gap | Reconciliation Part 2, item 7 |
| P1-6 | Add a scheduler-liveness check to `/health` | A deploy where scheduler-start silently fails currently reports "ok" and passes the deploy gate | Reconciliation Part 2, item 8 |
| P1-7 | Redact `cron_wrap.sh`'s shell-based Telegram crash alert | The one outbound alert path never covered by the Python redaction mechanism | Reconciliation Part 2, item 11 |
| ~~P1-8~~ | ~~Write the Operations Dashboard / Job History design document~~ | **DONE** — `docs/superpowers/specs/2026-08-15-operations-dashboard-job-history-design.md`. Data inventory found most of the backend already exists (2B-1/2B-2 scheduler+metrics APIs, `/api/agent/audit`); net-new work is one provider-failover endpoint + an AF2 metric query mapping pass + two frontend domain pages (both `domains/*` and `design-system/charts/` confirmed empty scaffolds, not populated as originally assumed). Incorporates the AF2 monitoring plan's 9 metrics and its own recommended layout verbatim; 2 of the 9 explicitly deferred (blocked on P2-4/P2-5 instrumentation, not yet built) | Reconciliation Part 1 |
| P1-9 | Fix `scripts/release.sh`'s `SHARED_PATHS` default to match the real `DB_PATH` default | Silently symlinks nothing on a stock configuration today | Reconciliation Part 2, item 9 |
| P1-10 | Exercise `scripts/release.sh` end-to-end in CI, not just via unit tests of its logic | No integration-level coverage of the actual release mechanism exists today | Reconciliation Part 2, item 10 |
| P1-11 | **Repair local `data/walkforward.db`'s corrupt `ticks` table** on the Windows dev box (`D:\IDX`) — run the incident doc's ranked recovery option 1 (targeted `.recover` of `ticks` against a copy) | `PRAGMA quick_check` (2026-08-15) confirms the corruption from `Audit/INCIDENT_VPIN_DB_CORRUPTION_2026-07-29.md` was never actually repaired locally — same error signature (Tree 637876, `btreeInitPage()` errors) still present today, on both the live file and the `.pre_recovery_cutover` backup. Production's copy is separately confirmed clean (`integrity_check: ok`, 2026-08-15). Not a trading risk, but leaves a known-corrupt 3.3GB file sitting in the Syncthing sync path indefinitely | This session, 2026-08-15 |
| P1-12 | **Add a check that `.stignore` still contains the corruption-hardening block** (`*.db`/`*.db-wal`/`*.db-shm`/`*.db-journal`/`*.sync-conflict-*`/`logs/`, from commit `520800c`) — e.g. a pre-commit hook, a `pytest` file-content assertion, or periodic Syncthing REST-API config check | This session found `.stignore`'s corruption-hardening rules had been silently overwritten in the working tree (wholesale replacement with an unrelated dev-tooling ignore list, zero overlap), re-exposing both `walkforward.db` and the newly-split `research.db` to the exact WAL-sync race that caused the 2026-07-29 incident. Fixed this session (rules restored + merged with the dev-tooling additions), but nothing currently prevents a repeat | This session, 2026-08-15 |

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
| P2-11 | Update `frontend/README.md` — still says "the application is intentionally empty, no shell, no routing," contradicting Workstream B (commit `48b2d4a`, directly under HEAD) which shipped `frontend/src/app/router/`, `providers/`, `design-system/`, `domains/`, `state/` | This session, 2026-08-15 |

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

- ADR-AF-001, ADR-AF-002, ADR-AF-003 (see P0-1), ADR-AF-004 — all complete, per the reconciliation
  matrix and (for AF-003) direct code re-verification 2026-08-15.
- RC1 (Telegram Reporting v2) and the Final Gate certification — complete, merged, CI-green.
- `PLAN.md`'s Agent Firm Optimization (2-stage evaluation) — shipped 2026-06-05/09, historical.
- General production-code technical debt (`_ROUTES_DEBT`, `_LIFECYCLE_DEBT`, etc.) — confirmed zero
  must-resolve items by `Audit/TECHNICAL_DEBT_RELEASE_REVIEW.md`, bounded and CI-enforced shrink-only.
- `paper_trade.py` duplicate-close race guard and `scripts/release.sh` dirty-tree guard — both
  landed alongside P0-4 in `e260b5c` (2026-08-05); not originally backlog items, found+fixed
  opportunistically during that work.
- R-5 (Tier-1 physical DB split) — code-complete and live-cut-over 2026-08-15
  (`Audit/R5_TIER1_DB_SPLIT_CLOSURE_REPORT.md`); its own backup-cron gap (found this session) is
  fixed and verified, not a backlog item.
- API Layer Phase 2 freeze (Workstreams 2A-2D) — frozen at `93c9343`, `tests/test_phase2_api_freeze.py`
  passes (7/7, re-verified 2026-08-15).
