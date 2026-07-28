"""Builds a ready-to-use ProviderRouter from AGENT_FIRM_* config (design doc
§5). The Router never constructs providers itself — this is the one place
that reads raw config, resolves provider names via the Registry, injects
every runtime dependency, and fails loud on invalid config."""

import importlib

from .. import config
from .circuit_breaker import CircuitBreaker
from .registry import build as _build_provider, registered_names
from .router import ProviderRouter


def _ensure_imported(name: str) -> None:
    """Provider classes self-register via the `@register` decorator as an
    import side effect (design doc §4a: "only the provider module(s)
    actually named in config get imported, via the Registry's lazy
    build()"). Nothing else in the import graph is guaranteed to have
    imported e.g. `providers/claude.py` yet, so import the same-named
    submodule here if it isn't registered already. A no-op if the name
    doesn't correspond to a module (caught in `_validate`'s unregistered
    check) or is already registered."""
    if name in registered_names():
        return
    try:
        importlib.import_module(f".{name}", package=__package__)
    except ImportError:
        pass


class TimeoutPolicy:
    def __init__(self, connection_timeout: float, read_timeout: float, overall_timeout: float):
        self.connection_timeout = connection_timeout
        self.read_timeout = read_timeout
        self.overall_timeout = overall_timeout


def _timeout_policy_for(name: str) -> TimeoutPolicy:
    if name == "claude":
        return TimeoutPolicy(
            connection_timeout=float(config.CLAUDE_CONNECTION_TIMEOUT_S or config.CONNECTION_TIMEOUT_S),
            read_timeout=float(config.CLAUDE_READ_TIMEOUT_S or config.READ_TIMEOUT_S),
            overall_timeout=float(config.CLAUDE_OVERALL_TIMEOUT_S or config.OVERALL_TIMEOUT_S),
        )
    return TimeoutPolicy(
        connection_timeout=config.CONNECTION_TIMEOUT_S,
        read_timeout=config.READ_TIMEOUT_S,
        overall_timeout=config.OVERALL_TIMEOUT_S,
    )


def _construct(name: str):
    _ensure_imported(name)
    if name == "claude":
        policy = _timeout_policy_for("claude")
        return _build_provider(
            "claude",
            model=config.CLAUDE_MODEL,
            max_concurrent=config.CLAUDE_MAX_CONCURRENT,
            overall_timeout=policy.overall_timeout,
        )
    return _build_provider(name)


def _validate() -> list[str]:
    mode = config.PROVIDER_MODE
    if mode not in ("claude", "zai", "auto"):
        raise ValueError(
            f"invalid AGENT_FIRM_PROVIDER={mode!r}; must be one of claude, zai, auto"
        )
    if mode != "auto":
        return [mode]

    order = config.PROVIDER_ORDER
    if not order:
        raise ValueError(
            "AGENT_FIRM_PROVIDER_ORDER must not be empty when AGENT_FIRM_PROVIDER=auto"
        )
    for n in order:
        _ensure_imported(n)
    unknown = [n for n in order if n not in registered_names()]
    if unknown:
        raise ValueError(
            f"AGENT_FIRM_PROVIDER_ORDER contains unregistered provider(s) {unknown}; "
            f"registered: {registered_names()}"
        )
    if len(set(order)) != len(order):
        raise ValueError(f"AGENT_FIRM_PROVIDER_ORDER contains duplicate provider names: {order}")
    return order


def build_router() -> ProviderRouter:
    order = _validate()
    routed = [
        (_construct(name), CircuitBreaker(
            failure_threshold=config.CIRCUIT_FAILURES, cooldown_s=config.CIRCUIT_COOLDOWN_S,
        ))
        for name in order
    ]
    import logging

    import data.db as _db
    logger = logging.getLogger("agent_firm.providers.factory")
    logger.info("provider router built: mode=%s order=%s", config.PROVIDER_MODE, order)
    if len(routed) < 2:
        # Audit 2026-07-10 P-1: a single-provider router means NO failover --
        # make that state loud so a config regression can't go unnoticed again.
        logger.warning(
            "provider router has a SINGLE provider (%s) -- failover DISABLED; "
            "set AGENT_FIRM_PROVIDER=auto to enable", order)
    return ProviderRouter(routed, db_path=str(_db.DB_PATH))
