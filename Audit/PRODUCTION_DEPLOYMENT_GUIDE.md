# Production Deployment Guide

**Version:** 1.0 · **Status:** ACTIVE · **Effective Date:** 2026-07-29
**Scope:** Deployment, startup, shutdown, upgrade, rollback, and disaster-recovery procedures for
the IDX Walkforward Strategy Suite (Flask/gunicorn, port 5001) as actually implemented in this
repository today. This document operationalizes `docs/OPERATIONS.md`'s "Runtime architecture" and
"Deployment (release-based)" sections into step-by-step operator procedures; where the two overlap,
`docs/OPERATIONS.md` remains the terse reference and this document is the walkthrough. Do not treat
this document as authoritative over a CI-enforced test — per `CLAUDE.md`'s Decision-Making
Hierarchy, a test is ground truth over any document's claim.

**Companion documents:** `Audit/OPERATIONS_RUNBOOK.md` (day/week/month operating cadence),
`Audit/PAPER_TRADING_OPERATING_PROCEDURE.md` (paper-trading-specific procedures),
`docs/OPERATIONS.md` (canonical quick-reference), `docs/SECURITY.md` (auth/route policy).

---

## 0. Before You Read Further — Current Repository State (verified 2026-07-29)

This guide describes the deployment *mechanism* as built. It does not certify that the mechanism's
current inputs (the working tree at time of writing) are ready to deploy. As of this writing:

- Branch `ops/hardening-2026-07-10` is 2 commits ahead of `origin/ops/hardening-2026-07-10`, and the
  working tree additionally carries a large set of modified/untracked tracked files
  (`engine/agent_firm/*`, `monitor.py`, `paper_trade.py`, `scheduler/jobs.py`, `scheduler/scanner.py`,
  `engine/position_sizing.py`, `data/db.py`, `config.py`, test files, etc.) that are **uncommitted**
  — including the ADR-AF-003 sizing-ownership fix and the `TELEGRAM_WEBHOOK_SECRET`
  `validate_config()` hardening verified in `Audit/OPERATIONAL_HARDENING_REPORT.md` (2026-07-29).
  This is the same class of gap `Audit/RC1_FINAL_CERTIFICATION_2026-07-28.md` (Finding F-1) flagged
  before: "a citable, CI-verified unit of work" does not yet exist for this state. `scripts/release.sh`
  now **refuses** (exit 1) to build from an uncommitted working tree by default — see §6 — so this is
  no longer a silent-omission risk, but it does mean **no release can be built at all until this work
  is committed**. Commit, push, and get CI green before the next real release.
- `Audit/PRODUCTION_ENGINE_BACKLOG.md` (dated 2026-07-29) listed 4 P0 items; all 4 are now
  **resolved** per `Audit/OPERATIONAL_HARDENING_REPORT.md` (2026-07-29), pending commit — see that
  report and `Audit/OPERATIONS_RUNBOOK.md`'s Incident Response section for detail.

---

## 1. Initial Installation

Target: a fresh Linux host that will run the service under **user systemd** (linger enabled).
Everything below matches `docs/OPERATIONS.md`'s "Runtime architecture" diagram.

```bash
# 1. Clone to the deployment host at the canonical no-space path.
#    (The venv's console-script shebangs break on paths containing spaces —
#    this is why deploy/idx-walkforward.service invokes `python -m gunicorn`
#    rather than the gunicorn console script, and why the crontab comment
#    calls out the same constraint.)
git clone <repo-url> /home/<user>/idx-walkforward-5001
cd /home/<user>/idx-walkforward-5001
git checkout ops/hardening-2026-07-10   # or master, per current deployment policy

# 2. Python environment
python3 -m venv venv
venv/bin/pip install -r requirements.txt
# Verify PyYAML resolves — engine/registry_loader.py imports it unconditionally
# but it is not independently pinned in requirements.txt (open item, see §9).
venv/bin/python -c "import yaml, feedparser, langgraph" && echo OK

# 3. Secrets and config
cp .env.example .env
chmod 600 .env
# Fill in at minimum: DB_PATH, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID.
# If AGENT_FIRM_ENABLED=true: ZAI_API_KEY (unless AGENT_FIRM_PROVIDER=claude only).
# See config.py::validate_config() for the exhaustive mandatory-field list —
# it is the single source of truth for what blocks startup.

# 4. Stockbit auth (headless token refresh, used by flow/OHLCV fetch jobs)
venv/bin/python3 auto_token.py
chmod 600 .stockbit_token
# auto_token.py --check can be used any time to test the current token
# without refreshing it.

# 5. Database bootstrap — a brand-new empty DB is explicitly allowed by
#    validate_config() (first-boot bootstrap path); table migrations run
#    idempotently inside app.init_runtime() on first start. No manual
#    schema step is required.
mkdir -p "$(dirname "$(grep ^DB_PATH .env | cut -d= -f2)")"

# 6. Directories the app/cron expect
mkdir -p logs
mkdir -p ~/backups/idx-walkforward-5001

# 7. Install the systemd unit (see §2 for the full cutover sequence —
#    do not skip scripts/release.sh first)
```

