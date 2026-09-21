"""SignalAdapter — ingest screener output into the forward-test signal model.

Reads (read-only): scheduled_signals.
Writes: ft_signal (SHADOW track), ft_signal_state, ft_transition_log.

Phase 1: every ingested signal lands on the SHADOW track at GENERATED.
Selection to the PORTFOLIO track happens in Phase 3 (Ranker/Sizer).
strategy_version_id/config_hash are populated from
engine.strategy_version (audit 2026-09-02, blocker #3): every ingested signal is
pinned to the canonical version of the strategy that produced it -- the backtest
function, the live checker, the live gate set and the exit policy, hashed
together -- so a forward-test row can always prove which rule it measured. They
were NULL on all 3,033 pre-existing rows; those stay NULL rather than being
back-filled with a version they did not run under.
"""
from forward_testing.lifecycle.states import SignalState
from forward_testing.storage.db import ft_get_db

SHADOW = "SHADOW"


class SignalAdapter:
    def __init__(self, repo, db_path):
        self.repo = repo
        self.db_path = db_path
        self._vcache = {}

    def _version(self, strategy):
        cached = self._vcache.get(strategy)
        if cached is not None:
            return cached
        from engine import strategy_version as sv
        with ft_get_db(self.db_path) as c:
            got = sv.resolve(c, strategy)
        self._vcache[strategy] = got
        return got

    def ingest(self, run_date):
        """Ingest all scheduled_signals whose scan_time falls on run_date.

        Returns the number of NEWLY ingested signals (re-runs return 0).
        """
        n = 0
        for row in self._read_source_signals(run_date):
            strategy = self._strategy(row)
            vid, chash = self._version(strategy)
            sid = self.repo.insert_signal(
                signal_date=run_date,
                ticker=row["ticker"],
                strategy=strategy,
                track=SHADOW,
                direction=self._direction(row),
                conviction=row["flow_score"],
                strategy_version_id=vid,
                source_table="scheduled_signals",
                source_id=row["id"],
                config_hash=chash,
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
