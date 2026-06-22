"""Tests for engine/wf_edge.py — cross-window OOS expectancy aggregation."""
import sqlite3

from engine.wf_edge import (
    aggregate_wf_windows,
    save_wf_edge,
    ensure_wf_edge_table,
    N_MIN_TRADES,
)


def _win(n, avg_pct, pnl_rp, winners, sharpe=1.0):
    """One per-window metrics dict (shape produced by compute_metrics)."""
    return {
        'total_trades':  n,
        'avg_pnl_pct':   avg_pct,
        'total_pnl_rp':  pnl_rp,
        'total_winners': winners,
        'sharpe':        sharpe,
    }


def _summary(strategy, windows, consistency_pct=80.0):
    """One ranked summary dict (shape produced by run_walk_forward)."""
    return {
        'strategy':        strategy,
        'consistency_pct': consistency_pct,
        'windows_tested':  len(windows),
        'windows':         windows,
    }


class TestAggregate:
    def test_empty_ranked(self):
        assert aggregate_wf_windows([]) == []

    def test_summary_with_no_windows_skipped(self):
        assert aggregate_wf_windows([_summary('x', [])]) == []

    def test_expectancy_pct_is_trade_weighted_pool(self):
        # (+2% over 10) and (-1% over 10) → (2*10 + -1*10)/20 = +0.5%
        ranked = [_summary('momentum', [_win(10, 2.0, 100_000, 6),
                                        _win(10, -1.0, -50_000, 3)])]
        out = aggregate_wf_windows(ranked)
        assert len(out) == 1
        assert out[0]['expectancy_pct'] == 0.5
        assert out[0]['n_trades'] == 20

    def test_expectancy_rp_is_informational_pool(self):
        ranked = [_summary('x', [_win(10, 2.0, 100_000, 6),
                                 _win(10, -1.0, -50_000, 3)])]
        out = aggregate_wf_windows(ranked)
        # (100_000 + -50_000) / 20
        assert out[0]['expectancy_rp'] == 2500.0

    def test_win_rate_pooled_exact_not_avg_of_avg(self):
        # 3/10 + 7/10 = 10/20 = 50%  (avg-of-avg would also be 50 here;
        # use asymmetric counts to prove pooling: 3/10 + 7/30 = 10/40 = 25%)
        ranked = [_summary('x', [_win(10, 1.0, 1, 3),
                                 _win(30, 1.0, 1, 7)])]
        out = aggregate_wf_windows(ranked)
        assert out[0]['win_rate'] == 25.0
        assert out[0]['n_trades'] == 40

    def test_sharpe_trade_weighted(self):
        ranked = [_summary('x', [_win(10, 1.0, 1, 5, sharpe=2.0),
                                 _win(30, 1.0, 1, 5, sharpe=1.0)])]
        out = aggregate_wf_windows(ranked)
        # (2.0*10 + 1.0*30) / 40 = 1.25
        assert out[0]['sharpe'] == 1.25

    def test_n_min_exclusion(self):
        ranked = [_summary('x', [_win(N_MIN_TRADES - 5, 1.0, 1, 8)])]
        assert aggregate_wf_windows(ranked) == []

    def test_n_min_inclusion(self):
        ranked = [_summary('x', [_win(N_MIN_TRADES + 5, 1.0, 1, 8)])]
        out = aggregate_wf_windows(ranked)
        assert len(out) == 1
        assert out[0]['n_trades'] == N_MIN_TRADES + 5

    def test_consistency_carried_through(self):
        ranked = [_summary('x', [_win(25, 1.0, 1, 12)], consistency_pct=66.7)]
        out = aggregate_wf_windows(ranked)
        assert out[0]['consistency_pct'] == 66.7


class TestSave:
    def test_save_and_readback(self):
        conn = sqlite3.connect(':memory:')
        ensure_wf_edge_table(conn)
        rows = aggregate_wf_windows(
            [_summary('momentum', [_win(25, 2.0, 250_000, 15)])]
        )
        written = save_wf_edge(conn, 'BBCA', rows, '2026-06-22 09:00')
        assert written == 1
        got = conn.execute(
            "SELECT ticker, strategy, expectancy_pct, win_rate, n_trades, "
            "last_computed FROM wf_edge WHERE ticker='BBCA'"
        ).fetchone()
        assert got == ('BBCA', 'momentum', 2.0, 60.0, 25, '2026-06-22 09:00')

    def test_save_is_idempotent_replace(self):
        conn = sqlite3.connect(':memory:')
        ensure_wf_edge_table(conn)
        r1 = aggregate_wf_windows([_summary('m', [_win(25, 2.0, 1, 15)])])
        save_wf_edge(conn, 'X', r1, 't1')
        r2 = aggregate_wf_windows([_summary('m', [_win(25, 3.0, 1, 20)])])
        save_wf_edge(conn, 'X', r2, 't2')
        rows = conn.execute("SELECT expectancy_pct, last_computed FROM wf_edge "
                            "WHERE ticker='X' AND strategy='m'").fetchall()
        assert rows == [(3.0, 't2')]   # replaced, not duplicated

    def test_ensure_table_idempotent(self):
        conn = sqlite3.connect(':memory:')
        ensure_wf_edge_table(conn)
        ensure_wf_edge_table(conn)   # second call must not raise
        save_wf_edge(conn, 'X', [], 't')   # empty rows ok
