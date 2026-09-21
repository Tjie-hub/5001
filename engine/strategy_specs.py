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

Phase 8/9 quarantine: 'NR7 Breakout' and 'ORB' are the legacy modern-retail
adaptations (volume filter, ATR targets, daily-bar approximation). They carry
legacy=True so no one can mistake them for the Phase 8 historical systems
(crabel_orb.v1 / crabel_open_stretch.v1 / raschke_id_nr4.v1 /
raschke_nr7.v1), which live in
engine.historical.provenance.HISTORICAL_SPECS and REQUIRE full provenance
metadata at registration (register_historical_spec refuses anything less).
Legacy specs are frozen: do not delete, do not rewrite their DB results, do
not extend them.

NOTE: 'Regime Adaptive' is intentionally absent — whole-window look-ahead
(audit C-7); it is removed from STRATEGY_FUNCS in this same plan.
NOTE: the unrelated dead-code package engine/strategy_registry/ was deleted
2026-07-11 (audit R-11); STRATEGY_FUNCS in engine/strategies.py is the sole
authoritative strategy registry.
"""
from dataclasses import dataclass
from typing import Optional

# HistoricalProvenance is referenced only as a quoted annotation; provenance
# validation duck-types the required fields at runtime (no import cycle).


@dataclass(frozen=True)
class StrategySpec:
    name: str            # canonical key: STRATEGY_FUNCS / wf_scores / regime maps
    family: str          # 'momentum' | 'breakout' | 'reversion' | 'trend' | 'counter_trend' | 'historical'
    live_checker: bool   # has an entry in engine.strategies._CHECKER_DISPATCH
    counter_trend: bool = False
    # Phase 8/9 quarantine + provenance:
    legacy: bool = False
    """True ONLY for the pre-Phase-8 modern-retail adaptations ('NR7 Breakout',
    'ORB'). Frozen: their DB results are historical fact about THOSE rules."""
    provenance: Optional["HistoricalProvenance"] = None
    """Required (non-None) for every historical system; rejected at registration
    otherwise. Carries tier, citations, recovered rules, engine conventions,
    data basis, and the PRIMARY SOURCE NOT RECOVERED. items."""


def register_historical_spec(spec: "StrategySpec") -> "StrategySpec":
    """Registration gate for Phase 8 historical systems: provenance is
    mandatory (Phase 9 §3). Legacy specs are refused."""
    from engine.historical.provenance import (HISTORICAL_SPECS,
                                              validate_provenance)
    if spec.legacy:
        raise ValueError(f"{spec.name}: legacy specs cannot register as historical")
    validate_provenance(spec.provenance, spec.name)
    HISTORICAL_SPECS[spec.name] = spec
    return spec


SPECS: dict = {s.name: s for s in [
    StrategySpec("vol_weighted",             "momentum",      True),
    StrategySpec("momentum",                 "momentum",      True),
    StrategySpec("vwap_reversion",           "reversion",     True),
    StrategySpec("conservative",             "momentum",      True),
    StrategySpec("Volume Profile POC",       "reversion",     False),
    StrategySpec("Inside Bar Breakout",      "breakout",      False),
    # QUARANTINED (Phase 8/9): modern-retail NR7 adaptation — open-gap trigger,
    # 0.8x volume filter, 2xATR14 target, 1.5%/0.2% gates. NOT Crabel, NOT
    # Raschke. Frozen; DB results untouched.
    StrategySpec("NR7 Breakout",             "breakout",      True,
                 legacy=True),
    # QUARANTINED (Phase 8/9): daily-bar ATR-around-open approximation,
    # explicitly NOT genuine intraday ORB (see engine/strategies.py note).
    # Frozen; DB results untouched.
    StrategySpec("ORB",                      "breakout",      False,
                 legacy=True),
    StrategySpec("VWMA Breakout Pullback",   "breakout",      False),
    StrategySpec("Swing Trend",              "trend",         False),
    StrategySpec("Trend Following Breakout", "trend",         True),
    StrategySpec("Crash Recovery",           "counter_trend", True,  counter_trend=True),
    StrategySpec("Panic Rebound",            "counter_trend", True,  counter_trend=True),
    StrategySpec("Liquidity Sweep",          "counter_trend", True,  counter_trend=True),
]}


def ensure_entry_price(result: dict, df=None) -> dict:
    """Guarantee details['price'] and details['price_basis'] on any
    has_signal=True checker result.

    Fallback order: existing details['price'] → details['close'] →
    details['current_price'] → last close of df. Mutates and returns result.

    AUDIT L-2 (2026-09-02): every signal must also declare WHAT its price is, so
    engine.entry_convention can refuse to fill a price that had already printed
    before the signal timestamp. Checkers that name their own `price_basis`
    (NR7 declares `session_open`) keep it; everything else derives from a
    completed/last close and is stamped `last_completed_close`. The entry RULE
    is always the validated next-session-open convention.
    """
    if not result.get("has_signal"):
        return result
    details = result.setdefault("details", {})
    from engine import entry_convention as _ec
    details.setdefault("entry_rule", _ec.ENTRY_RULE_NEXT_OPEN)
    if details.get("price"):
        details.setdefault("price_basis", _ec.BASIS_LAST_CLOSE)
        return result
    for key in ("close", "current_price"):
        val = details.get(key)
        if val:
            details["price"] = float(val)
            details.setdefault("price_basis", _ec.BASIS_LAST_CLOSE)
            return result
    if df is not None and len(df) > 0:
        details["price"] = float(df["close"].iloc[-1])
        details.setdefault("price_basis", _ec.BASIS_LAST_CLOSE)
    return result


# Display-name aliases: several strategy functions report display names that
# differ from their canonical registry keys, and paper_trades.strategy rows
# store those display names (open_trade defaults / backtest_cache).
DISPLAY_ALIASES = {
    "Momentum Following":   "momentum",
    "Vol-Weighted Entry":   "vol_weighted",
    "VWAP Reversion":       "vwap_reversion",
    "Conservative Confirm": "conservative",
}


def resolve_strategy_name(name: str) -> str:
    """Canonical registry key for a strategy/display name."""
    return DISPLAY_ALIASES.get(name, name)
