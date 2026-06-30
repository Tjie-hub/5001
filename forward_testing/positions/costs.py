"""Fill-cost economics. Defaults mirror engine.strategies (COMMISSION_BUY/SELL, SLIPPAGE).

side semantics: 'BUY' acquires (long open / short cover), 'SELL' disposes
(long close / short open). Injectable so tests can pass Costs.zero() for exact math.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Costs:
    commission_buy: float = 0.0015
    commission_sell: float = 0.0025
    slippage: float = 0.001

    @classmethod
    def zero(cls):
        return cls(0.0, 0.0, 0.0)


def apply_costs(price, side, costs):
    if side == "BUY":
        return price * (1 + costs.commission_buy + costs.slippage)
    return price * (1 - costs.commission_sell - costs.slippage)
