"""News/Sentiment agent. Interprets precomputed NewsContext + a live web search.

WP3 (Specialist Context Consumption Migration): this agent no longer receives a raw
news_mentions dict — engine.agent_firm_context.build_news_context() (Production Engine)
already computed mentions_count_7d and has_catalyst (a engine.catalyst.has_catalyst()
passthrough, per ADR-AF-001). The live Tavily web search is kept as-is: it is genuine
real-time NLU input the specialist itself interprets, not a deterministic fact with an
existing canonical producer.
"""

import json
import time
from pathlib import Path

from ..providers.base import FirmLLMProvider
from ..schemas import AgentResult, NewsContext, SignalCandidate
from ..tools import web_search as _web_search

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "news_v1.md"
PROMPT_VERSION = "v1"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()


def _candidate_summary(candidate: SignalCandidate) -> dict:
    return {"ticker": candidate.ticker, "strategy": candidate.strategy}


async def run(
    candidate: SignalCandidate,
    client: FirmLLMProvider,
) -> AgentResult:
    start = time.monotonic()
    tools_called: list[dict] = []
    resp = None
    try:
        tavily_results = await _web_search.search(
            f"{candidate.ticker} IDX saham berita terbaru site:idx.co.id OR site:bisnis.com OR site:kontan.co.id"
        )
        tools_called.append({"tool": "tavily_search", "results": len(tavily_results)})
        news_ctx = candidate.news or NewsContext()
        user_msg = json.dumps({
            "candidate": _candidate_summary(candidate),
            "news_context": {
                "mentions_7d": news_ctx.mentions_7d,
                "mentions_count_7d": news_ctx.mentions_count_7d,
                "has_catalyst": news_ctx.has_catalyst,
            },
            "web_search_results": tavily_results,
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
            role="news",
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
            role="news",
            status="failed",
            prompt_version=PROMPT_VERSION,
            error=str(err),
            duration_s=time.monotonic() - start,
            tools_called=tools_called,
            tokens_in=resp.tokens_in if resp is not None else 0,
            tokens_out=resp.tokens_out if resp is not None else 0,
            cost_usd=resp.cost_usd if resp is not None else 0.0,
            provider=resp.provider if resp is not None else getattr(err, "provider", ""),
            model=resp.model if resp is not None else "",
            runtime_version=resp.runtime_version if resp is not None else "",
            failover=resp.failover if resp is not None else False,
        )
