"""Technical Analyst agent. Interprets precomputed TechnicalContext facts.

WP3 (Specialist Context Consumption Migration): this agent no longer queries OHLCV or
derives moving averages/support-resistance itself — engine.agent_firm_context.
build_technical_context() (Production Engine) already computed every mechanical fact via
engine.indicators/engine.chart_indicators/engine.technicals (ADR-AF-001). This agent's job
is interpretation of those facts, not re-derivation.
"""

import json
import time
from pathlib import Path

from ..providers.base import FirmLLMProvider
from ..schemas import AgentResult, SignalCandidate, TechnicalContext

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "technical_v1.md"
PROMPT_VERSION = "v1"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()


def _candidate_summary(candidate: SignalCandidate) -> dict:
    return {
        "ticker": candidate.ticker,
        "strategy": candidate.strategy,
        "score": candidate.score,
        "regime": candidate.regime,
        "flow_verdict": candidate.flow_verdict,
        "foreign_score": candidate.foreign_score,
    }


async def run(
    candidate: SignalCandidate,
    client: FirmLLMProvider,
) -> AgentResult:
    start = time.monotonic()
    resp = None
    try:
        technical_ctx = candidate.technical or TechnicalContext()
        user_msg = json.dumps({
            "candidate": _candidate_summary(candidate),
            "technical_context": technical_ctx.model_dump(),
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
            role="technical",
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
            role="technical",
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
