"""
meta_validate.py — Walk-forward validation of ML strategy-selection vs score-ranking.

Question it answers
-------------------
Does an ML meta-model that PREDICTS the winning strategy per (ticker, window) from
features known *before* each test window beat the existing weighted-score ranking?
Everything is evaluated out-of-sample, pooled across tickers, with no look-ahead.

Four arms are compared per test window:
  - ml_pick    : strategy the meta-model predicts -> its realized test-window return
  - score_pick : strategy the current weighted-score ranking would choose
                 (computed from PAST windows only) -> its realized return
  - oracle     : best possible strategy that window (upper bound)
  - eqw        : mean return across all strategies (naive baseline)

Swappable data source (the "build both" requirement)
----------------------------------------------------
  --source backtest  (default): full per-window x per-strategy return matrix from the
                                 walk-forward engine. This is the ONLY source that gives
                                 the counterfactual returns ML training + comparison need.
  --source paper               : realized outcomes from the paper_trades table. Reports
                                 current feasibility and exits — paper trading has too few
                                 closed trades to train/validate (see report). The hook is
                                 here so that, once paper history matures, it can supply a
                                 realized arm to overlay on the backtest counterfactuals.

Usage
-----
  venv/bin/python meta_validate.py                  # full LQ45, backtest
  venv/bin/python meta_validate.py --limit 5        # quick smoke: first 5 tickers
  venv/bin/python meta_validate.py --tickers BBCA,BBRI,TLKM
  venv/bin/python meta_validate.py --no-cache       # force re-run the engine
  venv/bin/python meta_validate.py --source paper

Outputs (read-only; never touches the engine or DB)
  out/meta_dataset_<source>.json   cached per-(ticker,window) dataset
  out/meta_validate_report.md      comparison report
"""
import argparse
import json
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from engine.walkforward_multi import (
    run_walk_forward,
    walk_forward_split,
    _rank_strategies,
    STRATEGY_FUNCS,
)
from engine.regime_filter import build_regime_features

DB = "data/walkforward.db"
CAPITAL = 50_000_000
OUT_DIR = Path("out")
FEATURE_COLS = ["adx", "ma_slope", "vr_mean", "range_pct", "close_vs_ma", "pct_above_ma"]
MIN_TRAIN_EXAMPLES = 20  # need this many past (ticker,window) rows before trusting ML
MIN_BARS = 350           # < this can't form a 12+3mo walk-forward

LQ45 = [
    "ACES", "ADMR", "ADRO", "AKRA", "AMMN", "AMRT", "ANTM", "ARTO", "ASII", "BBCA",
    "BBNI", "BBRI", "BBTN", "BMRI", "BRIS", "BRPT", "CPIN", "CTRA", "ESSA", "EXCL",
    "GOTO", "ICBP", "INCO", "INDF", "INKP", "ISAT", "ITMG", "JPFA", "JSMR", "KLBF",
    "MAPA", "MAPI", "MBMA", "MDKA", "MEDC", "PGAS", "PGEO", "PTBA", "SIDO", "SMGR",
    "SMRA", "TLKM", "TOWR", "UNTR", "UNVR",
]


# ─────────────────────────────────────────────
# DATA SOURCES (swappable). Each returns a list of "examples":
#   {ticker, window, test_start, test_end, features:{col:val},
#    metrics:{strategy:{return, win_rate, sharpe, max_dd, profit_factor}}}
# ─────────────────────────────────────────────

def load_ohlcv(ticker: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB)
    df = pd.read_sql(
        "SELECT date, open, high, low, close, volume FROM ohlcv "
        "WHERE ticker = ? ORDER BY date ASC",
        conn, params=(ticker,),
    )
    conn.close()
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    return df


