# Operations Runbook

**Version:** 1.0 · **Status:** ACTIVE · **Effective Date:** 2026-07-29
**Scope:** Recurring daily/weekly/monthly operating procedures, monitoring strategy, and incident
response for the IDX Walkforward Strategy Suite in continuous operation. Companion to
`Audit/PRODUCTION_DEPLOYMENT_GUIDE.md` (one-time/event-driven procedures) and
`Audit/PAPER_TRADING_OPERATING_PROCEDURE.md` (trading-specific procedures). Consistent with, and a
detailed expansion of, `docs/OPERATIONS.md`'s "Operational checklist" section — that section remains
the terse quick-reference; this document is the walkthrough with reasoning and thresholds attached.

---

## 1. Daily Operating Procedure

All times WIB (Asia/Jakarta, UTC+7). IDX market hours: 09:00–15:30 WIB Mon–Fri.

### 1.1 Morning Checklist (before 08:35 premarket job)

- [ ] `systemctl --user status idx-walkforward` — `active (running)`, check `NRestarts` hasn't
      incremented overnight (an increment with no corresponding planned restart is itself a signal
      — check `journalctl` for why it restarted).
- [ ] `curl -s localhost:5001/health | python3 -m json.tool` — `status: ok`, `db: ok`, a
      `last_scan` timestamp from the previous trading day (or today if premarket has already run).
- [ ] No `🚨 CRON FAIL` Telegram messages overnight (from `scripts/cron_wrap.sh`'s alert path —
      covers `auto_token`, `stockbit_ohlcv`, `stockbit_flow`, `heartbeat_check`, `db_backup`, and on
      Sundays `db_restore_drill`).
- [ ] No `🔴 Scheduler Job Failed` alerts (`EVENT_JOB_ERROR` listener, `scheduler/__init__.py`). If
      any alert includes a "+N suppressed" count, the job has been failing repeatedly under the
      `SCHEDULER_JOB_ERROR_COOLDOWN_S` (default 3600s) rate-limit window, not just once — check
      `logs/app.log` for that `job_id` across the whole overnight window, not just the alert's own
      timestamp.
- [ ] `auto_token.py --check` (or confirm the 08:40 cron already refreshed it) — a stale Stockbit
      JWT silently degrades the 08:50 OHLCV fetch to failure.
- [ ] `logs/heartbeat_check.log` quiet (no alert lines) — the `*/10 * * * *` dead-man's-switch is
      the one signal that proves the *process*, not any individual job, is alive.
- [ ] Disk headroom sanity check (full check is weekly, §2.1; a quick `df -h /home` here catches
      anything acute before market open).

### 1.2 Market-Open Checklist (~09:00 WIB)

- [ ] Confirm the **Premarket Shortlist** report (08:35 WIB, `scheduler.jobs.run_premarket_firm_scan`)
      actually arrived in Telegram — it contains a PREMARKET SUMMARY (regime, risk tier, candidate
      counts, highest conviction) plus 📈 NEW / 📉 REMOVED / ⬆ UPGRADED / ⬇ DOWNGRADED / 🟢 STABLE
      sections. A missing report with **no** accompanying crash alert suggests the `_job_sentinel`
      dedup guard false-positived (e.g. a stale sentinel row from a prior manual run) — check:
      ```sql
      SELECT * FROM _job_sentinel WHERE job='premarket_firm' AND run_date=date('now','localtime');
      ```
      A row present with no Telegram message received means the job believed it already ran —
      investigate before manually re-triggering (re-triggering after deleting the sentinel row risks
      a duplicate send if the original silently did complete).
- [ ] Regime/risk tier in the Premarket Summary is sane relative to what you'd expect from the prior
      day's close — a wildly inconsistent regime read is worth a manual sanity check against price
      action before trusting the day's shortlist.
