import pytest
import respx
import httpx

from engine.agent_firm.tools.web_search import search


@pytest.mark.asyncio
@respx.mock
async def test_search_returns_results(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    import importlib
    from engine.agent_firm import config
    importlib.reload(config)
    import engine.agent_firm.tools.web_search as ws_mod
    importlib.reload(ws_mod)
    from engine.agent_firm.tools.web_search import search as _search

    respx.post("https://api.tavily.com/search").mock(return_value=httpx.Response(200, json={
        "results": [
            {"title": "BBRI News", "url": "https://example.com/1", "content": "Good outlook", "score": 0.9},
            {"title": "BBRI Flow", "url": "https://example.com/2", "content": "Foreign buy", "score": 0.8},
        ]
    }))
    results = await _search("BBRI IDX news", max_results=5)
    assert len(results) == 2
    assert results[0]["title"] == "BBRI News"


@pytest.mark.asyncio
async def test_search_returns_empty_when_no_key(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    import importlib
    from engine.agent_firm import config
    importlib.reload(config)
    import engine.agent_firm.tools.web_search as ws_mod
    importlib.reload(ws_mod)
    from engine.agent_firm.tools.web_search import search as _search

    results = await _search("BBRI IDX news")
    assert results == []


@pytest.mark.asyncio
@respx.mock
async def test_search_returns_empty_on_http_error(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    import importlib
    from engine.agent_firm import config
    importlib.reload(config)
    import engine.agent_firm.tools.web_search as ws_mod
    importlib.reload(ws_mod)
    from engine.agent_firm.tools.web_search import search as _search

    respx.post("https://api.tavily.com/search").mock(return_value=httpx.Response(500))
    results = await _search("BBRI IDX news")
    assert results == []
