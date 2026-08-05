"""Regime Analyst agent. Interprets precomputed RegimeContext facts.

WP3 (Specialist Context Consumption Migration): this agent no longer receives raw wf_scores/
daily_screen rows or re-thresholds VPIN/volume-ratio/Sharpe itself —
engine.agent_firm_context.build_regime_context() (Production Engine) already computed
regime_call (a detect_regime() passthrough, per ADR-AF-001), sector_tailwind, macro_risk,
best_strategy, and ticker_consistency_pct. This agent's job is to confirm or challenge that
already-computed reading, not build a second regime classifier.
"""

import json
import time
from pathlib import Path

from ..providers.base import FirmLLMProvider
from ..schemas import AgentResult, RegimeContext, SignalCandidate

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "regime_v1.md"
PROMPT_VERSION = "v1"


def _candidate_summary(candidate: SignalCandidate) -> dict:
    return {
        "ticker": candidate.ticker,
        "strategy": candidate.strategy,
        "score": candidate.score,
        "regime": candidate.regime,
    }


async def run(
    candidate: SignalCandidate,
    client: FirmLLMProvider,
) -> AgentResult:
    start = time.monotonic()
    resp = None
    try:
        regime_ctx = candidate.regime_context or RegimeContext()
        user_msg = json.dumps({
            "candidate": _candidate_summary(candidate),
            "regime_context": regime_ctx.model_dump(),
        })
        resp = await client.generate([
            {"role": "system", "content": _PROMPT_PATH.read_text()},
            {"role": "user", "content": user_msg},
        ])
        try:
            output = json.loads(resp.content)
        except json.JSONDecodeError as e:
            raise ValueError(f"json decode error: {e}") from e
        return AgentResult(
            role="regime", status="ok", output=output,
            prompt_version=PROMPT_VERSION,
            tokens_in=resp.tokens_in, tokens_out=resp.tokens_out,
            cost_usd=resp.cost_usd, duration_s=resp.duration_s,
            provider=resp.provider, model=resp.model,
            runtime_version=resp.runtime_version, failover=resp.failover,
        )
    except Exception as err:
        return AgentResult(
            role="regime", status="failed",
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
