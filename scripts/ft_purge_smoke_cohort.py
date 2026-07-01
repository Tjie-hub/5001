"""One-time purge of the smoke-test SHADOW cohort.

Deletes every ft_shadow_trade + ft_shadow_position row and resets the lifecycle
state of each affected signal to GENERATED, so a legitimately re-emitted signal
re-opens cleanly on the next nightly cycle. Idempotent. Touches ONLY ft-owned
shadow rows -- never scheduled_signals source data.

GENERATED is a *backward* transition, so this writes ft_signal_state directly
(a one-off maintenance op) rather than via LifecycleManager.transition, which
only permits forward moves.

Usage:
    venv/bin/python -m scripts.ft_purge_smoke_cohort
"""
import sqlite3

from config import DB_PATH


def purge_smoke_cohort(db_path=None):
    """Purge shadow rows and reset affected signals. Returns # of signals reset."""
    db = db_path or DB_PATH
    with sqlite3.connect(db, timeout=30) as c:
        sig_ids = [r[0] for r in c.execute(
            "SELECT DISTINCT signal_id FROM ft_shadow_position").fetchall()]
        c.execute("DELETE FROM ft_shadow_trade")
        c.execute("DELETE FROM ft_shadow_position")
        if sig_ids:
            qmarks = ",".join("?" * len(sig_ids))
            c.execute(
                f"UPDATE ft_signal_state SET state='GENERATED' "
                f"WHERE signal_id IN ({qmarks})",
                sig_ids,
            )
        c.commit()
    return len(sig_ids)


if __name__ == "__main__":
    n = purge_smoke_cohort()
    print(f"Purged shadow cohort; reset {n} signal(s) to GENERATED.")