**Deployment model is release-based, not working-tree.** Production never runs `git pull` in place
against a live process — it always runs from an immutable, versioned copy built by
`scripts/release.sh` (`git archive HEAD` → `~/releases/idx-walkforward/<timestamp>-<sha>`, chmod'd
read-only, with `.env`/`venv`/`logs`/DB files symlinked back in as shared mutable state) and
activated by atomically flipping the `~/idx-walkforward-current` symlink. See §3.

### 1.1 First release + systemd cutover (one-time)

```bash
cd /home/<user>/idx-walkforward-5001
scripts/release.sh
# → prints: released <version>
#           current -> ~/releases/idx-walkforward/<version>
#           activate with: systemctl --user restart idx-walkforward

cp deploy/idx-walkforward.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable idx-walkforward   # survives reboot once linger is on
loginctl enable-linger "$USER"            # if not already enabled — required
                                           # for a user unit to start at boot
                                           # and outlive the login session
systemctl --user start idx-walkforward
```

`deploy/idx-walkforward.service`'s `ExecStartPost` runs `scripts/wait_for_health.sh` — the unit does
not reach `active` until `/health` answers `200` with `"status": "ok"`. A start that never becomes
healthy is marked failed and retried (`Restart=always`, `RestartSec=5`), so a broken deploy
self-limits rather than silently running broken.

### 1.2 Install the cron jobs

```bash
crontab deploy/crontab
crontab -l   # verify
```

`deploy/crontab` is the source of truth (edit there, reinstall — do not hand-edit the live
crontab). `tests/test_cron_contract.py` asserts every referenced script exists and every job is
wrapped by `scripts/cron_wrap.sh` (per-job log in `logs/cron_<job>.log`, Telegram alert on any
nonzero exit) — run it after any crontab edit, before installing:

```bash
.winvenv/Scripts/python.exe -m pytest tests/test_cron_contract.py tests/test_config_validation.py -q
# (Windows dev checkout; on the Linux deploy host use venv/bin/python -m pytest instead)
```

---

## 2. First Startup

1. Confirm `.env` and `.stockbit_token` are both mode 600 — `validate_config()` aborts startup
   otherwise (`config.py`).
