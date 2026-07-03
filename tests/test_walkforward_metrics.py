"""Phase 2B — walk-forward summary metric correctness (audit item 2.7)."""
import math

from engine.walkforward_multi import _summarize_strategy


def _win(total_return_pct, profit_factor, win_rate=50.0, sharpe=0.5,
         max_drawdown_pct=-5.0, total_trades=10, total_winners=5,
         avg_pnl_pct=1.0, total_pnl_rp=1000):
    return {
        "total_return_pct": total_return_pct, "profit_factor": profit_factor,
        "win_rate": win_rate, "sharpe": sharpe,
        "max_drawdown_pct": max_drawdown_pct, "total_trades": total_trades,
        "total_winners": total_winners, "avg_pnl_pct": avg_pnl_pct,
        "total_pnl_rp": total_pnl_rp,
    }


def test_avg_pf_is_zero_when_all_windows_are_lossless():
    """Every window PF=999 (inf sentinel: zero losses) -> the old code did
    np.mean([]) = NaN and stored NaN. Must be a finite number now."""
    windows = [_win(5.0, 999), _win(3.0, 999)]
    summ = _summarize_strategy("t", windows)
    assert not math.isnan(summ["avg_profit_factor"])
    assert summ["avg_profit_factor"] == 999   # all lossless -> report the sentinel


def test_avg_pf_averages_only_finite_windows():
    windows = [_win(5.0, 2.0), _win(3.0, 4.0), _win(1.0, 999)]
    summ = _summarize_strategy("t", windows)
    assert summ["avg_profit_factor"] == 3.0   # mean(2,4), sentinel excluded


def test_summary_shapes_are_json_safe():
    """No NaN/inf may reach the summary (they break JSON + DB REAL columns)."""
    for pf in (999, 0.0, 1.5):
        summ = _summarize_strategy("t", [_win(2.0, pf)])
        v = summ["avg_profit_factor"]
        assert math.isfinite(v)


from engine.walkforward_multi import compute_metrics, SHARPE_MIN_TRADES


class _T:
    def __init__(self, pnl_pct):
        self.pnl_rp = pnl_pct * 1000
        self.pnl_pct = pnl_pct
        self.entry_date = "2026-01-01"
        self.exit_date = "2026-01-05"
        self.exit_reason = "TP"


def _result(pnls_pct):
    trades = [_T(p) for p in pnls_pct]
    eq = [1_000_000]
    for t in trades:
        eq.append(eq[-1] + t.pnl_rp)
    return {"strategy": "t", "trades": trades, "equity": eq,
            "initial_capital": 1_000_000, "final_capital": eq[-1]}


def test_sharpe_floor_is_at_least_five():
    assert SHARPE_MIN_TRADES >= 5


def test_sharpe_zero_below_floor():
    m = compute_metrics(_result([1.0, -0.5, 2.0, 1.5]))   # 4 trades < floor
    assert m["sharpe"] == 0
    assert m["total_trades"] == 4


def test_sharpe_computed_at_or_above_floor():
    m = compute_metrics(_result([1.0, -0.5, 2.0, 1.5, 0.8, -0.3]))  # 6 >= floor
    assert m["sharpe"] != 0
    assert -10.0 <= m["sharpe"] <= 10.0
