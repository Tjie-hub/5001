# Transfer — LQ45 Walk-Forward Run

**Goal**: Run walk-forward on all 45 LQ45 tickers across all 10 strategies, identify the winning strategy per ticker and overall, then export a compact markdown report we can review on Windows.

**Run from**: Linux box, `/home/tjiesar/10 Projects/idx-walkforward-5001/`
**Prereqs**: venv active, `data/walkforward.db` present, `engine/walkforward_multi.py` importable.

---

## Step 1 — Sanity check the DB

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
source venv/bin/activate

# Tables present?
sqlite3 data/walkforward.db ".tables"

# How many LQ45 tickers have OHLCV?
sqlite3 data/walkforward.db "SELECT ticker, COUNT(*) AS bars, MIN(date), MAX(date)
FROM ohlcv
WHERE ticker IN ('ACES','ADMR','ADRO','AKRA','AMMN','AMRT','ANTM','ARTO','ASII','BBCA',
                 'BBNI','BBRI','BBTN','BMRI','BRIS','BRPT','CPIN','CTRA','ESSA','EXCL',
                 'GOTO','ICBP','INCO','INDF','INKP','ISAT','ITMG','JPFA','JSMR','KLBF',
                 'MAPA','MAPI','MBMA','MDKA','MEDC','PGAS','PGEO','PTBA','SIDO','SMGR',
                 'SMRA','TLKM','TOWR','UNTR','UNVR')
GROUP BY ticker
ORDER BY ticker;"

# Existing wf_scores rows for LQ45?
sqlite3 data/walkforward.db "SELECT COUNT(DISTINCT ticker), COUNT(*) FROM wf_scores
WHERE ticker IN ('ACES','ADMR','ADRO','AKRA','AMMN','AMRT','ANTM','ARTO','ASII','BBCA',
                 'BBNI','BBRI','BBTN','BMRI','BRIS','BRPT','CPIN','CTRA','ESSA','EXCL',
                 'GOTO','ICBP','INCO','INDF','INKP','ISAT','ITMG','JPFA','JSMR','KLBF',
                 'MAPA','MAPI','MBMA','MDKA','MEDC','PGAS','PGEO','PTBA','SIDO','SMGR',
                 'SMRA','TLKM','TOWR','UNTR','UNVR');"
```

**Decision point**:
- If `wf_scores` already has fresh rows for all 45 tickers → **skip to Step 3** (aggregate only).
- If empty or stale → continue to **Step 2** (run walk-forward).

---

## Step 2 — Run walk-forward over LQ45

Save as `wf_lq45.py` at project root:

```python
"""
wf_lq45.py — Run walk-forward across LQ45 universe and dump JSON + MD report.

Usage:  python wf_lq45.py
Output: out/wf_lq45_results.json
        out/wf_lq45_report.md
"""
import json
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd
from engine.walkforward_multi import run_walk_forward

LQ45 = [
    "ACES","ADMR","ADRO","AKRA","AMMN","AMRT","ANTM","ARTO","ASII","BBCA",
    "BBNI","BBRI","BBTN","BMRI","BRIS","BRPT","CPIN","CTRA","ESSA","EXCL",
    "GOTO","ICBP","INCO","INDF","INKP","ISAT","ITMG","JPFA","JSMR","KLBF",
    "MAPA","MAPI","MBMA","MDKA","MEDC","PGAS","PGEO","PTBA","SIDO","SMGR",
    "SMRA","TLKM","TOWR","UNTR","UNVR",
]

DB = "data/walkforward.db"
CAPITAL = 50_000_000
OUT_DIR = Path("out")
OUT_DIR.mkdir(exist_ok=True)


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


def main():
    all_results = {}
    t0 = time.time()
    for i, t in enumerate(LQ45, 1):
        try:
            df = load_ohlcv(t)
            if len(df) < 350:
                print(f"[{i:2}/45] {t}: SKIP — only {len(df)} bars (need ≥350 for 12+3 mo WF)")
                continue
            wf = run_walk_forward(df, capital=CAPITAL)
            if "error" in wf:
                print(f"[{i:2}/45] {t}: ERROR — {wf['error']}")
                continue
            ranked = wf.get("ranked", [])
            # Strip per-window detail to keep JSON small
            for r in ranked:
                r.pop("windows", None)
            best = ranked[0] if ranked else None
            all_results[t] = {
                "bars": len(df),
                "windows": wf["windows"],
                "best": wf["best"],
                "ranked": ranked,
            }
            best_str = f"{best['strategy']} (score={best['score']}, ret={best['avg_return_pct']:.1f}%)" if best else "n/a"
            print(f"[{i:2}/45] {t}: best={best_str}  | elapsed={time.time()-t0:.0f}s")
        except Exception as e:
            print(f"[{i:2}/45] {t}: EXCEPTION — {e}")

    json_path = OUT_DIR / "wf_lq45_results.json"
    json_path.write_text(json.dumps(all_results, indent=2, default=str))
    print(f"\nWrote {json_path} ({len(all_results)} tickers, {time.time()-t0:.0f}s total)")

    # Build markdown report
    md = build_report(all_results)
    md_path = OUT_DIR / "wf_lq45_report.md"
    md_path.write_text(md)
    print(f"Wrote {md_path}")


