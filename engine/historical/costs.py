"""engine/historical/costs.py — cost model for historical systems.

Phase 9 §12: costs must NEVER alter historical trigger geometry. Triggers,
Opening Range levels, Stretch values and stop levels are computed on raw
prices; this model is applied ONLY when accounting net P&L for a recorded
fill. The default is a ZERO cost model, so a historical run is free to state
"costs were not part of the measurement".

Semantics mirror engine/exits/costs.py (BUY acquires, SELL disposes) so the
two models stay comparable, but historical modules import THIS one — they must
never apply costs to a level.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class CostModel:
    commission_buy: float = 0.0
    commission_sell: float = 0.0
    slippage: float = 0.0

    @classmethod
    def zero(cls) -> "CostModel":
        return cls(0.0, 0.0, 0.0)

    def buy_fill(self, raw_price: float) -> float:
        """Accounting price for an acquiring fill (long open / short cover)."""
        return raw_price * (1.0 + self.commission_buy + self.slippage)

    def sell_fill(self, raw_price: float) -> float:
        """Accounting price for a disposing fill (long close / short open)."""
        return raw_price * (1.0 - self.commission_sell - self.slippage)
