"""Technical Analyst agent. Reads OHLCV, returns technical conviction call."""

import json
import time
from pathlib import Path

from ..providers.base import FirmLLMProvider
from ..schemas import AgentResult, SignalCandidate
from ..tools.sqlite_query import query

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "technical_v1.md"
PROMPT_VERSION = "v1"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()


async def run(
    candidate: SignalCandidate,
    client: FirmLLMProvider,
    db_path: str,
) -> AgentResult:
    start = time.monotonic()
    tools_called: list[dict] = []
    resp = None
    try:
        ohlcv = query(
            db_path,
            "SELECT date, open, high, low, close, volume FROM ohlcv "
            "WHERE ticker = ? ORDER BY date DESC LIMIT 60",
            (candidate.ticker,),
        )
        tools_called.append({"tool": "sqlite_query", "rows": len(ohlcv)})
        user_msg = json.dumps({
            "candidate": candidate.model_dump(),
            "ohlcv_recent_60d": ohlcv,
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
            tools_called=tools_called,
        )
    except Exception as err:
        return AgentResult(
            role="technical",
            status="failed",
            prompt_version=PROMPT_VERSION,
            error=str(err),
            duration_s=time.monotonic() - start,
            tools_called=tools_called,
            tokens_in=resp.tokens_in if resp is not None else 0,
            tokens_out=resp.tokens_out if resp is not None else 0,
            cost_usd=resp.cost_usd if resp is not None else 0.0,
            provider=resp.provider if resp is not None else "",
            model=resp.model if resp is not None else "",
            runtime_version=resp.runtime_version if resp is not None else "",
            failover=resp.failover if resp is not None else False,
        )
