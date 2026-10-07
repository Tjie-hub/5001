"""
Exit comparison v2 — same harness as exit_compare.py, with the drift bias removed.

Why v2: v1 scores exits by raw net return per trade. Exits that hold longer (C holds ~13 bars, A ~3)
collect more market drift + survivorship drift, so they "win" even on pure noise (v1 null test:
momentum C +0.44%/trade, CI > 0). v2 changes the scoring, not the simulator:

  1. xs = net - EW benchmark return over the same holding window. Benchmark = equal-weight daily
     close-to-close return of the LIQUID names in the same panel (ADV >= min_adv), so it removes
     both market drift and survivor-panel drift.
  2. Random-entry control: for every strategy, the same number of entries per calendar year, drawn
     uniformly from all eligible (ticker, day) pairs of that year (entry next open), through the same
     A/B/C exits. Shows what the exit rule does with no entry information.
  3. Data hygiene: a signal is skipped if a >35% daily move (beyond IDX auto-reject limits ->
     corporate action / bad print) lies in the 30 bars BEFORE it (ATR contamination). Backward-looking
     only. NaN ADV no longer passes the ADV filter.
  4. Bootstrap blocks = calendar month across all tickers (trades in a month share the market path).

Decision (per strategy x variant):
  EXIT_BETTER = beats A on xs in >= 70% of years AND block-bootstrap 95% CI of mean xs-diff > 0,
                under BOTH same-bar conventions.
  BEATS_MKT   = avg xs per trade > 0 at stress cost 0.8%, both conventions.

Usage:
  python atr_plan/exit_compare_v2.py --db data/history_long.db
  python atr_plan/exit_compare_v2.py --db data/null_test_mg.db --out reports/null_v2
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atr_exits import add_indicators, cost_filter_ok, simulate_trade, tick_size  # noqa: E402
from exit_compare import (NORMAL, SAME_BAR_MODES, STRATS, STRESS, load_csv_dir,  # noqa: E402
                          load_db, portfolio, variants_for)

BAD_MOVE = 0.35
PRE_WIN = 30


# ================================================================ benchmark
def ew_benchmark(data: dict[str, pd.DataFrame], min_adv: float) -> pd.Series:
    """Equal-weight index level of liquid names (ADV20 as of prior day >= min_adv)."""
    rets = {}
    for t, df in data.items():
        r = df["close"].pct_change()
        adv_prev = (df["close"] * df["volume"]).rolling(20, min_periods=20).mean().shift(1)
        r = r.where((adv_prev >= min_adv) & (r.abs() <= BAD_MOVE))
        rets[t] = r
    R = pd.DataFrame(rets).sort_index()
    ew = R.mean(axis=1, skipna=True).fillna(0.0)
    return (1 + ew).cumprod()


def _bad_mask(df: pd.DataFrame) -> np.ndarray:
    """True where a >35% daily move lies in the PRIOR 30 bars (would contaminate ATR14/22).
    Backward-looking only: moves after the signal are real risk and stay in the test."""
    bad = (df["close"].pct_change().abs() > BAD_MOVE).astype(float)
    return (bad.rolling(PRE_WIN + 1, min_periods=1).max() > 0).to_numpy()


# ================================================================ trade generation
def _prep(data, strat_names, min_adv, use_cost_filter):
    """Per-ticker arrays + eligibility + real signals."""
    P = {}
    for tkr, df in data.items():
        df = add_indicators(df)
        adv = (df["close"] * df["volume"]).rolling(20, min_periods=20).mean().to_numpy()
        a14 = df["atr14"].to_numpy()
        c = df["close"].to_numpy(float)
        n = len(c)
        elig = np.zeros(n, bool)
        elig[:-1] = np.isfinite(a14[:-1]) & (adv[:-1] >= min_adv) & ~_bad_mask(df)[:-1]
        if use_cost_filter:
            with np.errstate(invalid="ignore", divide="ignore"):
                ok = np.array([cost_filter_ok(x) for x in a14 / c])
            elig &= ok
        sigs = {s: np.flatnonzero(STRATS[s][0](df).fillna(False).to_numpy(bool) & elig) for s in strat_names}
        P[tkr] = dict(o=df["open"].to_numpy(float), h=df["high"].to_numpy(float),
                      l=df["low"].to_numpy(float), c=c, a14=a14, a22=df["atr22"].to_numpy(),
                      hh=df["hh22"].to_numpy(), dates=df.index, years=df.index.year.to_numpy(),
                      elig=elig, sigs=sigs)
    return P


def generate_trades(data, strat_names, min_adv, use_cost_filter, bench, seed=11) -> pd.DataFrame:
    """Real signals + a random-entry control per strategy.

    Random control: same number of entries per CALENDAR YEAR as the strategy, drawn uniformly from
    all eligible (ticker, day) pairs of that year across the whole panel. Matching per ticker-year
    would leak each name's within-year trend (trend-filtered strategies fire more in a name's up
    years), which biased the control toward long-hold exits on a martingale null."""
    rng = np.random.default_rng(seed)
    rows = []
    bidx, blev = bench.index, bench.to_numpy()

    def blevel(d):
        k = bidx.searchsorted(d, side="right") - 1
        return blev[k] if k >= 0 else np.nan

    P = _prep(data, strat_names, min_adv, use_cost_filter)

    def run(tkr, t_list, sname, label, stype, fixed, entry_mode):
        A = P[tkr]
        o, h, l, c, a14, a22, hh, dates = (A[k] for k in ("o", "h", "l", "c", "a14", "a22", "hh", "dates"))
        n = len(c)
        specs = variants_for(stype, fixed)
        entry_mid = entry_mode != "open"
        for t in t_list:
            i = t + 1
            if entry_mode == "open":
                entry = o[i]
            else:
                trig = h[t] + tick_size(h[t])
                if h[i] < trig or o[i] > trig + a14[t]:
                    continue
                entry = max(o[i], trig)
            b0 = blevel(dates[t])
            for vname, spec in specs.items():
                for sb in SAME_BAR_MODES:
                    r = simulate_trade(o, h, l, c, a14, a22, hh, i, entry, spec, NORMAL,
                                       same_bar=sb, entry_mid=entry_mid)
                    if r is None:
                        continue
                    xd = dates[min(r["exit_i"], n - 1)]
                    bret = blevel(xd) / b0 - 1
                    r["net_stress"] = (r["exit"] * (1 - STRESS.sell)) / (r["entry"] * (1 + STRESS.buy)) - 1
                    r["bench"] = bret
                    r["xs"] = r["net"] - bret
                    r["xs_stress"] = r["net_stress"] - bret
                    r.update(ticker=tkr, strategy=label, base=sname, stype=stype, variant=vname,
                             mode=sb, sig_date=dates[t], entry_date=dates[i], exit_date=xd)
                    rows.append(r)

    # eligible pool per year, pooled across tickers
    pool = {}
    for tkr, A in P.items():
        for t in np.flatnonzero(A["elig"]):
            pool.setdefault(int(A["years"][t]), []).append((tkr, int(t)))

    for sname in strat_names:
        _, stype, fixed, entry_mode = STRATS[sname]
        per_year = {}
        for tkr, A in P.items():
            real_t = A["sigs"][sname]
            run(tkr, real_t, sname, sname, stype, fixed, entry_mode)
            for y in A["years"][real_t]:
                per_year[int(y)] = per_year.get(int(y), 0) + 1
        picks = {}
        for y, k in per_year.items():
            pl = pool.get(y, [])
            if not pl:
                continue
            for j in rng.choice(len(pl), size=min(k, len(pl)), replace=False):
                tkr, t = pl[j]
                picks.setdefault(tkr, []).append(t)
        for tkr, ts in picks.items():
            run(tkr, sorted(ts), sname, f"rand:{sname}", stype, fixed, "open")

    tr = pd.DataFrame(rows)
    if not tr.empty:
        tr["year"] = pd.to_datetime(tr["entry_date"]).dt.year
        tr["early_stop"] = tr["reason"].isin(["stop", "gap_stop"]) & (tr["bars"] <= 2)
        key = ["ticker", "strategy", "sig_date", "mode"]
        tr = tr[tr.groupby(key)["variant"].transform("nunique") == 3].copy()
    return tr


# ================================================================ statistics
def window_table(tr, min_trades):
    g = tr.groupby(["mode", "strategy", "variant", "year"])
    w = g.agg(n=("net", "size"), avg_net=("net", "mean"), avg_xs=("xs", "mean"),
              avg_xs_stress=("xs_stress", "mean"), avg_bars=("bars", "mean")).reset_index()
    return w[w["n"] >= min_trades]


def block_bootstrap_diff(tr, strategy, mode, var, value="xs", base="A", n_boot=2000, seed=7):
    key = ["ticker", "strategy", "sig_date", "mode"]
    sub = tr[(tr.strategy == strategy) & (tr["mode"] == mode) & tr.variant.isin([var, base])]
    p = sub.pivot_table(index=key, columns="variant", values=value).dropna()
    if p.empty:
        return np.nan, np.nan, np.nan, 0
    d = (p[var] - p[base]).rename("d").reset_index()
    # calendar-month blocks (all tickers together): trades in the same month share the market path
    # and the benchmark path, so ticker-month blocks would understate the CI.
    d["blk"] = pd.to_datetime(d["sig_date"]).dt.strftime("%Y-%m")
    agg = d.groupby("blk")["d"].agg(["sum", "size"])
    s, cnt = agg["sum"].to_numpy(), agg["size"].to_numpy()
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(n_boot // 200):
        pick = rng.integers(0, len(s), (200, len(s)))
        means.append(s[pick].sum(1) / cnt[pick].sum(1))
    means = np.concatenate(means)
    return d["d"].mean(), np.percentile(means, 2.5), np.percentile(means, 97.5), len(d)


def verdict_table(tr, win) -> pd.DataFrame:
    out = []
    for mode in SAME_BAR_MODES:
        for s in sorted(tr.strategy.unique()):
            wa = win[(win["mode"] == mode) & (win.strategy == s)]
            base = wa[wa.variant == "A"].set_index("year")["avg_xs"]
            for v in ("B", "C"):
                wv = wa[wa.variant == v].set_index("year")["avg_xs"]
                yrs = base.index.intersection(wv.index)
                share = float((wv[yrs] > base[yrs]).mean()) if len(yrs) else np.nan
                m, lo, hi, n = block_bootstrap_diff(tr, s, mode, v)
                sub = tr[(tr.strategy == s) & (tr["mode"] == mode) & (tr.variant == v)]
                suba = tr[(tr.strategy == s) & (tr["mode"] == mode) & (tr.variant == "A")]
                out.append(dict(mode=mode, strategy=s, variant=v, years=len(yrs), win_share=share,
                                mean_diff=m, ci_lo=lo, ci_hi=hi, n_pairs=n,
                                net_A=suba["net"].mean(), net_v=sub["net"].mean(),
                                xs_A=suba["xs"].mean(), xs_v=sub["xs"].mean(),
                                xs_stress_v=sub["xs_stress"].mean(), net_stress_v=sub["net_stress"].mean(),
                                bars_A=suba["bars"].mean(), bars_v=sub["bars"].mean(),
                                ok=bool(len(yrs) and share >= 0.70 and np.isfinite(lo) and lo > 0)))
    vt = pd.DataFrame(out)
    agg = vt.groupby(["strategy", "variant"]).agg(
        EXIT_BETTER=("ok", "all"),
        BEATS_MKT=("xs_stress_v", lambda x: bool((x > 0).all())),
        ABS_PROFIT=("net_stress_v", lambda x: bool((x > 0).all()))).reset_index()
    return vt.merge(agg, on=["strategy", "variant"])


def bench_stats(bench: pd.Series, start, end):
    s = bench[(bench.index >= start) & (bench.index <= end)]
    yrs = max((s.index[-1] - s.index[0]).days / 365.25, 1e-9)
    m = s.resample("ME").last().pct_change().dropna()
    return dict(cagr=(s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1,
                sharpe_m=m.mean() / m.std() * np.sqrt(12), max_dd=(s / s.cummax() - 1).min())


def fp(x):
    return "—" if pd.isna(x) else f"{x*100:+.2f}%"


# ================================================================ main
def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--db")
    src.add_argument("--csv-dir")
    ap.add_argument("--strategies", default=",".join(STRATS))
    ap.add_argument("--min-bars", type=int, default=500)
    ap.add_argument("--min-adv", type=float, default=5e9)
    ap.add_argument("--min-trades", type=int, default=10)
    ap.add_argument("--cost-filter", action="store_true")
    ap.add_argument("--out", default="reports")
    ap.add_argument("--from-trades", help="re-score a saved trades.csv.gz (skip simulation)")
    a = ap.parse_args()

    data = load_db(a.db, a.min_bars) if a.db else load_csv_dir(a.csv_dir, a.min_bars)
    names = [s.strip() for s in a.strategies.split(",") if s.strip()]
    print(f"{len(data)} tickers, strategies: {names}", flush=True)
    bench = ew_benchmark(data, a.min_adv)
    if a.from_trades:
        tr = pd.read_csv(a.from_trades, parse_dates=["sig_date", "entry_date", "exit_date"])
    else:
        tr = generate_trades(data, names, a.min_adv, a.cost_filter, bench)
    if tr.empty:
        sys.exit("No trades generated.")
    win = window_table(tr, a.min_trades)
    vt = verdict_table(tr, win)

    out = Path(a.out) / f"exit_compare_v2_{datetime.now():%Y%m%d_%H%M}"
    out.mkdir(parents=True, exist_ok=True)
    if not a.from_trades:
        tr.to_csv(out / "trades.csv.gz", index=False)
    win.to_csv(out / "windows.csv", index=False)
    vt.to_csv(out / "verdict.csv", index=False)

    src_name = a.db or a.csv_dir
    L = [f"# Exit comparison v2 — {datetime.now():%Y-%m-%d %H:%M}", "",
         f"Data: `{src_name}` · {len(data)} tickers · trades {tr.entry_date.min():%Y-%m}..{tr.entry_date.max():%Y-%m} · "
         f"min ADV Rp{a.min_adv/1e9:.0f}bn · cost 0.6% (stress 0.8%) · cost filter {a.cost_filter}", "",
         "Score = **xs** = net − equal-weight liquid-panel return over the same holding window "
         "(removes market + survivorship drift). `rand:` rows = same exits on random entry days.", "",
         "## 1. Decision", "",
         "EXIT_BETTER = beats A on xs in ≥70% of years AND 95% block-bootstrap CI of Δxs > 0, both same-bar "
         "conventions. BEATS_MKT = avg xs > 0 at 0.8% cost. ABS_PROFIT = avg raw net > 0 at 0.8% cost.", "",
         "| Strategy | Var | EXIT_BETTER | BEATS_MKT (0.8%) | ABS_PROFIT (0.8%) |", "|---|---|---|---|---|"]
    yes = lambda b: "**YES**" if b else "no"
    for r in vt.drop_duplicates(["strategy", "variant"]).itertuples():
        L.append(f"| {r.strategy} | {r.variant} | {yes(r.EXIT_BETTER)} | {yes(r.BEATS_MKT)} | {yes(r.ABS_PROFIT)} |")
    L += ["", "## 2. Detail vs A (Δ on xs)", "",
          "| Strategy | Var | Same-bar | Years | Win share | Δxs/trade | 95% CI | Δ raw net | bars A→V | xs V @0.8% |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in vt.itertuples():
        L.append(f"| {r.strategy} | {r.variant} | {r.mode} | {r.years} | "
                 f"{'—' if pd.isna(r.win_share) else f'{r.win_share*100:.0f}%'} | {fp(r.mean_diff)} | "
                 f"[{fp(r.ci_lo)}, {fp(r.ci_hi)}] | {fp(r.net_v - r.net_A)} | "
                 f"{r.bars_A:.1f}→{r.bars_v:.1f} | {fp(r.xs_stress_v)} |")
    for mode in SAME_BAR_MODES:
        L += ["", f"## 3. Per-trade, same-bar = {mode} (0.6% cost)", "",
              "| Strategy | Var | Trades | Win% | Avg net | Avg bench | Avg xs | Avg bars | Stopped ≤2 bars |",
              "|---|---|---|---|---|---|---|---|---|"]
        ov = tr[tr["mode"] == mode].groupby(["strategy", "variant"]).agg(
            n=("net", "size"), win=("net", lambda x: (x > 0).mean()), avg=("net", "mean"),
            b=("bench", "mean"), xs=("xs", "mean"), bars=("bars", "mean"),
            es=("early_stop", "mean")).reset_index()
        for r in ov.itertuples():
            L.append(f"| {r.strategy} | {r.variant} | {r.n} | {r.win*100:.0f}% | {fp(r.avg)} | {fp(r.b)} | "
                     f"{fp(r.xs)} | {r.bars:.1f} | {r.es*100:.0f}% |")
    t0, t1 = pd.to_datetime(tr.entry_date.min()), pd.to_datetime(tr.exit_date.max())
    bs = bench_stats(bench, t0, t1)
    L += ["", "## 4. Portfolio (realized P&L, max 5 positions, same-bar = ohlc, 0.6% cost)", "",
          f"Benchmark EW liquid panel, same span: CAGR {fp(bs['cagr'])} · Sharpe {bs['sharpe_m']:.2f} · "
          f"Max DD {fp(bs['max_dd'])}", "",
          "| Strategy | Setup | Trades | CAGR | Sharpe (monthly) | Max DD |", "|---|---|---|---|---|---|"]
    for s in [n for n in names] + [f"rand:{n}" for n in names]:
        for lab, v, atr in (("A fixed, 20% notional", "A", False), ("B, 20% notional", "B", False),
                            ("C, 20% notional", "C", False), ("D = C + ATR sizing", "C", True)):
            p = portfolio(tr, s, v, atr_sizing=atr)
            if p.get("trades"):
                L.append(f"| {s} | {lab} | {p['trades']} | {fp(p['cagr'])} | "
                         f"{p['sharpe_m']:.2f} | {fp(p['max_dd'])} |")
    L += ["", "## 5. Exit reasons (% of trades, same-bar = ohlc)", ""]
    rs = (tr[tr["mode"] == "ohlc"].groupby(["strategy", "variant"])["reason"]
          .value_counts(normalize=True).unstack(fill_value=0) * 100).round(0)
    rs.index = [f"{x}/{y}" for x, y in rs.index]
    try:
        L += [rs.to_markdown()]
    except ImportError:
        L += ["```", rs.to_string(), "```"]
    L += ["", "Notes: entries identical across variants (strict pairing). Random control enters at next open "
          "(also for nr7, whose real entry is a buy-stop). Mean-reversion C = B. Portfolio uses raw net."]
    (out / "summary.md").write_text("\n".join(L))
    print("\n".join(L))
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
