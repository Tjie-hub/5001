"""engine/strategy_specs.py — single source of truth about each strategy.

Pure module (no DB, no pandas requirement beyond duck-typing df in
ensure_entry_price). Two responsibilities:

1. SPECS: one StrategySpec per walk-forward strategy. Consistency tests
   (tests/test_strategy_specs.py) pin STRATEGY_FUNCS, the scanner's
   _REGIME_STRATEGY_MAP / _COUNTER_TREND_BOOK, and the live checker dispatch
   to this table, so a strategy can no longer be live-selectable without a
   working checker (audit C-1).

2. ensure_entry_price: the checker output contract. Any has_signal=True
   result MUST carry details['price'] — scheduler/scanner.py's trade-open
   path reads exactly that key and silently skipped signals without it
   (audit C-1: TFB/momentum/Liquidity Sweep could never open a trade).

NOTE: 'Regime Adaptive' is intentionally absent — whole-window look-ahead
(audit C-7); it is removed from STRATEGY_FUNCS in this same plan.
NOTE: engine/strategy_registry/ is an unrelated dead-code package; do not
confuse the two.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class StrategySpec:
    name: str            # canonical key: STRATEGY_FUNCS / wf_scores / regime maps
    family: str          # 'momentum' | 'breakout' | 'reversion' | 'trend' | 'counter_trend'
    live_checker: bool   # has an entry in engine.strategies._CHECKER_DISPATCH
    counter_trend: bool = False


SPECS: dict = {s.name: s for s in [
    StrategySpec("vol_weighted",             "momentum",      True),
    StrategySpec("momentum",                 "momentum",      True),
    StrategySpec("vwap_reversion",           "reversion",     True),
    StrategySpec("conservative",             "momentum",      True),
    StrategySpec("Volume Profile POC",       "reversion",     False),
    StrategySpec("Inside Bar Breakout",      "breakout",      False),
    StrategySpec("NR7 Breakout",             "breakout",      False),
    StrategySpec("ORB",                      "breakout",      False),
    StrategySpec("VWMA Breakout Pullback",   "breakout",      False),
    StrategySpec("Swing Trend",              "trend",         False),
    StrategySpec("Trend Following Breakout", "trend",         True),
    StrategySpec("Crash Recovery",           "counter_trend", True,  counter_trend=True),
    StrategySpec("Panic Rebound",            "counter_trend", True,  counter_trend=True),
    StrategySpec("Liquidity Sweep",          "counter_trend", True,  counter_trend=True),
]}


def ensure_entry_price(result: dict, df=None) -> dict:
    """Guarantee details['price'] on any has_signal=True checker result.

    Fallback order: existing details['price'] → details['close'] →
    details['current_price'] → last close of df. Mutates and returns result.
    """
    if not result.get("has_signal"):
        return result
    details = result.setdefault("details", {})
    if details.get("price"):
        return result
    for key in ("close", "current_price"):
        val = details.get(key)
        if val:
            details["price"] = float(val)
            return result
    if df is not None and len(df) > 0:
        details["price"] = float(df["close"].iloc[-1])
    return result
