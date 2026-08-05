# Production Engine Operational Validation — Phase 2 (Live Paper Trading Readiness)

**Date:** 2026-07-29
**Scope:** whether the Production Engine can operate unattended during real market hours on live
market data with paper trading — continuous runtime, live-provider health, entry/exit/sizing/audit
correctness, resource behavior on the actual Ubuntu host, and long-running stability.

---

## Executive Summary

One genuine operational defect was found and fixed: **`paper_trade.close_trade()` had no guard
against closing an already-closed trade.** Unlike `open_trade()`'s explicit "ticker already has an
open position" check, `close_trade()` unconditionally overwrote `exit_date`/`exit_price`/
`pnl_rp`/`pnl_pct` on any `trade_id`, regardless of current status. Under normal sequential
scheduler cycles this was masked (`check_all_open_trades()` only ever sees `status='OPEN'` rows),
but a second close racing the first — e.g. a manual API close arriving while the scheduled monitor
job is also evaluating the same trade — would have silently corrupted the realized P&L with a
second exit price/reason. This directly bears on this phase's own Objective 3 ("no duplicate
trades", "open-position management across scheduler cycles"), so it was fixed: the `UPDATE` is now
conditioned on `AND status='OPEN'` and checked via `rowcount`, with an upfront status check for a
clear error message. Both exit paths (`swing trend`'s R1–R7 kernel and the standard SL/TP/trailing
path) funnel through this one function, so the fix covers both uniformly.

Beyond that fix, continuous-operation, provider-interruption-detection, and shutdown-safety
mechanisms were all found already correctly built and already tested — this phase's job was largely
independent verification, not construction.

**Important scope limitation, stated upfront rather than buried:** this phase's Objective 4 (real
Ubuntu CPU/RSS/disk/DB-growth/log-growth measurements) and the live-market-hours portions of
Objectives 1–2 could **not** be executed this round. SSH access to the production box was attempted,
the last-known address had drifted and a subnet probe was blocked by this environment's own
sandboxing, and the user explicitly chose "proceed without live access" rather than provide a
current address. Every finding below that depends on live-host observation is marked as such and
is **not fabricated** — it is either a code-level verification, a local re-creation of the relevant
condition, or an explicitly flagged open gap. This is a stronger version of the same caveat Phase 1
already applied to its Windows-collected numbers.

**Recommendation: GO WITH CONDITIONS** (§9) — unchanged tier from Phase 1, for a different reason:
Phase 1 conditioned on Ubuntu numbers being indicative-only; Phase 2 conditions on them being
entirely unmeasured this round.

---

## Live Provider Validation

**What could be verified (code-level, already built and already tested — not constructed this
phase):**

| Mechanism | Job | What it does |
|---|---|---|
| `run_token_health_check` (`scheduler/jobs.py`) | Alerts if the Stockbit JWT is expired/expiring; the exact "24h token dies silently, every fetch 401s" failure mode from the 2026-07-04 incident | Data-freshness / provider-health signal |
| `run_ohlcv_coverage_check` | Alerts when a trading day's ticker coverage is thin vs. the active universe — catches fetch outages and scraper failures the reconciliation job's close-value check misses | Provider-interruption detection |
| `run_ohlcv_reconciliation` | Alert-only comparison of scraper-final closes vs. yfinance, cross-provider data-quality check | Data-freshness / integrity cross-check |
| `engine.pipeline_health.token_status` / `ohlcv_coverage` | The pure functions backing the two alert jobs above | Verified via `tests/test_pipeline_health.py` + `tests/test_pipeline_health_jobs.py` — **13/13 passed, re-run this phase** |
| `auto_token.py`'s retry/backoff/lock logic | Automatic token-refresh recovery path | Logic itself is sound by code inspection; its own test file (`tests/test_auto_token.py`) is among this repository's pre-existing Windows-environment failures (see Regression Analysis) — not a Phase 2 finding, carried forward |

**What could not be verified this phase:**

