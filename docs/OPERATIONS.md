# Operations Manual

Post-hardening (2026-07-10, audit `Audit/INSTITUTIONAL_AUDIT_2026-07-10.md`).
Everything here matches the implementation — if you change one, change the other.

## Runtime architecture

One process, managed by **user systemd** (linger enabled → starts at boot,
survives logout):

```
systemd (user) ── idx-walkforward.service   Restart=always, health-gated start
  └─ gunicorn (gthread, workers=1, threads=8, port 5001)   gunicorn.conf.py
       └─ wsgi:app (Flask)
            ├─ APScheduler   started in post_worker_init (gunicorn.conf.py)
            └─ Telegram poller thread
```

**workers must stay 1** — the process embeds APScheduler and owns the SQLite
writer; a second worker would double-run every job. Guard-tested in
`tests/test_config_validation.py::test_gunicorn_config_stays_single_worker`.

`config.validate_config()` runs at startup and refuses to boot when
mandatory config is missing (DB_PATH, Telegram creds, ZAI key if firm on).

## Deployment (release-based)

Production runs an **immutable, versioned release**, never the working tree.
`scripts/release.sh` builds `~/releases/idx-walkforward/<timestamp>-<sha>`
from `git archive HEAD` (code chmod'd read-only, `release.json` manifest
with version/git_sha/branch/built_at, shared mutable state — `.env`, `venv`,
`logs`, root DBs — symlinked in) and atomically flips the
`~/idx-walkforward-current` symlink. The DB is reached via the absolute
`DB_PATH` in `.env`.

```bash
# release procedure
git -C ~/idx-walkforward-5001 pull            # or merge the reviewed branch
scripts/release.sh                            # build + switch `current`
systemctl --user restart idx-walkforward      # activate (operator action)
scripts/wait_for_health.sh                    # explicit post-deploy check
curl -s localhost:5001/health | jq .version   # confirm the running version

# service management
systemctl --user status idx-walkforward
journalctl --user -u idx-walkforward -f       # live logs (gunicorn + app)
```

**Rollback**

```bash
scripts/rollback.sh --list      # releases, '*' marks current
scripts/rollback.sh             # previous release
scripts/rollback.sh <version>   # a specific release
systemctl --user restart idx-walkforward
```

Unit file source of truth: `deploy/idx-walkforward.service` (targets
`~/idx-walkforward-current`) → copy to `~/.config/systemd/user/` +
`systemctl --user daemon-reload` when it changes. **Cutover note:** until the
updated unit is installed, the installed service still runs from the legacy
working-tree symlink `~/idx-walkforward-5001`; the cutover steps are in the
unit file header.

The service is health-gated: a start where `/health` never answers is marked
failed and retried (`Restart=always`, `RestartSec=5`).

Manual fallbacks: `./start.sh` (same gunicorn runtime, foreground),
`./start.sh dev` (Flask dev server).

## Startup validation

`config.validate_config()` runs before the scheduler starts and **aborts
startup** (ConfigError listing every problem at once) on: missing
DB_PATH/Telegram config; a non-empty DB missing core tables (wrong DB_PATH);
provider order including `claude` without the CLI on PATH; missing ZAI key;
invalid `AUTH_MODE`; `AUTH_MODE=enforce` with no tokens (lockout guard);
tokens shorter than 16 chars; `.env`/`.stockbit_token` not mode 600; a
malformed `release.json`. A brand-new empty DB is allowed (first-boot
bootstrap). On abort, the health gate keeps the unit failed — read the
ConfigError list in `journalctl --user -u idx-walkforward`.

## Authentication & audit trail

Route auth (viewer/operator/scheduler/admin roles, `AUTH_MODE`
off/shadow/enforce) and the `audit_events` trail are documented in
[SECURITY.md](SECURITY.md), including the shadow→enforce migration runbook.
Quick queries:

```sql
-- recent operational actions & auth failures
SELECT ts, action, actor_role, resource, outcome FROM audit_events
ORDER BY ts DESC LIMIT 20;
```

### Known contamination: test-suite rows in production `audit_events` (2026-10-05)

