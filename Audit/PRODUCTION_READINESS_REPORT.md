# Production Engine — Production Readiness Report

**Date:** 2026-07-28
**Scope:** Phases 1–2 of the final adversarial release certification — repository-wide audit (startup,
configuration, scheduler, runtime, database, migrations, backup, restore, monitoring, logging, paper
trading, execution, agent firm, shutdown, recovery, deployment, release packaging) plus operational-
readiness verification. Generated, point-in-time record.
**Method:** Six parallel adversarial investigations (one per subsystem cluster) plus direct,
executed verification by this reviewer (a live isolated cold-start smoke test of `init_runtime()`,
direct inspection of the installed APScheduler library source to verify `shutdown(wait=)` semantics,
and direct reproduction of one crash). Every finding below is evidence-backed (file:line or a
reproduced failure) — nothing is asserted from inspection alone without a citation.
**Constraint honored:** no architecture changes, no new features, no refactors. Six fixes were
applied, each a minimal, isolated, evidence-backed correction to a genuine defect found during this
audit — not present in the certification brief's example list, but squarely inside "fix only genuine
production defects."

---

## Summary

Six genuine production defects were found and fixed this session (all committed, all validated). Two
of them are release-blocking in nature (P0): a boot deadlock on any fresh/disaster-recovery deploy,
and a crash-on-startup risk on any non-UTF-8 host. A further ~15 real findings were identified,
evidenced, and classified but **not** fixed in this pass — each is a genuine risk, but fixing it
either required a design decision this review isn't positioned to make unilaterally (e.g. changing
fail-open security behavior on an already-live system), touched more files than "minimal and
isolated" allows, or required new operational infrastructure rather than a code correction. These are
listed as required follow-up work, not silently accepted.

**No finding here is a regression introduced by RC1's own delivered work** (the Telegram reporting,
crash-alert rate limiting, and redaction fixes already certified in
`Audit/RC1_FINAL_CERTIFICATION_2026-07-28.md`). Everything found is pre-existing on this long-lived
branch, surfaced only because this is the first time the whole repository has been adversarially
re-examined end-to-end in one pass.

---

## Findings — Fixed This Session

### P0 — `paper_trades` table never created at startup → fresh-deploy boot deadlock

**Evidence (reproduced live, not inferred):** An isolated cold-start smoke test
(`init_runtime()` against a fresh, empty DB with a sandboxed `.env`) showed `init_runtime()` succeeds
on first boot (42 jobs registered, 12 tables created — `scheduled_signals` among them, via
`init_agent_firm_tables()`) but **never creates `paper_trades`** (created only lazily by
`paper_trade.py::init_paper_table()`, called only from `routes/backtest.py` and
`scheduler/jobs.py:477` — never from `init_runtime()`). A second `init_runtime()` call against the
same DB then raised `config.ConfigError: DB missing required table: paper_trades` — `validate_config()`'s
own DB-compatibility check (`config.py`) correctly refuses to boot once the DB is non-empty but
missing a required table.

**Why this is P0:** this is a *self-reinforcing deadlock* — the app won't restart because the table
doesn't exist, but the table can only be created by code that runs only after the app has already
started. Any fresh environment, disaster-recovery restore, or from-scratch setup would boot exactly
once and then be permanently unable to restart until an operator manually intervenes. Does not affect
the currently-running production database (it already has this table from historical use).

**Fix (commit `4826cae`):** `app.py::init_runtime()` now calls `paper_trade.init_paper_table()`
alongside the three table-init calls it already makes, same pattern, same place. Verified: a
simulated restart against the same DB now succeeds.

### P0 — crash-prone redundant `print()` in registry announcement, unprotected inside scheduler startup

**Evidence (reproduced live):** `engine/registry_loader.py::announce_registry()` (called from
`scheduler/__init__.py::start_scheduler()`, itself called from `init_runtime()`) did both
`logger.info(msg)` and `print(f"  {msg}")` for an identical message containing a literal emoji.
`logging.StreamHandler.emit()` swallows `UnicodeEncodeError` internally (its default `handleError()`
behavior), so the logger call never crashes — but the bare `print()` has no such protection.
Reproduced directly: this crashed with `UnicodeEncodeError` on this Windows dev venv's cp1252
console, during the actual cold-start smoke test above.

**Why this is P0:** `start_scheduler()`'s ~20 `add_job()` calls and this announcement have no
wrapping try/except (see Finding P1 below) — this specific exception, if it fires, aborts the entire
worker boot. Any host whose stdout encoding isn't UTF-8 (a minimal container base image, certain
locale configurations) would hit this on every single restart.