def build_report(results: dict) -> str:
    lines = ["# LQ45 Walk-Forward Report\n"]
    lines.append(f"_Tickers analyzed: {len(results)} of 45_\n")

    # Strategy popularity — which strategy is "best" most often
    from collections import Counter
    winner_count = Counter(r["best"] for r in results.values() if r.get("best"))
    lines.append("## Strategy ranking by # of LQ45 tickers where it wins\n")
    lines.append("| Strategy | Tickers Won | % of LQ45 |")
    lines.append("|---|---:|---:|")
    for strat, n in winner_count.most_common():
        lines.append(f"| {strat} | {n} | {n/len(results)*100:.0f}% |")

    # Per-ticker best
    lines.append("\n## Best strategy per ticker (ranked by score)\n")
    lines.append("| Ticker | Best Strategy | Score | Avg Return % | Win Rate % | Sharpe | Consistency % | Max DD % |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    rows = []
    for t, r in results.items():
        ranked = r.get("ranked", [])
        if not ranked:
            continue
        b = ranked[0]
        rows.append((
            b.get("score", 0), t, b["strategy"],
            b.get("avg_return_pct", 0), b.get("avg_win_rate", 0),
            b.get("avg_sharpe", 0), b.get("consistency_pct", 0),
            b.get("avg_max_drawdown", 0),
        ))
    rows.sort(key=lambda x: x[0], reverse=True)
    for score, t, s, ret, wr, sh, cons, dd in rows:
        lines.append(f"| {t} | {s} | {score} | {ret:.2f} | {wr:.1f} | {sh:.2f} | {cons:.1f} | {dd:.2f} |")

    # Top 10 ticker-strategy pairs by avg return (across any strategy)
    lines.append("\n## Top 15 (ticker × strategy) combos by avg walk-forward return\n")
    lines.append("| Rank | Ticker | Strategy | Avg Return % | Win Rate % | Consistency % | Max DD % |")
    lines.append("|---:|---|---|---:|---:|---:|---:|")
    flat = []
    for t, r in results.items():
        for entry in r.get("ranked", []):
            flat.append((entry.get("avg_return_pct", 0), t, entry["strategy"],
                         entry.get("avg_win_rate", 0), entry.get("consistency_pct", 0),
                         entry.get("avg_max_drawdown", 0)))
    flat.sort(reverse=True)
    for i, (ret, t, s, wr, cons, dd) in enumerate(flat[:15], 1):
        lines.append(f"| {i} | {t} | {s} | {ret:.2f} | {wr:.1f} | {cons:.1f} | {dd:.2f} |")

    # Worst performers — flag for blacklist
    lines.append("\n## Worst 10 (ticker × strategy) combos — avoid these pairs\n")
    lines.append("| Ticker | Strategy | Avg Return % | Max DD % |")
    lines.append("|---|---|---:|---:|")
    for ret, t, s, _, _, dd in sorted(flat)[:10]:
        lines.append(f"| {t} | {s} | {ret:.2f} | {dd:.2f} |")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
```

Then run:

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
source venv/bin/activate
python wf_lq45.py | tee out/wf_lq45_log.txt
```

**Expected runtime**: ~15–40 minutes depending on bars per ticker (10 strategies × 45 tickers × N windows). Log streams to terminal so you can monitor.

---

## Step 3 — Alternative: use existing `wf_scores` table (no re-run)

If Step 1 showed `wf_scores` already populated for LQ45, skip the heavy run and just aggregate:

```bash
sqlite3 -header -column data/walkforward.db <<SQL
.headers on
.mode markdown
SELECT
  ticker,
  strategy,
  ROUND(consistency_pct,1) AS cons_pct,
  ROUND(weighted_score,3)  AS score
FROM wf_scores
WHERE ticker IN ('ACES','ADMR','ADRO','AKRA','AMMN','AMRT','ANTM','ARTO','ASII','BBCA',
                 'BBNI','BBRI','BBTN','BMRI','BRIS','BRPT','CPIN','CTRA','ESSA','EXCL',
                 'GOTO','ICBP','INCO','INDF','INKP','ISAT','ITMG','JPFA','JSMR','KLBF',
                 'MAPA','MAPI','MBMA','MDKA','MEDC','PGAS','PGEO','PTBA','SIDO','SMGR',
                 'SMRA','TLKM','TOWR','UNTR','UNVR')
ORDER BY ticker, weighted_score DESC;
SQL
```

For the "best strategy per ticker" view:

```bash
sqlite3 -header -column data/walkforward.db > out/wf_lq45_best.md <<SQL
.headers on
.mode markdown
WITH ranked AS (
  SELECT ticker, strategy, consistency_pct, weighted_score,
         ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY weighted_score DESC) AS rn
  FROM wf_scores
  WHERE ticker IN ('ACES','ADMR','ADRO','AKRA','AMMN','AMRT','ANTM','ARTO','ASII','BBCA',
                   'BBNI','BBRI','BBTN','BMRI','BRIS','BRPT','CPIN','CTRA','ESSA','EXCL',
                   'GOTO','ICBP','INCO','INDF','INKP','ISAT','ITMG','JPFA','JSMR','KLBF',
                   'MAPA','MAPI','MBMA','MDKA','MEDC','PGAS','PGEO','PTBA','SIDO','SMGR',
                   'SMRA','TLKM','TOWR','UNTR','UNVR')
)
SELECT ticker, strategy AS best_strategy, ROUND(consistency_pct,1) AS cons_pct, ROUND(weighted_score,3) AS score
FROM ranked WHERE rn = 1
ORDER BY weighted_score DESC;
SQL
```

And the "strategy popularity across LQ45":

```bash
sqlite3 -header -column data/walkforward.db <<SQL
.headers on
.mode markdown
WITH ranked AS (
  SELECT ticker, strategy,
         ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY weighted_score DESC) AS rn
  FROM wf_scores
  WHERE ticker IN ('ACES','ADMR','ADRO','AKRA','AMMN','AMRT','ANTM','ARTO','ASII','BBCA',
                   'BBNI','BBRI','BBTN','BMRI','BRIS','BRPT','CPIN','CTRA','ESSA','EXCL',
                   'GOTO','ICBP','INCO','INDF','INKP','ISAT','ITMG','JPFA','JSMR','KLBF',
                   'MAPA','MAPI','MBMA','MDKA','MEDC','PGAS','PGEO','PTBA','SIDO','SMGR',
                   'SMRA','TLKM','TOWR','UNTR','UNVR')
)
SELECT strategy, COUNT(*) AS wins
FROM ranked WHERE rn = 1
GROUP BY strategy
ORDER BY wins DESC;
SQL
```

---

## Step 4 — What to bring back

Sync these files back to Windows (`D:\IDX\out\`) for review:

1. `out/wf_lq45_results.json` — full per-ticker × per-strategy walk-forward metrics
2. `out/wf_lq45_report.md` — aggregated markdown report
3. `out/wf_lq45_log.txt` — run log (helps debug skipped tickers)

If Step 3 path was used instead:
1. `out/wf_lq45_best.md` — best strategy per ticker
2. Console output of the popularity query (paste into a note)

---

## Notes / known things to verify

- **Existing strategies** in `STRATEGY_FUNCS` (engine/walkforward_multi.py:155): `vol_weighted, momentum, vwap_reversion, conservative, Volume Profile POC, Inside Bar Breakout, NR7 Breakout, ORB, Swing Trend, Trend Following Breakout`. Minervini VCP is **not implemented**. We can add it next as a new strategy function and re-run.
- **WF window**: 12 months train / 3 months test, rolling. Anything with <15 months of data is skipped.
- **Capital**: 50,000,000 IDR default (matches `rule.md`).
- **MBMA / ADMR / PGEO** are post-2023 listings — they may have insufficient bars for WF.
- **GOTO / BREN / DSSA** — historically choppy or removed from LQ45. Expect SKIP or poor scores.

---

## Next step after results land

Once `wf_lq45_report.md` is back, we'll:
1. Identify the **2–3 strategies that win across the most LQ45 tickers** (this is your real edge).
2. Find tickers where **multiple strategies converge** (highest conviction trades).
3. Decide whether to **add Minervini VCP** as strategy #11 or **lean on existing Swing Trend / Trend Following Breakout** which already encode a similar VCP-adjacent setup.
