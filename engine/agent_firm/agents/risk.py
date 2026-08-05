"""Risk Manager agent. Final approve/veto decision.

WP3 (Specialist Context Consumption Migration): consumes candidate.risk_limits (RiskContext)
and candidate.portfolio (PortfolioContext) in addition to the analyst/bull/bear reports it
already read. Both are Production-Engine-computed facts (paper_trade.py's existing
is_entries_blocked()/compute_drawdown(), and the open paper_trades snapshot, per ADR-AF-001) —
this agent never computes drawdown, exposure, or position sizing itself; it only weighs
already-computed facts qualitatively, per its own decision framework. `has_open_position()` is
a membership lookup on already-fetched data, not a calculation.

This closes a pre-existing gap: risk_v2.md has always instructed "no doubling up" on an open
position, but until this change the Risk agent was never actually given the open-trades data
to check that against (see Audit/AF2_WP3_REGRESSION_REPORT.md).
"""

import json
import time
from pathlib import Path

from ..guardrails import normalize_quant
from ..providers.base import FirmLLMProvider
from ..schemas import AgentResult, PortfolioContext, RiskContext, SignalCandidate

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "risk_v2.md"
PROMPT_VERSION = "v2"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()


def _candidate_summary(candidate: SignalCandidate) -> dict:
    cand = {
        "ticker": candidate.ticker,
        "strategy": candidate.strategy,
        "regime": candidate.regime,
        "flow_verdict": candidate.flow_verdict,
        "foreign_score": candidate.foreign_score,
    }
    # quant_score normalized to 0-1 so the prompt's gate is scale-consistent
    # across callers (flow -5..+5, premarket/eod 0-100). Raw stays as `score`.
    cand["quant_score"] = round(normalize_quant(candidate.score, candidate.strategy), 3)
    return cand


async def run(
    candidate: SignalCandidate,
    analyst_results: list[AgentResult],
    client: FirmLLMProvider,
) -> AgentResult:
    start = time.monotonic()
    resp = None
    try:
        portfolio_ctx = candidate.portfolio or PortfolioContext()
        risk_ctx = candidate.risk_limits or RiskContext()
        user_msg = json.dumps({
            "candidate": _candidate_summary(candidate),
            "analyst_reports": [
                {"role": r.role, "status": r.status, "output": r.output, "error": r.error}
                for r in analyst_results
            ],
            "portfolio_context": {
                "already_open_position": portfolio_ctx.has_open_position(candidate.ticker),
                "open_position_count": portfolio_ctx.open_position_count,
            },
            "risk_context": {
                "entries_blocked": risk_ctx.entries_blocked,
                "drawdown_pct": risk_ctx.drawdown_pct,
            },
        })
        resp = await client.generate([
            {"role": "system", "content": _load_prompt()},
            {"role": "user", "content": user_msg},
        ])
        try:
            output = json.loads(resp.content)
        except json.JSONDecodeError as json_err:
            raise ValueError(f"json decode error: {json_err}") from json_err
        return AgentResult(
            role="risk",
            status="ok",
            output=output,
            prompt_version=PROMPT_VERSION,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            cost_usd=resp.cost_usd, duration_s=resp.duration_s,
            provider=resp.provider, model=resp.model,
            runtime_version=resp.runtime_version, failover=resp.failover,
        )
    except Exception as err:
        return AgentResult(
            role="risk",
            status="failed",
            prompt_version=PROMPT_VERSION,
            error=str(err),
            duration_s=time.monotonic() - start,
            tokens_in=resp.tokens_in if resp is not None else 0,
            tokens_out=resp.tokens_out if resp is not None else 0,
            cost_usd=resp.cost_usd if resp is not None else 0.0,
            provider=resp.provider if resp is not None else getattr(err, "provider", ""),
            model=resp.model if resp is not None else "",
            runtime_version=resp.runtime_version if resp is not None else "",
            failover=resp.failover if resp is not None else False,
        )
