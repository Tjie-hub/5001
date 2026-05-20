"""Flow Specialist agent. Reads Stockbit and broker flow, returns smart-money verdict."""

import json
import time
from pathlib import Path
from typing import Any

from ..client import DeepSeekClient
from ..schemas import AgentResult, SignalCandidate

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "flow_v1.md"
PROMPT_VERSION = "v1"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()


async def run(
    candidate: SignalCandidate,
    client: DeepSeekClient,
    context: dict[str, Any],
) -> AgentResult:
    start = time.monotonic()
    try:
        user_msg = json.dumps({
            "candidate": candidate.model_dump(),
            "stockbit_flow_14d": context.get("stockbit_flow", []),
            "broker_flow_14d": context.get("broker_flow", []),
            "stockbit_flow_bars_7d": context.get("stockbit_flow_bars", []),
        })
        resp = await client.chat([
            {"role": "system", "content": _load_prompt()},
            {"role": "user", "content": user_msg},
        ])
        try:
            output = json.loads(resp["content"])
        except json.JSONDecodeError as e:
            raise ValueError(f"json decode error: {e}") from e
        return AgentResult(
            role="flow",
            status="ok",
            output=output,
            prompt_version=PROMPT_VERSION,
            tokens_in=resp["tokens_in"],
            tokens_out=resp["tokens_out"],
            duration_s=resp["duration_s"],
        )
    except Exception as err:
        return AgentResult(
            role="flow",
            status="failed",
            prompt_version=PROMPT_VERSION,
            error=str(err),
            duration_s=time.monotonic() - start,
        )
