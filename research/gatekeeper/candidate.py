"""Candidate assembly + the ctx bridge the stages consume (spec §3/§6).

`assemble_candidate` / `candidate_hash` / `build_ctx` are PURE (no DB, no backtest)
so they unit-test without a corpus. `build_candidate` is the live-corpus integration
builder (dependency-injected for testability) that collects trades with the proven
no-look-ahead pattern and computes the WF/OOS summaries, then delegates to the pure
assembler.

Net expectancy uses the single cost authority via research.nr7_study.round_trip_net_pct.
"""
from __future__ import annotations

import hashlib
import inspect
import json

from research import nr7_study as ns
from research import statistics as st
from research.gatekeeper.models import Candidate, ScanCell


def _nets(trades):
    return [ns.round_trip_net_pct(t["raw_entry"], t["raw_exit"]) for t in trades]


def assemble_candidate(strategy_fn, trades, scan_family, wf, oos,
                       target_regime=None, strategy_config_hash="") -> Candidate:
    """Group collected trades into regime cells and pack the analysis summaries.
    Pure: all heavy collection happens upstream."""
    regime_cells = {}
    for t in trades:
        regime_cells.setdefault(t["regime"], []).append(t)
    meta = {"target_regime": target_regime,
            "strategy_config_hash": strategy_config_hash,
            "wf": wf, "oos": oos}
    return Candidate(strategy_fn=strategy_fn, trades=list(trades),
                     regime_cells=regime_cells, scan_family=list(scan_family), meta=meta)


def candidate_hash(candidate: Candidate) -> str:
    """sha256 of the trade set + the strategy source config hash — the candidate's
    identity for reproducibility."""
    payload = {"strategy_fn": candidate.strategy_fn,
               "strategy_config_hash": candidate.meta.get("strategy_config_hash", ""),
               "trades": candidate.trades}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def build_ctx(candidate: Candidate, config) -> dict:
    """Derive the stage context from a candidate. Pure. The governing cell is the
    target regime (or OVERALL); multiplicity spans the pre-registered family."""
    target = candidate.meta.get("target_regime")
    governing = target or "OVERALL"
    claim_trades = (candidate.regime_cells.get(target, [])
                    if target else candidate.trades)

    labels = list(config.multiplicity["family"]["regimes"])
    if governing not in labels:
        labels.append(governing)
    pvalues = []
    for r in labels:
        cell = candidate.trades if r == "OVERALL" else candidate.regime_cells.get(r, [])
        nets = _nets(cell)
        pvalues.append(st.t_test_greater(nets, mu0=0.0)["p"] if len(nets) >= 2 else 1.0)

    return {
        "claim_net": _nets(claim_trades),
        "n_overall": len(candidate.trades),
        "cell_n": {r: len(ts) for r, ts in candidate.regime_cells.items()},
        "governing_cell": governing,
        "family_labels": labels,
        "family_pvalues": pvalues,
        "governing_index": labels.index(governing),
        "scan_sharpes": [c.sharpe for c in candidate.scan_family],
        "wf": candidate.meta.get("wf", {}),
        "oos": candidate.meta.get("oos", {}),
    }


# ─── live-corpus builder ──────────────────────────────────────────────────────

def _wf_summary(trades) -> dict:
    """Walk-forward summary using the engine's exact consistency definition
    (research.walkforward_multi._summarize_strategy): a window is profitable if its
    pooled return > 0, and consistency = profitable windows / windows tested.

    The window unit is the real quarterly OOS window each trade was tagged with at
    collection (`<ticker>@<test_start>`); if a trade lacks a tag (synthetic inputs)
    it falls back to (ticker, entry-month) so the summary is always defined."""
    pooled = ns.pool(trades)["exp_pct"]
    units = {}
    for t in trades:
        key = t.get("window") or (t.get("ticker"), t["entry_date"][:7])
        units.setdefault(key, []).append(t)
    profitable = sum(1 for ts in units.values() if ns.pool(ts)["exp_pct"] > 0)
    n = len(units)
    return {"consistency_pct": 100.0 * profitable / n if n else 0.0,
            "pooled_oos_exp": pooled, "windows_tested": n,
            "windows_profitable": profitable, "n_windows": n}


