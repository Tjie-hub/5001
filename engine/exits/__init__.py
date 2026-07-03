"""engine/exits — the single exit kernel (plan 1B, audit C-3/C-8).

Pure, stdlib-only (no pandas): forward_testing depends on this package and
must stay pandas-free. Backtests (engine/strategies.py), the live monitor
(monitor.py), and the SHADOW engine (forward_testing) all consume the same
ExitPolicyRegistry + evaluate_exit so live exits are the validated exits.
"""
from engine.exits.policy import ExitPolicy, InitialLevels, ExitPolicyRegistry
from engine.exits.evaluator import Bar, PositionView, ExitDecision, evaluate_exit
from engine.exits.costs import Costs, DEFAULT_COSTS, apply_costs

_REGISTRY = ExitPolicyRegistry()


def get_policy(strategy_name: str) -> ExitPolicy:
    """Registry lookup with display-name alias resolution (paper_trades rows
    store display names like 'Momentum Following' for legacy trades)."""
    from engine.strategy_specs import resolve_strategy_name
    return _REGISTRY.get(resolve_strategy_name(strategy_name or ""))
