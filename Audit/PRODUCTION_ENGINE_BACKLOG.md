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

**Amended 2026-08-18** — Housekeeping pass (Operations Dashboard / Job History session, step 0):
this doc had drifted stale again after the very next session closed nearly the entire P1 list
without updating it here. Verified against `git log` and the actual diff (not just the commit
message) for each: **P1-1, P1-2, P1-4, P1-5, P1-6, P1-7, P1-9, P1-10 are all DONE**
(`20ca93a`, `48ed038`, `dccfac2`, `4a204a5`, `a95c289`, `2418726`, `fc89490`, `e80cb9c`, all
2026-08-15) — struck through below. Also confirms P1-8 (design doc), P1-11, P1-12, P2-3, and P2-6
were already correctly marked done. Net: **P0 and P1 are now fully closed**; this milestone's own
entry criteria (`Audit/PRODUCTION_ENGINE_NEXT_MILESTONE.md`) are satisfied. Operations Dashboard /
Job History (Job History slice) is delivered this session — see the new entry under "Explicitly Not
Backlogged" below and `Audit/PRODUCTION_ENGINE_NEXT_MILESTONE.md`'s own update.

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
| ~~P1-1~~ | ~~Restructure `start_scheduler()`'s ~20 `add_job()` calls for per-job failure isolation~~ | **DONE**, commit `20ca93a` (2026-08-15) — `scheduler/__init__.py::_add_job()` wraps `scheduler.add_job()` in try/except, logs+alerts (best-effort Telegram), and continues registering the rest. Verified against the actual diff, not just the message. | Reconciliation Part 2, item 3 |
| ~~P1-2~~ | ~~Add a cron dead-man's-switch for backup/restore-drill cadence~~ | **DONE**, commit `48ed038` (2026-08-15) — reuses `engine.heartbeat`'s `heartbeat_status()` pattern over each backup cron's `cron_wrap.sh` log mtime; covers all 3 backup-related crons with cadence+slack thresholds. | Reconciliation Part 2, item 4 |
| ~~P1-3~~ | ~~Land the already-written `_write_token_atomic()` hardening~~ | **DONE**, commit `88165a6` (2026-08-04) — `auto_token.py:173-182` (tmpfile+rename+chmod 0600), called at `auto_token.py:604`. Verified present at HEAD. | Reconciliation Part 2, item 5 |
| ~~P1-4~~ | ~~Add per-trade exception isolation + alert to `monitor.py`'s SL/TP evaluation loop~~ | **DONE**, commit `dccfac2` (2026-08-15) — wraps the full per-trade loop body in try/except, logs with trade id/ticker + traceback, Telegram-alerts, continues to the next trade. | Reconciliation Part 2, item 6 |
| ~~P1-5~~ | ~~Extend redaction: fix the Stockbit-JWT structural gap and the truncate-before-redact ordering at 10+ call sites~~ | **DONE**, commit `4a204a5` (2026-08-15) — `redact_secrets()` now also reads `.stockbit_token` (fail-soft); 13 call sites across `scheduler/{jobs,__init__,scanner,utils,reports}.py` fixed to redact before truncating. | Reconciliation Part 2, item 7 |
| ~~P1-6~~ | ~~Add a scheduler-liveness check to `/health`~~ | **DONE**, commit `a95c289` (2026-08-15) — `app.py::health()` adds a `scheduler` field via `scheduler.get_scheduler()`; distinguishes "unavailable" (no scheduler in this process) from "not running" (flips overall `status` to `error`). Verified against the actual diff. | Reconciliation Part 2, item 8 |
| ~~P1-7~~ | ~~Redact `cron_wrap.sh`'s shell-based Telegram crash alert~~ | **DONE**, commit `2418726` (2026-08-15) — shells out to the venv's real `redact_secrets()` via `python3 -c` before sending; fails open (unredacted-but-sent) rather than silently dropping the alert if the venv is unavailable. | Reconciliation Part 2, item 11 |
| ~~P1-8~~ | ~~Write the Operations Dashboard / Job History design document~~ | **DONE** — `docs/superpowers/specs/2026-08-15-operations-dashboard-job-history-design.md`. Data inventory found most of the backend already exists (2B-1/2B-2 scheduler+metrics APIs, `/api/agent/audit`); net-new work is one provider-failover endpoint + an AF2 metric query mapping pass + two frontend domain pages (both `domains/*` and `design-system/charts/` confirmed empty scaffolds, not populated as originally assumed). Incorporates the AF2 monitoring plan's 9 metrics and its own recommended layout verbatim; 2 of the 9 explicitly deferred (blocked on P2-4/P2-5 instrumentation, not yet built). **Job History half implemented 2026-08-18 — see below.** | Reconciliation Part 1 |
| ~~P1-9~~ | ~~Fix `scripts/release.sh`'s `SHARED_PATHS` default to match the real `DB_PATH` default~~ | **DONE**, commit `fc89490` (2026-08-15) — default now `data/walkforward.db data/research.db`, dropped two dead names, added `mkdir -p` before the symlink loop. | Reconciliation Part 2, item 9 |
| ~~P1-10~~ | ~~Exercise `scripts/release.sh` end-to-end in CI, not just via unit tests of its logic~~ | **DONE**, commit `e80cb9c` (2026-08-15) — new release-smoke CI job builds a real release from HEAD and verifies file identity, immutability, byte-compiles every `.py`, and `rollback.sh --list` sees it. | Reconciliation Part 2, item 10 |
| ~~P1-11~~ | ~~Repair local `data/walkforward.db`'s corrupt `ticks` table~~ | **DONE.** Installed `sqlite3` CLI (winget, `SQLite.SQLite`, user-approved), ran the incident doc's Phase 5 recovery plan: copied the corrupted file, `sqlite3 <copy> ".recover" \| sqlite3 recovered.db` (~30min on the 3.3GB file), `PRAGMA integrity_check` → `ok`. Per-table row-count diff against the original found only `ticks` differed (12,694,770 vs 12,692,028); traced the gap to `.recover`'s own `lost_and_found` table (3,011 orphaned rows, all on the exact corrupted page range 804034–805321 from the original incident) — manually re-inserted the 2,099 fully-populated ones (`INSERT OR IGNORE`, respecting the `UNIQUE(date,ticker,time)` constraint; 57 were already-reattached duplicates), closing the gap to 643 rows (0.005%, attributable to 855 genuinely-incomplete `lost_and_found` fragments). Re-ran `integrity_check` (`ok`) and confirmed the date range matches the documented pre-incident range (`2026-04-18`–`2026-07-29`) exactly. Swapped into place (`data/walkforward.db`), corrupted original moved aside (not deleted) as `walkforward.db.corrupt_pre_p1-11_repair_20260815T174834.bak`. Found and fixed a related gap while doing this: the `.bak`/`.bak-wal`/`.bak-shm` aside-copy naming (this file and the pre-existing `.pre_recovery_cutover_*.bak` from the original incident) wasn't covered by any `.stignore` pattern — added `*.bak`/`*.bak-wal`/`*.bak-shm` and extended the P1-12 guard test to require them | This session, 2026-08-15 |
| ~~P1-12~~ | ~~**Add a check that `.stignore` still contains the corruption-hardening block**~~ (`*.db`/`*.db-wal`/`*.db-shm`/`*.db-journal`/`*.sync-conflict-*`/`logs/`, from commit `520800c`) | **DONE**, commit `4c0fa0d` (2026-08-15) — CI guard test added. This session found `.stignore`'s corruption-hardening rules had been silently overwritten in the working tree, re-exposing both `walkforward.db` and `research.db` to the exact WAL-sync race that caused the 2026-07-29 incident; rules restored + merged, and this test now fails CI if that regresses | This session, 2026-08-15 |