2. Confirm `DB_PATH` in `.env` is an **absolute path**. `data/` ships as read-only code inside each
   release (it's a tracked package, `data/db.py`), so a relative `DB_PATH` would resolve inside the
   frozen, read-only release directory instead of shared mutable state —
   `scripts/release.sh`'s own header comment calls this out explicitly.
3. Start the service (§1.1). Watch the gate:
   ```bash
   journalctl --user -u idx-walkforward -f
   ```
   Expect: config validation passes silently (no `ConfigError`), APScheduler starts and logs its
   full job list, the router composition log line for the agent firm (a single-provider router logs
   a loud `WARNING` — fix `.env` if you see it and failover was intended), Telegram poller thread
   starts.
4. Confirm health:
   ```bash
   scripts/wait_for_health.sh
   curl -s localhost:5001/health | python3 -m json.tool
   ```
   Expect `status: ok`, `db: ok`, a `version` matching the release you just built.
   **Known gap:** `/health` currently reports `status: ok` purely from a DB round-trip
   (`app.py:79-104`) — it does **not** check whether APScheduler actually started (`BACKLOG` P1-6,
   "Add a scheduler-liveness check to `/health`"). A deploy where the scheduler silently fails to
   register jobs will still report healthy. Cross-check `journalctl` for the job-list log line on
   every first startup until this gap is closed.
5. Confirm cron is live: `crontab -l`, and check `logs/cron_*.log` appears after the next scheduled
   fire (or force one manually to test, e.g. `scripts/cron_wrap.sh test_probe true`).

---

## 3. Normal Startup

Production is managed by systemd — do not run `python app.py` or `./start.sh` by hand against the
production DB except for isolated debugging with a copied DB.

```bash
systemctl --user start idx-walkforward
systemctl --user status idx-walkforward
scripts/wait_for_health.sh
```

Manual fallback (same runtime, foreground — useful only for interactive debugging):
```bash
./start.sh          # gunicorn, same as systemd
./start.sh dev       # Flask dev server, single-threaded, no gunicorn
```

---

## 4. Graceful Shutdown

```bash
systemctl --user stop idx-walkforward
```

`TimeoutStopSec=45`, `KillMode=mixed` in the unit file — gunicorn gets a `SIGTERM` and up to 45s to
finish in-flight requests and worker shutdown before a `SIGKILL`. `gunicorn.conf.py`'s
`worker_exit` hook must remain `wait=True` (not `wait=False`) for graceful shutdown to actually wait
— this was a real regression fixed in commit `368f6c8` (`fix(runtime): worker_exit graceful
shutdown must wait=True, not wait=False`); if you ever touch `gunicorn.conf.py`, re-verify this did
not regress.

Do **not** `kill -9` the process directly except as a last resort — APScheduler jobs and the SQLite
WAL checkpoint both prefer a clean exit. If a graceful stop hangs past `TimeoutStopSec`, check for a
long-running scheduler job (`journalctl --user -u idx-walkforward -n 100`) before escalating to a
forced kill.

---

## 5. Restart Procedure

```bash
systemctl --user restart idx-walkforward
scripts/wait_for_health.sh
journalctl --user -u idx-walkforward -n 50   # startup clean, registry announced
```

`Restart=always` means an unplanned crash restarts automatically after `RestartSec=5` — a manual
restart is for planned config/env changes or as a first response to a stuck process. A restart does
**not** rebuild the release; it re-execs the same `~/idx-walkforward-current` target. To pick up new
code, build a new release first (§6).

---

## 6. Upgrade Procedure

```bash
# 1. On the deployment host, fetch and check out the reviewed, tested commit
git -C ~/idx-walkforward-5001 fetch origin
git -C ~/idx-walkforward-5001 checkout <reviewed-sha-or-branch>
git -C ~/idx-walkforward-5001 status --porcelain   # MUST be empty — release.sh
                                                    # now aborts (exit 1) on
                                                    # uncommitted tracked changes
                                                    # (Audit/OPERATIONAL_HARDENING_REPORT.md,
                                                    # 2026-07-29); ALLOW_DIRTY_RELEASE=1
                                                    # is a documented, deliberate
                                                    # override for a one-off manual
                                                    # smoke build only — never use it
                                                    # for a real deploy

# 2. Build the release
cd ~/idx-walkforward-5001
scripts/release.sh
# → released <version>; current -> ~/releases/idx-walkforward/<version>

# 3. Activate (explicit operator action — release.sh never restarts the
#    service itself, by design)
systemctl --user restart idx-walkforward

# 4. Verify
scripts/wait_for_health.sh
curl -s localhost:5001/health | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])"
journalctl --user -u idx-walkforward -n 50
```

**Pre-upgrade checklist:**
- [ ] Full test suite green on the exact commit being deployed (`pytest -q`, or the targeted subset
      relevant to the change) — ideally via the actual GitHub Actions CI run
      (`.github/workflows/test.yml`, triggers on `push`/`pull_request`), not only a local venv. A
      local-only "tests pass" claim on this repo's Windows dev venv has previously diverged from
      what a clean Linux CI environment reports (`Audit/RC1_FINAL_CERTIFICATION_2026-07-28.md`
      Finding F-2) — treat local runs as a pre-check, not a substitute for CI green.
- [ ] `git status --porcelain` clean on the commit being released.
- [ ] Migration/schema changes (if any) are additive and idempotent (`CREATE TABLE IF NOT EXISTS` +
      `PRAGMA table_info` column-presence checks per `CLAUDE.md`'s Coding Conventions) — this repo
      has no separate migration runner; `app.init_runtime()` applies them on every startup.
  - [ ] A recent, verified-good backup exists (§8) before any release touching schema.

**Note on `SHARED_PATHS`:** `scripts/release.sh`'s default `SHARED_PATHS` list is
`.env venv logs walkforward.db flow.db idx_data.db .stockbit_token` — these are relative filenames
under the **project directory**, not `DB_PATH`'s actual configured value. If `.env`'s `DB_PATH`
points somewhere else (e.g. `data/walkforward.db`, the documented default), the DB symlink this
list tries to create will not match, and the release will not actually share the live DB the way
intended (open item — `BACKLOG` P1-9, "Fix `scripts/release.sh`'s `SHARED_PATHS` default to match
the real `DB_PATH` default"). **Verify after every release** that `ls -la
~/releases/idx-walkforward/<version>/` shows the expected DB file symlinked, not a fresh empty one,
before restarting the service.

---

## 7. Rollback Procedure

```bash
scripts/rollback.sh --list              # releases under ~/releases/idx-walkforward, '*' = current
scripts/rollback.sh                     # roll back to the release immediately before current
scripts/rollback.sh <version>           # roll back to a specific named release
systemctl --user restart idx-walkforward
scripts/wait_for_health.sh
```

Rollback only flips the `current` symlink — released code directories are chmod'd read-only and
never deleted by `rollback.sh`, so this is always safe to run and always reversible. It does **not**
roll back the database. If the upgrade you're rolling back from included a schema change or wrote
data in a format the older release's code can't read, a code-only rollback may not be sufficient —
evaluate whether a DB restore (§8) is also needed before rolling back code that expects an older
schema.

**Rollback checklist:**
- [ ] `scripts/rollback.sh --list` confirms the target release exists and its `built_at`/`git_sha`
      (`release.json` inside that release directory) match what you expect.
- [ ] Restart and health-check.
- [ ] Check `/health`'s `version` field matches the rolled-back release.
- [ ] If the incident involved data written in a new format, assess whether a DB restore is also
      required (§8) — do not assume code rollback alone is sufficient.
- [ ] Post-incident: capture what triggered the rollback before the failed release directory is
      pruned by any future manual cleanup.

---

## 8. Backup and Restore

### 8.1 Backup (automated, nightly)

`deploy/crontab`: `30 21 * * *` → `python -m scripts.db_backup` (after the 21:00 OHLCV
reconciliation). Cycle (`scripts/db_backup.py::run_backup`): SQLite online-backup API snapshot
(WAL-safe, consistent even while the app writes) → `PRAGMA integrity_check` + per-table row counts
**before** compression → zstd (falls back to gzip if `zstd` binary is absent) → `.meta.json`
sidecar → retention prune (7 daily + 4 weekly, by newest-per-day / newest-per-ISO-week). A backup
that fails verification is deleted and the run exits non-zero, which `cron_wrap.sh` turns into a
Telegram alert — a failed backup is never silently "successful."

Destination: `~/backups/idx-walkforward-5001/` (override via `BACKUP_DIR`).

Manual run:
```bash
venv/bin/python -m scripts.db_backup
venv/bin/python -m scripts.db_backup --db /path/to/db --dest /path/to/dest --keep-daily 7 --keep-weekly 4
```

### 8.2 Restore drill (verify-only — run weekly, and after any schema change)

`deploy/crontab`: `0 9 * * 0` (Sunday 09:00) → restore-drills the newest backup, verify-only, no
live DB touched.

```bash
venv/bin/python -m scripts.db_restore ~/backups/idx-walkforward-5001/<newest>.db.zst
```

Decompresses to a scratch temp dir, re-runs the same `PRAGMA integrity_check`, and compares
per-table row counts against the backup's `.meta.json`. **"A backup is not considered good until
this has passed"** (`docs/OPERATIONS.md`, `CLAUDE.md`) — a nightly backup alone is not a verified
recovery capability.

**Operational note (verify current status before relying on this):** `Audit/PRODUCTION_ENGINE_BACKLOG.md`
(P1-2, P2-6) records that the weekly restore-drill cron entry had a ~36h gap (2026-07-25/26) that
went undetected until manually noticed, and that as of the last audit there was no dead-man's-switch
on the drill's own cadence (only on the scheduler heartbeat, a different job). Confirm the drill has
actually run in the last 7 days (`logs/cron_db_restore_drill.log`) before trusting "backups are
good" as a standing fact — do not assume it from the crontab entry's presence alone.

### 8.3 Real restore (destructive to the current DB file — always reversible)

```bash
systemctl --user stop idx-walkforward
venv/bin/python -m scripts.db_restore ~/backups/idx-walkforward-5001/<file>.db.zst --apply
systemctl --user start idx-walkforward
scripts/wait_for_health.sh
```

`--apply` moves the current live DB aside to `<db>.pre_restore_<timestamp>` (including `-wal`/`-shm`
side files) — **never deletes it** — then moves the verified restored copy into place. To undo:
stop the service, move the `.pre_restore_<timestamp>` file back over the live path, restart.

**Restore checklist:**
- [ ] Service stopped before `--apply` (an in-place file swap under a live SQLite connection is
      unsafe).
- [ ] `--apply` run output shows `RESTORE APPLIED` with row counts matching `.meta.json`.
- [ ] Service restarted, `/health` green, spot-check a few recent rows in a key table
      (`paper_trades`, `scheduled_signals`) against expectations for the point in time being
      restored to.
- [ ] `.pre_restore_<timestamp>` file retained until the restore is confirmed correct — do not
      manually delete it same-day.

---

## 9. Disaster Recovery

Covers total loss of the live host (disk failure, accidental `rm`, unrecoverable corruption beyond
what §8.3 addresses).

1. **Provision a new host** and repeat §1 (Initial Installation) through the venv/deps/systemd-unit
   steps, using the same git remote and the last known-good commit/tag.
2. **Restore the database** from the most recent off-host-replicated backup in
   `~/backups/idx-walkforward-5001/` (see §8.1's retention: up to 7 daily + 4 weekly points).
   **Verify these backups are actually copied off the production host** — `docs/OPERATIONS.md` and
   this repo's tooling describe backup *creation* and *local retention* in detail, but this review
   found no documented off-host replication step (e.g. rsync to a second host, S3/object storage
   push). Confirm this exists operationally before treating "backups exist" as equivalent to
   "disaster recovery is possible" — a host-local backup directory does not survive the loss of that
   same host. **This is a gap to close, not an assumption to make** — see §9.1.
3. Run `scripts.db_restore --apply` against the newly provisioned host's DB path (§8.3).
4. Recreate `.env` from your secrets vault/password manager (never from a backup — secrets are
   deliberately excluded from the DB and from git).
5. Re-run `auto_token.py` for a fresh Stockbit JWT (tokens are short-lived and host-specific — do
   not attempt to restore `.stockbit_token` from a backup).
6. Install the systemd unit and cron (§1.1, §1.2).
7. Start, verify health (§2), verify the next scheduled job fires correctly, verify Telegram alerts
   are flowing (send a manual test via the bot or wait for the next scheduled report).
8. Post-recovery: reconcile any trades/signals that occurred in the gap between the last backup and
   the failure — the restored DB reflects a point in time, not the exact failure moment.

### 9.1 Open Gap: Off-Host Backup Replication

Not verified in this repository or its documentation as an implemented step. Recommended action
before relying on this DR procedure for a real host-loss event: confirm (or implement) that
`~/backups/idx-walkforward-5001/` is replicated to a second location on a schedule at least as
frequent as the nightly backup cron. This is an operational prerequisite, not a code change — track
it alongside the other items in §11 rather than treating it as resolved by this document's
existence.

---

## 10. Security & Config Prerequisites (deployment-blocking if unmet)

Per `config.py::validate_config()` (the actual enforcement point — this list mirrors what the
function checks, not a separate policy):

- [ ] `DB_PATH` set; if the DB file exists and is non-empty, it must already contain the expected
      core tables (guards against a wrong `DB_PATH` silently pointing at an unrelated DB). A
      brand-new empty DB is allowed.
- [ ] `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID` / `TELEGRAM_WEBHOOK_SECRET` set — the service refuses to
      boot without any of them (`TELEGRAM_WEBHOOK_SECRET` enforcement added
      `Audit/OPERATIONAL_HARDENING_REPORT.md`, 2026-07-29 — previously read but unvalidated;
      live production confirmed to already have it set, SSH-verified same date, so this is safe to
      deploy against the current `.env`).
- [ ] If `AGENT_FIRM_ENABLED=true`: `ZAI_API_KEY` set unless `AGENT_FIRM_PROVIDER=claude` only; if
      `claude` is anywhere in `AGENT_FIRM_PROVIDER_ORDER`, the `claude` CLI must be discoverable on
      `PATH`.
- [ ] `AUTH_MODE` is a valid value (`off`/`shadow`/`enforce`); if `enforce`, at least one
      `AUTH_TOKEN_*` is configured and every configured token is ≥16 chars (lockout guard).
- [ ] `.env` and `.stockbit_token` are both mode 600.
- [ ] `release.json` (inside the active release directory), if present, is well-formed.
- [x] `TELEGRAM_WEBHOOK_SECRET` is now enforced by `validate_config()` (see above) — P0-3/P0-4
      resolved 2026-07-29, both re-verified directly against live production (SSH). This fix is
      currently **uncommitted**; until it's committed and deployed, the live process is still
      running the old, unenforced check — treat P0-3's manual confirmation as still necessary for
      any deploy of the *current* running release.
- [ ] `gunicorn.conf.py` workers **must stay 1** — `tests/test_config_validation.py::test_gunicorn_config_stays_single_worker`
      guards this; do not override via environment or CLI flag.
- [ ] Every registered Flask route is classified in `security/route_policy.py` (63 route
      classifications present as of this writing) — `tests/security/test_route_policy.py` fails CI
      on an unclassified route (fail-closed default: admin-only). Any new route added as part of a
      release must be classified before merge, not after.

---

## 11. Deployment Checklist (consolidated)

**Before building a release:**
- [ ] Target commit is pushed and has a green CI run on GitHub Actions (not only local `pytest`).
- [ ] `git status --porcelain` clean at the target commit.
- [ ] §10's security/config prerequisites confirmed for the target `.env`.
- [ ] A verified-good backup exists if the release touches schema (§8.2's drill has run recently).

**Building and activating:**
- [ ] `scripts/release.sh` run; output's `version`/`git_sha` recorded (e.g. in the deploy log/ticket).
- [ ] Symlinked shared state spot-checked inside the new release dir (`.env`, DB file — see §6's
      `SHARED_PATHS` caveat).
- [ ] `systemctl --user restart idx-walkforward`.
- [ ] `scripts/wait_for_health.sh` passes.
- [ ] `/health`'s `version` matches the release just built.
- [ ] `journalctl --user -u idx-walkforward -n 50` shows a clean startup: config validation
      silent, scheduler job list logged, agent-firm router composition logged (multi-provider, not
      a single-provider `WARNING`, unless single-provider is intentional).

**After activation:**
- [ ] Next scheduled cron/APScheduler job fires and completes (spot-check `logs/cron_*.log` or
      `logs/app.log`).
- [ ] No `EVENT_JOB_ERROR` Telegram alert within the first cycle.
- [ ] Full test suite was green on the deployed commit before this deploy (recorded, not re-run
      post-deploy against a running prod instance).

---

## 12. Production Launch Recommendation

See `Audit/PAPER_TRADING_OPERATING_PROCEDURE.md` §"Production Launch Recommendation" for the
paper-trading-specific go/no-go call. From a pure deployment-mechanics standpoint: the release,
rollback, and backup/restore machinery itself is sound and exercised (first full restore drill
passed 2026-07-10 per `docs/OPERATIONS.md`), but **the current working tree is uncommitted** (see
§0) and **4 P0 items** in `Audit/PRODUCTION_ENGINE_BACKLOG.md` are open. Do not build the next
release from this working tree until those are resolved or an explicit owner decision accepts the
residual risk — see `Audit/OPERATIONS_RUNBOOK.md` and `Audit/PAPER_TRADING_OPERATING_PROCEDURE.md`
for the full prerequisite list.