**Fix (commit `e30d4f3`):** deleted the redundant `print()` line — the message is already fully
covered by the properly-configured, dual-handler (file + console) structured logger. No observability
lost.

### P1 — `gunicorn.conf.py::worker_exit` used `shutdown(wait=False)`, contradicting its own stated purpose

**Evidence:** the function's own docstring states its purpose is "so in-flight jobs aren't killed
mid-write." Verified directly against the installed APScheduler library's
`BaseScheduler.shutdown()` docstring: `wait=True` is "wait until all currently executing jobs have
finished"; `wait=False` (what the code actually used) does not wait at all.

**Concrete risk:** all three daily Telegram report jobs (EOD/Premarket/Forward-Test) `INSERT` into
`_job_sentinel` *before* doing the real work — a `SIGTERM` landing between that insert and the
eventual `send_telegram()` call (plausible during a deploy/restart at 08:35, 16:40, or 18:30 WIB)
would previously let the worker exit without waiting, permanently dropping that day's report with no
retry (the sentinel already marks it "sent").

**Fix (commit `368f6c8`):** changed to `wait=True`, bounded by gunicorn's existing
`graceful_timeout=30` as a backstop if a job genuinely hangs. Also changed the bare
`except Exception: pass` on the same call to log a warning instead of silently swallowing any real
shutdown failure.

### P1 — `redact_secrets()`'s `STOCKBIT_PASSWORD` never matched the real `STOCKBIT_PASS` env var

**Evidence:** `utils/logging_config.py`'s `_SECRET_VARS` listed `"STOCKBIT_PASSWORD"`; every actual
read of this credential in the codebase (`auto_token.py:28`) uses `STOCKBIT_PASS`. Since
`redact_secrets()` does `os.getenv(var, "")` per name, the wrong name always resolved empty — the
real password has never actually been in the redaction match set, despite the entry's clear intent.
The existing regression test asserted the same wrong name and "passed" only because both sides shared
the identical typo.

**Fix (commit `0c35d1b`):** one-word correction; also fixed the corresponding test assertion (and its
uncommitted mirror in `tests/test_auto_token.py`, left uncommitted per that file's existing RC1-scope
exclusion).

### P1 — `paper_trade.py`'s exception-echoing `print()` calls bypassed redaction entirely

**Evidence:** four `print()` calls (`calc_swing_tp`'s ATR fallback, `check_trend`'s error path, both
circuit-breaker Telegram-send `except` blocks) wrote exception text straight to stdout — outside both
the structured JSON log and the `SecretRedactionFilter` attached to every configured logging Handler.

**Fix (commit `21edd4d`):** added a module logger and routed these four call sites through
`logger.warning(...)` — since `SecretRedactionFilter` is attached to the handler, not the call site,
this automatically gains redaction with no new logic written. Three other `print()` calls in the same
file (informational TP/SL-cap values, no exception text) were left untouched — not part of the
evidenced gap.

### P3 — `.stockbit_token.lock` not gitignored

**Evidence:** confirmed via `git check-ignore -v` it was not ignored, unlike its sibling
`.stockbit_token`. File is empty (0 bytes, pure flock marker) — hygiene gap, not an active exposure.

**Fix (commit `ac2d349`):** one-line `.gitignore` addition.

---

## Findings — Evidenced, Classified, NOT Fixed (Required Follow-Up)

### P0 — `/telegram/updates` webhook fails open when `TELEGRAM_WEBHOOK_SECRET` is unset

**Evidence:** `routes/telegram.py`'s webhook handler skips its own HMAC check entirely
(`if TELEGRAM_WEBHOOK_SECRET:`) whenever the var is empty; `config.py` defaults it to `""`; it is
absent from `.env.example`; and it is **not** enforced by `validate_config()` the way
`TELEGRAM_TOKEN`/`TELEGRAM_CHAT_ID` are (those two fail startup if missing).

**Concrete risk:** if a deployment never sets this one specific env var (easy to miss — it's not in
the example file), the route accepts any unauthenticated POST and dispatches `/status`, `/signals`,
`/flow`, `/dashboard` using an attacker-supplied `chat_id` — an outsider could redirect live trading
signals to their own Telegram chat with zero credentials.

**Why not fixed here:** this route is pre-existing (not RC1 code), and this reviewer has no visibility
into whether the real production `.env` already has this secret set. Adding a hard `validate_config()`
requirement could refuse to boot an already-functioning live system on its next restart if it doesn't.
**Required action (before or immediately after this release): confirm `TELEGRAM_WEBHOOK_SECRET` is
set in the real production `.env` today.** Once confirmed, add the same `validate_config()` enforcement
already used for the other two Telegram vars, as a fast-follow, not a silent unilateral change.