def build_backtest_examples(tickers: list[str]) -> list[dict]:
    """Run the walk-forward engine per ticker; emit one example per (ticker, window)."""
    examples = []
    t0 = time.time()
    for i, tk in enumerate(tickers, 1):
        df = load_ohlcv(tk)
        if len(df) < MIN_BARS:
            print(f"[{i:2}/{len(tickers)}] {tk}: SKIP — {len(df)} bars (< {MIN_BARS})")
            continue

        windows = walk_forward_split(df, train_months=12, test_months=3)
        wf = run_walk_forward(df, capital=CAPITAL)
        if "error" in wf or not windows:
            print(f"[{i:2}/{len(tickers)}] {tk}: SKIP — {wf.get('error', 'no windows')}")
            continue

        # Per-window per-strategy returns, keyed by window index.
        by_window: dict[int, dict[str, dict]] = {}
        for strat, summ in wf["summary"].items():
            for w in summ["windows"]:
                by_window.setdefault(w["window"], {})[strat] = {
                    "return": float(w["total_return_pct"]),
                    "win_rate": float(w["win_rate"]),
                    "sharpe": float(w["sharpe"]),
                    "max_dd": float(w["max_drawdown_pct"]),
                    "profit_factor": float(min(w["profit_factor"], 999)),
                }

        n_made = 0
        for w in windows:
            widx = w["window"]
            metrics = by_window.get(widx)
            if not metrics or len(metrics) < len(STRATEGY_FUNCS):
                continue  # incomplete window
            feats = build_regime_features(w["train"])
            if feats.empty:
                continue
            row = feats.iloc[-1]
            if row[FEATURE_COLS].isna().any():
                continue
            examples.append({
                "ticker": tk,
                "window": widx,
                "test_start": w["test_start"],
                "test_end": w["test_end"],
                "features": {c: float(row[c]) for c in FEATURE_COLS},
                "metrics": metrics,
            })
            n_made += 1
        print(f"[{i:2}/{len(tickers)}] {tk}: {n_made} windows  | elapsed={time.time()-t0:.0f}s")

    print(f"\nBuilt {len(examples)} (ticker,window) examples in {time.time()-t0:.0f}s")
    return examples


def build_paper_examples(tickers: list[str]) -> list[dict]:
    """Paper-trade source. Currently reports infeasibility and returns []."""
    conn = sqlite3.connect(DB)
    n_closed = conn.execute(
        "SELECT COUNT(*) FROM paper_trades WHERE status != 'OPEN'"
    ).fetchone()[0]
    n_strats = conn.execute(
        "SELECT COUNT(DISTINCT strategy) FROM paper_trades WHERE status != 'OPEN'"
    ).fetchone()[0]
    conn.close()
    print("=" * 64)
    print("PAPER SOURCE — feasibility check")
    print("=" * 64)
    print(f"  closed paper trades : {n_closed}")
    print(f"  distinct strategies : {n_strats}")
    print(
        "\n  Paper trading executes only ONE strategy per signal, so it cannot\n"
        "  produce the per-window x ALL-strategies counterfactual matrix that ML\n"
        "  training and the oracle/eqw baselines require. It can only ever supply\n"
        "  a 'realized arm' to overlay on backtest counterfactuals — and even that\n"
        f"  needs months of fills. With {n_closed} closed trades, validation is not\n"
        "  possible yet. Re-run with --source backtest.\n"
    )
    return []


SOURCES = {"backtest": build_backtest_examples, "paper": build_paper_examples}


# ─────────────────────────────────────────────
# SCORE-RANKING PICK (current system's logic, on past windows only)
# ─────────────────────────────────────────────

def score_pick(past_examples_for_ticker: list[dict]) -> str | None:
    """Rank strategies by the engine's weighted score using only PAST windows."""
    if not past_examples_for_ticker:
        return None
    agg: dict[str, list[dict]] = {}
    for ex in past_examples_for_ticker:
        for strat, m in ex["metrics"].items():
            agg.setdefault(strat, []).append(m)

    summary = {}
    for strat, ms in agg.items():
        rets = [m["return"] for m in ms]
        summary[strat] = {
            "strategy": strat,
            "avg_win_rate": float(np.mean([m["win_rate"] for m in ms])),
            "avg_return_pct": float(np.mean(rets)),
            "avg_sharpe": float(np.mean([m["sharpe"] for m in ms])),
            "avg_max_drawdown": float(np.mean([m["max_dd"] for m in ms])),
            "consistency_pct": float(sum(1 for r in rets if r > 0) / len(rets) * 100),
        }
    ranked = _rank_strategies(summary)
    return ranked[0]["strategy"] if ranked else None


