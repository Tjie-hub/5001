"""IDX ARA/ARB price-limit fillability — the single authority for backtest,
walk-forward and live (audit P4-2).

Live paper trades have always capped TP/SL to the exchange's auto-rejection
bands (paper_trade.open_trade); backtests and walk-forward never did, so every
historical expectancy assumed each computed SL/TP was fillable at any distance
— structurally inflating the breakout/momentum family (NR7, ORB, Inside Bar,
VWMA BP, Volume Profile POC), which trades exactly the volatility most likely
to press a level against the band. This module is the shared model: the same
tier table, the same safety margin, one definition of "this level cannot fill".

Tier table per BEI Peng-00009/BEI.POP/03-2023 (symmetric), referenced to the
entry fill — the same reference live open_trade uses, so backtest and live
produce identical capped levels for identical entries.

What this model deliberately does NOT capture (documented, not silent):

- The bands are re-referenced daily (vs each session's previous close) while a
  trade is held; a fixed level far from entry can sit beyond a later session's
  band. Level-triggered fills remain bounded by that session's printed
  high/low — the price the backtest fills at is one the market actually
  reached — so entry-day capping is what removes the structurally unfillable
  level, and per-hold-day re-referencing would add precision, not correctness.
- Locked-limit non-fills (an ARB-locked session where no bid exists to sell
  into) are not modeled. That is an exit-timing/risk question the repo has
  already deferred for the live monitor (P3 implementation note) and it
  deserves the same explicit Owner decision before backtests get it.
"""
from __future__ import annotations

# Stay 0.5% inside the band — the same safety margin paper_trade.open_trade
# has always applied, so the live path's behavior is the definition here.
ARA_ARB_SAFETY = 0.005


def ara_arb_levels(price: float) -> dict:
    """Auto-rejection bands around `price`.

    Tier: <=200 -> +-35%; 200-5000 -> +-25%; >5000 -> +-20% (symmetric).
    Sub-Rp50 treated as tier 1 (IDX board convention). Returns
    {ara_pct, arb_pct, ara_price, arb_price}.
    """
    if price <= 200:
        pct = 0.35
    elif price <= 5000:
        pct = 0.25
    else:
        pct = 0.20
    return {
        "ara_pct":   pct,
        "arb_pct":   pct,
        "ara_price": price * (1 + pct),
        "arb_price": price * (1 - pct),
    }


def cap_levels(entry_price: float, tp_price: float | None = None,
               sl_price: float | None = None) -> dict:
    """Cap LONG TP/SL to what the price-limit band lets fill.

    TP above ARA cannot fill (the market halts at the ceiling); SL below ARB
    cannot fill (the market halts at the floor). Both are pulled just inside
    the band with the shared safety margin. Returns
    {tp_price, sl_price, tp_capped, sl_capped, ara_price, arb_price}; the
    *_capped flags say whether each level actually moved.
    """
    ar = ara_arb_levels(entry_price)
    tp_capped = sl_capped = False
    if tp_price is not None and tp_price >= ar["ara_price"]:
        tp_price = ar["ara_price"] * (1 - ARA_ARB_SAFETY)
        tp_capped = True
    if sl_price is not None and sl_price <= ar["arb_price"]:
        sl_price = ar["arb_price"] * (1 + ARA_ARB_SAFETY)
        sl_capped = True
    return {
        "tp_price": tp_price, "sl_price": sl_price,
        "tp_capped": tp_capped, "sl_capped": sl_capped,
        "ara_price": ar["ara_price"], "arb_price": ar["arb_price"],
    }


def capped_rr_ok(entry_price: float, tp_price: float | None,
                 sl_price: float | None, min_rr: float) -> bool:
    """Live open_trade's capped-level R/R gate: after capping, the trade must
    still deliver min_rr reward per unit of risk. True when the question does
    not apply (no TP or no SL) — mirrors live, which gates only when both a
    target and a stop exist and skips swing/pure-trail policies.
    """
    if tp_price is None or sl_price is None:
        return True
    reward = tp_price - entry_price
    risk = entry_price - sl_price
    if risk <= 0:
        return False
    return reward / risk >= min_rr