### P1 — `validate_config()` requires `DB_PATH` to already exist as a file, contradicting its own "fresh DB allowed" comment

`config.py` fails startup with "DB_PATH does not exist" for a genuinely fresh/DR-restored environment
with no pre-existing DB file — no script or the systemd unit ever creates/touches this file first.
Reproduced live during this review's own smoke test. Needs either an automated bootstrap step
(`ExecStartPre` touching the file, or `release.sh` creating an empty placeholder) or relaxing the
check to allow a genuinely absent file the same way it already allows an empty one.

### P1 — Silent auth-token role downgrade on duplicate values

`security/auth.py::configured_tokens()` builds a `{token: role}` dict by iterating roles in a fixed
order; if the same token string is accidentally set for two roles, the later-iterated role silently
wins with zero validation. Bounded to `AUTH_MODE=enforce` deployments (off by default).

### P1 — `start_scheduler()`'s ~20 `add_job()` calls have no wrapping try/except

Any exception during job registration (like the one found and fixed above) propagates uncaught
through the entire boot path. A future bug in any one job's registration would crash the whole worker
rather than degrading to "N-1 jobs running." Fixing this properly means restructuring ~20 call sites
to isolate failures — larger than a single-pass minimal fix.

### P1 — No external alert on a boot crash-loop

`deploy/idx-walkforward.service` relies on systemd defaults for `StartLimitBurst`; if the process
fails every boot, systemd eventually stops restarting and the service goes fully dark with zero
Telegram alert (all alerting lives inside the process that never successfully starts). Ops-level
configuration change, not a code fix.

### P1 — Backup/restore-drill cron silently stopped firing for ~36h around 2026-07-25/26