Running `pytest` on the production checkout (XPS-13) wrote **887 fake
`provider_switch` rows** into production `data/walkforward.db` between
2026-07-10 20:04:55 and 2026-10-01 05:00:23 (5–35 rows per suite run). They
come from `tests/agent_firm/providers/test_alerts.py`, whose frozen `_RESET_A`
timestamp appears in every row's `detail`
(`session limit; resumes ~2026-07-10T11:20:00+00:00`). Root cause: the suite
resolved `DB_PATH` to the real database; fixed by PR #31 (`af1ce24`), which
pins `DB_PATH` to a scratch file and fails any run that writes under `data/`.

**Owner decision 2026-10-05: the rows are kept, not deleted** — `audit_events`
is append-only. Exclude them in any analysis of provider switches:

```sql
-- real provider switches only (excludes the test-suite contamination)
SELECT ts, detail FROM audit_events
WHERE action = 'provider_switch'
  AND detail NOT LIKE '%2026-07-10T11:20:00%'
ORDER BY ts DESC;
```

Checked and clean: `provider_events` holds no test-origin rows. Telegram was
pinned off for tests from 2026-08-05 (`fb39846`); runs before that date are
unverified.

## Backup & restore

**Since 2026-08-15 (P2-6): these 3 jobs run on systemd `--user` timers, not cron** — source of
truth `deploy/systemd/` (`README.md` has install/verify/uninstall). Vanilla cron has no catch-up
semantics: a fire time missed while this box (a laptop that suspends/reboots on its own schedule)
was asleep is silently skipped, not retried. That's exactly what caused the weekly restore drill
to go 27 days (2026-07-19 → 2026-08-15) without actually running, discovered only via the P1-2
dead-man's-switch. Every `.timer` sets `Persistent=true`, so a missed fire runs shortly after the
next boot/wake instead. All 3 still route through `scripts/cron_wrap.sh` under the same job names
(`db_backup`, `db_backup_research`, `db_restore_drill`) — per-job logs, Telegram alert-on-failure,
and the dead-man's-switch below all keep working unmodified; only the trigger mechanism changed.

Nightly (21:30) runs `python -m scripts.db_backup`:
snapshot via SQLite online-backup API (WAL-safe while the app writes) →
`PRAGMA integrity_check` + per-table row counts **before** compression →
zstd → `.meta.json` → retention prune (**7 daily + 4 weekly**).
Destination: `~/backups/idx-walkforward-5001/` (override: `BACKUP_DIR`).
A failed verification deletes the snapshot and exits non-zero → alert.

Since 2026-07-21 (R-5 Tier-1 split): a second nightly job (21:35) backs up `data/research.db`
the same way, with `--prefix research` so its retention pool never interleaves with
`walkforward-*` backups. Restore drills (`scripts.db_restore`) are single-DB by design; run the
drill against whichever backup you need to verify by passing its exact filename.

Weekly restore drill (Sunday 09:00): `python -m scripts.db_restore
<newest backup>` — decompress, integrity check, row-count match vs meta,
touch nothing. **A backup is not considered good until this has passed.**
First full drill on the real 3.2 GB DB passed 2026-07-10 (52 tables,
24,003,548 rows verified). The drill's glob is prefix-scoped to
`walkforward-*.db.zst` (P2-6, 2026-08-15) — a bare `*.db.zst` picks the
newest backup of *either* prefix sharing the directory, so the
much-smaller `research-*` backup silently made a real drill run verify the
wrong, non-critical file while reporting "RESTORE VERIFIED OK."

Real restore:

```bash
systemctl --user stop idx-walkforward
venv/bin/python -m scripts.db_restore ~/backups/idx-walkforward-5001/<file>.db.zst --apply
systemctl --user start idx-walkforward
```

`--apply` moves the current DB aside to `walkforward.db.pre_restore_<ts>`
(never deletes) — reversible by moving it back.

## Data integrity — Syncthing exclusion

