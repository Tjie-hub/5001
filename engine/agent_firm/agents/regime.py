"""Regime Analyst agent. Reads WF scores and daily screen data."""

import json
import time
from pathlib import Path
from typing import Any

from ..client import DeepSeekClient
from ..schemas import AgentResult, SignalCandidate

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "regime_v1.md"
PROMPT_VERSION = "v1"


async def run(
    candidate: SignalCandidate,
    client: DeepSeekClient,
    context: dict[str, Any],
) -> AgentResult:
    start = time.monotonic()
    try:
        user_msg = json.dumps({
            "candidate": candidate.model_dump(),
            "wf_scores": context.get("wf_scores", []),
            "sector_data_10d": context.get("sector_data", []),
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
            role="regime", status="ok", output=output,
            prompt_version=PROMPT_VERSION,
            tokens_in=resp["tokens_in"], tokens_out=resp["tokens_out"],
            duration_s=resp["duration_s"],
        )
    except Exception as err:
        return AgentResult(
            role="regime", status="failed",
            prompt_version=PROMPT_VERSION,
            error=str(err),
            duration_s=time.monotonic() - start,
        )
