# IDX systemd user timers — DB backup + restore drill

**THIS DIRECTORY IS THE SOURCE OF TRUTH** for these 3 jobs — edit here, then reinstall
(commands below). They moved off `deploy/crontab` on 2026-08-15 (P2-6): vanilla `cron` has no
catch-up semantics, so a fire time missed while this box (a laptop that suspends/reboots on its
own schedule) was asleep is silently skipped, not retried, until the next scheduled slot. That's
exactly what happened to the weekly restore drill for 27 days (2026-07-19 → 2026-08-15). Every
`.timer` unit here sets `Persistent=true`, which makes systemd run the job shortly after the next
boot/wake if it missed its scheduled time — the direct fix.

All other cron jobs in `deploy/crontab` stay on cron; only these 3 (the two nightly DB backups and
the weekly restore drill) moved, since they're the ones where a silently-skipped run has real
consequences (an unverified/missing backup) and the least frequent (weekly) job is the one most
exposed to landing in a sleep window.

## Install / update

```bash
mkdir -p ~/.config/systemd/user
cp deploy/systemd/idx-db-backup.service deploy/systemd/idx-db-backup.timer \
   deploy/systemd/idx-db-backup-research.service deploy/systemd/idx-db-backup-research.timer \
   deploy/systemd/idx-db-restore-drill.service deploy/systemd/idx-db-restore-drill.timer \
   ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now idx-db-backup.timer idx-db-backup-research.timer idx-db-restore-drill.timer
```

Requires `loginctl show-user $USER | grep Linger` to show `Linger=yes` (already the case on the
production box — confirmed 2026-08-15, same setup that already lets `idx-walkforward.service`
itself run unattended) — without it, user-scope timers only fire while a session is logged in,
which would be no better than cron for this specific problem.

## Verify

```bash
systemctl --user list-timers 'idx-db-*'          # next/last fire times
systemctl --user start idx-db-backup.service      # run one on demand, same as `crontab`'s job did
journalctl --user -u idx-db-restore-drill.service --no-pager | tail -20
tail -f logs/cron_db_backup.log                   # still the same cron_wrap.sh log -- unchanged
```

Each service still runs through `scripts/cron_wrap.sh` with the exact same job name it had under
cron (`db_backup`, `db_backup_research`, `db_restore_drill`) — per-job log path, Telegram
alert-on-failure, and `scripts/check_backup_heartbeat.py`'s dead-man's-switch (P1-2) all keep
working unmodified; only the trigger mechanism changed.

## Uninstall (revert to cron)

```bash
systemctl --user disable --now idx-db-backup.timer idx-db-backup-research.timer idx-db-restore-drill.timer
rm ~/.config/systemd/user/idx-db-backup{,-research}.{service,timer} ~/.config/systemd/user/idx-db-restore-drill.{service,timer}
systemctl --user daemon-reload
```
Then restore the 3 lines from `deploy/crontab`'s git history and reinstall with `crontab deploy/crontab`.