**Never remove `.stignore` from the repo root.** It excludes `*.db`, `*.db-wal`, `*.db-shm`,
`*.db-journal`, `*.sync-conflict-*.db(-wal|-shm)`, and `logs/` from Syncthing sync — root cause of
a real, confirmed production data corruption incident
(`Audit/INCIDENT_VPIN_DB_CORRUPTION_2026-07-29.md`): a bidirectional Syncthing folder racing the
live app's own WAL-mode writes to `data/walkforward.db` corrupted one table (`ticks`). If this repo
directory is ever a Syncthing folder (check `~/.local/state/syncthing/config.xml` for a folder
entry at this path) — WAL-mode SQLite files being synced by any file-sync tool while a writer is
live is a well-documented corruption mechanism, not specific to Syncthing. `.stignore` closing this
was verified holding as of 2026-08-06 (8 days, zero new sync-conflict artifacts despite continuous
DB writes) — see the incident report's addendum for the evidence trail.

## Provider failover (agent firm)

`.env`: `AGENT_FIRM_PROVIDER=auto`, `AGENT_FIRM_PROVIDER_ORDER=claude,zai`
— Claude Sonnet primary (flipped 2026-09-15; was ZAI-primary before), GLM-5.3
Flash (`zai`) fallback. Per-provider circuit breaker (3 failures → 30 s
cooldown → half-open trial); Claude has a daily call cap
(`AGENT_FIRM_CLAUDE_MAX_CALLS_PER_DAY`) — now more load-bearing than before
since Claude is tried on every invocation, not just as a fallback. Claude's
usage also shares the same subscription 5-hour window as interactive Claude
Code use on this account (see "Provider failover" in CLAUDE.md).

Every router decision is persisted to the `provider_events` table (as of
2026-07-10 — it was write-less before) AND logged as JSON. Check health:

```sql
SELECT event_type, provider, COUNT(*) FROM provider_events
WHERE created_at >= date('now', '-7 days') GROUP BY 1, 2;
```

Startup logs the router composition; a single-provider router logs a loud
WARNING (that state means failover is off — fix `.env`).

### Session limits & quota-aware routing (RCA 2026-07-10)

Both providers run on subscription plans with **5-hour usage windows**:
Claude ("You've hit your session limit · resets 6:20pm (Asia/Jakarta)",
exit 1 with the message on **stdout**) and Z.ai (HTTP 429 code 1308
"Usage limit reached for 5 hour"). The Claude window is **shared with any
interactive Claude Code session on this account** — heavy interactive use
drains the same quota the failover leg depends on.

Behavior (`Audit/CLAUDE_PROVIDER_RCA_2026-07-10.md` is the source of truth):

- Failed CLI invocations are classified from **both stdout and stderr**
  into explicit categories (`session_limit_exceeded`, `rate_limited`,
  `authentication_failed`, `timeout`, `network_failure`,
  `provider_unavailable`, `unexpected_error`, `unknown`).
- On a session limit the Router **holds the provider out of rotation**
  until the advertised reset time + `AGENT_FIRM_QUOTA_RESET_BUFFER`
  (fallback `AGENT_FIRM_QUOTA_FALLBACK_HOLD` when no reset was parseable;
  capped at `AGENT_FIRM_QUOTA_MAX_HOLD`). No CLI process is spawned for a
  held provider. Recovery is automatic: after the hold expires the next
  request tries the provider again; the first success emits
  `provider_restored` and re-enables normal rotation. The Circuit Breaker
  is unchanged and operates in parallel.
- Events: `provider_session_limit` (with `reset_time`), `provider_skipped`
  (hold active), `provider_restored`. Telegram alerts fire on transitions
  only (one per reset window; escalation after
  `AGENT_FIRM_QUOTA_REPEAT_THRESHOLD` hits without recovery; one
  "all providers down" alert per `AGENT_FIRM_ALERT_MIN_INTERVAL`).

Check current availability and why:

```sql
SELECT provider, event_type, reason, reset_time, created_at
FROM provider_events
WHERE event_type IN ('provider_session_limit','provider_restored')
ORDER BY id DESC LIMIT 10;
```

Operator actions when quota alarms fire:

1. Session limit on **claude**: expected on heavy interactive-use days —
   nothing to fix; routing already skips it until the reset shown in the
   alert. Reduce interactive Claude Code load or wait for the window.
2. Repeated-exhaustion alert: firm volume is chewing whole windows —
   lower burst size / call volume, or consider a metered API key for the
   firm (structural fix, out of scope of quota-aware routing).
