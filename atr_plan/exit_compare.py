"""
Step 2 — Exit comparison: same entries, different exits.

  A = current fixed % TP/SL
  B = ATR stop + ATR TP  (mean-rev: 1.5/1.5 ATR + 5-bar time stop; momentum: 2 ATR stop / 3 ATR TP)
  C = ATR stop + chandelier (momentum only; mean-rev C == B)
  D = C exits + ATR risk sizing (0.75% risk, 30% cap) — portfolio level only

No parameters are fitted, so every calendar year is out-of-sample. Adoption rule
(BETTER_THAN_A): variant beats A in >= 70% of yearly windows AND block-bootstrap 95% CI of
the mean per-trade difference is > 0, under BOTH same-bar conventions (stop_first, ohlc).
Separately, PROFITABLE: variant's average net per trade > 0 at stress cost 0.8%.

Usage:
  python atr_plan/exit_compare.py --db data/history_long.db
  python atr_plan/exit_compare.py --db data/history_long.db --strategies nr7,momentum --cost-filter
  python atr_plan/exit_compare.py --csv-dir some/dir      # one CSV per ticker: date,open,high,low,close,volume
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atr_exits import (Costs, ExitSpec, add_indicators, atr_position_size,  # noqa: E402
                       cost_filter_ok, simulate_trade, tick_size)

NORMAL = Costs(0.0025, 0.0035)   # 0.6% round trip
STRESS = Costs(0.0035, 0.0045)   # 0.8% round trip
SAME_BAR_MODES = ("stop_first", "ohlc")


# ================================================================ reference entries
# NOTE: these approximate the 5001 strategies from their spec. For the real test,
# replace with adapters that call engine/strategies.py (see CLAUDE_CODE_PROMPT.md).
def _vr(df):
    return df["volume"] / df["volume"].rolling(20, min_periods=20).mean()


def sig_vol_weighted(df):
    return (_vr(df) > 1.8) & (df["close"] > df["open"])


def sig_momentum(df):
    up = df["close"] > df["close"].shift(1)
    return up & up.shift(1, fill_value=False) & (_vr(df) > 1.3)


def sig_vwap_rev(df):
    tp = (df["high"] + df["low"] + df["close"]) / 3
    vwap20 = (tp * df["volume"]).rolling(20).sum() / df["volume"].rolling(20).sum()
    return (df["close"] / vwap20 - 1 < -0.01) & (_vr(df) > 1.3)


def sig_conservative(df):
    ma20 = df["close"].rolling(20).mean()
    return (_vr(df) > 1.3) & (df["close"] > ma20) & df["atr_pct"].between(0.01, 0.05)


def sig_nr7(df):
    rng = df["high"] - df["low"]
    return (rng <= rng.rolling(7, min_periods=7).min()) & (df["close"] > df["close"].rolling(50).mean())


STRATS = {
    #  name           signal fn          type   fixed TP/SL (A)   entry mode
    "vol_weighted": (sig_vol_weighted, "mom", (0.020, 0.015), "open"),
    "momentum":     (sig_momentum,     "mom", (0.035, 0.025), "open"),
    "vwap_rev":     (sig_vwap_rev,     "mr",  (0.015, 0.010), "open"),
    "conservative": (sig_conservative, "mr",  (0.015, 0.010), "open"),
    "nr7":          (sig_nr7,          "mom", (0.030, 0.020), "stop_high"),
}


def variants_for(stype: str, fixed: tuple[float, float]) -> dict[str, ExitSpec]:
    tp, sl = fixed
    A = ExitSpec("fixed", tp_pct=tp, sl_pct=sl, max_hold=20, label="A_fixed")
    if stype == "mr":
        B = ExitSpec("atr_tpsl", stop_k=1.5, tp_k=1.5, time_stop=5, max_hold=5, label="B_atr_tpsl")
        C = ExitSpec("atr_tpsl", stop_k=1.5, tp_k=1.5, time_stop=5, max_hold=5, label="C_same_as_B")
    else:
        B = ExitSpec("atr_tpsl", stop_k=2.0, tp_k=3.0, max_hold=20, label="B_atr_tpsl")
        C = ExitSpec("chandelier", stop_k=2.0, chand_k=3.0, max_hold=60, label="C_chandelier")
    return {"A": A, "B": B, "C": C}


# ================================================================ data
def load_db(path: str, min_bars: int) -> dict[str, pd.DataFrame]:
    con = sqlite3.connect(path)
    raw = pd.read_sql("SELECT ticker,date,open,high,low,close,volume FROM ohlcv_long ORDER BY ticker,date", con)
    con.close()
    out = {}
    for t, g in raw.groupby("ticker"):
        if t.startswith("^"):
            continue
        g = g.set_index(pd.to_datetime(g["date"])).drop(columns=["ticker", "date"])
        if len(g) >= min_bars:
            out[t] = g
    return out


def load_csv_dir(d: str, min_bars: int) -> dict[str, pd.DataFrame]:
    out = {}
    for f in sorted(Path(d).glob("*.csv")):
        g = pd.read_csv(f, parse_dates=["date"]).set_index("date").sort_index()
        g.columns = [c.lower() for c in g.columns]
        if len(g) >= min_bars:
            out[f.stem] = g[["open", "high", "low", "close", "volume"]]
    return out


# ================================================================ trade generation
def generate_trades(data, strat_names, min_adv, use_cost_filter) -> pd.DataFrame:
    rows = []
    for tkr, df in data.items():
        df = add_indicators(df)
        adv = (df["close"] * df["volume"]).rolling(20).mean()
        o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        a14, a22, hh = df["atr14"].to_numpy(), df["atr22"].to_numpy(), df["hh22"].to_numpy()
        dates = df.index
        for sname in strat_names:
            fn, stype, fixed, entry_mode = STRATS[sname]
            sig = fn(df).fillna(False).to_numpy(bool)
            specs = variants_for(stype, fixed)
            for t in np.flatnonzero(sig):
                i = t + 1
                if i >= len(c) or not np.isfinite(a14[t]) or adv.iloc[t] < min_adv:
                    continue
                if use_cost_filter and not cost_filter_ok(a14[t] / c[t]):
                    continue
                entry_mid = entry_mode != "open"
                if entry_mode == "open":
                    entry = o[i]
                else:  # buy-stop at signal-bar high + 1 tick
                    trig = h[t] + tick_size(h[t])
                    if h[i] < trig or o[i] > trig + a14[t]:   # not triggered / gapped > 1 ATR
                        continue
                    entry = max(o[i], trig)
                for vname, spec in specs.items():
                    for sb in SAME_BAR_MODES:
                        r = simulate_trade(o, h, l, c, a14, a22, hh, i, entry, spec, NORMAL,
                                           same_bar=sb, entry_mid=entry_mid)
                        if r is None:
                            continue
                        r["net_stress"] = (r["exit"] * (1 - STRESS.sell)) / (r["entry"] * (1 + STRESS.buy)) - 1
                        r.update(ticker=tkr, strategy=sname, stype=stype, variant=vname,
                                 mode=sb, sig_date=dates[t], entry_date=dates[i],
                                 exit_date=dates[min(r["exit_i"], len(dates) - 1)])
                        rows.append(r)
    tr = pd.DataFrame(rows)
    if not tr.empty:
        tr["year"] = pd.to_datetime(tr["entry_date"]).dt.year
        tr["early_stop"] = tr["reason"].isin(["stop", "gap_stop"]) & (tr["bars"] <= 2)
        # keep only signals where every variant produced a trade (strict pairing)
        key = ["ticker", "strategy", "sig_date", "mode"]
        full = tr.groupby(key)["variant"].transform("nunique") == 3
        tr = tr[full].copy()
    return tr


# ================================================================ statistics
def window_table(tr: pd.DataFrame, min_trades: int) -> pd.DataFrame:
    g = tr.groupby(["mode", "strategy", "variant", "year"])
    w = g.agg(n=("net", "size"), win=("net", lambda x: (x > 0).mean()), avg_net=("net", "mean"),
              avg_net_stress=("net_stress", "mean"), exp_R=("R", "mean"), avg_bars=("bars", "mean"),
              early_stop=("early_stop", "mean")).reset_index()
    return w[w["n"] >= min_trades]


def block_bootstrap_diff(tr, strategy, mode, var, base="A", n_boot=2000, seed=7):
    """Paired per-trade difference (var - base), resampling (ticker, year-month) blocks."""
    key = ["ticker", "strategy", "sig_date", "mode"]
    sub = tr[(tr.strategy == strategy) & (tr["mode"] == mode) & tr.variant.isin([var, base])]
    p = sub.pivot_table(index=key, columns="variant", values="net").dropna()
    if p.empty:
        return np.nan, np.nan, np.nan, 0
    d = (p[var] - p[base]).rename("d").reset_index()
    d["blk"] = d["ticker"] + "_" + pd.to_datetime(d["sig_date"]).dt.strftime("%Y-%m")
    blocks = [g.to_numpy() for _, g in d.groupby("blk")["d"]]
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.integers(0, len(blocks), len(blocks))
        means[b] = np.concatenate([blocks[k] for k in pick]).mean()
    return d["d"].mean(), np.percentile(means, 2.5), np.percentile(means, 97.5), len(d)


def verdict_table(tr, win) -> pd.DataFrame:
    out = []
    for mode in SAME_BAR_MODES:
        for s in sorted(tr.strategy.unique()):
            wa = win[(win["mode"] == mode) & (win.strategy == s)]
            base = wa[wa.variant == "A"].set_index("year")["avg_net"]
            for v in ("B", "C"):
                wv = wa[wa.variant == v].set_index("year")["avg_net"]
                yrs = base.index.intersection(wv.index)
                share = float((wv[yrs] > base[yrs]).mean()) if len(yrs) else np.nan
                m, lo, hi, n = block_bootstrap_diff(tr, s, mode, v)
                sub = tr[(tr.strategy == s) & (tr["mode"] == mode) & (tr.variant == v)]
                out.append(dict(mode=mode, strategy=s, variant=v, years=len(yrs), win_share=share,
                                mean_diff=m, ci_lo=lo, ci_hi=hi, n_pairs=n,
                                abs_net_stress=sub["net_stress"].mean(),
                                ok=bool(len(yrs) and share >= 0.70 and np.isfinite(lo) and lo > 0)))
    vt = pd.DataFrame(out)
    # BETTER_THAN_A: passes under BOTH same-bar modes.  PROFITABLE: avg net > 0 at 0.8% cost, both modes.
    agg = vt.groupby(["strategy", "variant"]).agg(
        BETTER_THAN_A=("ok", "all"),
        PROFITABLE=("abs_net_stress", lambda x: bool((x > 0).all()))).reset_index()
    return vt.merge(agg, on=["strategy", "variant"])


# ================================================================ portfolio sim
def portfolio(tr, strategy, variant, mode="ohlc", start_eq=100e6, max_pos=5,
              notional_frac=0.20, atr_sizing=False):
    """Realized-P&L portfolio: max `max_pos` concurrent, one position per ticker."""
    t = tr[(tr.strategy == strategy) & (tr.variant == variant) & (tr["mode"] == mode)]
    t = t.sort_values(["entry_date", "ticker"])
    eq, open_pos, curve, taken = start_eq, [], [], 0
    for r in t.itertuples():
        still = []
        for p in open_pos:
            if p["exit_date"] < r.entry_date:
                eq += p["pnl"]
                curve.append((p["exit_date"], eq))
            else:
                still.append(p)
        open_pos = still
        if len(open_pos) >= max_pos or any(p["ticker"] == r.ticker for p in open_pos):
            continue
        notional = atr_position_size(eq, r.entry, r.stop0) * r.entry if atr_sizing else eq * notional_frac
        if notional <= 0:
            continue
        open_pos.append(dict(ticker=r.ticker, exit_date=r.exit_date, pnl=notional * r.net))
        taken += 1
    for p in sorted(open_pos, key=lambda x: x["exit_date"]):
        eq += p["pnl"]
        curve.append((p["exit_date"], eq))
    if not curve:
        return dict(trades=0)
    s = pd.Series([v for _, v in curve], index=pd.to_datetime([d for d, _ in curve]))
    s = s.groupby(level=0).last()
    yrs = max((s.index[-1] - s.index[0]).days / 365.25, 1e-9)
    m = s.resample("ME").last().ffill().pct_change().dropna()
    return dict(trades=taken, cagr=(max(s.iloc[-1], 1) / start_eq) ** (1 / yrs) - 1,
                sharpe_m=(m.mean() / m.std() * np.sqrt(12)) if m.std() > 0 else np.nan,
                max_dd=(s / s.cummax() - 1).min())


# ================================================================ report
def fmt_pct(x):
    return "—" if pd.isna(x) else f"{x*100:+.2f}%"


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--db")
    src.add_argument("--csv-dir")
    ap.add_argument("--strategies", default=",".join(STRATS))
    ap.add_argument("--min-bars", type=int, default=500)
    ap.add_argument("--min-adv", type=float, default=5e9, help="min 20d avg traded value (Rp)")
    ap.add_argument("--min-trades", type=int, default=10, help="min trades for a yearly window")
    ap.add_argument("--cost-filter", action="store_true", help="skip signals with ATR%% < ~1.6%%")
    ap.add_argument("--out", default="reports")
    a = ap.parse_args()

    data = load_db(a.db, a.min_bars) if a.db else load_csv_dir(a.csv_dir, a.min_bars)
    names = [s.strip() for s in a.strategies.split(",") if s.strip()]
    print(f"{len(data)} tickers, strategies: {names}")
    tr = generate_trades(data, names, a.min_adv, a.cost_filter)
    if tr.empty:
        sys.exit("No trades generated.")
    win = window_table(tr, a.min_trades)
    vt = verdict_table(tr, win)

    out = Path(a.out) / f"exit_compare_{datetime.now():%Y%m%d_%H%M}"
    out.mkdir(parents=True, exist_ok=True)
    tr.to_csv(out / "trades.csv", index=False)
    win.to_csv(out / "windows.csv", index=False)
    vt.to_csv(out / "verdict.csv", index=False)

    yrs = f"{tr.year.min()}–{tr.year.max()}"
    L = [f"# Exit comparison — {datetime.now():%Y-%m-%d %H:%M}", "",
         f"Tickers: {len(data)} · years {yrs} · cost filter: {a.cost_filter} · "
         f"min ADV Rp{a.min_adv/1e9:.0f}bn · cost 0.6% (stress 0.8%)", "",
         "## 1. Decision", "",
         "BETTER_THAN_A = beats fixed-% in ≥70% of years AND block-bootstrap 95% CI of Δ/trade > 0, "
         "under BOTH same-bar conventions. PROFITABLE = avg net/trade > 0 at 0.8% cost.", "",
         "| Strategy | Var | BETTER_THAN_A | PROFITABLE (0.8%) |", "|---|---|---|---|"]
    for r in vt.drop_duplicates(["strategy", "variant"]).itertuples():
        L.append(f"| {r.strategy} | {r.variant} | {'**YES**' if r.BETTER_THAN_A else 'no'} | "
                 f"{'**YES**' if r.PROFITABLE else 'no'} |")
    L += ["", "## 2. Detail vs A", "",
          "| Strategy | Var | Same-bar | Years | Win share | Mean Δ/trade | 95% CI | Net/trade @0.8% |",
          "|---|---|---|---|---|---|---|---|"]
    for r in vt.itertuples():
        L.append(f"| {r.strategy} | {r.variant} | {r.mode} | {r.years} | "
                 f"{'—' if pd.isna(r.win_share) else f'{r.win_share*100:.0f}%'} | {fmt_pct(r.mean_diff)} | "
                 f"[{fmt_pct(r.ci_lo)}, {fmt_pct(r.ci_hi)}] | {fmt_pct(r.abs_net_stress)} |")
    for mode in SAME_BAR_MODES:
        L += ["", f"## 3. Per-trade, same-bar = {mode} (0.6% cost)", "",
              "| Strategy | Var | Trades | Win% | Avg net | Exp R | Avg bars | Stopped ≤2 bars |",
              "|---|---|---|---|---|---|---|---|"]
        ov = tr[tr["mode"] == mode].groupby(["strategy", "variant"]).agg(
            n=("net", "size"), win=("net", lambda x: (x > 0).mean()), avg=("net", "mean"),
            R=("R", "mean"), bars=("bars", "mean"), es=("early_stop", "mean")).reset_index()
        for r in ov.itertuples():
            L.append(f"| {r.strategy} | {r.variant} | {r.n} | {r.win*100:.0f}% | {fmt_pct(r.avg)} | "
                     f"{r.R:+.2f} | {r.bars:.1f} | {r.es*100:.0f}% |")
    L += ["", "## 4. Portfolio (realized P&L, max 5 positions, same-bar = ohlc, 0.6% cost)", "",
          "| Strategy | Setup | Trades | CAGR | Sharpe (monthly) | Max DD |", "|---|---|---|---|---|---|"]
    for s in names:
        for lab, v, atr in (("A fixed, 20% notional", "A", False), ("B, 20% notional", "B", False),
                            ("C, 20% notional", "C", False), ("D = C + ATR sizing", "C", True)):
            p = portfolio(tr, s, v, atr_sizing=atr)
            if p.get("trades"):
                L.append(f"| {s} | {lab} | {p['trades']} | {fmt_pct(p['cagr'])} | "
                         f"{p['sharpe_m']:.2f} | {fmt_pct(p['max_dd'])} |")
    L += ["", "## 5. Exit reasons (% of trades, same-bar = ohlc)", ""]
    rs = (tr[tr["mode"] == "ohlc"].groupby(["strategy", "variant"])["reason"]
          .value_counts(normalize=True).unstack(fill_value=0) * 100).round(0)
    rs.index = [f"{a}/{b}" for a, b in rs.index]
    try:
        L += [rs.to_markdown()]
    except ImportError:
        L += ["```", rs.to_string(), "```"]
    L += ["", "Notes: entries identical across variants (strict pairing). Gap through stop fills at open. "
          "Chandelier evaluated on close, executed next open. No parameters fitted -> every year is OOS. "
          "Mean-reversion strategies have no chandelier variant (C = B). Portfolio DD is on realized equity."]
    (out / "summary.md").write_text("\n".join(L))
    print("\n".join(L))
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