---

## Operations Dashboard / Job History — delivery status (2026-08-18)

P0 and P1 fully closed above satisfies this milestone's own entry criteria
(`Audit/PRODUCTION_ENGINE_NEXT_MILESTONE.md` §"Entry Criteria"). Delivered this session, narrower
than the full design doc scope (design doc §6 exit criteria 1-4) — the Job History slice only,
per the design doc's own finding that it "has zero backend gaps — pure frontend work over
already-frozen API":

- **Backend:** no new endpoints needed. `GET /api/v1/scheduler`, `/scheduler/jobs`,
  `/scheduler/jobs/<id>` (`routes/v1/scheduler.py`) and `/api/v1/status/jobs/{history,failed,
  latest,running}`, `/status/summary` (`routes/v1/status.py` over `engine/job_status.py`'s
  `job_execution_log`) already existed, tested, and classified VIEWER in
  `security/route_policy.py`. One small additive change: `job_name` query-param filter on
  `/status/jobs/history` (`engine/job_status.py::get_recent_jobs()`, `routes/v1/status.py`) for
  the per-job drill-down, with its own tests (`tests/engine/test_job_status.py`,
  `tests/test_v1_status_routes.py`).
- **Frontend:** `frontend/src/domains/operations/` (scheduler banner, sortable job table,
  job-detail drill-down with execution history + failure reason) + `frontend/src/api/{client,
  operations}.ts` + `frontend/src/models/operations.ts`. All 4 quality gates pass (lint, typecheck,
  test — 125/125, build). **Deliberately not registered in the frozen 7-workspace registry**
  (`app/router/workspaces.ts` — adding an 8th workspace requires an ADR per that file's own
  docstring, and this is an ops/engineering surface, not a trading-decision workspace). Mounted as
  a standalone route (`/internal/operations`, same pattern as `NotFoundPage`), reachable by direct
  URL only — not linked from Zone A/B nav, both of which have their own frozen, enumerated content
  lists. See `frontend/src/domains/operations/operations-page.tsx`'s docstring and this session's
  report for the full rationale — this is a flagged deviation from the design doc's own (incorrect)
  assumption that `domains/decision/`'s empty scaffold could double as the Agent Firm ops page.
