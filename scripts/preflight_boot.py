"""Boot preflight: prove the working tree can boot BEFORE the running service is stopped.

Why (2026-10-15): d57e6f4 registered run_post_close_sweep without re-exporting it, so start_scheduler() raised
NameError inside gunicorn's post_worker_init and idx-walkforward was down 17:52:15-17:54:47 WIB. Production runs
from the working tree, so "commit + systemctl restart" deploys whatever is on disk; a plain import check would not
have caught it (the name is evaluated inside start_scheduler()). This runs the real boot path in a throwaway DB:

  1. import wsgi (the Flask app and every blueprint/route module gunicorn loads);
  2. start_scheduler() with BackgroundScheduler.start stubbed (no job ever runs) and Telegram captured;
  3. fail on any exception, any _add_job registration failure (it alerts with event system.job_register_fail
     instead of raising), or a job count
     below MIN_JOBS.

  venv/bin/python scripts/preflight_boot.py        # exit 0 = safe to restart
  scripts/safe_restart.sh                          # preflight, then systemctl --user restart idx-walkforward
"""
import os
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIN_JOBS = 45   # 52 registered on 2026-10-16; a big drop means registrations went missing


def verdict(n_jobs, alerts, error=None):
    """(ok, reason)."""
    if error:
        return False, f"boot raised: {error}"
    if alerts:
        return False, f"{len(alerts)} job registration(s) failed: {alerts[0][:200]}"
    if n_jobs < MIN_JOBS:
        return False, f"only {n_jobs} jobs registered (expected >= {MIN_JOBS})"
    return True, f"{n_jobs} jobs registered"


def run():
    tmp = tempfile.mkdtemp(prefix="wf-preflight-")
    # Every module reads DB_PATH from the environment first (config/app/scheduler), so nothing touches the live DB.
    os.environ["DB_PATH"] = os.path.join(tmp, "preflight.db")
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    alerts = []

    def capture(*a, **k):
        # Startup also sends ordinary notices (registry summary); only a failed registration fails the preflight.
        if k.get("event") == "system.job_register_fail":
            alerts.append(str(a[0]) if a else "")
    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        BackgroundScheduler.start = lambda self, *a, **k: None
        import utils.telegram

        utils.telegram.send_telegram = capture
        import wsgi  # noqa: F401
        import scheduler

        scheduler.send_telegram = capture
        sched = scheduler.start_scheduler()
        return verdict(len(sched.get_jobs()), alerts)
    except BaseException as e:  # SystemExit from config validation counts too
        traceback.print_exc()
        return verdict(0, alerts, error=f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    ok, reason = run()
    print(f"preflight {'OK' if ok else 'FAILED'}: {reason}")
    sys.exit(0 if ok else 1)
