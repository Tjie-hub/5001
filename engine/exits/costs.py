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
