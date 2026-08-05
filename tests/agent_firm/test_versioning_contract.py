"""AF-2 ADR-AF-004 (Versioning Contract) — automated enforcement of the decision's central
claim: `evaluate`/`evaluate_staged`/`reset_market_ctx`'s signatures are byte-for-byte unchanged
by the Tier 1 context migration (ADR-AF-002) and the sizing migration (ADR-AF-003), which is
exactly what classifies both as MINOR rather than MAJOR under `AGENT_FIRM_GOVERNANCE.md`'s
versioning rule.

Background (Blocker B4): the open question this ADR resolved was whether Tier 1 context should
reach `evaluate()` via a new parameter (which the unamended governance rule already classifies
as MAJOR, even if optional/defaulted) or via new optional fields on `SignalCandidate` (MINOR, by
the rule's own existing carve-out for additive data-class fields). The decision was the latter —
these tests are the permanent, automated guarantee that the migration actually took that path and
continues to, not just a one-time claim in a document.
"""
import inspect

import pytest
from unittest.mock import AsyncMock, patch

from engine.agent_firm import firm
from engine.agent_firm.schemas import AgentResult, SignalCandidate

# The frozen parameter contract, per ADR-AF-004. Any change here is a MAJOR version event and
# must be accompanied by an explicit, dated, superseding ADR — never a silent edit to this list.
_EVALUATE_PARAMS = ("candidates", "client")
_RESET_MARKET_CTX_PARAMS = ()


# ── Normal behavior: exact signature snapshot ────────────────────────────────────────

@pytest.mark.parametrize("fn_name", ["evaluate", "evaluate_async", "evaluate_staged", "evaluate_staged_async"])
def test_evaluate_family_signature_unchanged(fn_name):
    fn = getattr(firm, fn_name)
    params = list(inspect.signature(fn).parameters)
    assert params == list(_EVALUATE_PARAMS), (
        f"{fn_name}'s parameter list changed from {_EVALUATE_PARAMS} to {params} — "
        f"per ADR-AF-004, ANY signature change here (including an additive, optional, "
        f"defaulted parameter) is a MAJOR version event requiring explicit owner sign-off, "
        f"not a routine code change"
    )


def test_reset_market_ctx_signature_unchanged():
    params = list(inspect.signature(firm.reset_market_ctx).parameters)
    assert params == list(_RESET_MARKET_CTX_PARAMS), (
        "reset_market_ctx() must remain a zero-argument function — any parameter addition "
        "is a MAJOR version event per ADR-AF-004"
    )


def test_evaluate_client_parameter_remains_optional_and_defaulted():
    """The one parameter besides `candidates` must stay optional — this is not itself a MINOR
    vs MAJOR question (client already existed before ADR-AF-002/003), but a regression here
    would silently break every caller that doesn't pass client explicitly."""
    sig = inspect.signature(firm.evaluate)
    assert sig.parameters["client"].default is None


# ── Boundary condition: old-style SignalCandidate (zero Tier 1 fields) ──────────────

def _old_style_candidate() -> SignalCandidate:
    """Constructed with exactly the fields that existed before ADR-AF-002 — no technical/
    flow/regime_context/news/market/portfolio/risk_limits/execution, no size_tier-adjacent
    anything. This is the exact shape every pre-ADR-AF-002 call site still uses unmodified."""
    return SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-07-29T10:00:00+07:00",
        regime="BULL", flow_verdict="STRONG_BUY", foreign_score=3.42,
        indicators={"vwma_above": True},
    )


def _ok(role):
    return AgentResult(role=role, status="ok", output={"verdict": "ok"},
                       tokens_in=10, tokens_out=5, duration_s=0.1)


