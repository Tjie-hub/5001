"""Live-corpus collector for Phase D (spec §7, Flow A).

Reuses the gatekeeper's proven no-look-ahead trade collector, then tags each trade
with its per-ticker entry regime + vol-tier + liq-tier so build_profile can group
into hierarchical cells. Read-only w.r.t. production.
"""
from __future__ import annotations

import hashlib
import json

from data.loaders import load_ohlcv_df
from engine.liquidity import get_adv_value_30d
from research.studies.regime_edge_scan import _regime_at
from research.studies.nr7_generalization_study import liquid_universe
from research.regime.conditioners import vol_tier, liq_tier


def tag_trade(conn, trade: dict, full_df, config) -> dict:
    """Attach regime + vol_tier + liq_tier to one trade dict (in place, returned)."""
    ticker, entry = trade["ticker"], trade["entry_date"]
    vcfg = config.conditioning["vol"]
    lcfg = config.conditioning["liq"]
    trade["regime"] = _regime_at(full_df, ticker, entry)
    trade["vol_tier"] = vol_tier(full_df, entry, window=vcfg["window"],
                                 median_lookback=vcfg["median_lookback"])
    adv = get_adv_value_30d(conn, ticker, entry)
    trade["liq_tier"] = liq_tier(adv, high_multiple=lcfg["high_multiple"])
    return trade


def collect_tagged_trades(conn, strategy_fn, config, *, universe=None) -> list:
    """Collect OOS trades for a strategy across the liquid universe and tag each.

    The default universe is the CANONICAL 187-ticker liquidity-filtered set
    (`liquid_universe`, ADV>=VALUE_LIQ_MIN_IDR as-of the latest bar) — the exact
    Phase B/C NR7 corpus. NOT the full ~958-ticker ohlcv universe: an unfiltered
    universe silently inflates the trade set and corrupts the regime cells.

    NR7 uses the gatekeeper's exact collector (preserving the validated trade set);
    other strategies are the documented extension point (Task 13 follow-up)."""
    from research.gatekeeper.candidate import _default_collect

    if universe is None:
        as_of = conn.execute("SELECT MAX(date) FROM ohlcv").fetchone()[0]
        universe = liquid_universe(conn, as_of)
    tagged = []
    for ticker in universe:
        df = load_ohlcv_df(conn, ticker)
        if len(df) < 300:
            continue
        df = df.sort_values("date").reset_index(drop=True)
        for tr in _default_collect(conn, ticker, config):
            tagged.append(tag_trade(conn, tr, df, config))
    return tagged


def corpus_fingerprint(trades) -> str:
    """Order-independent sha256 of the (ticker, entry_date) trade identities."""
    ids = sorted(f"{t['ticker']}@{t['entry_date']}" for t in trades)
    return hashlib.sha256(json.dumps(ids).encode()).hexdigest()