def _window_tag(entry: str, schedule, ticker: str) -> str:
    """The quarterly OOS window (by test_start) that contains an entry date."""
    for w in schedule:
        if w["test_start"] <= entry < w["test_end"]:
            return f"{ticker}@{w['test_start']}"
    return f"{ticker}@unassigned"


def _oos_summary(trades) -> dict:
    """Chronological CV: split at the median entry date, measure late/early retention
    (reuses research.nr7_study.cv_split — the same held-out logic as the NR7 study)."""
    dates = sorted(t["entry_date"] for t in trades)
    boundary = dates[len(dates) // 2] if dates else "2099-01-01"
    early, late = ns.cv_split(trades, boundary)
    ep, lp = ns.pool(early), ns.pool(late)
    retention = lp["exp_pct"] / ep["exp_pct"] if ep["exp_pct"] > 0 else 0.0
    return {"retention": retention, "late_exp": lp["exp_pct"], "late_n": lp["n"],
            "early_exp": ep["exp_pct"], "boundary": boundary}


def _strategy_config_hash(strategy_fn: str) -> str:
    """sha256 of the strategy's source (mirrors the registry manifest's config_hash).
    Fail-soft to '' so a missing dispatch never kills a build."""
    try:
        from engine.strategies import STRATEGY_FUNCS
        src = inspect.getsource(STRATEGY_FUNCS[strategy_fn])
        return hashlib.sha256(src.encode()).hexdigest()
    except Exception:
        return ""


def _default_collect(conn, ticker, config):
    """Live-corpus trade collector. Delegates to the proven, no-look-ahead NR7
    collector for NR7 (preserving the exact trade set), then tags each trade with
    its real quarterly OOS window so WF consistency uses the engine's windows —
    other strategies are a documented extension point."""
    from data.loaders import load_ohlcv_df
    from research.studies import nr7_generalization_study as gen
    from research.walkforward_multi import walk_forward_split
    df = load_ohlcv_df(conn, ticker)
    if len(df) < 300:
        return []
    trades = gen.collect_trades_for_ticker(ticker, df)
    schedule = walk_forward_split(df, train_months=12, test_months=3)
    for t in trades:
        t["window"] = _window_tag(t["entry_date"], schedule, ticker)
    return trades


def build_candidate(conn, strategy_fn, universe, config, *, collect_fn=None) -> Candidate:
    """Assemble a Candidate from the live corpus (spec §3). `collect_fn` is injected
    for testing; the default collects real OOS trades per ticker.

    The scan family is the per-regime-cell Sharpe set — the REAL trial distribution
    for the Deflated Sharpe (no proxy). With multiplicity.family.parameter_axes empty
    the family is regimes only; declaring axes widens it."""
    collect_fn = collect_fn or _default_collect
    all_trades = []
    for t in universe:
        all_trades.extend(collect_fn(conn, t, config))

    cells = {}
    for tr in all_trades:
        cells.setdefault(tr["regime"], []).append(tr)

    scan_family, target, best_exp = [], None, None
    for regime, ts in cells.items():
        nets = _nets(ts)
        sr = st.sharpe(nets) if len(nets) >= 2 else 0.0
        scan_family.append(ScanCell(regime, sr, len(ts)))
        exp = ns.pool(ts)["exp_pct"]
        if best_exp is None or exp > best_exp:
            best_exp, target = exp, regime

    # WF/OOS judge the SAME governing claim as CI/PSR/DSR — the target regime cell,
    # not the unscoped pool. A regime-scoped edge (e.g. NR7_BULL) is only ever
    # deployed inside its regime, so validating it across regimes it never trades
    # would reject it for the wrong reason.
    governing_trades = cells.get(target, all_trades) if target else all_trades

    return assemble_candidate(
        strategy_fn=strategy_fn, trades=all_trades, scan_family=scan_family,
        wf=_wf_summary(governing_trades), oos=_oos_summary(governing_trades),
        target_regime=target, strategy_config_hash=_strategy_config_hash(strategy_fn))