Live log evidence: `logs/cron_db_backup.log` jumps from `2026-07-24` straight to `2026-07-26`;
`logs/cron_db_restore_drill.log`'s last entry is `2026-07-19` — the most recent scheduled weekly
drill never ran. No dead-man's-switch exists for "did this cron job fire at all" (only for "did it
fail after firing"). No evidence of actual data loss — every run that *did* execute passed cleanly —
but the gap itself went undetected. Requires new monitoring infrastructure (a "last successful
backup timestamp" health check), not a code correction.

### P1 — Zero `PRAGMA integrity_check` anywhere in the application startup path

If `data/walkforward.db` were corrupted at process start, the app would boot "successfully" and fail
unpredictably later, rather than failing loud and fast. Partially mitigated: the nightly backup's own
verify step would independently catch corruption within 24h — assuming that cron fires (see above).

### P1 — `monitor.py`'s per-trade SL/TP loop has no per-trade exception isolation, and its caller only logs (never alerts) on failure

An unhandled exception evaluating trade N (bad data, a NaN edge case) aborts the whole batch — every
trade after N in that tick goes unmonitored, silently, with no Telegram alert (contrast with
`run_agent_firm_gate`'s exemplary fail-open+alert design, found clean below).

### P1 — Open positions on a halted/delisted ticker silently stop being monitored, no alert

Correct fail-safe against acting on stale data, but no companion alert exists for "this position
hasn't had a new bar in N days."

### P1 — `redact_secrets()` structurally cannot redact the live Stockbit bearer JWT

The token lives only in the file `.stockbit_token`, never an env var — the entire redaction mechanism
matches against configured env-var values, so it has no way to ever know this token's value.

### P1 — Truncation happens before redaction at 10+ call sites

`str(e)[:120..300]` is applied before the truncated text reaches `send_telegram()`'s internal
`redact_secrets()` call — a secret whose full value straddles the truncation cutoff leaves an
unredacted partial fragment. Fixing properly touches 10+ call sites across `scheduler/`.

### P1 — Committed token-write path (`auto_token.py`/`stockbit_fetcher.py`) lacks atomic write / explicit permission hardening

A hardened `_write_token_atomic()` (mkstemp + chmod 0600 + os.replace) exists only in local,
uncommitted working-tree state — deliberately excluded from RC1 per
`Audit/RC1_RELEASE_PACKAGING_2026-07-28.md` §2c. This finding confirms that exclusion has a real,
now-documented cost; recommend prioritizing that separate commit shortly after this release.

### P1 — `cron_wrap.sh`'s Telegram crash alert bypasses redaction entirely

This shell-based alert path (raw `curl`, not Python) was never in scope of the R-4 Python
`redact_secrets()` fix. A cron-wrapped script whose crash log embeds a token/URL fragment would ship
it unredacted.

### P1 — `/health` doesn't verify the scheduler is alive; a broken deploy can pass the deploy gate

`scripts/wait_for_health.sh` gates deploy success purely on `/health`, which checks DB connectivity
but never scheduler liveness. A deploy where scheduler-start silently fails (already wrapped in
try/except per the codebase's fail-soft convention) would report "ok" and pass, caught only later by
the separate heartbeat dead-man's-switch (~10 min delay).

### P1 — `scripts/release.sh`'s default `SHARED_PATHS` doesn't match the actual default `DB_PATH` location

Symlinks a top-level `walkforward.db` that doesn't match `config.py`'s actual default
(`data/walkforward.db`) — silently matches nothing on a stock configuration. Mitigated: `validate_config()`'s
DB-existence check (see the P1 above) would fail loud rather than corrupt anything, but only if
`DB_PATH` is set to an absolute path manually — nothing enforces that.

### P1 — Release packaging (`scripts/release.sh`) is never exercised end-to-end by CI

`.github/workflows/test.yml` runs only `pytest -q`; the real `git archive`/symlink-swap path has no
integration-level CI coverage.

### P2 (acceptable technical debt, tracked)
- `redact_secrets()` is exact-value-match only, not pattern-based (misses a bare JWT, unusual-format keys).
- `metrics.py::provider_stats()` defaults `success_rate=1.0` on zero calls — mitigated by the same
  object's `available`/`circuit_state` fields not sharing this default.
- `.playwright_state/`'s live session cookies aren't covered by the `.env`/`.stockbit_token`
  permission check (correctly gitignored, so a host-hardening gap, not a git-exposure one).
- No release-directory retention/pruning — unbounded disk growth over time, not a correctness risk.
- No explicit `wal_checkpoint` call — relies on SQLite's default auto-checkpoint; no evidence of
  actual unbounded WAL growth found.

### P3 (future improvement)
- No `signal.signal()` handler for the `python app.py` dev-mode path (production always runs under
  gunicorn, which handles this natively).
- 13 files with bare `print()` in non-critical CLI/debug-tool paths.
- No disaster-recovery runbook exists for total server loss / lost secrets / Stockbit lockout with no
  working refresh path.
- `rollback.sh`'s fallback-to-newest-release behavior when no `current` symlink exists at all
  (bootstrap-only edge case, reasonable default).

---

## Verified Clean (explicitly checked, no finding)

- `gunicorn.conf.py`: `workers=1` enforced; `post_worker_init`/`worker_exit` correctly wired; no
  double-invocation risk under normal gunicorn semantics (one call per forked worker's lifetime).
- `data/db.py::connect()` is genuinely the single entry point for all production SQLite access — no
  bypass found outside `research/`/`scripts/`/`_archive/`/`scratchpad/`, all explicitly out of scope.
- Every schema-owning module (`data/db.py`, `research/tracking.py`, `forward_testing/storage/db.py`,
  `engine/trade_plan.py`) uses the same idempotent `PRAGMA table_info()` → `ALTER TABLE ADD COLUMN`
  pattern consistently.
- `scripts/db_backup.py` genuinely uses the SQLite online-backup API against a read-only URI
  connection, verifies via `PRAGMA integrity_check` + row counts before compressing, and correctly
  implements 7-daily + 4-weekly retention.
- `scripts/db_restore.py` defaults to verify-only; `--apply` moves the live DB aside to a timestamped
  file rather than deleting it — reversible by design. Confirmed actually run weekly with passing logs.
- WAL side-file (`-wal`/`-shm`) handling in both backup and restore is correct — no orphaned state risk.
- `open_trade`/`close_trade` are each single atomic INSERT/UPDATE — no half-opened/half-closed window.
- `engine/exits/evaluator.py` is pure, deterministic, correctly ordered (STOP→TP→TIME).
- `run_agent_firm_gate` has an exemplary fail-open design: wraps everything in try/except, correctly
  distinguishes degraded/bypassed from real approvals, and fires a genuine, verified Telegram+log
  alarm when both LLM providers are down.
- Log rotation is bounded (10MB × 5 backups = 50MB max) — cannot fill disk unboundedly.
- `release.sh` genuinely builds from `git archive HEAD`; the `current` symlink flip is genuinely
  atomic in both `release.sh` and `rollback.sh`; `release.json` contains exactly what
  `validate_config()` requires; `rollback.sh --list`/named-version rollback logic is correct;
  no race can leave `current` pointing at a partially-removed directory.
- `wait_for_health.sh` hits a real endpoint with real DB-connectivity verification and a sane retry
  budget.
- Every entry in `deploy/crontab` is wrapped by `cron_wrap.sh` — no cron job can fail silently.
- Technical debt inventory: zero must-resolve items — see `Audit/TECHNICAL_DEBT_RELEASE_REVIEW.md`.
