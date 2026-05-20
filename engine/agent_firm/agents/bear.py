"""Bear Researcher agent. Steelmans the bear case from analyst + bull outputs."""

import json
import time
from pathlib import Path

from ..client import DeepSeekClient
from ..schemas import AgentResult, SignalCandidate

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "bear_v1.md"
PROMPT_VERSION = "v1"


async def run(
    candidate: SignalCandidate,
    analyst_results: list[AgentResult],
    bull_result: AgentResult,
    client: DeepSeekClient,
) -> AgentResult:
    start = time.monotonic()
    try:
        user_msg = json.dumps({
            "candidate": candidate.model_dump(),
            "analyst_reports": [
                {"role": r.role, "status": r.status, "output": r.output, "error": r.error}
                for r in analyst_results
            ],
            "bull_case": {"status": bull_result.status, "output": bull_result.output},
        })
        resp = await client.chat([
            {"role": "system", "content": _PROMPT_PATH.read_text()},
            {"role": "user", "content": user_msg},
        ])
        try:
            output = json.loads(resp["content"])
        except json.JSONDecodeError as e:
            raise ValueError(f"json decode error: {e}") from e
        return AgentResult(
            role="bear", status="ok", output=output,
            prompt_version=PROMPT_VERSION,
            tokens_in=resp["tokens_in"], tokens_out=resp["tokens_out"],
            duration_s=resp["duration_s"],
        )
    except Exception as err:
        return AgentResult(
            role="bear", status="failed",
            prompt_version=PROMPT_VERSION,
            error=str(err),
            duration_s=time.monotonic() - start,
        )
