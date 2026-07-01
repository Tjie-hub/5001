"""SignalAdapter — ingest screener output into the forward-test signal model.

Reads (read-only): scheduled_signals.
Writes: ft_signal (SHADOW track), ft_signal_state, ft_transition_log.

Phase 1: every ingested signal lands on the SHADOW track at GENERATED.
Selection to the PORTFOLIO track happens in Phase 3 (Ranker/Sizer).
strategy_version_id/config_hash are left NULL until Phase 2 wires the
strategy registry.
"""
from forward_testing.lifecycle.states import SignalState
from forward_testing.storage.db import ft_get_db

SHADOW = "SHADOW"


class SignalAdapter:
    def __init__(self, repo, db_path):
        self.repo = repo
        self.db_path = db_path

    def ingest(self, run_date):
        """Ingest all scheduled_signals whose scan_time falls on run_date.

        Returns the number of NEWLY ingested signals (re-runs return 0).
        """
        n = 0
        for row in self._read_source_signals(run_date):
            sid = self.repo.insert_signal(
                signal_date=run_date,
                ticker=row["ticker"],
                strategy=self._strategy(row),
                track=SHADOW,
                direction=self._direction(row),
                conviction=row["flow_score"],
                source_table="scheduled_signals",
                source_id=row["id"],
            )
            if self.repo.get_signal_state(sid) is None:
                self.repo.init_signal_state(sid, SignalState.GENERATED.value)
                self.repo.write_transition(
                    sid, None, SignalState.GENERATED.value, run_date,
                    actor="adapter", reason="ingest",
                )
                n += 1
        return n

    def _read_source_signals(self, run_date):
        # scan_time is stored as "YYYY-MM-DD HH:MM"; match by date prefix.
        with ft_get_db(self.db_path) as c:
            return c.execute(
                """SELECT id, ticker, strategies, flow_score, signal_direction
                   FROM scheduled_signals
                   WHERE substr(scan_time, 1, 10) = ?
                   ORDER BY id""",
                (run_date,),
            ).fetchall()

    @staticmethod
    def _strategy(row):
        # scheduled_signals.strategies is comma-joined; first entry is primary.
        joined = (row["strategies"] or "").strip()
        first = joined.split(",")[0].strip()
        return first or "UNKNOWN"

    @staticmethod
    def _direction(row):
        d = (row["signal_direction"] or "BUY").upper()
        return "SHORT" if d == "SELL" else "LONG"