3. All-providers-down alert: firm requests are failing; the agent-firm
   gate falls back per the flow-gate fail-open policy. Check both
   providers' reset times; nothing to restart — recovery is time-based.
4. Kill switch for the hold behavior: `AGENT_FIRM_QUOTA_HOLD=false`
   (reverts to pre-2026-07-10 retry-every-cooldown behavior).

Known limitations: holds are **process-local** (an app restart forgets
them — worst case the provider is re-probed once and re-held); reset-time
parsing covers Claude's "resets H:MMam/pm (Zone)" phrasing — anything else
degrades to the fallback hold; Z.ai's 1308 carries no reset timestamp, so
it always uses the fallback hold; quota stays shared with interactive
Claude Code use — routing can route around exhaustion, not create capacity.

## Cron

Source of truth: `deploy/crontab` (install: `crontab deploy/crontab`).
Every job runs through `scripts/cron_wrap.sh`: per-job log at
`logs/cron_<job>.log` + Telegram alert on ANY nonzero exit — a missing
script alarms instead of failing silently for weeks (audit P-4).
`tests/test_cron_contract.py` asserts every referenced script exists.

The two DB backups and the weekly restore drill moved to systemd `--user` timers
(`deploy/systemd/`) — see **Backup & restore** above for why. Everything else stays on cron.
`tests/test_systemd_timers_contract.py` covers those 3; `test_cron_contract.py` asserts they
aren't also still scheduled on cron (double-run guard).

## Telegram operational reporting (Production Engine Phases 1–3, 2026-07-28)

Three daily Telegram reports, all read-only over engine outputs that were already computed
elsewhere — none of them recompute a score, rank, or exit decision:

| Report | Job | Time (WIB) | What it shows |
|---|---|---|---|
| EOD Trade Plan | `scheduler.jobs.run_eod_trade_plan` | 16:40 | Agent-ranked long shortlist + Watchlist Changes (added/removed/upgraded/downgraded, rank + confidence deltas) |
| Premarket Shortlist | `scheduler.jobs.run_premarket_firm_scan` | 08:35 | Firm-vetted shortlist + PREMARKET SUMMARY (regime/risk/candidates/highest conviction) + NEW/REMOVED/UPGRADED/DOWNGRADED/STABLE |
| Forward-Testing Summary | `scheduler.jobs.run_forward_test_cycle` | 18:30 | New/closed/active shadow positions, cumulative win/loss scoreboard, best/worst trades |

The EOD and Premarket reports share one snapshot/diff mechanism: `engine/trade_plan.py`'s
`record_snapshot()`/`diff_watchlist()` against a `watchlist_snapshot` table (`date, strategy,
ticker, rank, confidence, conviction, confluence, sources`; `strategy` is `'eod'` or `'premarket'`,
keeping the two histories independent). The Forward-Testing report reads `ft_shadow_position`/
`ft_shadow_trade` directly (`forward_testing/reporting.py`) — no new table.

All three jobs guard against duplicate sends with a shared `_job_sentinel` table (`job, run_date`
primary key, first `INSERT` wins) — the same pattern each already used individually, so a
systemd-restart race never double-sends a day's report.

**Scheduler crash alerting**: an `EVENT_JOB_ERROR` listener (`scheduler/__init__.py`) sends one
Telegram alert per uncaught in-process job exception — this is what actually tells you *which* job
died, as distinct from the heartbeat below (which only proves the process is alive). Rate-limited
per `job_id` via `SCHEDULER_JOB_ERROR_COOLDOWN_S` (default 3600s): the first failure always alerts;
repeats inside the cooldown window are logged only (`[scheduler] job <id> failed (alert on
cooldown)`) and rolled into the next alert as a "+N suppressed" count once the cooldown expires.

```sql
-- N/A: job-error alerts are not persisted to a table today, only Telegram + logs/app.log.
-- "which jobs ran today" still requires grepping logs/app.log — a persisted, queryable job-run
-- ledger is the scoped remaining gap (see the Operations Dashboard / Job History phase).
```

## EOD finalisation & the Stockbit token (2026-09-23)

The 16:15 `screener_eod` pass is what turns the day's scraper bars FINAL (`ohlcv.is_final=1`);
research reads only final bars. Its token defences, in time order (WIB, Mon–Fri):

