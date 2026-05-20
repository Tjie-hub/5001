"""Tavily web search tool for the News agent.

Falls back to empty list if TAVILY_API_KEY is absent or the request fails.
"""

import logging

import httpx

from .. import config

logger = logging.getLogger(__name__)

_TAVILY_URL = "https://api.tavily.com/search"


async def search(query: str, max_results: int | None = None) -> list[dict]:
    if not config.TAVILY_API_KEY:
        return []
    n = max_results if max_results is not None else config.TAVILY_MAX_RESULTS
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                _TAVILY_URL,
                json={"api_key": config.TAVILY_API_KEY, "query": query, "max_results": n},
            )
            resp.raise_for_status()
            return resp.json().get("results", [])
    except Exception as exc:
        logger.warning("Tavily search failed: %s", exc)
        return []