- **Verified against real production data**, not just fixtures: SSH-queried the live
  `job_execution_log` (2,403 real rows) and curled the live `/api/v1/*` endpoints directly; then
  tunneled the live API into a local `npm run dev` and rendered the real page against it
  (screenshot-verified 46 real scheduler jobs, real cron triggers, real execution history). This
  caught one real bug before it shipped: the job-detail drill-down was filtering history by
  `job.name` (APScheduler's human-readable display string, e.g. "Premarket Firm Scan 08:35")
  instead of `job.job_id` (the actual key `job_execution_log.job_name` uses, e.g.
  `premarket_firm_scan`) — invisible to unit tests whose fixtures happened to use the same string
  for both fields. Fixed, and the fixtures were changed to use distinct id/name values so this bug
  class stays caught.
- **Deferred, not built:** `domains/decision/` (Agent Firm operational view, design doc §3's other
  half), the new provider-failover endpoint (§4.1), and the AF2 metric query mapping (§4.2) — all
  larger, separate pieces of the design doc's full scope, and the `domains/decision/` piece
  specifically needs an owner decision on where it belongs given the frozen-workspace conflict
  above (that scaffold is reserved for the real trading-decision "Decision Center" workspace).
  Not deployed to production — that's a separate, higher-risk step for the repo owner to trigger
  (`scripts/release.sh` + `systemctl --user restart`), not something this session did unilaterally.

---

## Admin-route auth gate — incident + stop-gap (2026-08-19)

**Incident:** during a live route audit, a manual `curl -X POST /api/agent/config` with an empty
body was issued as an ad hoc "is this ADMIN route actually protected?" probe. It succeeded
unauthenticated (`AUTH_MODE=off` in production, as it has been since the security-hardening work —
see `docs/SECURITY.md`) and, because `routes/backtest.py`'s handler defaults a missing `mode` field
to `"off"` rather than rejecting the request, silently disabled the Agent Firm for 45s
(09:22:23–09:23:08 WIB, corrected in-session). Forensics: the window overlapped market hours but no
scheduled job, signal, decision, or trade fell inside it (`job_execution_log`, `agent_decisions`,
`scheduled_signals`, `paper_trades`, `ft_shadow_trade`, `ft_shadow_position`, `provider_events` all
checked directly for the window — zero rows). Root cause of the probe itself: "read-only
investigation" is a convention this repo has no code-level way to enforce — nothing stops a
mutating call from being issued mid-audit, by a human or an agent.

**Fix (this session, stop-gap):** `security/middleware.py`'s existing `before_request` RBAC hook
(already built for `AUTH_MODE=shadow/enforce`, just previously inert because production runs
`AUTH_MODE=off`) now gates ADMIN-classified routes **unconditionally**, independent of `AUTH_MODE`
— reusing the same `AUTH_TOKEN_ADMIN` credential mechanism the module already supported, no new
secret system. `AUTH_TOKEN_ADMIN` is now set in `.env` (mode 600, gitignored, not in this doc).
VIEWER/OPERATOR routes are deliberately left on the existing `AUTH_MODE`-gated path — the frontend
(`frontend/`) has no token-attachment mechanism yet (README's U-4 "no identity layer"), so widening
enforcement to VIEWER under `AUTH_MODE=off` would break it. Verified live: unauthenticated
`POST /api/agent/config` → 401; with `AUTH_TOKEN_ADMIN` → 200; frontend and scheduler unaffected
(neither ever called an ADMIN route).

**Follow-up incident (same day, 10:05:57–10:06:21 WIB, after the gate above was already live at
10:05:34):** a second unread-before-calling verification probe — `curl -X POST /api/scheduler/run`,
made to check that OPERATOR routes were correctly *unaffected* by the ADMIN-only gate — triggered a
real, live `daily_signal_scan()` (the same function the real scheduled job runs): a full universe
scan (~24s, real yfinance calls) and one unscheduled Telegram send ("no signals today", since 0
signals were found). No paper trades opened (auto-trade only fires on a non-empty signal list), no
capital impact. This demonstrated live that `/api/scheduler/run` being OPERATOR-classified (open
under `AUTH_MODE=off`, same as before this session) is itself a real external-side-effect gap, not
just a hypothetical one.

**Follow-up fix — inventory + expanded gate (2026-08-19, same day):** every POST route (plus the one
GET route already flagged in this file's own `route_policy.py` comment as launching a scrape) was
checked for calls to `send_telegram` or an external network fetch (Stockbit/yfinance), and for any
internal caller (scheduler, cron, frontend) that would break if gated — none were found for any
candidate. **10 routes moved from OPERATOR to the same unconditional ADMIN gate**, all confirmed to
send a real Telegram message and/or make a real external API call, all previously reachable
unauthenticated under `AUTH_MODE=off`:

| Route | Confirmed external effect |
|---|---|
| `/api/scheduler/run` | Telegram (unconditional) + yfinance fetch — demonstrated live (above) |
| `/api/paper/open` | Telegram "Paper Trade OPENED" (`notify=True` default) + opens a real paper trade |
| `/api/paper/close` | Telegram "Paper Trade Closed" sent directly in the handler |
| `/api/signals/custom` | Telegram sent directly |
| `/api/paper/report-telegram` | Explicit Telegram report send |
| `/api/premover/run` | Real scan wired directly to a Telegram alert callback |
| `/api/screener/run` | Real background Stockbit scrape across the universe |
| `/api/screener/stockbit/run` | External Stockbit scrape (`run_screener`) |
| `/api/screener/swing_onset` | External Stockbit flow-batch fetch |
| `/api/flow/check` | External Stockbit flow-batch fetch |

Checked and confirmed **clean** (no external call, left as-is): `/api/fastmover/run` (pure local
pandas/SQLite, verified no network imports), `/api/backtest/{scan_all,quick_scan,precompute,
multi_quick_scan,roll,multi,walkforward,equity}`, `/api/optimizer/run`, `/api/portfolio/backtest`.
**Flagged as unverified, not gated:** `/api/chart/tv/sync` — calls into a `urllib.request`-importing
bridge module; likely a local TradingView desktop bridge rather than a third-party service, but the
destination wasn't traced (bounded-scope decision, not a determination that it's safe).

**Explicitly not done (separate, deliberate decisions, not resolved by this stop-gap):**
- Full `AUTH_MODE=shadow`/`enforce` activation (U-4 / real identity+login layer for the frontend).
- Remaining OPERATOR-classified routes (the "checked and confirmed clean" list above, plus anything
  not covered by this pass) stay unenforced under `AUTH_MODE=off` — only routes with a *confirmed*
  external side effect were moved.
- The `/api/agent/config` handler's own footgun (missing `mode` silently defaults to `"off"` instead
  of rejecting the request) was not changed — the auth gate now prevents an *unauthenticated* call
  from reaching it, but an authenticated caller can still hit the same footgun by omission.
- `/api/chart/tv/sync`'s external-call destination was not traced — revisit if it turns out to reach
  a genuine third party rather than a local bridge.

---

## P2 — Maintenance

| # | Item | Source |
|---|---|---|
| P2-1 | Resolve or explicitly accept the `validate_config()` DB_PATH-must-pre-exist contradiction (Owner Decision 2) | Reconciliation Part 4 |
| P2-2 | Remove `reset_market_ctx()` compatibility shim + update the two developer scripts that still call it | `Audit/AF2_WP4_TECHNICAL_DEBT_REPORT.md`, re-confirmed unchanged in `Audit/ADR-AF-002_HANDOFF_CHECKLIST.md` |
| P2-3 | Fix the stale docstring in `tests/test_agent_firm_context_wiring.py` (line 9, claims `_build_context()` "is untouched" — deleted in WP3) | `Audit/PRODUCTION_ENGINE_NEXT_MILESTONE.md` |
| P2-4 | Instrument batch-context cache hit/miss as a structured, queryable signal | `Audit/AF2_POST_DEPLOYMENT_MONITORING_PLAN.md` §5 |
| P2-5 | Promote "unexpected fail-soft" log lines to a structured event table | `Audit/AF2_POST_DEPLOYMENT_MONITORING_PLAN.md` §9 |
| ~~P2-6~~ | ~~Run a manual restore drill and investigate why the weekly cron entry stopped firing~~ | **DONE.** Root cause: not a broken cron entry — the production box is a personal laptop (XPS-13, suspends/reboots on its own schedule), and `journalctl` confirms a boot gap spanning exactly Sunday 08-09's 09:00 trigger. Vanilla `cron` has no catch-up semantics (unlike `anacron`/systemd timers with `Persistent=true`) — a missed fire time is silently skipped, not retried, which is why every Sunday since 07-19 landed in a sleep/off window. Ran the drill manually — first attempt exposed a **second, real bug**: the crontab's bare `ls -t *.db.zst \| head -1` glob picked the newest backup of *either* prefix sharing the dir, so R-5's same-session research.db backup made it silently verify a 0.1MB/6-table file while reporting "RESTORE VERIFIED OK," never actually testing walkforward.db. Fixed the glob to `walkforward-*.db.zst` (prune() was already correctly prefix-scoped — only the drill's shell glob was missed), added a static regression test (`test_restore_drill_targets_walkforward_backups_specifically`), re-ran correctly: `walkforward-20260815-115758.db.zst`, 4150MB, 68 tables, 36,926,680 rows, integrity `ok`, row counts match meta. Installed on production. **Durable fix also done** (2026-08-15, same session): all 3 jobs (`db_backup`, `db_backup_research`, `db_restore_drill`) moved from `deploy/crontab` to systemd `--user` timers (`deploy/systemd/`, `Persistent=true` on each) — a missed fire time now catches up shortly after next boot/wake instead of silently skipping for a full cycle. Verified: `loginctl` confirmed lingering already enabled (no sudo needed), `systemd-analyze --user verify` clean, all 3 services test-run manually end-to-end with correct output, crontab's 3 lines removed + reinstalled (no double-scheduling), `docs/OPERATIONS.md` updated, static regression tests added (`tests/test_systemd_timers_contract.py`, `tests/test_cron_contract.py::test_db_backup_and_restore_drill_are_not_double_scheduled`) | Reconciliation Part 4 |
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
