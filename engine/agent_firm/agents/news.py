"""News/Sentiment agent. Reads news_mentions + optional Tavily web search."""

import json
import time
from pathlib import Path
from typing import Any

from ..client import DeepSeekClient
from ..schemas import AgentResult, SignalCandidate
from ..tools import web_search as _web_search

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "news_v1.md"
PROMPT_VERSION = "v1"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()


async def run(
    candidate: SignalCandidate,
    client: DeepSeekClient,
    context: dict[str, Any],
) -> AgentResult:
    start = time.monotonic()
    tools_called: list[dict] = []
    try:
        tavily_results = await _web_search.search(
            f"{candidate.ticker} IDX saham berita terbaru site:idx.co.id OR site:bisnis.com OR site:kontan.co.id"
        )
        tools_called.append({"tool": "tavily_search", "results": len(tavily_results)})
        user_msg = json.dumps({
            "candidate": candidate.model_dump(),
            "news_mentions_7d": context.get("news_mentions", []),
            "web_search_results": tavily_results,
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
            role="news",
            status="ok",
            output=output,
            prompt_version=PROMPT_VERSION,
            tokens_in=resp["tokens_in"],
            tokens_out=resp["tokens_out"],
            duration_s=resp["duration_s"],
            tools_called=tools_called,
        )
    except Exception as err:
        return AgentResult(
            role="news",
            status="failed",
            prompt_version=PROMPT_VERSION,
            error=str(err),
            duration_s=time.monotonic() - start,
            tools_called=tools_called,
        )
