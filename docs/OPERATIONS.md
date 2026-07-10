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

## Deployment

```bash
# code update (working tree is prod — keep master clean):
git -C ~/idx-walkforward-5001 pull            # or merge the reviewed branch
systemctl --user restart idx-walkforward
scripts/wait_for_health.sh                     # explicit post-deploy check

# service management
systemctl --user status idx-walkforward
journalctl --user -u idx-walkforward -f       # live logs (gunicorn + app)
```

Unit file source of truth: `deploy/idx-walkforward.service` → copy to
`~/.config/systemd/user/` + `systemctl --user daemon-reload` when it changes.

Rollback = `git checkout <last-good>` + restart. The service is
health-gated: a start where `/health` never answers is marked failed and
retried (`Restart=always`, `RestartSec=5`).

Manual fallbacks: `./start.sh` (same gunicorn runtime, foreground),
`./start.sh dev` (Flask dev server).

## Backup & restore

Nightly cron (21:30) runs `python -m scripts.db_backup`:
snapshot via SQLite online-backup API (WAL-safe while the app writes) →
`PRAGMA integrity_check` + per-table row counts **before** compression →
zstd → `.meta.json` → retention prune (**7 daily + 4 weekly**).
Destination: `~/backups/idx-walkforward-5001/` (override: `BACKUP_DIR`).
A failed verification deletes the snapshot and exits non-zero → cron alert.

Weekly restore drill (Sunday 09:00, cron): `python -m scripts.db_restore
<newest backup>` — decompress, integrity check, row-count match vs meta,
touch nothing. **A backup is not considered good until this has passed.**
First full drill on the real 3.2 GB DB passed 2026-07-10 (52 tables,
24,003,548 rows verified).

Real restore:

```bash
systemctl --user stop idx-walkforward
venv/bin/python -m scripts.db_restore ~/backups/idx-walkforward-5001/<file>.db.zst --apply
systemctl --user start idx-walkforward
```

`--apply` moves the current DB aside to `walkforward.db.pre_restore_<ts>`
(never deletes) — reversible by moving it back.

## Provider failover (agent firm)

`.env`: `AGENT_FIRM_PROVIDER=auto`, `AGENT_FIRM_PROVIDER_ORDER=zai,claude`
— ZAI primary (unchanged behavior), Claude CLI fallback. Per-provider
circuit breaker (3 failures → 30 s cooldown → half-open trial); Claude has
a daily call cap (`AGENT_FIRM_CLAUDE_MAX_CALLS_PER_DAY`).

Every router decision is persisted to the `provider_events` table (as of
2026-07-10 — it was write-less before) AND logged as JSON. Check health:

```sql
SELECT event_type, provider, COUNT(*) FROM provider_events
WHERE created_at >= date('now', '-7 days') GROUP BY 1, 2;
```

Startup logs the router composition; a single-provider router logs a loud
WARNING (that state means failover is off — fix `.env`).

## Cron

Source of truth: `deploy/crontab` (install: `crontab deploy/crontab`).
Every job runs through `scripts/cron_wrap.sh`: per-job log at
`logs/cron_<job>.log` + Telegram alert on ANY nonzero exit — a missing
script alarms instead of failing silently for weeks (audit P-4).
`tests/test_cron_contract.py` asserts every referenced script exists.

## Logging

- `logs/app.log` — structured JSON (rotating 10 MB × 5), correlation IDs.
- `journalctl --user -u idx-walkforward` — gunicorn/systemd lifecycle.
- `logs/cron_*.log` — per-cron-job output.
- Scheduler jobs log at INFO/WARNING (no print()) — guard: keep it that way.

## Operational checklist

Daily (or after any alert):
- [ ] Telegram: no 🚨 CRON FAIL / ⚠️ FAIL-OPEN messages overnight
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
