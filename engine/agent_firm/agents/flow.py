"""Flow Specialist agent. Interprets precomputed FlowContext facts.

WP3 (Specialist Context Consumption Migration): this agent no longer receives raw
stockbit_flow/broker_flow/stockbit_flow_bars rows or sums lots itself —
engine.agent_firm_context.build_flow_context() (Production Engine) already computed
verdict/smart_money/composite_score/foreign_score (passthroughs of stockbit_flow's own
columns) and net_foreign_14d/trend_7d (the only genuinely new aggregations, per ADR-AF-001).
This agent's job is interpretation of those facts, not re-aggregation.
"""

import json
import time
from pathlib import Path

from ..providers.base import FirmLLMProvider
from ..schemas import AgentResult, FlowContext, SignalCandidate

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "flow_v1.md"
PROMPT_VERSION = "v1"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()


def _candidate_summary(candidate: SignalCandidate) -> dict:
    return {
        "ticker": candidate.ticker,
        "strategy": candidate.strategy,
        "score": candidate.score,
        "regime": candidate.regime,
        "foreign_score": candidate.foreign_score,
    }


async def run(
    candidate: SignalCandidate,
    client: FirmLLMProvider,
) -> AgentResult:
    start = time.monotonic()
    resp = None
    try:
        flow_ctx = candidate.flow or FlowContext()
        user_msg = json.dumps({
            "candidate": _candidate_summary(candidate),
            "flow_context": flow_ctx.model_dump(),
        })
        resp = await client.generate([
            {"role": "system", "content": _load_prompt()},
            {"role": "user", "content": user_msg},
        ])
        try:
            output = json.loads(resp.content)
        except json.JSONDecodeError as e:
            raise ValueError(f"json decode error: {e}") from e
        return AgentResult(
            role="flow",
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
            role="flow",
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
