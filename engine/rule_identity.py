"""engine/rule_identity.py — proof that the live rule is the researched rule.

WHY THIS EXISTS (audit 2026-09-02, finding L-1)
------------------------------------------------
`wf_edge` is computed by running `engine.strategies.STRATEGY_FUNCS[name]` over
rolling OOS windows. The live scanner does NOT run those functions: it calls
`check_current_entry_signal()`, which dispatches to `_CHECKER_DISPATCH[name]`
**and then applies a weekly multi-timeframe trend gate** that no backtest
function applies (`engine/strategies.py`, `_WEEKLY_GATE_BYPASS` exempts only
Crash Recovery / Panic Rebound / Liquidity Sweep).

The live signal set is therefore a proper subset of the backtested one, filtered
by a rule whose effect on expectancy has never been measured. `wf_edge` is
evidence about a rule that is not the deployed rule — which silently invalidates
the OOS claim for every strategy subject to the gate.

The fix is not to delete the gate (it may well help) and not to quietly re-run
research (that would change frozen evidence). It is to make the divergence
*visible and blocking*: every strategy carries a `rule_id` derived from the exact
gate set that will execute, research records the `rule_id` it measured, and
admission refuses a strategy whose live `rule_id` differs from the researched
one. A production-only filter can then never invalidate an OOS claim without
failing CI and failing admission.

To close a divergence you either
  (a) remove the production-only gate, or
  (b) re-run the walk-forward with the gate applied and record the new
      `rule_id` in the strategy's registry manifest as `rule_id:`.
Both are deliberate, reviewable acts. Neither can happen by accident.
"""
from __future__ import annotations

import hashlib
from typing import Iterable, Optional, Tuple

# Gates the LIVE path applies on top of the raw strategy function.
GATE_WEEKLY_MTF = "weekly_mtf_trend"

# Strategies the live path exempts from the weekly gate
# (mirrors engine.strategies._WEEKLY_GATE_BYPASS; asserted equal by tests).
_WEEKLY_GATE_BYPASS = frozenset({"Crash Recovery", "Panic Rebound", "Liquidity Sweep"})

# The research path (research/walkforward_multi.py -> STRATEGY_FUNCS) applies no
# extra gates at all. If that ever changes, add them here and the ids move
# together, which is the point.
_RESEARCH_GATES: Tuple[str, ...] = ()


def _canonical(strategy: str, gates: Iterable[str]) -> str:
    body = f"{strategy}|{','.join(sorted(gates))}"
    return hashlib.sha256(body.encode()).hexdigest()[:12]


def rule_id(strategy: str, gates: Iterable[str]) -> str:
    """Stable identifier for '<strategy> executed under <gate set>'."""
    gates = tuple(sorted(gates))
    suffix = "+".join(gates) if gates else "bare"
    return f"{strategy}@{suffix}#{_canonical(strategy, gates)}"


def live_gates(strategy: str) -> Tuple[str, ...]:
    """Gates the production scanner applies on top of the strategy function."""
    if strategy in _WEEKLY_GATE_BYPASS:
        return ()
    return (GATE_WEEKLY_MTF,)


def research_gates(strategy: str) -> Tuple[str, ...]:
    """Gates the walk-forward backtest applies. Currently none, for every
    strategy — `run_walk_forward` calls STRATEGY_FUNCS directly."""
    return _RESEARCH_GATES


def live_rule_id(strategy: str) -> str:
    return rule_id(strategy, live_gates(strategy))


def research_rule_id(strategy: str) -> str:
    return rule_id(strategy, research_gates(strategy))


def rule_parity(strategy: str, manifest_rule_id: Optional[str] = None
                ) -> Tuple[bool, str]:
    """Does the rule production will execute match the rule research measured?

    `manifest_rule_id` is the id recorded in the strategy's registry manifest
    (`rule_id:`), which is the authoritative statement of what was measured.
    When absent, the researched rule is assumed to be the bare strategy function
    — true today for every strategy, since `run_walk_forward` applies no gates.

    Returns (ok, reason). `reason` is empty when ok.
    """
    live = live_rule_id(strategy)
    researched = manifest_rule_id or research_rule_id(strategy)
    if live == researched:
        return True, ""
    extra = sorted(set(live_gates(strategy)) - set(research_gates(strategy)))
    detail = (f"production applies {extra} that research did not"
              if extra else "gate sets differ")
    return False, (f"rule mismatch for {strategy!r}: live={live} "
                   f"researched={researched} — {detail}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 9: HISTORICAL rule identity (v2)
#
# The legacy hash above covers (strategy name, gate set) only — Phase 9 §E
# demonstrated a concrete pair of materially different rules (backtest fill at
# trigger-day open vs staged fill at next open) receiving the SAME identity.
# Historical systems therefore hash EVERY material convention:
#
#   setup definition, lookback, entry mechanism, entry timing, Stretch
#   definition/lookback, data basis, tie policy, opening-range duration,
#   session definition, tick size, gap policy, ambiguity policy, exit
#   mechanism, break-even policy, kernel version.
#
# Changing ANY material convention produces a different id (pinned by
# tests/test_historical_identity.py). The legacy functions above are untouched.
# ─────────────────────────────────────────────────────────────────────────────

HISTORICAL_IDENTITY_VERSION = "hist-identity-v2"

# v2 (2026-09-03 provenance closure audit). Three changes, each forced by a
# rule the v1 field set could not distinguish:
#   nr7_tie_policy -> setup_tie_policy   ID/NR4 and NR7 are different setups;
#                                        a field named for one of them cannot
#                                        identify the other.
#   + protective_stop_mode               Crabel 1990 documents a with-stop
#                                        trading rule AND a no-stop test
#                                        protocol. Same levels, different rule.
#   + reversal_policy                    Street Smarts' stop-and-reverse is a
#                                        different rule from a protective stop
#                                        at the same level.
# The version bump is deliberate: every historical id changes, because the
# rules they identify are now stated more precisely than they were.
_HISTORICAL_REQUIRED_FIELDS = (
    "rule_id", "setup_definition", "setup_lookback", "setup_tie_policy",
    "entry_mechanism", "entry_timing", "data_basis", "gap_policy",
    "ambiguity_policy", "session_definition", "tick_size", "exit_mechanism",
    "protective_stop_mode", "reversal_policy", "kernel_version",
)


def historical_rule_id(material: dict) -> str:
    """Deterministic identity for a Phase 8 historical system configuration.

    `material` is the system config's identity_material() dict. Every field in
    _HISTORICAL_REQUIRED_FIELDS must be present — a config that cannot state
    its conventions cannot be identified, and therefore cannot run.
    """
    import json

    missing = [k for k in _HISTORICAL_REQUIRED_FIELDS if k not in material]
    if missing:
        raise ValueError(
            f"historical rule identity incomplete; missing {sorted(missing)}")
    canonical = json.dumps(
        {"identity_version": HISTORICAL_IDENTITY_VERSION, **material},
        sort_keys=True, separators=(",", ":"), default=str)
    return "hid:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