- [ ] `/health`'s `event_guard` and `macro_panic_state` fields (`app.py:97-103`) reflect current
      conditions, not a stale fail-soft default (`{"active": false, "error": ...}` means the guard
      check itself errored — investigate, don't just read `active: false` as "guard is off by
      design").
- [ ] Agent firm provider health — no unexpected single-provider `WARNING` in `journalctl` (would
      mean failover silently isn't configured); check quota state if either provider has recently
      alerted:
      ```sql
      SELECT provider, event_type, reason, reset_time, created_at
      FROM provider_events
      WHERE event_type IN ('provider_session_limit','provider_restored')
      ORDER BY id DESC LIMIT 10;
      ```

### 1.3 Intraday Monitoring (09:00–15:30 WIB)

- [ ] Spot-check `/health` at least once mid-session — `open_trades` count should track what you
      expect from the morning's shortlist plus/minus any manual actions.
- [ ] Watch Telegram for `monitor.py`'s SL/TP/trailing-stop alerts on open paper trades
      (`monitor.py::check_all_open_trades`, invoked on the scheduler's monitoring cadence) —
      each auto-close (swing-trend R1–R7 triggers, or the generic SL/TP/trail path in
      `_check_trade`) sends a Telegram message and logs via `screener.db.log_trade_alert`.
  - **Known gap to watch for:** `monitor.py`'s per-trade loop currently has no per-trade exception
    isolation (`Audit/PRODUCTION_ENGINE_BACKLOG.md` P1-4) — an unhandled exception evaluating trade
    N can abort monitoring for every trade after N in that tick, silently. If you notice a trade
    that should have triggered an alert but didn't, check `logs/app.log` around that monitoring
    tick for an unhandled exception on an *earlier* ticker in the same run, not just the ticker in
    question.
- [ ] Watch for `🔴 Scheduler Job Failed` alerts firing mid-session — these are the highest-signal
      indicator something in the live pipeline (scan, monitor, flow fetch) broke while the market is
      open, when it matters most.
- [ ] If a DD (drawdown) circuit breaker trips (`paper_trade.py::check_dd_circuit_breaker`), entries
      are blocked (`is_entries_blocked()`) but existing open trades continue to be monitored — verify
      this is the expected behavior for the trip you're seeing, and check `get_summary()` /
      the DD status route for context on why it tripped.

### 1.4 Market-Close Checklist (~15:30–16:40 WIB)

- [ ] Confirm the **EOD Trade Plan** report (16:40 WIB, `scheduler.jobs.run_eod_trade_plan`) arrived
      — agent-ranked long shortlist plus a Watchlist Changes section (added/removed/upgraded/
      downgraded, rank + confidence deltas via `engine/trade_plan.py::diff_watchlist()` against the
      `watchlist_snapshot` table, `strategy='eod'`).
  - This job's dedup-guard `OperationalError` handling was hardened (`scheduler/jobs.py:983-994`,
    RC1 fix F-3) to fail open under DB write contention rather than crash — a missing EOD report
    should now surface via `EVENT_JOB_ERROR` alert rather than silently vanishing. If you see
    neither the report nor a crash alert, treat that as its own anomaly worth investigating (not
    the previously-known failure mode).
- [ ] Cross-check the Watchlist Changes section against your own read of the day's price action for
      anything that looks like a data artifact (e.g. a ticker "upgraded" on stale flow data).
- [ ] Confirm the 18:30 WIB **Forward-Testing Summary** (`scheduler.jobs.run_forward_test_cycle`,
      `forward_testing/reporting.py`) arrived — new/closed/active shadow positions, cumulative
      win/loss scoreboard, best/worst closed trades. Exit reasons (SL/TP/TRAIL/TIME/STALE) are shown
      verbatim; do not reinterpret them into a different taxonomy when reviewing.
- [ ] Post-close flow fetch (`18:30` cron, `stockbit_fetcher.py flow`) completed without a
      `🚨 CRON FAIL` alert — this runs after the APScheduler 16:05 cycle finishes (~16:25) by design;
      an overlap alert here may indicate the earlier cycle ran long.

### 1.5 End-of-Day Review

- [ ] All three daily reports (Premarket 08:35, EOD 16:40, Forward-Testing 18:30) accounted for —
      arrived, or a known/investigated reason why not.
- [ ] Any DD circuit-breaker trips, provider quota exhaustion, or `EVENT_JOB_ERROR` alerts from the
      day are logged in your own incident/ops log with root cause (even if root cause is "known,
      transient, self-recovered") — don't rely on Telegram history alone as the record; it isn't
      queryable and isn't retained indefinitely.
- [ ] Nightly backup (21:30 cron) — confirm it completes tonight; check tomorrow morning
      (§1.1) that no `🚨 CRON FAIL` for `db_backup` came through.
- [ ] If today included a deploy, confirm the post-deploy checklist in
      `Audit/PRODUCTION_DEPLOYMENT_GUIDE.md` §11 was fully worked, not just "service came back up."

---

## 2. Weekly Operating Procedure

### 2.1 Database Maintenance

- [ ] Confirm the Sunday 09:00 WIB restore drill (`0 9 * * 0`, `scripts.db_restore` verify-only on
      the newest backup) actually ran and passed:
      ```bash
      tail -30 logs/cron_db_restore_drill.log
      ```
      **Do not assume it ran from the crontab entry's presence alone** — a documented ~36h gap in
      this exact job occurred once (2026-07-25/26, `Audit/PRODUCTION_ENGINE_BACKLOG.md` P1-2/P2-6)
      and went undetected until manually noticed; there is currently no dead-man's-switch on the
      drill's own cadence (only the general scheduler heartbeat, a different mechanism). Treat this
      as a manual verification step until that gap is closed.
- [ ] SQLite health: `PRAGMA integrity_check` is already run by every backup/restore cycle — if you
      want an out-of-band check on the *live* DB (not just the backup), run it during a low-traffic
      window: `sqlite3 <DB_PATH> "PRAGMA integrity_check;"`.
- [ ] WAL file size sanity check — `data/db.py::connect()` sets `journal_mode=WAL`; an unusually
      large `-wal` sidecar file can indicate a checkpoint isn't happening (e.g. a long-held read
      transaction somewhere). `ls -la $(dirname $DB_PATH)/*.db-wal`.

### 2.2 Log Review

- [ ] `logs/app.log` (structured JSON, rotating 10 MB × 5) — scan for WARNING/ERROR-level entries
      across the week that didn't trigger a Telegram alert (not everything logged reaches Telegram —
      e.g. degraded/fail-soft paths that recovered on their own).
- [ ] `logs/cron_*.log` — spot-check each job's log for the week; a job that "succeeded" (exit 0)
      can still have produced warnings worth reading in its own output.
- [ ] `journalctl --user -u idx-walkforward --since "-7 days"` — any unplanned restarts, OOM kills,
      or systemd-level anomalies not visible in application logs.
- [ ] Confirm `utils.logging_config.redact_secrets()` is doing its job — no plaintext secret-shaped
      value should appear in `logs/app.log` for any of `_SECRET_VARS`
      (`TELEGRAM_TOKEN`, `ZAI_API_KEY`, `DEEPSEEK_API_KEY`, `TAVILY_API_KEY`, `FLASK_SECRET_KEY`,
      `STOCKBIT_PASS`, per `utils/logging_config.py:82-84`). **Known gap:** the Stockbit bearer JWT
      itself (as opposed to `STOCKBIT_PASS`, the login password) is not in `_SECRET_VARS`
      (`Audit/PRODUCTION_ENGINE_BACKLOG.md` P1-5) — if you spot a raw JWT in a log line during
      review, that's the known gap manifesting, not a new defect; still worth flagging for
      prioritization.

### 2.3 Paper-Trade Review

See `Audit/PAPER_TRADING_OPERATING_PROCEDURE.md` §"Weekly Operating Procedure" for the full
checklist. Summary here for runbook completeness:
- [ ] Review the week's closed trades (`get_summary()` / paper trade routes) — win rate, average
      R-multiple, exit-reason distribution (SL vs TP vs TRAIL vs TIME vs STALE) against expectations
      for the strategy mix in play.
- [ ] Review any DD circuit-breaker trips this week and confirm they resolved (entries unblocked)
      as expected, not stuck blocked past their intended window.
- [ ] Spot-check a handful of the week's `evaluate_premover_trade`/`open_trade` gate rejections
      (`skip_reason`: `dd_circuit_breaker`, `max_open_N`, `already_open`, regime filter) for anything
      that looks like a gate firing on bad input rather than a correct reject.

### 2.4 Performance Review

- [ ] Agent-firm provider health for the week — failover/timeout rates:
      ```sql
      SELECT event_type, provider, COUNT(*) FROM provider_events
      WHERE created_at >= date('now', '-7 days') GROUP BY 1, 2;
      ```
      Sudden increases in `circuit_open`, `provider_session_limit`, or `unexpected_error` events
      warrant investigation before they become a full outage.
- [ ] Decision latency / throughput if the Operations Dashboard metrics from
      `Audit/AF2_POST_DEPLOYMENT_MONITORING_PLAN.md` are being tracked manually (no dashboard exists
      yet — see §6 below) — at minimum, spot-check that agent-firm decision volume for the week is
      in the expected range, not silently near-zero (which would indicate fail-open masking a
      systemic provider issue rather than genuine low signal volume).
- [ ] Disk: `df -h /home` and `du -sh ~/backups/idx-walkforward-5001` — trend week over week, not
      just the absolute number (full monthly disk review in §3.2).

---

## 3. Monthly Operating Procedure

### 3.1 Backup Verification

- [ ] Beyond the weekly automated drill, do a **manual, end-to-end restore rehearsal** at least
      monthly against a scratch environment (not production) — decompress a real recent backup,
      apply it (`scripts.db_restore --apply --db <scratch-path>`), and confirm the app can actually
      boot against the restored file (`validate_config()` passes, `/health` on a locally-started
      instance is green). The weekly cron drill verifies integrity and row counts; it does not
      exercise the app actually starting against the restored file end-to-end.
- [ ] Confirm off-host backup replication is functioning (see
      `Audit/PRODUCTION_DEPLOYMENT_GUIDE.md` §9.1 — this is flagged as an unverified/likely-missing
      step; monthly review is the checkpoint to either confirm it exists or escalate that it
      doesn't).
- [ ] Review retention: `ls ~/backups/idx-walkforward-5001/` should show roughly 7 daily + 4 weekly
      points per `scripts/db_backup.py::prune()`'s policy — a count far outside that range means
      pruning isn't running as expected.

### 3.2 Disk Usage

- [ ] `df -h /home` — trend against prior months; the DB alone was ~3.2 GB / 52 tables / 24M+ rows
      at the last full restore-drill measurement (2026-07-10, `docs/OPERATIONS.md`) and grows over
      time.
- [ ] `du -sh ~/backups/idx-walkforward-5001` and `du -sh ~/releases/idx-walkforward/*` — old
      release directories are never auto-pruned by `scripts/release.sh`/`rollback.sh` (by design,
      for rollback safety); decide and execute a manual retention policy for releases beyond what
      you need for rollback confidence, rather than letting them accumulate unbounded.
- [ ] `du -sh logs/` — rotation is 10 MB × 5 for `app.log`, but `logs/cron_*.log` files are
      append-only with no built-in rotation; confirm they aren't growing unbounded.

### 3.3 Provider Health

- [ ] Full-month `provider_events` review (extend §2.4's weekly query to `-30 days`) — look for
      trend shifts in circuit-breaker trips, quota exhaustion frequency, or a creeping increase in
      `unexpected_error`/`unknown` classification (a category that should stay near zero — anything
      landing there is, by construction, not yet mapped to a specific known failure mode).
- [ ] Confirm `AGENT_FIRM_CLAUDE_MAX_CALLS_PER_DAY` headroom is adequate for current firm volume —
      if the Claude leg is regularly approaching the cap, that's a capacity-planning signal, not
      just a quota-routing event.
- [ ] Reconfirm the Claude CLI is still discoverable on `PATH` on the production host (a host-level
      change — OS update, PATH change — could silently break this without any config change on the
      repo side; `validate_config()` only checks this at startup, not continuously).

### 3.4 Configuration Audit

- [ ] Diff the live `.env` against `.env.example` — flag any variable present in one but not the
      other (a stale var no longer read, or a new var not yet set).
- [ ] Re-confirm `AUTH_MODE` matches the intended posture for this deployment stage
      (`off`/`shadow`/`enforce`) — `Audit/PRODUCTION_ENGINE_BACKLOG.md` P2-10 notes the last
      confirmed production value was `off` as of 2026-07-28; re-verify this hasn't silently drifted.
- [ ] `TELEGRAM_WEBHOOK_SECRET` — as of `Audit/OPERATIONAL_HARDENING_REPORT.md` (2026-07-29),
      `validate_config()` now refuses to start without it (matching `TELEGRAM_TOKEN`'s pattern), so a
      silent drift will fail the *next restart* rather than go unnoticed — this checklist item is now
      a belt-and-suspenders confirmation, not the only safety net. (Uncommitted; see §6/§Deployment
      Guide note — confirm this fix has actually been deployed before relying on it.)
- [ ] Re-run `tests/security/test_route_policy.py` against the live route set to confirm no route
      was added since the last audit without a classification (this should already be CI-blocked at
      merge time, but a monthly re-run against production's actual deployed commit is a
      belt-and-suspenders check for anything merged outside normal review).
- [ ] Review `Audit/PRODUCTION_ENGINE_BACKLOG.md` itself for newly-closed vs. still-open items — it
      is the canonical, dated tracking document for outstanding operational debt; this monthly audit
      should reconcile against it rather than maintaining a second, parallel list.

---

## 4. Operational Checklist (quick reference)

Daily (or after any alert) — same as `docs/OPERATIONS.md`'s existing checklist, repeated here for
completeness:
- [ ] Telegram: no 🚨 CRON FAIL / ⚠️ FAIL-OPEN messages overnight
- [ ] Telegram: 🔴 Scheduler Job Failed alerts — check "+N suppressed" counts
- [ ] Three daily reports arrived (Premarket 08:35, EOD 16:40, Forward-Testing 18:30)
- [ ] `systemctl --user status idx-walkforward` active; NRestarts stable
- [ ] `/health` returns `status: ok` and a fresh `last_scan`
- [ ] Heartbeat watchdog quiet (`logs/heartbeat_check.log`)

Weekly:
- [ ] Sunday restore drill passed (`logs/cron_db_restore_drill.log`)
- [ ] `provider_events`: failover/timeout rates sane
- [ ] Disk: `df -h /home` and `du -sh ~/backups/idx-walkforward-5001`
- [ ] Paper-trade review complete (`Audit/PAPER_TRADING_OPERATING_PROCEDURE.md`)

Monthly:
- [ ] Manual end-to-end restore rehearsal
- [ ] Off-host backup replication confirmed
- [ ] Release/log directory disk growth reviewed
- [ ] `.env` vs `.env.example` diff reviewed; `AUTH_MODE`/`TELEGRAM_WEBHOOK_SECRET` re-confirmed
- [ ] `Audit/PRODUCTION_ENGINE_BACKLOG.md` reconciled against actual closed/open state

After any deploy (cross-reference `Audit/PRODUCTION_DEPLOYMENT_GUIDE.md` §11 for the full version):
- [ ] `scripts/wait_for_health.sh`
- [ ] `journalctl --user -u idx-walkforward -n 50` — startup clean, registry announced
- [ ] Full test suite green (CI, not just local) before merging to the deploy branch

---

## 5. Incident Response

General principle for every incident type below: **check `/health`, `journalctl`, and the relevant
`logs/*.log` in that order before taking any corrective action** — most of this system's failure
modes are designed to be fail-soft/fail-open and self-describing in logs; a corrective action taken
before reading the actual error risks masking the real cause or, in the case of DB operations,
causing new damage.

### 5.1 Scheduler Crash / `EVENT_JOB_ERROR` Alert

**Signal:** Telegram `🔴 Scheduler Job Failed` message, naming the `job_id`.

1. Read the alert in full — it names the specific job, not just "something failed." Note whether it
   includes a "+N suppressed" count (repeated failures within the `SCHEDULER_JOB_ERROR_COOLDOWN_S`
   cooldown, default 3600s — treat as an ongoing problem, not a one-off).
2. `journalctl --user -u idx-walkforward | grep <job_id>` or grep `logs/app.log` for the same
   window — get the actual traceback, not just the alert summary.
3. Determine severity:
   - A scan/monitoring job failing mid-day is high urgency (directly affects trading decisions).
   - A reporting job (EOD/premarket/forward-test) failing is medium urgency (visibility loss, not
     a trading-correctness issue) — but confirm the underlying data pipeline it reports on didn't
     also fail for the same root cause.
   - A research/backfill job failing (these run on cron, not APScheduler, and don't go through this
     listener) is out of scope for this alert type — see §5.2 for cron failures generally.
4. The process itself keeps running (`Restart=always` covers a full process crash; this listener
   covers an *in-process* job exception that doesn't crash the worker) — do not restart the service
   as a first response unless the traceback indicates corrupted in-memory state. Fix the underlying
   cause, or if it's a known-transient condition (e.g. a provider timeout), confirm the next
   scheduled run of the same job self-recovers.
5. If suppressed-count alerts keep escalating without resolution, treat as a standing incident —
   don't let repeated cooldown-suppressed failures become invisible background noise.

### 5.2 Telegram Delivery Failure

**Signal:** `logs/cron_*.log` shows `ALERT SEND FAILED` (from `cron_wrap.sh`) or `logs/app.log`
shows a `send_telegram`/`send_telegram_reply` exception; or — more insidiously — you notice an
*absence* of an expected report with no visible error at all.

1. Check Telegram bot token/chat ID validity directly:
   ```bash
   curl -s "https://api.telegram.org/bot${TELEGRAM_TOKEN}/getMe"
   ```
2. Check for Telegram API-side outage/rate-limiting (HTTP 429 or 5xx from the above call).
3. If `cron_wrap.sh` itself couldn't find credentials (`ALERT SKIPPED (no telegram creds)` in the
   job log), check `.env` wasn't accidentally truncated/corrupted, and its permissions are still
   600 (a permission or encoding issue can make `grep` inside `cron_wrap.sh` fail silently).
4. Once root cause is fixed, do **not** manually re-send historical alerts — the dedup guards
   (`_job_sentinel`) mean a manual re-trigger of a reporting job risks a duplicate send once
   delivery is restored; prefer explaining the gap in the next natural report or a manual one-off
   message, not replaying the job.
5. This is the one alert-delivery path with an unredacted gap: `cron_wrap.sh`'s own Telegram send
   (used for its own `🚨 CRON FAIL` alerts) is shell-based and does not go through
   `redact_secrets()` (`Audit/PRODUCTION_ENGINE_BACKLOG.md` P1-7) — be aware that a cron failure
   message containing an exception with an embedded secret could itself leak unredacted. Do not
   forward raw cron-failure alert text outside the operational team until this is closed.

### 5.3 Provider Failover Exhaustion (agent firm)

**Signal:** `⚠️ FAIL-OPEN` alert, or a `provider_events` query showing both providers in
`provider_session_limit`/circuit-open state simultaneously.

1. Confirm both providers' state and reset times:
   ```sql
   SELECT provider, event_type, reason, reset_time, created_at
   FROM provider_events ORDER BY id DESC LIMIT 20;
   ```
2. If both are session-limited: this is time-based recovery, not a config problem — confirm the
   reset times shown are sane (not implausibly far out, which would indicate a reset-time parsing
   failure defaulting to the max fallback hold, `AGENT_FIRM_QUOTA_MAX_HOLD`, default 21600s/6h).
3. If Claude is limited: remember the quota window is **shared with interactive Claude Code use on
   the same account** (`docs/OPERATIONS.md`) — heavy interactive usage during market hours can
   itself induce this incident. This is a known, documented tradeoff, not a bug to fix in code.
4. Confirm the agent-firm gate's fail-open behavior is doing what's expected — signals should still
   flow through the pipeline without agent review during an outage window (flow-gate fail-open
   policy), not silently block all signal processing. If signals are being blocked instead of
   fail-open, that's a distinct, higher-severity bug, not the expected exhaustion behavior.
5. If exhaustion is recurring frequently (not just occasional), it's a capacity issue — consider a
   metered API key for the firm (noted in `docs/OPERATIONS.md` as the structural fix, out of scope
   of the quota-routing mechanism itself) rather than repeatedly treating each occurrence as a
   one-off incident.

### 5.4 DB Lock / Corruption

**Signal:** `sqlite3.OperationalError` (lock timeout beyond the 30s `busy_timeout` set by
`data/db.py::connect()`) in logs, or a failed `PRAGMA integrity_check` from a backup/restore run.

1. **Lock timeout (not corruption):** identify the long-held writer — check for an unusually long
   cron job (e.g. `research.cli wf-refresh`, which explicitly runs off the production scheduler but
   still writes to the same DB file) overlapping with a production write. `data/db.py::connect()` is
   the single connection entry point (WAL + `busy_timeout=30000`) — if you find code calling
   `sqlite3.connect()` directly instead, that's the actual bug (`CLAUDE.md`'s "Things Contributors
   Must Never Do"), not a transient lock.
2. **Integrity check failure:** this should only ever be discovered via the backup/restore pipeline,
   which already deletes a corrupt backup snapshot rather than compressing/retaining it. If the
   *live* DB itself fails `PRAGMA integrity_check` when run manually, stop the service immediately,
   do not attempt writes, and restore from the most recent verified-good backup (§8.3 of the
   Deployment Guide) rather than attempting in-place repair.
3. Do not delete `-wal`/`-shm` side files by hand while the app is running — they're actively
   managed by SQLite's WAL mode; only touch them as part of a full stop + restore procedure.

### 5.5 Disk Full

**Signal:** `🚨 CRON FAIL` on `db_backup` (write failure), or `journalctl` showing the app itself
erroring on writes, or a direct `df -h` alert if one is configured externally (none is currently
wired into this repo's own alerting — a genuine gap; see §6).

1. `df -h /home` immediately — identify which mount is full.
2. Likely largest contributors, in order: `~/backups/idx-walkforward-5001` (bounded by retention,
   but a stuck prune could let it grow), `~/releases/idx-walkforward/*` (unbounded — never
   auto-pruned), `logs/cron_*.log` (unbounded — no built-in rotation), the live DB itself (grows
   with data, not typically the acute cause of a *sudden* full-disk event).
3. Safe to free space: manually remove old release directories beyond your rollback comfort window
   (never remove the current or immediately-prior release), truncate/rotate old `cron_*.log` files
   (do not truncate a file currently being written by an in-flight job).
4. Not safe to free space from: `~/backups/` without confirming what you'd be deleting is truly
   redundant with an off-host copy (see the DR gap noted in the Deployment Guide §9.1) — don't solve
   a disk-full incident by deleting the only copy of a needed backup.
5. Once resolved, retroactively check whether the nightly backup that failed during the disk-full
   window needs to be re-run manually before the next nightly cron fires, to avoid a longer-than-
   expected gap in verified recovery points.

### 5.6 Stale Heartbeat / Dead-Man's-Switch Trip

**Signal:** alert from `scripts/check_scheduler_heartbeat.py` (runs every 10 minutes via cron,
`*/10 * * * *`).

1. This is the highest-severity alert type — it means the *process itself* may not be alive, which
   is a stronger claim than any individual job or report failing (those can fail while the process
   stays up; this specifically catches the process being down or wedged).
2. `systemctl --user status idx-walkforward` — if inactive/failed, check `journalctl` for the crash
   reason before simply restarting (a crash-loop restarting blindly can mask a real config or code
   regression that will just crash again).
3. If active but the heartbeat still trips: the process is running but something inside it (event
   loop, scheduler thread) is wedged — a restart is the appropriate remediation here, but capture
   `journalctl`/thread state first if possible, since a wedge is harder to diagnose after restart
   destroys the in-memory state that caused it.
4. After recovery, cross-check whether any scheduled jobs were missed during the down window and
   whether they need manual catch-up (most reporting jobs are dedup-guarded by date, so a missed
   run generally means a missed report for that day, not corrupted state — confirm this is
   acceptable rather than assuming it).

---

## 6. Monitoring Strategy

**What exists today:**
- Telegram push alerts for cron failures (`cron_wrap.sh`), scheduler job errors (`EVENT_JOB_ERROR`
  listener, rate-limited per job), agent-firm provider quota transitions, and the three daily
  operational reports (all of which double as passive "the pipeline is alive" signals).
- `/health` HTTP endpoint — DB reachability, last scan time, open trade count, event-guard/macro-
  panic state. **Does not** currently check scheduler liveness (§10 of the Deployment Guide) —
  treat a green `/health` as necessary, not sufficient, evidence the system is fully healthy.
- `logs/heartbeat_check.log` + the 10-minute cron dead-man's-switch — the strongest "process is
  alive" signal available today.
- `provider_events` table — queryable history of every agent-firm routing decision, circuit state
  change, and quota event. This is the closest thing to a structured monitoring data source that
  exists in the repo today.
- `audit_events` table (when `AUTH_MODE` is shadow/enforce) — operational action + auth-failure
  trail, per `docs/SECURITY.md`.

**What does not exist today (known gaps, not to be assumed present):**
- No persisted, queryable "which jobs ran today and how long they took" ledger —
  `docs/OPERATIONS.md` states this explicitly: "N/A: job-error alerts are not persisted to a table
  today, only Telegram + `logs/app.log`." Reconstructing "what ran" currently means grepping logs.
- No dashboard/UI over any of the above — the standing next roadmap milestone ("Operations
  Dashboard / Job History," `Audit/PRODUCTION_ENGINE_NEXT_MILESTONE.md`,
  `Audit/PRODUCTION_ENGINE_BACKLOG.md` P1-8) exists specifically to close this gap, and has not yet
  started (no design doc found under `docs/` or `Audit/` as of this writing).
- No external disk-space or host-level alerting wired into this repo's own Telegram pipeline — disk
  checks are manual (§2.4, §3.2) unless something else at the infra layer (outside this repo) covers
  it. Confirm whether such infra-level monitoring exists separately; do not assume this repo's
  Telegram alerts cover it.
- No dead-man's-switch on the *backup/restore-drill* cadence specifically (only the general
  scheduler heartbeat) — the ~36h gap incident in §2.1 is the concrete cost of this gap.

**Recommended monitoring posture until the dashboard milestone lands:** treat the Daily/Weekly/
Monthly checklists in this document as the monitoring system — they are manual because no
automated equivalent exists yet, not because manual is preferred. Prioritize closing the P1-2/P2-6
backup-drill dead-man's-switch gap and the `/health` scheduler-liveness gap (P1-6) as the two
highest-leverage automation additions, since both convert an already-happened incident class from
"discovered late by a human" to "alerted immediately."

---

## 7. Cross-References

- `docs/OPERATIONS.md` — canonical quick-reference (this document expands, does not replace it).
- `Audit/PRODUCTION_DEPLOYMENT_GUIDE.md` — installation, startup/shutdown, upgrade, rollback, DR.
- `Audit/PAPER_TRADING_OPERATING_PROCEDURE.md` — trading-specific validation and procedures.
- `Audit/PRODUCTION_ENGINE_BACKLOG.md` — canonical, dated, prioritized (P0–P3) list of open items;
  the authoritative source for "is X actually fixed yet," supersedes any older audit report's status
  claims on the same item.
- `docs/SECURITY.md` — auth modes, route policy, audit trail.
- `Audit/AF2_POST_DEPLOYMENT_MONITORING_PLAN.md` — the 9 proposed agent-firm metrics that should
  inform the eventual Operations Dashboard design.