# ─────────────────────────────────────────────
# WALK-FORWARD META-MODEL LOOP (leakage-free)
# ─────────────────────────────────────────────

def winner(metrics: dict[str, dict]) -> str:
    return max(metrics.items(), key=lambda kv: kv[1]["return"])[0]


def walk_forward_meta(examples: list[dict]) -> dict:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    examples = sorted(examples, key=lambda e: e["test_start"])
    step_dates = sorted({e["test_start"] for e in examples})

    records = []
    burn_in = 0
    for d in step_dates:
        train = [e for e in examples if e["test_start"] < d]
        current = [e for e in examples if e["test_start"] == d]

        clf = scaler = None
        if len(train) >= MIN_TRAIN_EXAMPLES:
            X = np.array([[e["features"][c] for c in FEATURE_COLS] for e in train])
            y = np.array([winner(e["metrics"]) for e in train])
            if len(set(y)) >= 2:
                scaler = StandardScaler().fit(X)
                clf = LogisticRegression(
                    C=1.0, max_iter=1000, class_weight="balanced"
                ).fit(scaler.transform(X), y)

        for e in current:
            rets = {s: m["return"] for s, m in e["metrics"].items()}
            oracle = max(rets.values())
            eqw = float(np.mean(list(rets.values())))

            past_tk = [t for t in train if t["ticker"] == e["ticker"]]
            sp = score_pick(past_tk)
            score_ret = rets.get(sp) if sp else None

            if clf is None:
                burn_in += 1
                ml_ret = ml_strat = None
            else:
                xv = scaler.transform([[e["features"][c] for c in FEATURE_COLS]])
                ml_strat = clf.predict(xv)[0]
                ml_ret = rets.get(ml_strat)

            records.append({
                "ticker": e["ticker"], "test_start": e["test_start"],
                "ml_strat": ml_strat, "ml_ret": ml_ret,
                "score_strat": sp, "score_ret": score_ret,
                "oracle_ret": oracle, "eqw_ret": eqw,
            })

    evaluated = [r for r in records if r["ml_ret"] is not None and r["score_ret"] is not None]
    return {
        "n_examples": len(examples),
        "n_records": len(records),
        "n_burn_in": burn_in,
        "n_evaluated": len(evaluated),
        "records": records,
        "evaluated": evaluated,
    }


# ─────────────────────────────────────────────
# REPORT
# ─────────────────────────────────────────────