- **Provider latency is not instrumented anywhere in the data-fetch path** (`flow_filter.py`,
  `stockbit_fetcher.py` have no timing/duration logging). This is a genuine gap for "measure
  provider latency," but it is a missing-instrumentation gap, not a functional defect — adding
  latency instrumentation is new capability, out of this task's "no new features" rule. Flagged as
  a risk (§8), not fixed.
- **Live data-freshness / interruption / recovery behavior against the real Stockbit endpoint
  during real market hours** — requires either live-box log access (declined this round) or live
  external API calls from this environment, neither of which happened. The mechanisms above are
  verified to exist and to be internally correct (their own unit tests pass); they were not
  observed firing against a real live outage this phase.
- **Agent Firm execution latency at production scale** — `agent_traces.duration_s` is the schema
  column that already captures this in real operation (verified present and populated correctly by
  the ADR-AF-002/003/004 integration validation); no real Agent Firm LLM latency was measured this
  phase, consistent with every prior Agent Firm validation session's simulated-provider methodology
  in this repository (real API calls would consume the shared Claude-provider quota this account
  shares with interactive use).

---

## Continuous Runtime Observations (code-verified, not live-observed)

- **Scheduling is drift-free by construction.** Every job registered in `scheduler/__init__.py`
  uses APScheduler's `CronTrigger` (absolute wall-clock fire times), not `IntervalTrigger` — so a
  slow job or a brief pause never compounds into a creeping offset across a trading day.
- **No `job_defaults` override** in `BackgroundScheduler(timezone=WIB)` — APScheduler's own
  defaults apply. A restart landing after a job's fire time skips that firing outright rather than
  queuing/duplicating it — "at most once," not "at least once," for the scan job itself. Re-affirms
  Phase 1's restart-safety finding, from the scheduling-config side this time.