@pytest.mark.asyncio
async def test_old_style_candidate_evaluates_with_zero_call_site_changes(monkeypatch, tmp_path):
    """The direct end-to-end proof of ADR-AF-004's claim: a caller that never adopted Tier 1
    context (or ADR-AF-003's size_tier) can still call evaluate_async() exactly as it always
    has — same two positional/keyword arguments, no new required input — and get a normal
    decision back. Every Tier 1/size_tier field defaults to None/absent throughout."""
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "true")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    import importlib
    from data import db as data_db
    importlib.reload(data_db)
    from engine.agent_firm import config as _config
    importlib.reload(_config)
    importlib.reload(firm)

    import sqlite3
    from data.db import init_agent_firm_tables
    conn = sqlite3.connect(tmp_path / "t.db")
    conn.execute("""CREATE TABLE ohlcv (id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT,
        date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)""")
    conn.commit()
    conn.close()
    init_agent_firm_tables()

    candidate = _old_style_candidate()
    assert candidate.technical is None and candidate.portfolio is None  # boundary: unset

    with patch("engine.agent_firm.agents.technical.run", return_value=_ok("technical")), \
         patch("engine.agent_firm.agents.flow.run",      return_value=_ok("flow")), \
         patch("engine.agent_firm.agents.regime.run",    return_value=_ok("regime")), \
         patch("engine.agent_firm.agents.news.run",      return_value=_ok("news")), \
         patch("engine.agent_firm.agents.bull.run",      return_value=_ok("bull")), \
         patch("engine.agent_firm.agents.bear.run",      return_value=_ok("bear")), \
         patch("engine.agent_firm.agents.risk.run",
               return_value=AgentResult(
                   role="risk", status="ok",
                   output={"decision": "approve", "confidence": 0.7,
                           "size_tier": "normal", "rationale": "ok.\nok."},
                   tokens_in=100, tokens_out=50, duration_s=1.0)):
        decisions = await firm.evaluate_async([candidate])  # exact pre-ADR-AF-002 call shape

    assert len(decisions) == 1
    assert decisions[0].decision == "approve"


# ── Failure path: the signature must not silently swallow an unexpected parameter ───

def test_evaluate_rejects_unexpected_keyword_argument():
    """A closed, exact signature is what makes 'no signature change' a verifiable fact rather
    than an assumption — if evaluate() accepted **kwargs, a future caller could add a new
    Tier-1-carrying parameter without ever tripping the MAJOR-version rule, silently defeating
    the whole point of this ADR. This must raise, not silently accept."""
    with pytest.raises(TypeError):
        firm.evaluate([], not_a_real_parameter=True)  # type: ignore[call-arg]


def test_reset_market_ctx_rejects_any_argument():
    with pytest.raises(TypeError):
        firm.reset_market_ctx(candidates=[])  # type: ignore[call-arg]


# ── B4 regression: Tier 1 context lives on SignalCandidate, never on evaluate()'s call surface ──

def test_tier1_context_fields_live_on_signal_candidate_not_evaluate_params():
    """Direct regression test for Blocker B4 itself: the eight Tier 1 context fields must be
    reachable only through SignalCandidate's own field set, never through a parameter added to
    evaluate()/evaluate_staged(). This is what ADR-AF-004 calls 'the migration is designed not
    to need [the MAJOR rule]' — encoded here as an executable assertion, not just prose.

    Note: ADR-AF-004's own illustrative text names the regime field `.regime` — the actual
    implemented field is `regime_context` (SignalCandidate already had a pre-existing, unrelated
    `regime: Optional[str]` field, the legacy quant-pipeline regime tag, predating ADR-AF-002;
    reusing the name `regime` for the new RegimeContext object would collide with it on the same
    Pydantic model). This is a documented deviation from the ADR's prose, not from its decision —
    see Audit/ADR-AF-004_IMPLEMENTATION_REPORT.md for the full justification.
    """
    tier1_fields = {
        "technical", "flow", "regime_context", "news",
        "market", "portfolio", "risk_limits", "execution",
    }
    assert tier1_fields.issubset(SignalCandidate.model_fields.keys())

    evaluate_params = set(inspect.signature(firm.evaluate).parameters)
    evaluate_staged_params = set(inspect.signature(firm.evaluate_staged).parameters)
    assert tier1_fields.isdisjoint(evaluate_params)
    assert tier1_fields.isdisjoint(evaluate_staged_params)


def test_size_tier_lives_on_agent_decision_not_risk_run_params():
    """Same regression shape for ADR-AF-003's size_tier: it is a field on AgentDecision's
    output type, never a parameter risk.run()/evaluate() needed to grow to accommodate."""
    from engine.agent_firm.schemas import AgentDecision
    from engine.agent_firm.agents import risk as risk_agent

    assert "size_tier" in AgentDecision.model_fields
    risk_run_params = set(inspect.signature(risk_agent.run).parameters)
    assert "size_tier" not in risk_run_params
    evaluate_params = set(inspect.signature(firm.evaluate).parameters)
    assert "size_tier" not in evaluate_params
