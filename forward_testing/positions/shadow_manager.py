"""ShadowPositionManager — paper-trades every SHADOW signal to a closed round-trip.

Two idempotent passes per run_date: OPEN (GENERATED -> OPENED at next-open fill),
then EXIT-CHECK (OPEN positions evaluated against the run_date bar -> ft_shadow_trade).
All writes are short compute-then-write transactions via FTRepo (DB-lock discipline).
"""
from forward_testing.positions.costs import Costs, apply_costs
from forward_testing.positions.exit_evaluator import PositionView, evaluate_exit
from forward_testing.lifecycle.states import SignalState


def _default_suspension_checker(db_path):
    """Returns (ticker, on_date) -> bool using suspension_events if the table exists.

    A ticker is suspended on on_date when a 'suspension'-classified row covers it:
    last_normal_date < on_date <= resume_date (or resume_date unknown).
    """
    import sqlite3

    def check(ticker, on_date):
        conn = sqlite3.connect(db_path, timeout=30)
        try:
            row = conn.execute(
                "SELECT 1 FROM suspension_events WHERE ticker=? AND classification='suspension' "
                "AND ? > last_normal_date AND (resume_date IS NULL OR ? <= resume_date) LIMIT 1",
                (ticker, on_date, on_date),
            ).fetchone()
            return row is not None
        except sqlite3.OperationalError:
            return False  # table missing -> treat as not suspended
        finally:
            conn.close()
    return check


class ShadowPositionManager:
    def __init__(self, repo, resolver, registry, lifecycle, db_path,
                 costs=None, suspension_checker=None):
        self.repo = repo
        self.resolver = resolver
        self.registry = registry
        self.lifecycle = lifecycle
        self.db_path = db_path
        self.costs = costs if costs is not None else Costs()
        self._suspended = suspension_checker or _default_suspension_checker(db_path)

    # ---- public API ----
    def run(self, run_date):
        run_id = self.repo.create_run(run_date, kind="SHADOW_EOD")
        self._open_pass(run_date)
        self._exit_pass(run_date)
        self.repo.finish_run(run_id, "OK")

    # ---- OPEN pass ----
    def _open_pass(self, run_date):
        for sig in self.repo.get_signals_by_state(SignalState.GENERATED.value, track="SHADOW"):
            self._maybe_open(sig, run_date)

    def _maybe_open(self, sig, run_date):
        signal_id = sig["id"]
        if self.repo.get_shadow_position(signal_id) is not None:
            return  # already opened (idempotent)

        nxt = self.resolver.next_open(sig["ticker"], sig["signal_date"])
        if nxt is None:
            return  # D+1 bar not yet available -> defer
        entry_date, raw_entry = nxt

        atr = self.resolver.atr14(sig["ticker"], sig["signal_date"])
        if atr is None:
            return  # insufficient history -> do not open blind

        policy = self.registry.get(sig["strategy"])
        open_side = "BUY" if sig["direction"] == "LONG" else "SELL"
        entry_price = apply_costs(raw_entry, open_side, self.costs)
        # Levels/anchors derive from the stored (cost-adjusted) entry so they match what
        # ExitEvaluator recomputes each pass from pos["entry_price"].
        lv = policy.initial_levels(sig["direction"], entry_price, atr)

        self.repo.open_shadow_position(
            signal_id=signal_id, ticker=sig["ticker"], strategy=sig["strategy"],
            direction=sig["direction"], entry_date=entry_date, entry_price=entry_price,
            atr14=atr, sl_price=lv.sl_price, tp_price=lv.tp_price,
            trail_atr_mult=policy.trail_atr_mult, trail_anchor=entry_price,
            highest_seen=entry_price, lowest_seen=entry_price,
        )
        self.lifecycle.transition(signal_id, SignalState.OPENED, run_date, actor="shadow_mgr",
                                  reason="next-open-fill")

        # Evaluate the entry bar itself (a gap can exit on day one).
        self._check_one(signal_id, entry_date)

    # ---- EXIT pass (replaces the stubs below in Task 8) ----
    def _exit_pass(self, run_date):
        return  # TEMPORARY STUB — replaced in Task 8 Step 3

    def _check_one(self, signal_id, on_date):
        return  # TEMPORARY STUB — replaced in Task 8 Step 3
