"""
engine/wf_edge.py — Cross-window OOS expectancy aggregation.

Aggregates across all walk-forward windows for a (ticker, strategy) pair so
expectancy is *pooled* (Σ over trades), not an average of per-window averages.

Expectancy is stored as per-trade PERCENT (capital-invariant). Rupiah
expectancy is kept for reference only — it scales with backtest capital and
per-trade position size, so it is unsuitable as a normalization anchor.

Self-contained: ensure_wf_edge_table() owns the DDL (CREATE TABLE IF NOT
EXISTS), so the table is created on first use without a separate migration.
"""
import sqlite3
from typing import List

N_MIN_TRADES = 20   # below this we make no edge claim — exclude, never zero-fill


WF_EDGE_DDL = """
CREATE TABLE IF NOT EXISTS wf_edge (
    ticker            TEXT    NOT NULL,
    strategy          TEXT    NOT NULL,
    expectancy_pct    REAL    NOT NULL,
    expectancy_rp     REAL    NOT NULL,
    win_rate          REAL    NOT NULL,
    consistency_pct   REAL    NOT NULL,
    sharpe            REAL    NOT NULL,
    n_trades          INTEGER NOT NULL,
    windows_tested    INTEGER NOT NULL,
    last_computed     TEXT    NOT NULL,
    PRIMARY KEY (ticker, strategy)
)
"""


def ensure_wf_edge_table(conn: sqlite3.Connection) -> None:
    """Idempotently create the wf_edge table."""
    conn.execute(WF_EDGE_DDL)


def aggregate_wf_windows(ranked: List[dict]) -> List[dict]:
    """One row per strategy from run_walk_forward()'s `ranked` list.

    Each entry in `ranked` is a summary dict carrying a `windows` list of
    per-window metrics (the shape compute_metrics returns: total_trades,
    avg_pnl_pct, total_pnl_rp, total_winners, sharpe). Strategies with fewer
    than N_MIN_TRADES pooled OOS trades are excluded (no edge claim on thin
    samples).
    """
    results = []
    for metrics in ranked:
        windows = metrics.get('windows', [])
        if not windows:
            continue

        n = sum(w['total_trades'] for w in windows)
        if n < N_MIN_TRADES:
            continue

        pnl_rp  = sum(w['total_pnl_rp'] for w in windows)
        winners = sum(w.get('total_winners', 0) for w in windows)
        # trade-weighted pooled means
        exp_pct = sum(w['avg_pnl_pct'] * w['total_trades'] for w in windows) / n
        sharpe  = sum(w['sharpe']      * w['total_trades'] for w in windows) / n

        results.append({
            'strategy':        metrics['strategy'],
            'expectancy_pct':  round(exp_pct, 3),
            'expectancy_rp':   round(pnl_rp / n, 2),
            'win_rate':        round(winners / n * 100, 1),
            'consistency_pct': metrics.get('consistency_pct', 0.0),
            'sharpe':          round(sharpe, 2),
            'n_trades':        n,
            'windows_tested':  metrics.get('windows_tested', len(windows)),
        })
    return results


def save_wf_edge(conn: sqlite3.Connection, ticker: str,
                 rows: List[dict], now_str: str) -> int:
    """INSERT OR REPLACE the aggregated rows for one ticker. Returns count."""
    ensure_wf_edge_table(conn)
    for r in rows:
        conn.execute(
            """INSERT OR REPLACE INTO wf_edge
               (ticker, strategy, expectancy_pct, expectancy_rp, win_rate,
                consistency_pct, sharpe, n_trades, windows_tested, last_computed)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (ticker, r['strategy'], r['expectancy_pct'], r['expectancy_rp'],
             r['win_rate'], r['consistency_pct'], r['sharpe'],
             r['n_trades'], r['windows_tested'], now_str),
        )
    return len(rows)
