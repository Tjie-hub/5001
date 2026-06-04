"""
backtest_roller.py — Auto-rolling walk-forward window pipeline.

Maintains backtest_windows table: one row per (ticker, test_start), covering
both complete 3-month windows and the current in-progress partial window.
Partial windows are flagged is_partial=1 and replaced when they become complete.
"""
import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from config import DB_PATH

OUT_PATH = str(Path(__file__).parent.parent / "out" / "meta_dataset_backtest.json")
FEATURE_COLS = ["adx", "ma_slope", "vr_mean", "range_pct", "close_vs_ma", "pct_above_ma"]
CAPITAL = 50_000_000
WARMUP_BARS = 60
MIN_PARTIAL_BARS = 10

logger = logging.getLogger(__name__)


def _init_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS backtest_windows (
            ticker        TEXT NOT NULL,
            window_num    INTEGER,
            train_start   TEXT,
            train_end     TEXT,
            test_start    TEXT NOT NULL,
            test_end      TEXT NOT NULL,
            is_partial    INTEGER DEFAULT 0,
            features_json TEXT,
            metrics_json  TEXT,
            computed_at   TEXT,
            PRIMARY KEY (ticker, test_start)
        )
    """)
    conn.commit()


def roll_ticker(ticker: str, df: pd.DataFrame, conn: sqlite3.Connection,
                include_partial: bool = True) -> dict:
    """
    Insert any new walk-forward windows for ticker into backtest_windows.
    Returns {'new_complete': int, 'new_partial': int}.
    """
    from engine.walkforward_multi import run_walk_forward, walk_forward_split, STRATEGY_FUNCS
    from engine.regime_filter import build_regime_features

    if len(df) < 60:
        return {"new_complete": 0, "new_partial": 0}

    # Existing complete windows for this ticker (skip these)
    complete_starts = {r[0] for r in conn.execute(
        "SELECT test_start FROM backtest_windows WHERE ticker=? AND is_partial=0",
        (ticker,)
    ).fetchall()}

    wf = run_walk_forward(df)
    if "error" in wf:
        return {"new_complete": 0, "new_partial": 0}

    windows = walk_forward_split(df, train_months=12, test_months=3)

    # Index per-window metrics from wf summary
    by_window: dict = {}
    for strat, summ in wf["summary"].items():
        for w in summ["windows"]:
            widx = w["window"]
            by_window.setdefault(widx, {})[strat] = {
                "return":        float(w["total_return_pct"]),
                "win_rate":      float(w["win_rate"]),
                "sharpe":        float(w["sharpe"]),
                "max_dd":        float(w["max_drawdown_pct"]),
                "profit_factor": float(min(w["profit_factor"], 999)),
            }

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    new_complete = 0

    for w in windows:
        test_start = w["test_start"]
        if test_start in complete_starts:
            continue

        metrics = by_window.get(w["window"])
        if not metrics or len(metrics) < len(STRATEGY_FUNCS):
            continue

        feats = build_regime_features(w["train"])
        if feats.empty:
            continue
        last_row = feats.iloc[-1]
        if pd.Series([last_row[c] for c in FEATURE_COLS]).isna().any():
            continue

        features = {c: float(last_row[c]) for c in FEATURE_COLS}

        conn.execute("""
            INSERT OR REPLACE INTO backtest_windows
            (ticker, window_num, train_start, train_end, test_start, test_end,
             is_partial, features_json, metrics_json, computed_at)
            VALUES (?,?,?,?,?,?,0,?,?,?)
        """, (ticker, w["window"], w["train_start"], w["train_end"],
              w["test_start"], w["test_end"],
              json.dumps(features), json.dumps(metrics), now_str))
        new_complete += 1

    new_partial = 0
    if include_partial:
        new_partial = _roll_partial(ticker, df, windows, conn, now_str)

    return {"new_complete": new_complete, "new_partial": new_partial}


def _roll_partial(ticker: str, df: pd.DataFrame, windows: list,
                  conn: sqlite3.Connection, now_str: str) -> int:
    """
    Insert/update the current in-progress test window (data beyond last complete test_end).
    Replaces any existing partial row for this ticker. Returns 1 if inserted, 0 otherwise.
    """
    from engine.walkforward_multi import STRATEGY_FUNCS, compute_metrics
    from engine.regime_filter import build_regime_features

    if not windows:
        return 0

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    last_complete_end = max(w["test_end"] for w in windows)
    partial_mask = df["date"] >= pd.to_datetime(last_complete_end)
    partial_df = df[partial_mask]

    if len(partial_df) < MIN_PARTIAL_BARS:
        return 0

    partial_start = last_complete_end
    partial_end = str(df["date"].max().date())

    # Skip if this test_start is already a finalized complete window
    already_complete = conn.execute(
        "SELECT COUNT(*) FROM backtest_windows WHERE ticker=? AND test_start=? AND is_partial=0",
        (ticker, partial_start)
    ).fetchone()[0]
    if already_complete:
        return 0

    # Features from end of last train window
    last_window = max(windows, key=lambda w: w["window"])
    feats = build_regime_features(last_window["train"])
    if feats.empty:
        return 0
    last_row = feats.iloc[-1]
    if pd.Series([last_row[c] for c in FEATURE_COLS]).isna().any():
        return 0
    features = {c: float(last_row[c]) for c in FEATURE_COLS}

    # Run all strategies on partial slice with warmup tail from preceding data
    train_df = df[df["date"] < pd.to_datetime(last_complete_end)]
    if train_df.empty:
        return 0
    warmup_tail = train_df.tail(WARMUP_BARS) if len(train_df) >= WARMUP_BARS else train_df
    extended = pd.concat([warmup_tail, partial_df], ignore_index=True)

    partial_metrics: dict = {}
    for strat_name, strat_func in STRATEGY_FUNCS.items():
        try:
            raw = strat_func(extended, capital=CAPITAL)
            kept = [t for t in raw["trades"] if t.entry_date >= partial_start]
            # Rebuild equity curve for the partial period
            cur_cap = CAPITAL
            new_equity = [CAPITAL]
            for t in kept:
                cur_cap += t.pnl_rp
                new_equity.append(cur_cap)
            raw["trades"] = kept
            raw["equity"] = new_equity
            raw["initial_capital"] = CAPITAL
            raw["final_capital"] = cur_cap
            m = compute_metrics(raw)
            partial_metrics[strat_name] = {
                "return":        float(m["total_return_pct"]),
                "win_rate":      float(m["win_rate"]),
                "sharpe":        float(m["sharpe"]),
                "max_dd":        float(m["max_drawdown_pct"]),
                "profit_factor": float(min(m["profit_factor"], 999)),
            }
        except Exception as exc:
            logger.debug("partial window %s %s: %s", ticker, strat_name, exc)

    if not partial_metrics:
        return 0

    window_num = max(w["window"] for w in windows) + 1
    train_start_str = str(train_df["date"].iloc[0].date())

    conn.execute("""
        INSERT OR REPLACE INTO backtest_windows
        (ticker, window_num, train_start, train_end, test_start, test_end,
         is_partial, features_json, metrics_json, computed_at)
        VALUES (?,?,?,?,?,?,1,?,?,?)
    """, (ticker, window_num, train_start_str, last_complete_end,
          partial_start, partial_end,
          json.dumps(features), json.dumps(partial_metrics), now_str))

    return 1


def roll_all(tickers: list = None, include_partial: bool = True,
             db_path: str = None) -> dict:
    """
    Roll walk-forward windows for all (or a subset of) tickers.
    Returns summary: {new_complete, new_partial, tickers_updated, errors, total_tickers}.
    """
    from scheduler.utils import get_all_tickers, _load_ohlcv_bulk

    if db_path is None:
        db_path = DB_PATH
    if tickers is None:
        tickers = get_all_tickers()

    ohlcv_map = _load_ohlcv_bulk()
    conn = sqlite3.connect(db_path)
    _init_table(conn)

    total_new_complete = 0
    total_new_partial = 0
    tickers_updated = 0
    errors: list = []

    for ticker in tickers:
        df = ohlcv_map.get(ticker)
        if df is None or len(df) < 60:
            continue
        try:
            result = roll_ticker(ticker, df, conn, include_partial=include_partial)
            conn.commit()
            if result["new_complete"] > 0 or result["new_partial"] > 0:
                tickers_updated += 1
            total_new_complete += result["new_complete"]
            total_new_partial += result["new_partial"]
        except Exception as exc:
            logger.warning("roll_all %s error: %s", ticker, exc)
            errors.append({"ticker": ticker, "error": str(exc)})

    conn.close()
    return {
        "new_complete":    total_new_complete,
        "new_partial":     total_new_partial,
        "tickers_updated": tickers_updated,
        "errors":          errors,
        "total_tickers":   len(tickers),
    }


def export_meta_dataset(path: str = None, tickers: list = None,
                        db_path: str = None) -> int:
    """
    Write backtest_windows to out/meta_dataset_backtest.json (or custom path).
    Returns number of records exported.
    """
    if path is None:
        path = OUT_PATH
    if db_path is None:
        db_path = DB_PATH

    conn = sqlite3.connect(db_path)
    query = (
        "SELECT ticker, window_num, test_start, test_end, features_json, metrics_json "
        "FROM backtest_windows"
    )
    params: list = []
    if tickers:
        placeholders = ",".join("?" * len(tickers))
        query += f" WHERE ticker IN ({placeholders})"
        params = list(tickers)
    query += " ORDER BY ticker, test_start"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    records = []
    for ticker, window_num, test_start, test_end, features_json, metrics_json in rows:
        records.append({
            "ticker":     ticker,
            "window":     window_num,
            "test_start": test_start,
            "test_end":   test_end,
            "features":   json.loads(features_json) if features_json else {},
            "metrics":    json.loads(metrics_json)  if metrics_json  else {},
        })

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(records, fh, indent=2)

    logger.info("export_meta_dataset: %d records → %s", len(records), path)
    return len(records)
