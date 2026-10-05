"""A-OPEN audit (REVIEW_R1 2.2) -- local-corpus legs · 2026-10-05.

The review requires comparing daily opens with the first print in the frozen
minute-bar store (stockbit-flow-bars-v002). THAT STORE (7.8 GB) IS NOT PRESENT
ON THIS HOST (data/frozen/stockbit-flow-bars-v002/ holds only MANIFEST.json;
the store was built on the production host). This script therefore runs the two
legs that ARE runnable locally and documents the blocked leg:

  LEG 1 (model check, 2.2): predicted unchanged-open rate from tick/price and
       trailing gap sigma vs the observed rate, by price bucket. IDX tick
       schedule: <200:1; 200-500:2; 500-2000:5; 2000-5000:10; >=5000:25.
       Model: open_ret ~ N(0, sigma_gap20); P(open == prev_close) ~
       2*Phi(tick / (2 * prev_close * sigma_gap20)) - 1, clipped to [0,1].
  LEG 2 (cross-source): corpus open vs yfinance open on the same cells
       (both yfinance-sourced per data/fetcher.py -- NOT independent; recorded
       for continuity with the reviewer's production check).
  LEG 3 (BLOCKED HERE): daily open vs first minute print in the v002 store.
       Requires the store file; reviewer runs it or ships the store (see
       HANDOFF_R2).

Read-only on the local walkforward.db (fingerprint + max date recorded by the
caller). Output: a_open_audit.json next to this file.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

WINDOW_START, WINDOW_END = "2024-01-01", "2026-07-29"   # matches the reviewer's check window
out = {"window": [WINDOW_START, WINDOW_END],
       "minute_store_leg": ("BLOCKED on this host -- data/frozen/stockbit-flow-bars-v002/ "
                            "contains only MANIFEST.json (store sha pin fa7f07b3..., 7.8 GB, "
                            "window 2025-01-02..2026-04-28, built on the production host)."),
       "tick_schedule": "<200:1; 200-500:2; 500-2000:5; 2000-5000:10; >=5000:25"}


def tick_size(p: float) -> float:
    if p < 200: return 1.0
    if p < 500: return 2.0
    if p < 2000: return 5.0
    if p < 5000: return 10.0
    return 25.0


def main() -> None:
    import data.db as _ddb
    _orig = _ddb.connect
    def _c(*a, **k):
        c = _orig(*a, **k)
        try: c.execute("PRAGMA mmap_size=0")
        except Exception: pass
        return c
    _ddb.connect = _c
    from data.db import connect
    with connect(read_only=True) as c:
        df = pd.read_sql(
            "SELECT ticker, date, open, close FROM ohlcv "
            "WHERE COALESCE(is_final,1)=1 AND date >= ? AND date <= ? AND open > 0 AND close > 0",
            c, params=(WINDOW_START, WINDOW_END))
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
    g = df.groupby("ticker", sort=False)
    df["prev_close"] = g["close"].shift(1)
    df["gap"] = df["open"] / df["prev_close"] - 1.0
    df["gap_sig20"] = g["gap"].transform(lambda x: x.rolling(20, min_periods=10).std())
    df = df.dropna(subset=["prev_close", "gap_sig20"]).reset_index(drop=True)
    df["tick"] = df["prev_close"].map(tick_size)
    df["unchanged"] = (df["open"] == df["prev_close"]).astype(float)
    df["eq_close"] = (df["open"] == df["close"]).astype(float)
    # predicted unchanged-open probability from discreteness
    with np.errstate(divide="ignore", invalid="ignore"):
        z = df["tick"] / (2.0 * df["prev_close"] * df["gap_sig20"])
    df["pred_unchanged"] = (2.0 * _norm_cdf(z) - 1.0).clip(0.0, 1.0)

    def bucket(p):
        for hi in (200, 500, 2000, 5000, np.inf):
            if p < hi: return f"<{hi if hi != np.inf else 'inf'}"
        return "inf"

    df["pbucket"] = df["prev_close"].map(bucket)
    rows = []
    for b, gg in df.groupby("pbucket", sort=False):
        rows.append({
            "bucket": b, "n": int(len(gg)),
            "observed_unchanged_pct": round(100 * gg["unchanged"].mean(), 2),
            "predicted_unchanged_pct": round(100 * gg["pred_unchanged"].mean(), 2),
            "observed_eq_close_pct": round(100 * gg["eq_close"].mean(), 2),
            "median_tick_pct": round(100 * (gg["tick"] / gg["prev_close"]).median(), 3),
            "median_gap_sig20_pct": round(100 * gg["gap_sig20"].median(), 3),
        })
    rows.sort(key=lambda r: r["bucket"])
    out["model_check_by_price_bucket"] = rows
    out["model_check_all"] = {
        "n": int(len(df)),
        "observed_unchanged_pct": round(100 * df["unchanged"].mean(), 2),
        "predicted_unchanged_pct": round(100 * df["pred_unchanged"].mean(), 2),
        "observed_eq_close_pct": round(100 * df["eq_close"].mean(), 2),
    }

    # LEG 2: corpus opens vs yfinance opens (same-window overlap; NOT independent)
    try:
        yf_path = HERE / "x1" / "data" / "jkse.csv"   # existence probe only
        import yfinance as yf
        tk = sorted(df["ticker"].unique())
        sample = [t for t in tk if t in ("BBCA", "TLKM", "BBRI", "ANTM", "GOTO",
                                          "ASII", "BMRI", "BBNI", "ADRO", "UNTR")]
        rows2 = []
        for t in sample:
            h = yf.Ticker(t + ".JK").history(start=WINDOW_START, end=WINDOW_END,
                                             auto_adjust=False)
            if h is None or h.empty:
                continue
            h = h.reset_index().rename(columns={"Open": "yf_open"})
            h["date"] = pd.to_datetime(h["Date"]).dt.tz_localize(None)
            m = df[df["ticker"] == t].merge(h[["date", "yf_open"]], on="date", how="inner")
            if m.empty:
                continue
            rows2.append({"ticker": t, "n": int(len(m)),
                          "open_eq_yf_open_pct": round(100 * (m["open"] == m["yf_open"]).mean(), 1),
                          "open_eq_prev_close_pct": round(100 * m["unchanged"].mean(), 1)})
        out["corpus_vs_yfinance"] = rows2
    except Exception as e:  # noqa: BLE001
        out["corpus_vs_yfinance"] = f"ERROR {type(e).__name__}: {e}"[:200]

    (HERE / "a_open_audit.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1)[:3500])


def _norm_cdf(x):
    from math import erf, sqrt
    x = np.clip(np.nan_to_num(np.asarray(x, dtype=float), nan=0.0, posinf=30.0, neginf=-30.0),
                -30.0, 30.0)
    return 0.5 * (1.0 + np.vectorize(erf)(x / sqrt(2.0)))


if __name__ == "__main__":
    main()
