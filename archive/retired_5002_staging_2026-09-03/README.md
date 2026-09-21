# Retired 5002 Staging Environment — Archive

Retirement date: **2026-09-03**

## What 5002 was

Port 5002 was the **staging instance** of the Production OS ("IDX Strategy
Suite"). It was never a separate codebase or database: it was a plain Flask
dev-server process launched from the **same repository** as production
(`/home/tjiesar/10 Projects/idx-walkforward-5001`, via the
`/home/tjiesar/idx-walkforward-5001` symlink) against the **same**
`data/walkforward.db`, with the APScheduler/Telegram poller deliberately
stubbed out (`scheduler.start_scheduler = lambda: None`) so it could never
double-run jobs while production owned them.

## Why it was retired

After the Investment Dashboard (ex-port 5003) consolidation was completed and
verified, a production handover was performed (2026-09-03):

- `idx-walkforward.service` (systemd --user, gunicorn, **port 5001**) was
  restarted to load the consolidated code.
- 5001 was verified healthy with the scheduler running exactly once (46 jobs),
  and serving `/portfolio` and `/intelligence` with the migrated data.
- The redundant staging process on 5002 was then stopped and the port left
  free.

**5001 is now the single production application, scheduler owner, and
database consumer.** See `docs/INTEGRATION_CONSOLIDATION_MAP_2026-09-03.md`
for the integration background.

## What is archived here

- `staging_5002.log` — stdout/stderr of the retired staging process
  (copied from `/tmp/staging_5002.log`, which is ephemeral).
- `verify_5004_handover_check.log` — output of the throwaway verification
  server (port 5004) used during the handover checks.
- `restore_5002_staging.sh` — exact command to bring a staging instance back,
  should one ever be needed again.

Nothing else was archived, because nothing else was 5002-specific: the
repository, venv, database, migrations and backups were always shared with
production and remain in their canonical locations, untouched.

## How to restore 5002 if required

Run `./restore_5002_staging.sh` (or read it first — it is one command). It
relaunches the same staging pattern: dev server on 127.0.0.1:5002, scheduler
stubbed, same repo, same DB. It is safe alongside production precisely because
the scheduler stub prevents any second scheduler.

Before restoring, confirm the port is actually free:
`ss -tln | grep 5002` should return nothing.