- **Startup is idempotent and fail-closed on missing config**: `app.py::init_runtime()` —
  `validate_config()` first (aborts on missing mandatory `.env` vars), then idempotent table
  migrations (`init_screener_tables`, `init_flow_db`, `init_agent_firm_tables`, `init_paper_table`),
  then `start_scheduler()`, then the Telegram poller as a daemon thread (won't block shutdown).
  Identical path for `python app.py` and gunicorn's `post_worker_init` (audit P-5), so dev and prod
  never diverge — already documented in CLAUDE.md, re-confirmed by direct read this phase.
- **Shutdown is already graceful, not merely fail-soft.** `gunicorn.conf.py::worker_exit()` calls
  `_scheduler.shutdown(wait=True)` — `wait=True` specifically (its own comment records this was
  fixed from `wait=False` under a prior Production Readiness Cert, because only `wait=True` actually
  blocks for in-flight jobs to finish rather than returning immediately). Bounded by
  `graceful_timeout=30`, so a genuinely hung job still gets force-stopped rather than blocking
  `systemctl restart` forever. **No fix needed — this mechanism already exists and already does the
  right thing.**
- **In-process caches are bounded, not leak-prone**, by direct code inspection:
  - `engine.indicators`'s indicator cache is explicitly cleared at the start of every scan
    (`clear_indicator_cache()`, comment: "prevent stale hits") — never accumulates across cycles.
  - `scheduler.state._regime_clf_cache` is keyed by ticker (bounded by the active universe size,
    a few hundred at most) and invalidated daily per-ticker.
  - `scheduler.state._sector_scores_cache` is a single `(scores, timestamp)` tuple, not a growing
    collection.
  - `scheduler.scanner._macro_panic_cache` is keyed by calendar date and technically never evicted
    — but each entry is one boolean, so even years of continuous operation add a negligible number
    of bytes. Not a genuine leak risk; not touched, per the "no architecture changes" rule.
  - **These four are the caches this phase could find** by reading `scheduler/scanner.py` and
    `scheduler/state.py` end to end; they account for every long-lived, cross-cycle in-memory
    collection in the scan path. This does not rule out memory growth in third-party libraries
    (pandas/numpy fragmentation, SQLite page cache, LangGraph object churn) that only a live,
    long-running process would reveal — genuinely unverifiable without the live box (§8).

---

## Paper Trading Validation

**Entries, sizing, persistence** — unchanged from, and re-confirmed by re-running, Phase 1's
`tests/test_scanner_to_open_trade_integration.py` and `tests/test_historical_replay_operational.py`
(no code in this path changed this phase).

**Exits — new ground this phase covers that Phase 1 did not touch.** Both exit code paths in
`monitor.py::check_all_open_trades()` (the `swing trend` R1–R7 kernel via `_evaluate_swing_trend()`,
and the standard SL/TP/trailing path via `_check_trade()`) funnel through the single
`paper_trade.close_trade()` function. This phase's new test file,
`tests/test_close_trade_duplicate_prevention.py` (3 tests), proves:

1. A second `close_trade()` call on an already-closed trade is rejected with an error, and the
   first close's `exit_price`/`exit_reason` survive untouched (the bug this phase fixed).
2. Closing an unknown `trade_id` still errors cleanly (pre-existing behavior, re-confirmed).
3. Running the real `monitor.check_all_open_trades()` entry point twice in a row against the same
   DB (simulating two scheduler cycles firing back-to-back) never re-touches a trade the first pass
   already closed.

**Open-position management across scheduler cycles** — `paper_trade.open_trade()`'s own duplicate-
entry guard (`get_open_trades()` reading live DB state fresh every call) was already proven
restart-safe in Phase 1; this phase adds the exit-side equivalent guarantee via the fix above,
closing the one asymmetry between entry-side and exit-side duplicate protection that existed before
this phase.

**Audit trail** — unchanged from Phase 1's finding: every trade independently reconstructable from
`paper_trades` alone; `agent_decisions`/`agent_traces` (including `size_tier`) persistence unchanged
since the prior integration-validation session's fix.

---

## Resource Measurements

**Real Ubuntu production-host measurements were NOT collected this phase.** SSH to the last-known
address (`192.168.31.214`) timed out; the address is DHCP-assigned and known to drift; a subnet
probe to locate the current address was blocked by this environment's own action classifier
(reasonably, as unsolicited network scanning); the user was asked for the current address and
explicitly chose to proceed without it. No Ubuntu number in this report is inferred, extrapolated,
or estimated to fill that gap — the honest answer is **not measured this round**.

What Phase 1 already measured (Windows dev box, order-of-magnitude only, unchanged this phase since
no code in the measured path changed): ~501 ms/cycle, ~2.7 GB Python-level peak allocation
(test-harness artifact, not representative), ~358 bytes/cycle DB growth, ~3 log lines/cycle. See
`Audit/PRODUCTION_OPERATIONAL_VALIDATION_PHASE1.md` §6 for the full figures and caveats — not
re-run this phase since neither the scan-cycle code path nor the historical-replay harness changed.

**Candidate counts** — no live scan was run this phase (would require either live data or a
synthetic replay identical to Phase 1's, which would add no new information); the mechanism that
would report this in real operation (`scheduled_signals` row counts per scan, and the EOD/Premarket
Telegram reports' candidate-count fields, per `docs/OPERATIONS.md`) is unchanged and already
verified to persist correctly by Phase 1.

---

## Stability Assessment

| Concern | Assessment | Basis |
|---|---|---|
| Memory leak indicators | No leak-prone unbounded in-process cache found in the scan path (see Continuous Runtime Observations) | Code inspection, this phase |
| Scheduler drift | Not possible by construction — all jobs use `CronTrigger` (absolute-time), none use `IntervalTrigger` | Code inspection, this phase |
| Database corruption | Nightly `scripts.db_backup` already runs a `PRAGMA integrity_check` before compression (CLAUDE.md Data Integrity section); its own test suite re-run this phase | `tests/test_db_backup_restore.py` — **10/10 passed** |
| Accumulation of stale state | `scheduled_signals` grows unbounded by design (documented in Phase 1 as an audit-log table, not a state table); no other growing table was found without either a retention mechanism or a natural, small per-cycle growth rate (Phase 1 §6) | Carried forward from Phase 1, re-affirmed |
| Recovery after simulated provider disconnect | **Not tested against the live provider this phase** — the closest available evidence is Phase 1's `test_edge_veto_stage_exception_fails_open_to_default_sizing` (a DB-layer exception fails open) and this phase's confirmation that `run_ohlcv_coverage_check`/`run_token_health_check` exist specifically to detect a real Stockbit outage. Simulating an actual live-network disconnect against the real Stockbit endpoint was out of reach without live-box access and was not attempted against any external service from this environment | Partial — see Risks |

---

## Recommended Operational Procedures

Extending, not replacing, `docs/OPERATIONS.md`'s existing runbook:

**Startup:** `systemctl --user start idx-walkforward` only — never `python app.py` /
`bash start.sh` / `nohup ./start.sh` on the box while the unit is enabled (a second process grabs
:5001 and crash-loops the systemd unit while the manual instance silently keeps serving — a
documented recurring incident). Confirm with `systemctl --user status idx-walkforward` (active) and
`curl localhost:5001/health` (`status: ok`, fresh `last_scan`).

**Shutdown:** `systemctl --user stop|restart idx-walkforward` — already graceful
(`worker_exit`'s `scheduler.shutdown(wait=True)`, bounded by `graceful_timeout=30`). No special
sequencing needed; do not `kill -9` the process, which would skip the graceful drain for no benefit.

**Daily health checklist** (extends `docs/OPERATIONS.md`'s existing checklist with this phase's
specific findings, does not replace it):
- [ ] `/health` → `status: ok`, `last_scan` within the last scheduled scan interval
- [ ] No 🔴 Stockbit Token alert (from `run_token_health_check`) overnight
- [ ] No OHLCV Coverage 🔴/⚠️ alert (from `run_ohlcv_coverage_check`)
- [ ] `open_trades` count in `/health` matches expectation; no unexplained jump (would indicate the
  entry-side duplicate guard was somehow bypassed)
- [ ] `systemctl --user status idx-walkforward` active, `NRestarts` stable since yesterday
- [ ] (existing) EOD Trade Plan / Premarket Shortlist / Forward-Testing Summary all arrived

**Log rotation guidance:** already correctly configured — `logs/app.log` rotates at 10 MB × 5
backups (`utils/logging_config.py`); nothing to change. `logs/cron_*.log` files are not covered by
that rotation; if disk pressure is ever observed on the real host (unverified this phase — see
Risks), a simple `logrotate` drop-in for `logs/cron_*.log` would be the minimal fix, not attempted
here since it wasn't confirmed to be a real problem.

**Database maintenance guidance:** already correctly configured — nightly `scripts.db_backup`
(integrity check + row counts + WAL-safe online backup, 7 daily + 4 weekly retention) and the weekly
restore drill (`docs/OPERATIONS.md`: "a backup is not considered good until this has passed").
Nothing new recommended; verifying the weekly drill's log (`logs/cron_db_restore_drill.log`) on the
real host is an existing checklist item, not a new one.

**Recovery procedure after unexpected reboot:** systemd's `Restart=always` brings the unit back
without manual intervention. Post-reboot, confirm via the daily health checklist above; if `NRestarts`
jumped unexpectedly, check `journalctl -u idx-walkforward-5001 | grep -E "Address already in use"`
for the documented manual-launch collision pattern before assuming a code defect.

---

## Test Results

| Suite | Result |
|---|---|
| `tests/test_close_trade_duplicate_prevention.py` (new, this phase) | **3 passed, 0 failed** |
| Full targeted suite touched by this phase's fix (`tests/agent_firm/`, historical-replay + scanner integration, sizing, monitor exit review, pipeline health, DB backup/restore) | **205 passed, 0 failed** |
| Full repository suite (`pytest -q --ignore=tests/agent_firm/providers`) | **1635 passed, 44 failed, 9 errors** in 538.0s |

## Regression Analysis

**Baseline** (Phase 1's certified run): 1633 passed / 43 failed / 9 errors.

**This phase:** 1635 passed / 44 failed / 9 errors.

Reconciles exactly: **+3** new tests in `tests/test_close_trade_duplicate_prevention.py`, all
passing, **−1** because `tests/regime/test_storage.py::test_append_only_rerun_makes_a_new_profile_id`
— already documented across every prior session in this sequence as a known, order/timing-sensitive
flaky test unrelated to any Agent Firm/paper-trade/scheduler code — flipped from passing (in Phase
1's run) to failing (in this run). `1633 + 3 − 1 = 1635` passed; `43 + 1 = 44` failed. Zero files
under `research/` or `tests/regime/` were touched this phase or last. Every other failure/error is
the same pre-existing Windows-local-tooling set carried across every session in this sequence
(`test_release_scripts.py`, `test_secret_hygiene.py`, `test_auto_token.py`,
`test_config_validation.py`, `test_cron_contract.py`, `test_experiment_tracking.py`,
`test_logging_config.py`, `test_news_filter.py`, `test_stockbit_fetcher_ensure_valid_token.py`,
`test_value_format.py`).

**Zero unexplained regressions.**

---

## Remaining Risks

1. **No real Ubuntu resource/latency measurements this round** (§6) — the single largest gap
   against this phase's own stated objectives. Recommend capturing `ps`/`systemd-cgtop`/`du`/
   `wc -l` snapshots on the real host during a live session as soon as access is available; this is
   the same recommendation Phase 1 made, now stronger since even the indicative Windows numbers
   weren't refreshed (they didn't need to be — no code in that path changed).
2. **Provider latency is uninstrumented** (§2) — a genuine, pre-existing gap, not something to
   silently patch under this task's "no new features" rule; worth a small, separately-scoped
   follow-up (timing wrapper around `flow_filter`/`stockbit_fetcher` calls) if provider latency
   becomes an active operational concern.
3. **No live-provider-disconnect test against a real endpoint** (§5) — the existing fail-soft/
   alerting mechanisms are verified correct in isolation; an actual live outage's real-world
   behavior remains unobserved. Recommend treating the next real Stockbit outage (there will be one
   — `run_token_health_check`'s own docstring references a real 2026-07-04 incident) as a natural
   validation opportunity: confirm the alert fires and the pipeline degrades as designed, rather
   than manufacturing an artificial one against production.
4. **Third-party memory behavior over multi-day uptime is unverified** (§5) — this phase's code-level
   cache audit is thorough but cannot substitute for observing real RSS over a real multi-day run.

None of these four block continuous paper-trading operation; all are honestly-scoped follow-ups, not
newly-discovered blockers.

---

## Recommendation

# GO WITH CONDITIONS

**Rationale for GO:** the one genuine defect this phase's objectives were designed to surface (an
asymmetry between entry-side and exit-side duplicate-trade protection) was found and fixed with a
minimal, targeted, already-regression-tested change; every other continuous-operation/shutdown/
scheduling/DB-integrity mechanism this phase examined was already correctly built and already
independently tested; zero unexplained regressions across a 1635-test full-suite run.

**Conditions (carried and refined from Phase 1, plus this phase's own):**

1. Capture real CPU/RSS/disk/DB-growth/log-growth numbers on the actual Ubuntu host during a live
   trading session as soon as access is available — this remains not done, not merely
   indicative-only, for two phases running now.
2. Treat the next real Stockbit provider outage as the actual validation event for Objective 5's
   "recovery after disconnect" — don't manufacture one against production to close this report's
   gap artificially.
3. Provider-latency instrumentation remains a genuine, tracked gap, appropriately out of scope for
   this validation-only task.
4. Real-provider (Z.ai/Claude) Agent Firm latency at production scale remains validated only by the
   existing manual smoke probe, unchanged across every session in this sequence.
