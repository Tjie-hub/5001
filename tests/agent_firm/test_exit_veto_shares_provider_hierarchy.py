"""Rule (2026-09-15): the intraday exit-veto call (monitor._agent_confirms_exit
-> engine.agent_firm.firm.evaluate()) is a separate, event-driven Agent Firm
invocation from the two scheduled daily-planning runs, but MUST use the same
Claude-primary/GLM-5.3-Flash-fallback hierarchy — not a parallel provider
configuration of its own.

engine.agent_firm.firm.py is not modified by this change. This is a structural
regression guard: both evaluate() (used by the exit veto) and
evaluate_staged_async() (used by the two scheduled planning runs) must
construct their router via the SAME zero-argument
providers.factory.build_router() call — the one function that reads
config.PROVIDER_MODE/PROVIDER_ORDER — so neither path can silently drift into
its own provider list.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIRM_SRC = (ROOT / "engine" / "agent_firm" / "firm.py").read_text(encoding="utf-8")

# Matches `client = build_router()` (optionally with kwargs, but never a
# hardcoded provider-order argument — build_router() takes none) wherever it
# appears, so this survives incidental reformatting.
_BUILD_ROUTER_CALL = re.compile(r"\bclient\s*=\s*build_router\(\s*\)")


def test_evaluate_and_evaluate_staged_both_call_build_router_with_no_args():
    calls = _BUILD_ROUTER_CALL.findall(FIRM_SRC)
    assert len(calls) >= 2, (
        "expected evaluate() (exit veto) and evaluate_staged_async() (scheduled "
        "planning) to each construct their router via an identical, argument-"
        "less build_router() call -- found only: " + repr(calls)
    )


def test_no_second_router_factory_or_hardcoded_provider_order_in_firm_module():
    """Guard against a future change accidentally giving the exit-veto path
    (or any evaluate*() function) its own provider list, bypassing
    config.PROVIDER_ORDER."""
    assert "PROVIDER_ORDER" not in FIRM_SRC, (
        "firm.py must not read/override PROVIDER_ORDER directly -- provider "
        "hierarchy is owned entirely by providers/factory.py + config.py"
    )
    assert re.search(r"ProviderRouter\(\[", FIRM_SRC) is None, (
        "firm.py must not construct a ProviderRouter directly with its own "
        "provider list -- always go through providers.factory.build_router()"
    )
