"""Fill-cost economics — the single authority (plan 1C item 1.7).

Consumed by engine/strategies.py (backtests), forward_testing (SHADOW fills,
via shim), and paper_trade.close_trade (net P&L). side semantics: 'BUY'
acquires (long open / short cover), 'SELL' disposes (long close / short open).
"""
from dataclasses import dataclass

COMMISSION_BUY = 0.0015   # 0.15%
COMMISSION_SELL = 0.0025  # 0.25%
SLIPPAGE = 0.001          # 0.10%


@dataclass(frozen=True)
class Costs:
    commission_buy: float = COMMISSION_BUY
    commission_sell: float = COMMISSION_SELL
    slippage: float = SLIPPAGE

    @classmethod
    def zero(cls):
        return cls(0.0, 0.0, 0.0)


DEFAULT_COSTS = Costs()


def apply_costs(price, side, costs=DEFAULT_COSTS):
    if side == "BUY":
        return price * (1 + costs.commission_buy + costs.slippage)
    return price * (1 - costs.commission_sell - costs.slippage)


# ── Liquidity-scaled slippage (audit P4-6) ──────────────────────────────────
# The flat SLIPPAGE above (0.10%/leg, -> 0.60% RT with the two commission
# legs) is what the 0.60% RT / D-059 floor documented across
# docs/research_programs/P-M/** assumes and is left untouched here so nothing
# that already relies on that fixed number changes behaviour. It is only
# realistic for the liquid end of the roster, though: on a mostly-illiquid
# universe (research/studies/nr7_generalization_study.py's liquid_universe()
# admits anything down to VALUE_LIQ_MIN_IDR = Rp 5bn/day ADV) a name near that
# floor eats far more real-world slippage than one trading Rp 50bn/day, and
# the flat rate has no way to reflect that. These buckets are this module's
# opt-in, ADV-aware alternative -- used explicitly where a caller has ADV in
# hand (research/nr7_study.py), never substituted for DEFAULT_COSTS.
# Thresholds/values are a reasoned first cut (anchored so the top bucket
# reproduces the existing flat 0.10%), not independently calibrated against
# realized fill data -- recalibrate here if better evidence shows up.
_LIQUIDITY_SLIPPAGE_BUCKETS = (
    # (adv_floor_idr, slippage) — first matching floor (highest first) wins.
    (20_000_000_000, 0.0010),  # >= Rp 20bn/day: liquid, matches the flat rate
    (10_000_000_000, 0.0020),  # Rp 10-20bn/day
    (0,              0.0035),  # < Rp 10bn/day, incl. the 5bn admission floor
)


def liquidity_scaled_slippage(adv_value_idr: float) -> float:
    """Per-leg slippage bucketed by 30d ADV traded value (Rupiah).

    None/negative input is treated as the worst (lowest-ADV) bucket — fail
    conservative, never silently assume liquid."""
    if adv_value_idr is None or adv_value_idr < 0:
        adv_value_idr = 0
    for floor, slippage in _LIQUIDITY_SLIPPAGE_BUCKETS:
        if adv_value_idr >= floor:
            return slippage
    return _LIQUIDITY_SLIPPAGE_BUCKETS[-1][1]


def liquidity_scaled_costs(adv_value_idr: float, commission_buy: float = COMMISSION_BUY,
                            commission_sell: float = COMMISSION_SELL) -> Costs:
    """Costs with slippage bucketed by ADV instead of the flat default."""
    return Costs(commission_buy=commission_buy, commission_sell=commission_sell,
                 slippage=liquidity_scaled_slippage(adv_value_idr))
