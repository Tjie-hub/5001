"""Risk Manager agent. Final approve/veto decision."""

import json
import time
from pathlib import Path

from ..client import DeepSeekClient
from ..guardrails import normalize_quant
from ..schemas import AgentResult, SignalCandidate

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "risk_v2.md"
PROMPT_VERSION = "v2"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()


async def run(
    candidate: SignalCandidate,
    analyst_results: list[AgentResult],
    client: DeepSeekClient,
) -> AgentResult:
    start = time.monotonic()
    try:
        cand = candidate.model_dump()
        # quant_score normalized to 0-1 so the prompt's gate is scale-consistent
        # across callers (flow -5..+5, premarket/eod 0-100). Raw stays as `score`.
        cand["quant_score"] = round(normalize_quant(cand.get("score"), candidate.strategy), 3)
        user_msg = json.dumps({
            "candidate": cand,
            "analyst_reports": [
                {"role": r.role, "status": r.status, "output": r.output, "error": r.error}
                for r in analyst_results
            ],
        })
        resp = await client.chat([
            {"role": "system", "content": _load_prompt()},
            {"role": "user", "content": user_msg},
        ])
        try:
            output = json.loads(resp["content"])
        except json.JSONDecodeError as json_err:
            raise ValueError(f"json decode error: {json_err}") from json_err
        return AgentResult(
            role="risk",
            status="ok",
            output=output,
            prompt_version=PROMPT_VERSION,
            tokens_in=resp["tokens_in"],
            tokens_out=resp["tokens_out"],
            duration_s=resp["duration_s"],
        )
    except Exception as err:
        return AgentResult(
            role="risk",
            status="failed",
            prompt_version=PROMPT_VERSION,
            error=str(err),
            duration_s=time.monotonic() - start,
        )