def build_report(res: dict, source: str, tickers: list[str]) -> str:
    ev = res["evaluated"]
    L = ["# Meta-Model Validation — ML Strategy-Selection vs Score-Ranking\n"]
    L.append(f"_Source: **{source}** | tickers requested: {len(tickers)} | "
             f"examples: {res['n_examples']} | evaluated windows: {res['n_evaluated']} "
             f"| burn-in (no ML yet): {res['n_burn_in']}_\n")

    if not ev:
        L.append("> No windows could be evaluated. With this little history the meta-model "
                 "has nothing to train on. This is the expected result for thin data — "
                 "it is evidence the approach is premature, not a bug.\n")
        return "\n".join(L) + "\n"

    def avg(key):
        return float(np.mean([r[key] for r in ev]))

    ml, sc, orc, eq = avg("ml_ret"), avg("score_ret"), avg("oracle_ret"), avg("eqw_ret")
    ml_beats = sum(1 for r in ev if r["ml_ret"] > r["score_ret"])
    ml_ties = sum(1 for r in ev if r["ml_ret"] == r["score_ret"])

    L.append("## Average realized test-window return per arm\n")
    L.append("| Arm | Avg Return % | vs Score-Pick |")
    L.append("|---|---:|---:|")
    L.append(f"| Oracle (upper bound) | {orc:.2f} | {orc-sc:+.2f} |")
    L.append(f"| **ML-Pick** | **{ml:.2f}** | **{ml-sc:+.2f}** |")
    L.append(f"| Score-Pick (current system) | {sc:.2f} | — |")
    L.append(f"| Equal-weight (naive) | {eq:.2f} | {eq-sc:+.2f} |")

    L.append(f"\n## Head-to-head (ML vs Score), n = {len(ev)}\n")
    L.append(f"- ML strictly better : **{ml_beats}** ({ml_beats/len(ev)*100:.0f}%)")
    L.append(f"- Tie (same pick)    : {ml_ties}")
    L.append(f"- Score better       : {len(ev)-ml_beats-ml_ties}")

    verdict = ("ML picking shows an edge" if ml - sc > 0.25
               else "no meaningful edge — score-ranking holds" if abs(ml - sc) <= 0.25
               else "ML picking is WORSE — do not adopt")
    L.append(f"\n**Verdict:** {verdict}. ML−Score = {ml-sc:+.2f}%/window. "
             f"Score captures {sc/orc*100:.0f}% of oracle; ML captures {ml/orc*100:.0f}%."
             if orc > 0 else f"\n**Verdict:** {verdict}. ML−Score = {ml-sc:+.2f}%/window.")

    ml_cnt = Counter(r["ml_strat"] for r in ev)
    sc_cnt = Counter(r["score_strat"] for r in ev)
    L.append("\n## What each arm picks\n")
    L.append("| Strategy | ML picks | Score picks |")
    L.append("|---|---:|---:|")
    for s in sorted(set(ml_cnt) | set(sc_cnt), key=lambda x: -(ml_cnt[x]+sc_cnt[x])):
        L.append(f"| {s} | {ml_cnt.get(s,0)} | {sc_cnt.get(s,0)} |")

    L.append("\n## Per-window detail\n")
    L.append("| Test Start | Ticker | ML Pick | ML % | Score Pick | Score % | Oracle % |")
    L.append("|---|---|---|---:|---|---:|---:|")
    for r in sorted(ev, key=lambda x: (x["test_start"], x["ticker"])):
        L.append(f"| {r['test_start']} | {r['ticker']} | {r['ml_strat']} | {r['ml_ret']:.2f} "
                 f"| {r['score_strat']} | {r['score_ret']:.2f} | {r['oracle_ret']:.2f} |")

    L.append("\n## Caveats\n")
    L.append(f"- Sample is thin ({len(ev)} evaluated windows). Treat as **directional "
             "evidence, not proof** — exactly the overfitting risk flagged before building.")
    L.append("- Labels = realized in-window winner; features = regime/vol at train-end. "
             "No look-ahead: each prediction trains only on strictly earlier windows.")
    L.append("- Score-pick uses the engine's weighted-score ranking on past windows only, "
             "mirroring how the live system selects per ticker.")
    return "\n".join(L) + "\n"


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=list(SOURCES), default="backtest")
    ap.add_argument("--tickers", help="comma-separated; default = LQ45")
    ap.add_argument("--limit", type=int, help="use only the first N tickers")
    ap.add_argument("--no-cache", action="store_true", help="ignore cached dataset")
    args = ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    tickers = args.tickers.split(",") if args.tickers else list(LQ45)
    if args.limit:
        tickers = tickers[:args.limit]

    cache = OUT_DIR / f"meta_dataset_{args.source}.json"
    if cache.exists() and not args.no_cache and not args.tickers and not args.limit:
        print(f"Loading cached dataset {cache} (use --no-cache to rebuild)")
        examples = json.loads(cache.read_text())
    else:
        examples = SOURCES[args.source](tickers)
        if examples and not args.tickers and not args.limit:
            cache.write_text(json.dumps(examples, default=float))
            print(f"Cached dataset -> {cache}")

    if not examples:
        print("\nNo examples — nothing to validate.")
        return 0

    res = walk_forward_meta(examples)
    report = build_report(res, args.source, tickers)
    report_path = OUT_DIR / "meta_validate_report.md"
    report_path.write_text(report)
    print(f"\nWrote {report_path}")
    print("\n" + report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
