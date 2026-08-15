"""P2-6 (2026-08-15): db_backup, db_backup_research, and db_restore_drill
moved from deploy/crontab to systemd --user timers under deploy/systemd/,
because vanilla cron has no catch-up semantics -- a fire time missed while
the production box (a laptop that suspends/reboots on its own schedule) was
asleep is silently skipped, not retried. That's exactly what happened to the
weekly restore drill for 27 days (2026-07-19 -> 2026-08-15). Every .timer
here sets Persistent=true so a missed fire runs shortly after the next
boot/wake instead. See deploy/systemd/README.md for the install procedure."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYSTEMD_DIR = ROOT / "deploy" / "systemd"

JOBS = ("idx-db-backup", "idx-db-backup-research", "idx-db-restore-drill")


def test_every_job_has_a_service_and_timer_pair():
    for job in JOBS:
        assert (SYSTEMD_DIR / f"{job}.service").exists(), f"missing {job}.service"
        assert (SYSTEMD_DIR / f"{job}.timer").exists(), f"missing {job}.timer"


def test_every_service_runs_through_cron_wrap():
    """Moving the trigger mechanism must not lose cron_wrap.sh's per-job
    logging + Telegram alert-on-failure -- the whole point of P1-2's
    dead-man's-switch (which reads those same log files) depends on it."""
    for job in JOBS:
        text = (SYSTEMD_DIR / f"{job}.service").read_text()
        assert "cron_wrap.sh" in text, f"{job}.service bypasses cron_wrap.sh"


def test_every_timer_is_persistent():
    """The actual fix: without Persistent=true, a systemd timer has the
    exact same missed-fire-time gap as cron -- it would just be a more
    elaborate way to reproduce the same bug."""
    for job in JOBS:
        text = (SYSTEMD_DIR / f"{job}.timer").read_text()
        assert "Persistent=true" in text, f"{job}.timer is missing Persistent=true"


def test_restore_drill_targets_walkforward_backups_specifically():
    """Found 2026-08-15 running the drill by hand: a bare `*.db.zst | head
    -1` glob picks the newest backup of EITHER prefix sharing the backup
    dir. R-5's research.db backup (added same session) landing after the
    last walkforward.db one made the drill silently verify the wrong, tiny,
    non-critical file while reporting "RESTORE VERIFIED OK" -- the
    production-critical database was never actually tested that run."""
    text = (SYSTEMD_DIR / "idx-db-restore-drill.service").read_text()
    assert "walkforward-*.db.zst" in text, (
        "restore-drill glob must be prefix-scoped to walkforward-*.db.zst, "
        "not a bare *.db.zst that can match a different backup family's "
        "file (e.g. research-*.db.zst)"
    )


def test_every_service_working_directory_matches_cron_wrap_expectations():
    """cron_wrap.sh resolves its own log dir relative to $0's parent, but
    the python modules it invokes (scripts.db_backup / scripts.db_restore)
    are run with relative paths (data/research.db, etc.) that depend on the
    process cwd -- must be the repo root, same as cron's `cd $D &&`."""
    for job in JOBS:
        text = (SYSTEMD_DIR / f"{job}.service").read_text()
        assert "WorkingDirectory=" in text, f"{job}.service has no WorkingDirectory="
        assert "idx-walkforward-5001" in text, (
            f"{job}.service's WorkingDirectory doesn't point at the "
            f"no-space symlink cron_wrap.sh/venv shebangs require"
        )