| time | job id | what |
|---|---|---|
| 08:20, 12:00 | `token_health_*` | JWT `exp` claim only — blind to a server-side revocation |
| 16:05 | `token_live_probe_1605` | live API call; on 401/403 runs `auto_token.py` once (a credential login takes 3–4 min, hence 16:05, not 16:10) |
| 16:15 | `screener_eod` | verifies the token live before scraping (401/403 → one refresh; 5xx/timeout → retried with backoff, never a login). Refresh fails → Telegram, nothing saved. A scrape under 50% coverage whose failures are mostly 401/403 → one refresh + re-fetch of just those tickers. Under 50% after that → "EOD finalisation DEGRADED" Telegram |
| 17:30 | `eod_retry_1730` | same-day retry: on a degraded day re-scrapes every ticker without a final bar, otherwise only leftover provisional bars. Deduped per day via `_job_sentinel` (`eod_retry`). The tradebook serves only the current session, so this cannot run for a past date |
| 09:00 next day | cron `provisional_bars_check` | backstop: alerts on any past session still provisional |

**Incident (2026-09-21/22).** The Stockbit token was revoked server-side mid-afternoon (09-21
~15:35; 09-22 between 12:52 and 13:35) while its `exp` claim showed ~21h left. The exp-only
check reported OK, and the 16:15 pass got HTTP 401 on all 958 tickers, so both sessions stayed
provisional with no alert until the next morning. This host made no login in that window. The
revocation came from elsewhere — the working hypothesis is one active session per account, so a
login on another device (the Windows box keeps its own token; `.stockbit_token*` is not synced)
invalidates this host's token. Avoid ad-hoc Stockbit logins on other devices during market hours.

**Manual recovery** when a session is still provisional after 17:30:
`python3 auto_token.py --login`, then the same evening re-run the retry
(`python3 -c "from screener.screener_jobs import run_eod_retry; print(run_eod_retry())"`), or for a
past session `python3 scripts/repair_provisional_bars.py` (dry run) → `--apply` (settled
yfinance data, split-guarded; IHSG is fetched as `^JKSE`).

## Logging

- `logs/app.log` — structured JSON (rotating 10 MB × 5), correlation IDs.
- `journalctl --user -u idx-walkforward` — gunicorn/systemd lifecycle.
- `logs/cron_*.log` — per-cron-job output.
- Scheduler jobs log at INFO/WARNING (no print()) — guard: keep it that way.
- `utils.logging_config.redact_secrets()` masks configured secret env-var values
  (`_SECRET_VARS`) in any text before it's logged (`SecretRedactionFilter`) **or** sent to
  Telegram (`utils.telegram.send_telegram`, `routes.telegram.send_telegram_reply`, RC1 fix R-4) —
  one masking rule, two consumers, so an exception message that embeds a token can't leak through
  whichever path skips the other.

## Operational checklist

Daily (or after any alert):
- [ ] Telegram: no 🚨 CRON FAIL / ⚠️ FAIL-OPEN messages overnight
- [ ] Telegram: 🔴 Scheduler Job Failed alerts — if any include a "+N suppressed" count, the
      underlying job has been failing repeatedly, not just once; check `logs/app.log` for that
      `job_id`, don't treat it as a one-off
- [ ] The three daily reports (EOD Trade Plan 16:40, Premarket Shortlist 08:35, Forward-Testing
      Summary 18:30) actually arrived — a missing one with no crash alert suggests the dedup guard
      false-positived (check `_job_sentinel` for that job/date)
- [ ] `systemctl --user status idx-walkforward` active; NRestarts stable
- [ ] `/health` returns `status: ok` and a fresh `last_scan`
- [ ] Heartbeat watchdog quiet (`logs/heartbeat_check.log`)

Weekly:
- [ ] Sunday restore drill passed (`logs/cron_db_restore_drill.log`)
- [ ] `provider_events`: failover/timeout rates sane (query above)
- [ ] Disk: `df -h /home` and `du -sh ~/backups/idx-walkforward-5001`

After any deploy:
- [ ] `scripts/wait_for_health.sh`
- [ ] `journalctl --user -u idx-walkforward -n 50` — startup clean, registry announced
- [ ] full test suite green before merging to master
