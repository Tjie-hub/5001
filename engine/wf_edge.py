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


# ── rule-indexed evidence (audit 2026-09-02, finding L-1) ────────────────────
# wf_edge answers "what is the OOS expectancy of <strategy> on <ticker>?" but
# leaves the rule implicit -- and the rule research ran was NOT the rule
# production executes (production adds a weekly MTF trend gate). Evidence is
# only meaningful against the rule that produced it, so this table keys on the
# rule_id from engine/rule_identity.py as well.
#
# wf_edge is deliberately left intact rather than migrated: it is the frozen
# record of the bare-rule study, and remains the valid evidence for the three
# strategies the live path exempts from the gate (parity already holds there).
WF_EDGE_RULE_DDL = """
CREATE TABLE IF NOT EXISTS wf_edge_rule (
    ticker            TEXT    NOT NULL,
    strategy          TEXT    NOT NULL,
    rule_id           TEXT    NOT NULL,
    expectancy_pct    REAL    NOT NULL,
    expectancy_rp     REAL    NOT NULL,
    win_rate          REAL    NOT NULL,
    consistency_pct   REAL    NOT NULL,
    sharpe            REAL    NOT NULL,
    n_trades          INTEGER NOT NULL,
    windows_tested    INTEGER NOT NULL,
    last_computed     TEXT    NOT NULL,
    run_id            TEXT,
    PRIMARY KEY (ticker, strategy, rule_id)
)
"""


# A study can legitimately produce ZERO qualifying rows -- every (ticker,
# strategy) cell fell below N_MIN_TRADES. "The rule was studied and nothing
# qualified" and "the rule was never studied" demand opposite remedies (accept
# the evidence floor vs. run the study), and wf_edge_rule alone cannot tell them
# apart because both look like an empty result set. This manifest records the
# study itself, so absence of rows stops being ambiguous.
WF_RULE_STUDY_DDL = """
CREATE TABLE IF NOT EXISTS wf_rule_study (
    strategy        TEXT    NOT NULL,
    rule_id         TEXT    NOT NULL,
    run_id          TEXT,
    tickers_scored  INTEGER NOT NULL,
    rows_written    INTEGER NOT NULL,
    warmup_bars     INTEGER,
    gates           TEXT,
    last_computed   TEXT    NOT NULL,
    PRIMARY KEY (strategy, rule_id)
)
"""


# Per-ticker completion marker for a long rule-parity study. The 2026-09-02 run
# computed 950/959 tickers correctly over 229 minutes and then discarded all of
# it when its single end-of-run transaction hit `database is locked` (audit P-1).
# With a checkpoint the same failure costs one ticker, not the whole study.
#
# Keyed on config_hash so a study under a DIFFERENT rule set / warm-up never
# reuses another study's completions -- resuming must never silently mix
# configurations.
WF_PARITY_CHECKPOINT_DDL = """
CREATE TABLE IF NOT EXISTS wf_parity_checkpoint (
    config_hash   TEXT    NOT NULL,
    ticker        TEXT    NOT NULL,
    rows_written  INTEGER NOT NULL,
    run_id        TEXT,
    completed_at  TEXT    NOT NULL,
    PRIMARY KEY (config_hash, ticker)
)
"""


def ensure_wf_parity_checkpoint_table(conn: sqlite3.Connection) -> None:
    conn.execute(WF_PARITY_CHECKPOINT_DDL)


def completed_parity_tickers(conn: sqlite3.Connection, config_hash: str) -> set:
    """Tickers already persisted under this exact study configuration."""
    ensure_wf_parity_checkpoint_table(conn)
    return {r[0] for r in conn.execute(
        "SELECT ticker FROM wf_parity_checkpoint WHERE config_hash=?",
        (config_hash,))}


def save_parity_checkpoint(conn: sqlite3.Connection, config_hash: str,
                           ticker: str, rows_written: int, completed_at: str,
                           run_id: str = None) -> None:
    """Mark one ticker done. MUST be written in the SAME transaction as that
    ticker's wf_edge_rule rows, or a crash between the two would either lose
    results or skip an unwritten ticker on resume."""
    ensure_wf_parity_checkpoint_table(conn)
    conn.execute(
        """INSERT OR REPLACE INTO wf_parity_checkpoint
           (config_hash, ticker, rows_written, run_id, completed_at)
           VALUES (?,?,?,?,?)""",
        (config_hash, ticker, int(rows_written), run_id, completed_at))


def ensure_wf_rule_study_table(conn: sqlite3.Connection) -> None:
    conn.execute(WF_RULE_STUDY_DDL)


def save_wf_rule_study(conn: sqlite3.Connection, strategy: str, rule_id: str,
                       *, tickers_scored: int, rows_written: int,
                       warmup_bars: int = None, gates=None,
                       last_computed: str, run_id: str = None) -> None:
    """Record that a walk-forward study was RUN for (strategy, rule_id)."""
    ensure_wf_rule_study_table(conn)
    conn.execute(
        """INSERT OR REPLACE INTO wf_rule_study
           (strategy, rule_id, run_id, tickers_scored, rows_written,
            warmup_bars, gates, last_computed)
           VALUES (?,?,?,?,?,?,?,?)""",
        (strategy, rule_id, run_id, int(tickers_scored), int(rows_written),
         warmup_bars, ",".join(sorted(gates or [])), last_computed))


def ensure_wf_edge_rule_table(conn: sqlite3.Connection) -> None:
    """Idempotently create the rule-indexed wf_edge table."""
    conn.execute(WF_EDGE_RULE_DDL)


def save_wf_edge_rule(conn: sqlite3.Connection, ticker: str, rule_ids: dict,
                      rows: List[dict], now_str: str, run_id: str = None) -> int:
    """INSERT OR REPLACE aggregated rows keyed by the rule that produced them.

    `rule_ids` maps strategy name -> rule_id. A strategy absent from it is
    skipped rather than recorded under an unknown rule: unlabelled evidence is
    exactly the defect this table exists to remove.
    """
    ensure_wf_edge_rule_table(conn)
    n = 0
    for r in rows:
        rid = rule_ids.get(r['strategy'])
        if not rid:
            continue
        conn.execute(
            """INSERT OR REPLACE INTO wf_edge_rule
               (ticker, strategy, rule_id, expectancy_pct, expectancy_rp,
                win_rate, consistency_pct, sharpe, n_trades, windows_tested,
                last_computed, run_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ticker, r['strategy'], rid, r['expectancy_pct'], r['expectancy_rp'],
             r['win_rate'], r['consistency_pct'], r['sharpe'],
             r['n_trades'], r['windows_tested'], now_str, run_id),
        )
        n += 1
    return n


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
