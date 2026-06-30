"""FTRepo — compute-then-write data-access objects for forward testing.

DISCIPLINE: each method opens its own short connection, writes in one
transaction, and closes. Never hold a connection open across long computation.
A run is single-writer (pid-locked at the scheduler level in Phase 7), so
read-then-write within a method is race-free in practice.
"""
import os

from forward_testing.storage.db import ft_get_db


class FTRepo:
    def __init__(self, db_path):
        self.db_path = db_path

    # ---- signals ----
    def insert_signal(self, signal_date, ticker, strategy, track,
                      direction="LONG", entry_price_intent=None, atr14=None,
                      conviction=None, strategy_version_id=None,
                      source_table=None, source_id=None, config_hash=None):
        """Idempotent insert on (signal_date, ticker, strategy, track).

        Returns the signal id (existing id on duplicate).
        """
        with ft_get_db(self.db_path) as c:
            c.execute(
                """INSERT INTO ft_signal
                   (signal_date, ticker, strategy, strategy_version_id, track,
                    direction, entry_price_intent, atr14, conviction,
                    source_table, source_id, config_hash)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(signal_date, ticker, strategy, track) DO NOTHING""",
                (signal_date, ticker, strategy, strategy_version_id, track,
                 direction, entry_price_intent, atr14, conviction,
                 source_table, source_id, config_hash),
            )
            c.commit()
            row = c.execute(
                """SELECT id FROM ft_signal
                   WHERE signal_date=? AND ticker=? AND strategy=? AND track=?""",
                (signal_date, ticker, strategy, track),
            ).fetchone()
            return row["id"]

    def get_signal_state(self, signal_id):
        with ft_get_db(self.db_path) as c:
            row = c.execute(
                "SELECT state FROM ft_signal_state WHERE signal_id=?",
                (signal_id,),
            ).fetchone()
            return row["state"] if row else None

    def init_signal_state(self, signal_id, state):
        """Create the state row if absent (PK = signal_id). Idempotent."""
        with ft_get_db(self.db_path) as c:
            c.execute(
                """INSERT INTO ft_signal_state (signal_id, state, since)
                   VALUES (?,?, datetime('now','localtime'))
                   ON CONFLICT(signal_id) DO NOTHING""",
                (signal_id, state),
            )
            c.commit()

    def write_transition(self, signal_id, from_state, to_state, run_date,
                         actor=None, reason=None):
        """Append a transition row AND advance ft_signal_state. One transaction.

        Use only for LEGAL transitions that actually change state. For rejected
        attempts, use log_violation() (which does not advance state).
        """
        with ft_get_db(self.db_path) as c:
            c.execute(
                """INSERT INTO ft_transition_log
                   (signal_id, from_state, to_state, actor, reason, run_date, violation)
                   VALUES (?,?,?,?,?,?, NULL)""",
                (signal_id, from_state, to_state, actor, reason, run_date),
            )
            c.execute(
                """UPDATE ft_signal_state
                   SET state=?, since=datetime('now','localtime'),
                       updated_at=datetime('now','localtime')
                   WHERE signal_id=?""",
                (to_state, signal_id),
            )
            c.commit()

    def log_violation(self, signal_id, from_state, attempted_to, run_date,
                      actor=None, reason=None):
        """Log an illegal transition ATTEMPT. Does NOT change ft_signal_state."""
        with ft_get_db(self.db_path) as c:
            c.execute(
                """INSERT INTO ft_transition_log
                   (signal_id, from_state, to_state, actor, reason, run_date, violation)
                   VALUES (?,?,?,?,?,?, 'ILLEGAL')""",
                (signal_id, from_state, attempted_to, actor, reason, run_date),
            )
            c.commit()

    def count_transitions(self, signal_id):
        with ft_get_db(self.db_path) as c:
            return c.execute(
                "SELECT COUNT(*) AS n FROM ft_transition_log WHERE signal_id=?",
                (signal_id,),
            ).fetchone()["n"]

    # ---- run bookkeeping ----
    def create_run(self, run_date, kind="EOD"):
        with ft_get_db(self.db_path) as c:
            cur = c.execute(
                "INSERT INTO ft_run (run_date, kind, started_at, status, pid) "
                "VALUES (?,?, datetime('now','localtime'),'RUNNING',?)",
                (run_date, kind, os.getpid()),
            )
            c.commit()
            return cur.lastrowid

    def finish_run(self, run_id, status):
        with ft_get_db(self.db_path) as c:
            c.execute(
                "UPDATE ft_run SET status=?, finished_at=datetime('now','localtime') "
                "WHERE id=?",
                (status, run_id),
            )
            c.commit()

    # ---- shadow signals lookup ----
    def get_signals_by_state(self, state, track=None):
        """Return ft_signal rows currently in `state` (optionally filtered by track).

        Each row exposes: id, signal_date, ticker, strategy, direction, track.
        """
        with ft_get_db(self.db_path) as c:
            sql = ("SELECT s.id, s.signal_date, s.ticker, s.strategy, s.direction, s.track "
                   "FROM ft_signal s JOIN ft_signal_state st ON st.signal_id = s.id "
                   "WHERE st.state = ?")
            params = [state]
            if track is not None:
                sql += " AND s.track = ?"
                params.append(track)
            sql += " ORDER BY s.id"
            return [dict(r) for r in c.execute(sql, params).fetchall()]

    # ---- shadow positions ----
    def open_shadow_position(self, signal_id, ticker, strategy, direction,
                             entry_date, entry_price, atr14, sl_price, tp_price,
                             trail_atr_mult, trail_anchor, highest_seen, lowest_seen):
        """Idempotent open (PK = signal_id). No-op if a row already exists."""
        with ft_get_db(self.db_path) as c:
            c.execute(
                """INSERT INTO ft_shadow_position
                   (signal_id, ticker, strategy, direction, entry_date, entry_price,
                    atr14, sl_price, tp_price, trail_atr_mult, trail_anchor,
                    highest_seen, lowest_seen, hold_days, status)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0,'OPEN')
                   ON CONFLICT(signal_id) DO NOTHING""",
                (signal_id, ticker, strategy, direction, entry_date, entry_price,
                 atr14, sl_price, tp_price, trail_atr_mult, trail_anchor,
                 highest_seen, lowest_seen),
            )
            c.commit()

    def get_shadow_position(self, signal_id):
        with ft_get_db(self.db_path) as c:
            row = c.execute(
                "SELECT * FROM ft_shadow_position WHERE signal_id=?", (signal_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_open_shadow_positions(self):
        with ft_get_db(self.db_path) as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM ft_shadow_position WHERE status='OPEN' ORDER BY signal_id"
            ).fetchall()]

    def update_shadow_position(self, signal_id, highest_seen, lowest_seen, hold_days):
        """Update running extremes + hold-days for an open position. One transaction."""
        with ft_get_db(self.db_path) as c:
            c.execute(
                """UPDATE ft_shadow_position
                   SET highest_seen=?, lowest_seen=?, hold_days=?,
                       updated_at=datetime('now','localtime')
                   WHERE signal_id=?""",
                (highest_seen, lowest_seen, hold_days, signal_id),
            )
            c.commit()

    def close_shadow_position(self, signal_id, exit_date, exit_price, exit_reason):
        with ft_get_db(self.db_path) as c:
            c.execute(
                """UPDATE ft_shadow_position
                   SET status='CLOSED', exit_date=?, exit_price=?, exit_reason=?,
                       updated_at=datetime('now','localtime')
                   WHERE signal_id=?""",
                (exit_date, exit_price, exit_reason, signal_id),
            )
            c.commit()

    # ---- shadow trades ----
    def insert_shadow_trade(self, signal_id, ticker, strategy, direction, signal_date,
                            entry_date, entry_price, exit_date, exit_price, exit_reason,
                            pnl_pct, r_multiple, hold_days, mae_pct, mfe_pct):
        """Idempotent closed round-trip (PK = signal_id)."""
        with ft_get_db(self.db_path) as c:
            c.execute(
                """INSERT INTO ft_shadow_trade
                   (signal_id, ticker, strategy, direction, signal_date, entry_date,
                    entry_price, exit_date, exit_price, exit_reason, pnl_pct, r_multiple,
                    hold_days, mae_pct, mfe_pct)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(signal_id) DO NOTHING""",
                (signal_id, ticker, strategy, direction, signal_date, entry_date,
                 entry_price, exit_date, exit_price, exit_reason, pnl_pct, r_multiple,
                 hold_days, mae_pct, mfe_pct),
            )
            c.commit()

    def get_shadow_trade(self, signal_id):
        with ft_get_db(self.db_path) as c:
            row = c.execute(
                "SELECT * FROM ft_shadow_trade WHERE signal_id=?", (signal_id,)
            ).fetchone()
            return dict(row) if row else None
