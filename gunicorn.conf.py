"""Gunicorn production config (audit P-5).

WHY workers=1: the process embeds APScheduler and owns the SQLite writer;
a second worker would double-run every scheduled job and fight for the
write lock. Concurrency comes from threads (gthread worker), matching the
previous Flask-server threading behavior. Do not add workers without first
moving the scheduler out of the web process.
"""
import logging

bind = "0.0.0.0:5001"
workers = 1
threads = 8
worker_class = "gthread"
timeout = 300            # interactive backtest routes can legitimately run minutes
graceful_timeout = 30
loglevel = "info"
errorlog = "-"           # gunicorn's own errors → journald via systemd
accesslog = None         # request logging already done by app.after_request (JSON)

_scheduler = None


def post_worker_init(worker):
    """Start the trading runtime inside the (single) worker — mirrors what
    `python app.py` does under __main__."""
    global _scheduler
    from app import init_runtime
    _scheduler = init_runtime()
    logging.getLogger("gunicorn.error").info(
        "worker %s: trading runtime started", worker.pid)


def worker_exit(server, worker):
    """Graceful shutdown: stop APScheduler so in-flight jobs aren't killed
    mid-write when systemd stops/restarts the service."""
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
            logging.getLogger("gunicorn.error").info(
                "worker %s: scheduler shut down", worker.pid)
        except Exception:
            pass
        _scheduler = None
