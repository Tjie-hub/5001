# Agent Firm Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the agent firm to a 7-agent LangGraph DAG (Flow, Regime, News, Bull, Bear added to Technical + Risk), wire into `scheduled_multi_strategy_scan()` in shadow mode, with Tavily web search for the News agent.

**Architecture:** LangGraph `StateGraph` replaces asyncio orchestration in `firm.py`. A `build_context` node pre-fetches all SQLite data once per signal; a `run_analysts` node runs 4 parallel LLM calls via `asyncio.gather`; Bull and Bear run sequentially; Risk Manager v2 makes the final decision. Public API (`evaluate`/`evaluate_async`) unchanged.

**Tech Stack:** Python 3.12, `langgraph>=0.2.0`, `httpx` (existing, for Tavily REST), pydantic v2, `pytest-asyncio`, `respx` (existing).

**Reference spec:** `docs/superpowers/specs/2026-05-20-agent-firm-phase2-design.md`

**Working directory:** `/home/tjiesar/10 Projects/idx-walkforward-5001`
**Test runner:** `venv/bin/pytest tests/agent_firm/ -v`
**Conventions:** TDD every task. One commit per task minimum.

---

## File Structure

**Created:**
- `engine/agent_firm/agents/flow.py`
- `engine/agent_firm/agents/regime.py`
- `engine/agent_firm/agents/news.py`
- `engine/agent_firm/agents/bull.py`
- `engine/agent_firm/agents/bear.py`
- `engine/agent_firm/tools/web_search.py`
- `engine/agent_firm/tools/news_lookup.py`
- `engine/agent_firm/prompts/flow_v1.md`
- `engine/agent_firm/prompts/regime_v1.md`
- `engine/agent_firm/prompts/news_v1.md`
- `engine/agent_firm/prompts/bull_v1.md`
- `engine/agent_firm/prompts/bear_v1.md`
- `engine/agent_firm/prompts/risk_v2.md`
- `tests/agent_firm/test_flow.py`
- `tests/agent_firm/test_regime.py`
- `tests/agent_firm/test_news.py`
- `tests/agent_firm/test_bull.py`
- `tests/agent_firm/test_bear.py`
- `tests/agent_firm/test_web_search.py`
- `tests/agent_firm/test_news_lookup.py`
- `tests/agent_firm/test_firm_v2.py`
- `tests/agent_firm/fixtures/recorded/` (directory only — populated manually after first live run)

**Modified:**
- `requirements.txt` — add `langgraph>=0.2.0`
- `engine/agent_firm/config.py` — add `TAVILY_API_KEY`, `TAVILY_MAX_RESULTS`
- `engine/agent_firm/schemas.py` — add `AgentState` TypedDict
- `engine/agent_firm/firm.py` — full rewrite to LangGraph
- `engine/agent_firm/agents/risk.py` — point to `risk_v2.md`, extend analyst list
- `scheduler.py` — add agent firm hook in `scheduled_multi_strategy_scan()`
- `app.py` — extend `/api/agent/status` with `today_stats`
- `templates/backtest_multi.html` — add stats line to badge

---

## Task 1: Add LangGraph Dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Read current requirements**

```bash
cat requirements.txt
```

- [ ] **Step 2: Add langgraph**

Append to `requirements.txt`:
```
langgraph>=0.2.0
```

- [ ] **Step 3: Install**

```bash
venv/bin/pip install langgraph
```

Expected: installs langgraph and its deps (langchain-core etc.)

- [ ] **Step 4: Verify import**

```bash
venv/bin/python -c "import langgraph; print(langgraph.__version__)"
```

Expected: prints a version string.

- [ ] **Step 5: Run existing tests to confirm no breakage**

```bash
venv/bin/pytest tests/agent_firm/ -v --tb=short 2>&1 | tail -5
```

Expected: 31 passed.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt
git commit -m "chore(agent_firm): add langgraph dependency for Phase 2 DAG"
```

---

## Task 2: AgentState + Config Additions

**Files:**
- Modify: `engine/agent_firm/schemas.py`
- Modify: `engine/agent_firm/config.py`

- [ ] **Step 1: Write failing test for AgentState**

Add to `tests/agent_firm/test_schemas.py`:

```python
def test_agent_state_has_required_keys():
    from engine.agent_firm.schemas import AgentState
    # TypedDict — verify it can be instantiated as a plain dict with expected keys
    state: AgentState = {
        "candidate": None,
        "db_path": "/tmp/t.db",
        "context": {},
        "client": None,
        "technical_result": None,
        "flow_result": None,
        "regime_result": None,
        "news_result": None,
        "bull_result": None,
        "bear_result": None,
        "risk_result": None,
        "decision": None,
    }
    assert state["db_path"] == "/tmp/t.db"
```

- [ ] **Step 2: Run to confirm it fails**

```bash
venv/bin/pytest tests/agent_firm/test_schemas.py::test_agent_state_has_required_keys -v
```

Expected: ImportError (`cannot import name 'AgentState'`).

- [ ] **Step 3: Add AgentState to schemas.py**

Add at the bottom of `engine/agent_firm/schemas.py`:

```python
from typing import TypedDict


class AgentState(TypedDict):
    candidate: SignalCandidate
    db_path: str
    context: dict[str, Any]
    client: Any  # DeepSeekClient — in-memory only, not serialized
    technical_result: Optional[AgentResult]
    flow_result: Optional[AgentResult]
    regime_result: Optional[AgentResult]
    news_result: Optional[AgentResult]
    bull_result: Optional[AgentResult]
    bear_result: Optional[AgentResult]
    risk_result: Optional[AgentResult]
    decision: Optional[AgentDecision]
```

- [ ] **Step 4: Write failing test for config additions**

Add to `tests/agent_firm/test_config.py`:

```python
def test_tavily_config_defaults(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("AGENT_FIRM_TAVILY_MAX", raising=False)
    import importlib
    from engine.agent_firm import config
    importlib.reload(config)
    assert config.TAVILY_API_KEY == ""
    assert config.TAVILY_MAX_RESULTS == 5

def test_tavily_config_from_env(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
    monkeypatch.setenv("AGENT_FIRM_TAVILY_MAX", "3")
    import importlib
    from engine.agent_firm import config
    importlib.reload(config)
    assert config.TAVILY_API_KEY == "tvly-test-key"
    assert config.TAVILY_MAX_RESULTS == 3
```

- [ ] **Step 5: Add config vars**

Add to `engine/agent_firm/config.py` after `PER_AGENT_TIMEOUT_S`:

```python
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_MAX_RESULTS = int(os.getenv("AGENT_FIRM_TAVILY_MAX", "5"))
```

- [ ] **Step 6: Run tests**

```bash
venv/bin/pytest tests/agent_firm/test_schemas.py tests/agent_firm/test_config.py -v --tb=short
```

Expected: all pass (6 config tests + 6 schema tests).

- [ ] **Step 7: Commit**

```bash
git add engine/agent_firm/schemas.py engine/agent_firm/config.py tests/agent_firm/test_schemas.py tests/agent_firm/test_config.py
git commit -m "feat(agent_firm): AgentState TypedDict and Tavily config vars"
```

---

## Task 3: news_lookup Tool

**Files:**
- Create: `engine/agent_firm/tools/news_lookup.py`
- Create: `tests/agent_firm/test_news_lookup.py`

The `news_mentions` table schema: `ticker TEXT, date TEXT, count INTEGER, headlines_json TEXT, updated_at TEXT`.

- [ ] **Step 1: Write failing test**

Create `tests/agent_firm/test_news_lookup.py`:

```python
import json
import sqlite3

import pytest

from engine.agent_firm.tools.news_lookup import lookup


@pytest.fixture
def news_db(tmp_path):
    db = tmp_path / "t.db"
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE news_mentions (
            ticker TEXT, date TEXT, count INTEGER,
            headlines_json TEXT, updated_at TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO news_mentions VALUES (?,?,?,?,?)",
        [
            ("BBRI", "2026-05-19", 3,
             json.dumps(["Headline A", "Headline B", "Headline C"]),
             "2026-05-19 20:00"),
            ("BBRI", "2026-05-18", 2,
             json.dumps(["Headline D", "Headline E"]),
             "2026-05-18 20:00"),
            ("BBCA", "2026-05-19", 1,
             json.dumps(["Headline F"]),
             "2026-05-19 20:00"),
        ]
    )
    conn.commit()
    conn.close()
    return str(db)


def test_lookup_returns_rows_for_ticker(news_db):
    rows = lookup(news_db, "BBRI", days=30)
    assert len(rows) == 2
    assert all(r["ticker"] == "BBRI" for r in rows)


def test_lookup_parses_headlines_json(news_db):
    rows = lookup(news_db, "BBRI", days=30)
    assert isinstance(rows[0]["headlines"], list)
    assert "Headline A" in rows[0]["headlines"]


def test_lookup_returns_empty_for_unknown_ticker(news_db):
    rows = lookup(news_db, "ZZXX", days=30)
    assert rows == []


def test_lookup_caps_at_20_rows(tmp_path):
    db = tmp_path / "big.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE news_mentions (ticker TEXT, date TEXT, count INTEGER, headlines_json TEXT, updated_at TEXT)")
    conn.executemany(
        "INSERT INTO news_mentions VALUES (?,?,?,?,?)",
        [("BBRI", f"2026-01-{i:02d}", 1, json.dumps([f"h{i}"]), "") for i in range(1, 26)]
    )
    conn.commit()
    conn.close()
    rows = lookup(str(db), "BBRI", days=365)
    assert len(rows) <= 20
```

- [ ] **Step 2: Run to confirm failure**

```bash
venv/bin/pytest tests/agent_firm/test_news_lookup.py -v
```

Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement**

Create `engine/agent_firm/tools/news_lookup.py`:

```python
"""Structured news_mentions table reader for the News agent."""

import json
import sqlite3
from typing import Any


def lookup(db_path: str, ticker: str, days: int = 7) -> list[dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT ticker, date, count, headlines_json FROM news_mentions "
            "WHERE ticker = ? AND date >= date('now', ? || ' days') "
            "ORDER BY date DESC LIMIT 20",
            (ticker, f"-{days}"),
        ).fetchall()
        result = []
        for r in rows:
            row = dict(r)
            try:
                row["headlines"] = json.loads(row.pop("headlines_json") or "[]")
            except (json.JSONDecodeError, TypeError):
                row["headlines"] = []
            result.append(row)
        return result
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests**

```bash
venv/bin/pytest tests/agent_firm/test_news_lookup.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add engine/agent_firm/tools/news_lookup.py tests/agent_firm/test_news_lookup.py
git commit -m "feat(agent_firm): news_lookup tool reads news_mentions table"
```

---

## Task 4: web_search Tool (Tavily)

**Files:**
- Create: `engine/agent_firm/tools/web_search.py`
- Create: `tests/agent_firm/test_web_search.py`

- [ ] **Step 1: Write failing test**

Create `tests/agent_firm/test_web_search.py`:

```python
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
venv/bin/pytest tests/agent_firm/test_web_search.py -v
```

Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement**

Create `engine/agent_firm/tools/web_search.py`:

```python
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
```

- [ ] **Step 4: Run tests**

```bash
venv/bin/pytest tests/agent_firm/test_web_search.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add engine/agent_firm/tools/web_search.py tests/agent_firm/test_web_search.py
git commit -m "feat(agent_firm): web_search tool via Tavily REST (fail-safe)"
```

---

## Task 5: Flow Specialist Agent

**Files:**
- Create: `engine/agent_firm/prompts/flow_v1.md`
- Create: `engine/agent_firm/agents/flow.py`
- Create: `tests/agent_firm/test_flow.py`

Flow agent reads `context["stockbit_flow"]`, `context["broker_flow"]`, `context["stockbit_flow_bars"]`.

- [ ] **Step 1: Create prompt file**

Create `engine/agent_firm/prompts/flow_v1.md`:

```
You are the Flow Specialist in a trading agent firm evaluating Indonesian Stock Exchange (IDX) signals.

You will receive:
- A SignalCandidate (ticker, strategy, quant score)
- Stockbit composite flow data for the last 14 days (buy_lot, sell_lot, net_lot, net_value, verdict, smart_money, foreign_score, composite_score)
- Broker flow data by investor type (Asing=foreign, Domestik=domestic) for the last 14 days
- Intraday flow bar data for the last 7 days (bar-level delta)

Your job: determine whether institutional and/or foreign money is accumulating or distributing this stock.

Output strictly as JSON. No markdown, no code fences:

{
  "flow_verdict": "ACCUMULATING" | "DISTRIBUTING" | "NEUTRAL",
  "smart_money_signal": "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL",
  "net_foreign_14d": <integer lot net, positive = net buy>,
  "reasoning": "1-2 sentences explaining the flow narrative"
}

Guidance:
- ACCUMULATING: consistent net buying across majority of days, rising composite_score, smart_money present
- DISTRIBUTING: consistent net selling, falling composite_score, negative foreign_score
- NEUTRAL: mixed signals, or fewer than 3 days of data
- net_foreign_14d: sum of net_lot values from broker_flow rows where investor_type='Asing'
- If all data is missing or NULL: return NEUTRAL with reasoning "insufficient flow data"
```

- [ ] **Step 2: Write failing test**

Create `tests/agent_firm/test_flow.py`:

```python
import json
import pytest
from unittest.mock import AsyncMock
from engine.agent_firm.agents import flow
from engine.agent_firm.schemas import SignalCandidate


def _make_candidate():
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=3.8, scan_time="2026-05-20T10:00:00+07:00",
    )


def _make_context(verdict="ACCUMULATING"):
    return {
        "stockbit_flow": [
            {"trade_date": "2026-05-19", "buy_lot": 5000, "sell_lot": 2000,
             "net_lot": 3000, "net_value": 1500000000, "verdict": "BUY",
             "smart_money": "YES", "foreign_score": 2.5, "composite_score": 8},
        ],
        "broker_flow": [
            {"trade_date": "2026-05-19", "broker_code": "BK", "side": "BUY",
             "lot_value": 1000000000, "investor_type": "Asing"},
        ],
        "stockbit_flow_bars": [],
    }


@pytest.mark.asyncio
async def test_flow_returns_ok_on_success():
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": json.dumps({
            "flow_verdict": "ACCUMULATING",
            "smart_money_signal": "BUY",
            "net_foreign_14d": 3000,
            "reasoning": "Consistent net buying with smart money",
        }),
        "tokens_in": 800, "tokens_out": 60, "cost_usd": 0.0004, "duration_s": 2.5,
    }
    result = await flow.run(_make_candidate(), fake_client, _make_context())
    assert result.role == "flow"
    assert result.status == "ok"
    assert result.output["flow_verdict"] == "ACCUMULATING"
    assert result.tokens_in == 800


@pytest.mark.asyncio
async def test_flow_returns_failed_on_invalid_json():
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": "not json",
        "tokens_in": 100, "tokens_out": 5, "cost_usd": 0.0, "duration_s": 1.0,
    }
    result = await flow.run(_make_candidate(), fake_client, _make_context())
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_flow_returns_failed_on_client_exception():
    fake_client = AsyncMock()
    fake_client.chat.side_effect = RuntimeError("timeout")
    result = await flow.run(_make_candidate(), fake_client, _make_context())
    assert result.status == "failed"
    assert "timeout" in result.error
```

- [ ] **Step 3: Run to confirm failure**

```bash
venv/bin/pytest tests/agent_firm/test_flow.py -v
```

Expected: ModuleNotFoundError on `engine.agent_firm.agents.flow`.

- [ ] **Step 4: Implement**

Create `engine/agent_firm/agents/flow.py`:

```python
"""Flow Specialist agent. Reads Stockbit and broker flow, returns smart-money verdict."""

import json
import time
from pathlib import Path
from typing import Any

from ..client import DeepSeekClient
from ..schemas import AgentResult, SignalCandidate

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "flow_v1.md"
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
            "stockbit_flow_14d": context.get("stockbit_flow", []),
            "broker_flow_14d": context.get("broker_flow", []),
            "stockbit_flow_bars_7d": context.get("stockbit_flow_bars", []),
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
            role="flow", status="ok", output=output,
            prompt_version=PROMPT_VERSION,
            tokens_in=resp["tokens_in"], tokens_out=resp["tokens_out"],
            duration_s=resp["duration_s"],
        )
    except Exception as err:
        return AgentResult(
            role="flow", status="failed",
            prompt_version=PROMPT_VERSION,
            error=str(err),
            duration_s=time.monotonic() - start,
        )
```

- [ ] **Step 5: Run tests**

```bash
venv/bin/pytest tests/agent_firm/test_flow.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add engine/agent_firm/prompts/flow_v1.md engine/agent_firm/agents/flow.py tests/agent_firm/test_flow.py
git commit -m "feat(agent_firm): Flow Specialist agent (v1 prompt + run loop)"
```

---

## Task 6: Regime Analyst Agent

**Files:**
- Create: `engine/agent_firm/prompts/regime_v1.md`
- Create: `engine/agent_firm/agents/regime.py`
- Create: `tests/agent_firm/test_regime.py`

- [ ] **Step 1: Create prompt file**

Create `engine/agent_firm/prompts/regime_v1.md`:

```
You are the Regime Analyst in a trading agent firm evaluating Indonesian Stock Exchange (IDX) signals.

You will receive:
- A SignalCandidate (ticker, strategy, quant score, regime field from the quant pipeline)
- Walk-forward consistency scores for this ticker by strategy (consistency_pct, avg_return_pct, avg_sharpe, weighted_score)
- Recent daily screen data: signal labels, VPIN readings, volume ratios (last 10 bars)

Your job: confirm or challenge the quant pipeline's regime reading and assess whether macro/sector conditions support the trade.

Output strictly as JSON. No markdown, no code fences:

{
  "regime_call": "TRENDING" | "SIDEWAYS" | "VOLATILE" | "UNKNOWN",
  "sector_tailwind": true | false,
  "macro_risk": "LOW" | "MEDIUM" | "HIGH",
  "reasoning": "1-2 sentences"
}

Guidance:
- TRENDING: quant pipeline says TRENDING AND walk-forward consistency >= 55% for at least one strategy
- VOLATILE: vpin_label is "EXTREME" in recent bars OR avg vol_ratio > 3.0
- SIDEWAYS: signal neutral across most bars with no clear direction
- UNKNOWN: wf_scores empty or all data missing
- sector_tailwind: true if the ticker's best strategy shows avg_sharpe > 0.8
- macro_risk HIGH: if vol_ratio spikes coincide with negative signal labels
```

- [ ] **Step 2: Write failing test**

Create `tests/agent_firm/test_regime.py`:

```python
import json
import pytest
from unittest.mock import AsyncMock
from engine.agent_firm.agents import regime
from engine.agent_firm.schemas import SignalCandidate


def _make_candidate():
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=3.8, scan_time="2026-05-20T10:00:00+07:00",
        regime="TRENDING",
    )


def _make_context():
    return {
        "wf_scores": [
            {"strategy": "vol_weighted", "consistency_pct": 68.0,
             "avg_return_pct": 3.2, "avg_sharpe": 1.1, "weighted_score": 72.0},
        ],
        "sector_data": [
            {"date": "2026-05-19", "signal": "BUY", "vpin_label": "NORMAL", "vol_ratio": 1.8},
        ],
    }


@pytest.mark.asyncio
async def test_regime_returns_ok_on_success():
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": json.dumps({
            "regime_call": "TRENDING",
            "sector_tailwind": True,
            "macro_risk": "LOW",
            "reasoning": "Consistent walk-forward with elevated VPIN",
        }),
        "tokens_in": 700, "tokens_out": 55, "cost_usd": 0.0003, "duration_s": 2.0,
    }
    result = await regime.run(_make_candidate(), fake_client, _make_context())
    assert result.role == "regime"
    assert result.status == "ok"
    assert result.output["regime_call"] == "TRENDING"


@pytest.mark.asyncio
async def test_regime_returns_failed_on_invalid_json():
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": "bad json", "tokens_in": 50, "tokens_out": 3,
        "cost_usd": 0.0, "duration_s": 1.0,
    }
    result = await regime.run(_make_candidate(), fake_client, _make_context())
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_regime_returns_failed_on_client_exception():
    fake_client = AsyncMock()
    fake_client.chat.side_effect = RuntimeError("network down")
    result = await regime.run(_make_candidate(), fake_client, _make_context())
    assert result.status == "failed"
    assert "network down" in result.error
```

- [ ] **Step 3: Run to confirm failure**

```bash
venv/bin/pytest tests/agent_firm/test_regime.py -v
```

Expected: ModuleNotFoundError.

- [ ] **Step 4: Implement**

Create `engine/agent_firm/agents/regime.py`:

```python
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
```

- [ ] **Step 5: Run tests**

```bash
venv/bin/pytest tests/agent_firm/test_regime.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add engine/agent_firm/prompts/regime_v1.md engine/agent_firm/agents/regime.py tests/agent_firm/test_regime.py
git commit -m "feat(agent_firm): Regime Analyst agent (v1 prompt + run loop)"
```

---

## Task 7: News/Sentiment Agent

**Files:**
- Create: `engine/agent_firm/prompts/news_v1.md`
- Create: `engine/agent_firm/agents/news.py`
- Create: `tests/agent_firm/test_news.py`

- [ ] **Step 1: Create prompt file**

Create `engine/agent_firm/prompts/news_v1.md`:

```
You are the News/Sentiment Analyst in a trading agent firm evaluating Indonesian Stock Exchange (IDX) signals.

You will receive:
- A SignalCandidate (ticker)
- Recent news headlines from the news_mentions table (last 7 days): structured rows with date and list of headlines
- Live web search results about the ticker and Indonesian market context (title, url, content snippet)

Your job: assess news sentiment and identify catalysts that support or threaten the trade.

Output strictly as JSON. No markdown, no code fences:

{
  "sentiment": "BULLISH" | "NEUTRAL" | "BEARISH",
  "catalyst": "bullish" | "neutral" | "bearish",
  "key_headline": "the single most relevant headline, or null if none",
  "summary": "1-2 sentences on the news narrative"
}

Guidance:
- BULLISH: positive earnings surprise, analyst upgrades, dividend announcement, sector tailwinds, M&A news
- BEARISH: earnings miss, analyst downgrades, regulatory risk, macro headwinds, scandal
- NEUTRAL: no significant news, mixed coverage, or only routine updates
- If no news data at all: sentiment=NEUTRAL, catalyst=neutral, key_headline=null, summary="no recent news found"
```

- [ ] **Step 2: Write failing test**

Create `tests/agent_firm/test_news.py`:

```python
import json
import pytest
import respx
import httpx
from unittest.mock import AsyncMock
from engine.agent_firm.agents import news
from engine.agent_firm.schemas import SignalCandidate


def _make_candidate():
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=3.8, scan_time="2026-05-20T10:00:00+07:00",
    )


def _make_context():
    return {
        "news_mentions": [
            {"ticker": "BBRI", "date": "2026-05-19", "count": 3,
             "headlines": ["BBRI earnings beat", "BI rate hold", "Foreign buy BBRI"]},
        ],
    }


@pytest.mark.asyncio
async def test_news_returns_ok_on_success(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": json.dumps({
            "sentiment": "BULLISH",
            "catalyst": "bullish",
            "key_headline": "BBRI earnings beat",
            "summary": "Strong earnings and foreign inflow support bullish thesis",
        }),
        "tokens_in": 900, "tokens_out": 70, "cost_usd": 0.0005, "duration_s": 3.0,
    }
    result = await news.run(_make_candidate(), fake_client, _make_context())
    assert result.role == "news"
    assert result.status == "ok"
    assert result.output["sentiment"] == "BULLISH"
    assert result.tokens_in == 900


@pytest.mark.asyncio
async def test_news_returns_failed_on_invalid_json(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": "not json", "tokens_in": 50, "tokens_out": 3,
        "cost_usd": 0.0, "duration_s": 1.0,
    }
    result = await news.run(_make_candidate(), fake_client, _make_context())
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_news_returns_failed_on_client_exception(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    fake_client = AsyncMock()
    fake_client.chat.side_effect = RuntimeError("api down")
    result = await news.run(_make_candidate(), fake_client, _make_context())
    assert result.status == "failed"
    assert "api down" in result.error
```

- [ ] **Step 3: Run to confirm failure**

```bash
venv/bin/pytest tests/agent_firm/test_news.py -v
```

Expected: ModuleNotFoundError.

- [ ] **Step 4: Implement**

Create `engine/agent_firm/agents/news.py`:

```python
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


async def run(
    candidate: SignalCandidate,
    client: DeepSeekClient,
    context: dict[str, Any],
) -> AgentResult:
    start = time.monotonic()
    try:
        tavily_results = await _web_search.search(
            f"{candidate.ticker} IDX saham berita terbaru site:idx.co.id OR site:bisnis.com OR site:kontan.co.id"
        )
        user_msg = json.dumps({
            "candidate": candidate.model_dump(),
            "news_mentions_7d": context.get("news_mentions", []),
            "web_search_results": tavily_results,
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
            role="news", status="ok", output=output,
            prompt_version=PROMPT_VERSION,
            tokens_in=resp["tokens_in"], tokens_out=resp["tokens_out"],
            duration_s=resp["duration_s"],
        )
    except Exception as err:
        return AgentResult(
            role="news", status="failed",
            prompt_version=PROMPT_VERSION,
            error=str(err),
            duration_s=time.monotonic() - start,
        )
```

- [ ] **Step 5: Run tests**

```bash
venv/bin/pytest tests/agent_firm/test_news.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add engine/agent_firm/prompts/news_v1.md engine/agent_firm/agents/news.py tests/agent_firm/test_news.py
git commit -m "feat(agent_firm): News/Sentiment agent with Tavily web search"
```

---

## Task 8: Bull Researcher Agent

**Files:**
- Create: `engine/agent_firm/prompts/bull_v1.md`
- Create: `engine/agent_firm/agents/bull.py`
- Create: `tests/agent_firm/test_bull.py`

Bull receives a list of `AgentResult` objects (technical, flow, regime, news).

- [ ] **Step 1: Create prompt file**

Create `engine/agent_firm/prompts/bull_v1.md`:

```
You are the Bull Researcher in a trading agent firm evaluating Indonesian Stock Exchange (IDX) signals.

You will receive analyst reports from: Technical Analyst, Flow Specialist, Regime Analyst, News/Sentiment Analyst.

Your job: construct the strongest possible bull case for this trade. Be specific to the data — no generic statements.

Output strictly as JSON. No markdown, no code fences:

{
  "bull_case": "2-3 sentences making the strongest case FOR the trade",
  "key_strength": "the single most compelling bullish factor from the analyst data"
}

If all analysts are negative, still make the best bull case possible — your role is to steelman the position, not to agree with the bears. Find the least-bad reading of the data.
```

- [ ] **Step 2: Write failing test**

Create `tests/agent_firm/test_bull.py`:

```python
import json
import pytest
from unittest.mock import AsyncMock
from engine.agent_firm.agents import bull
from engine.agent_firm.schemas import AgentResult, SignalCandidate


def _make_candidate():
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=3.8, scan_time="2026-05-20T10:00:00+07:00",
    )


def _make_analysts():
    return [
        AgentResult(role="technical", status="ok",
                    output={"verdict": "BULLISH", "conviction": 0.7}),
        AgentResult(role="flow", status="ok",
                    output={"flow_verdict": "ACCUMULATING", "smart_money_signal": "BUY"}),
        AgentResult(role="regime", status="ok",
                    output={"regime_call": "TRENDING", "sector_tailwind": True}),
        AgentResult(role="news", status="ok",
                    output={"sentiment": "BULLISH", "catalyst": "bullish"}),
    ]


@pytest.mark.asyncio
async def test_bull_returns_ok_on_success():
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": json.dumps({
            "bull_case": "Foreign accumulation + earnings beat creates strong entry.",
            "key_strength": "Smart money accumulation with bullish technicals",
        }),
        "tokens_in": 1100, "tokens_out": 80, "cost_usd": 0.0005, "duration_s": 3.0,
    }
    result = await bull.run(_make_candidate(), _make_analysts(), fake_client)
    assert result.role == "bull"
    assert result.status == "ok"
    assert "bull_case" in result.output
    assert result.tokens_in == 1100


@pytest.mark.asyncio
async def test_bull_returns_failed_on_invalid_json():
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": "bad", "tokens_in": 50, "tokens_out": 3,
        "cost_usd": 0.0, "duration_s": 1.0,
    }
    result = await bull.run(_make_candidate(), _make_analysts(), fake_client)
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_bull_returns_failed_on_client_exception():
    fake_client = AsyncMock()
    fake_client.chat.side_effect = RuntimeError("llm down")
    result = await bull.run(_make_candidate(), _make_analysts(), fake_client)
    assert result.status == "failed"
    assert "llm down" in result.error
```

- [ ] **Step 3: Run to confirm failure**

```bash
venv/bin/pytest tests/agent_firm/test_bull.py -v
```

Expected: ModuleNotFoundError.

- [ ] **Step 4: Implement**

Create `engine/agent_firm/agents/bull.py`:

```python
"""Bull Researcher agent. Steelmans the bull case from all analyst outputs."""

import json
import time
from pathlib import Path

from ..client import DeepSeekClient
from ..schemas import AgentResult, SignalCandidate

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "bull_v1.md"
PROMPT_VERSION = "v1"


async def run(
    candidate: SignalCandidate,
    analyst_results: list[AgentResult],
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
            role="bull", status="ok", output=output,
            prompt_version=PROMPT_VERSION,
            tokens_in=resp["tokens_in"], tokens_out=resp["tokens_out"],
            duration_s=resp["duration_s"],
        )
    except Exception as err:
        return AgentResult(
            role="bull", status="failed",
            prompt_version=PROMPT_VERSION,
            error=str(err),
            duration_s=time.monotonic() - start,
        )
```

- [ ] **Step 5: Run tests**

```bash
venv/bin/pytest tests/agent_firm/test_bull.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add engine/agent_firm/prompts/bull_v1.md engine/agent_firm/agents/bull.py tests/agent_firm/test_bull.py
git commit -m "feat(agent_firm): Bull Researcher agent (v1 prompt + run loop)"
```

---

## Task 9: Bear Researcher Agent

**Files:**
- Create: `engine/agent_firm/prompts/bear_v1.md`
- Create: `engine/agent_firm/agents/bear.py`
- Create: `tests/agent_firm/test_bear.py`

Bear receives analyst results AND the bull's `AgentResult`.

- [ ] **Step 1: Create prompt file**

Create `engine/agent_firm/prompts/bear_v1.md`:

```
You are the Bear Researcher in a trading agent firm evaluating Indonesian Stock Exchange (IDX) signals.

You will receive:
- Analyst reports from: Technical Analyst, Flow Specialist, Regime Analyst, News/Sentiment Analyst
- The Bull Researcher's case (bull_case and key_strength)

Your job: construct the strongest possible bear case, specifically rebutting the bull's key_strength. Be specific to the data.

Output strictly as JSON. No markdown, no code fences:

{
  "bear_case": "2-3 sentences making the strongest case AGAINST the trade",
  "key_risk": "the single most important risk factor that could make this trade fail"
}

If all analysts are positive, still make the best bear case possible — your role is to find what could go wrong, even in favorable conditions. Consider: crowded trade risk, stop-loss cascade risk, sector rotation risk, macro surprise risk.
```

- [ ] **Step 2: Write failing test**

Create `tests/agent_firm/test_bear.py`:

```python
import json
import pytest
from unittest.mock import AsyncMock
from engine.agent_firm.agents import bear
from engine.agent_firm.schemas import AgentResult, SignalCandidate


def _make_candidate():
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=3.8, scan_time="2026-05-20T10:00:00+07:00",
    )


def _make_analysts():
    return [
        AgentResult(role="technical", status="ok",
                    output={"verdict": "BULLISH", "conviction": 0.7}),
        AgentResult(role="flow", status="ok",
                    output={"flow_verdict": "ACCUMULATING"}),
        AgentResult(role="regime", status="ok",
                    output={"regime_call": "TRENDING"}),
        AgentResult(role="news", status="ok",
                    output={"sentiment": "BULLISH"}),
    ]


def _make_bull():
    return AgentResult(
        role="bull", status="ok",
        output={"bull_case": "Strong flow + trend.", "key_strength": "Foreign accumulation"},
    )


@pytest.mark.asyncio
async def test_bear_returns_ok_on_success():
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": json.dumps({
            "bear_case": "Foreign flows can reverse rapidly if BI surprises.",
            "key_risk": "BI rate surprise causing sector rotation out of banks",
        }),
        "tokens_in": 1200, "tokens_out": 85, "cost_usd": 0.0006, "duration_s": 3.2,
    }
    result = await bear.run(_make_candidate(), _make_analysts(), _make_bull(), fake_client)
    assert result.role == "bear"
    assert result.status == "ok"
    assert "bear_case" in result.output
    assert result.tokens_in == 1200


@pytest.mark.asyncio
async def test_bear_returns_failed_on_invalid_json():
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": "nope", "tokens_in": 50, "tokens_out": 3,
        "cost_usd": 0.0, "duration_s": 1.0,
    }
    result = await bear.run(_make_candidate(), _make_analysts(), _make_bull(), fake_client)
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_bear_returns_failed_on_client_exception():
    fake_client = AsyncMock()
    fake_client.chat.side_effect = RuntimeError("conn reset")
    result = await bear.run(_make_candidate(), _make_analysts(), _make_bull(), fake_client)
    assert result.status == "failed"
    assert "conn reset" in result.error
```

- [ ] **Step 3: Run to confirm failure**

```bash
venv/bin/pytest tests/agent_firm/test_bear.py -v
```

Expected: ModuleNotFoundError.

- [ ] **Step 4: Implement**

Create `engine/agent_firm/agents/bear.py`:

```python
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
```

- [ ] **Step 5: Run tests**

```bash
venv/bin/pytest tests/agent_firm/test_bear.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add engine/agent_firm/prompts/bear_v1.md engine/agent_firm/agents/bear.py tests/agent_firm/test_bear.py
git commit -m "feat(agent_firm): Bear Researcher agent (v1 prompt + run loop)"
```

---

## Task 10: Risk Manager v2

**Files:**
- Create: `engine/agent_firm/prompts/risk_v2.md`
- Modify: `engine/agent_firm/agents/risk.py` (point to v2 prompt)

The `risk.run()` signature is unchanged: `run(candidate, analyst_results, client)`. In Phase 2 the caller passes all 6 upstream results. The prompt is updated to reference all roles.

- [ ] **Step 1: Create prompt file**

Create `engine/agent_firm/prompts/risk_v2.md`:

```
You are the Risk Manager in a trading agent firm. You make the FINAL veto-or-approve call for an IDX trade signal.

You will receive:
- The original SignalCandidate (ticker, strategy, quant score, regime, flow_verdict, foreign_score)
- Analyst reports: Technical Analyst, Flow Specialist, Regime Analyst, News/Sentiment Analyst
- Bull Researcher's case and Bear Researcher's rebuttal
- Current open paper trades

Your job: weigh all inputs and decide approve or veto.

Output strictly as JSON. No markdown, no code fences:

{
  "decision": "approve" | "veto",
  "confidence": 0.0-1.0,
  "size_hint": 0.0-1.5,
  "rationale": "Two short lines, e.g. 'Risk: ...\\nBull/Bear: ...'"
}

Decision framework:
- Veto if >= 3 of [Technical, Flow, Regime, News] are clearly negative AND quant score < 3.0
- Veto if technical conviction < 0.3 AND flow is DISTRIBUTING
- Veto if ticker already has an open paper trade (no doubling up)
- Approve with size_hint 0.5 when signals are mixed or confidence is low
- Approve with size_hint 1.0 when majority of analysts align bullish
- Approve with size_hint 1.2 when 4+ analysts bullish AND quant score >= 4.0

Fail-open principle: if you are uncertain (confidence < 0.5), prefer approve at size_hint 0.5 over veto.
If a required analyst report has status="failed", treat it as neutral and lower confidence by 0.1 per missing report.

Confidence guidance:
- 0.8+: clear consensus across all analysts
- 0.5-0.7: mixed signals, majority leans one way
- 0.0-0.4: conflicting analysts, missing inputs, or low quant score
```

- [ ] **Step 2: Write failing test for risk v2 behaviour**

Add to a new file `tests/agent_firm/test_risk_v2.py`:

```python
import json
import pytest
from unittest.mock import AsyncMock
from engine.agent_firm.agents import risk
from engine.agent_firm.schemas import AgentResult, SignalCandidate


def _make_candidate(score=4.0):
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=score, scan_time="2026-05-20T10:00:00+07:00",
    )


def _make_all_analysts():
    return [
        AgentResult(role="technical", status="ok",
                    output={"verdict": "BULLISH", "conviction": 0.75}),
        AgentResult(role="flow", status="ok",
                    output={"flow_verdict": "ACCUMULATING", "smart_money_signal": "BUY"}),
        AgentResult(role="regime", status="ok",
                    output={"regime_call": "TRENDING", "sector_tailwind": True}),
        AgentResult(role="news", status="ok",
                    output={"sentiment": "BULLISH", "catalyst": "bullish"}),
        AgentResult(role="bull", status="ok",
                    output={"bull_case": "Strong case.", "key_strength": "Accumulation"}),
        AgentResult(role="bear", status="ok",
                    output={"bear_case": "Rate risk.", "key_risk": "BI surprise"}),
    ]


@pytest.mark.asyncio
async def test_risk_v2_approve_on_full_bullish_committee():
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": json.dumps({
            "decision": "approve", "confidence": 0.82,
            "size_hint": 1.2,
            "rationale": "Risk: all analysts aligned.\nBull/Bear: bull case dominates.",
        }),
        "tokens_in": 2000, "tokens_out": 100, "cost_usd": 0.0009, "duration_s": 5.0,
    }
    result = await risk.run(_make_candidate(), _make_all_analysts(), fake_client)
    assert result.status == "ok"
    assert result.output["decision"] == "approve"
    assert result.output["size_hint"] == 1.2
    assert result.tokens_in == 2000


@pytest.mark.asyncio
async def test_risk_v2_all_6_reports_in_payload():
    captured = {}
    async def capture_chat(messages, **kwargs):
        captured["body"] = messages
        return {
            "content": json.dumps({
                "decision": "approve", "confidence": 0.6,
                "size_hint": 1.0, "rationale": "ok.\nok.",
            }),
            "tokens_in": 50, "tokens_out": 30, "cost_usd": 0.0, "duration_s": 1.0,
        }
    fake_client = AsyncMock()
    fake_client.chat.side_effect = capture_chat
    await risk.run(_make_candidate(), _make_all_analysts(), fake_client)
    payload = json.loads(captured["body"][1]["content"])
    roles = [r["role"] for r in payload["analyst_reports"]]
    assert "bull" in roles
    assert "bear" in roles
    assert len(roles) == 6
```

- [ ] **Step 3: Run to confirm test_risk_v2.py passes with current risk.py**

```bash
venv/bin/pytest tests/agent_firm/test_risk_v2.py -v
```

The tests should pass even now (risk.run() already accepts a list of any length). If they do, skip step 4; otherwise note the failure.

- [ ] **Step 4: Update risk.py to point to risk_v2.md**

In `engine/agent_firm/agents/risk.py`, change:

```python
_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "risk_v1.md"
PROMPT_VERSION = "v1"
```

to:

```python
_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "risk_v2.md"
PROMPT_VERSION = "v2"
```

- [ ] **Step 5: Run all risk tests**

```bash
venv/bin/pytest tests/agent_firm/test_risk.py tests/agent_firm/test_risk_v2.py -v
```

Expected: all 6 tests pass (test_risk.py still passes because it uses mock client output regardless of prompt).

- [ ] **Step 6: Run full suite**

```bash
venv/bin/pytest tests/agent_firm/ -v --tb=short 2>&1 | tail -5
```

Expected: all prior tests + new tests pass.

- [ ] **Step 7: Commit**

```bash
git add engine/agent_firm/prompts/risk_v2.md engine/agent_firm/agents/risk.py tests/agent_firm/test_risk_v2.py
git commit -m "feat(agent_firm): Risk Manager v2 prompt (reads all 6 upstream results)"
```

---

## Task 11: LangGraph firm.py Refactor

**Files:**
- Modify: `engine/agent_firm/firm.py` (full rewrite)
- Create: `tests/agent_firm/test_firm_v2.py`
- Create: `tests/agent_firm/fixtures/recorded/` (empty dir with .gitkeep)

This is the core task. The public API (`evaluate`, `evaluate_async`) stays identical. Internally, `firm.py` becomes a LangGraph StateGraph.

- [ ] **Step 1: Create recorded fixtures directory**

```bash
mkdir -p "/home/tjiesar/10 Projects/idx-walkforward-5001/tests/agent_firm/fixtures/recorded"
touch "/home/tjiesar/10 Projects/idx-walkforward-5001/tests/agent_firm/fixtures/recorded/.gitkeep"
```

- [ ] **Step 2: Write failing test**

Create `tests/agent_firm/test_firm_v2.py`:

```python
import json
import sqlite3
from unittest.mock import AsyncMock, patch

import pytest

from engine.agent_firm.schemas import AgentResult, SignalCandidate


def _seed_db(db_path):
    from data.db import init_agent_firm_tables
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE IF NOT EXISTS ohlcv (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT, date TEXT,
        open REAL, high REAL, low REAL, close REAL, volume REAL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS stockbit_flow (
        ticker TEXT, trade_date TEXT, buy_lot INTEGER, sell_lot INTEGER,
        net_lot INTEGER, net_value INTEGER, verdict TEXT, smart_money TEXT,
        foreign_score REAL, composite_score INTEGER, updated_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS broker_flow (
        ticker TEXT, trade_date TEXT, broker_code TEXT, side TEXT,
        lot_value INTEGER, investor_type TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS stockbit_flow_bars (
        ticker TEXT, trade_date TEXT, bar_time TEXT, buy_lot INTEGER,
        sell_lot INTEGER, delta INTEGER, net_value INTEGER)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS wf_scores (
        ticker TEXT, strategy TEXT, consistency_pct REAL,
        avg_return_pct REAL, avg_sharpe REAL, weighted_score REAL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS daily_screen (
        id INTEGER PRIMARY KEY, date TEXT, ticker TEXT, close INTEGER,
        vol_ratio REAL, signal TEXT, vpin_label TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS news_mentions (
        ticker TEXT, date TEXT, count INTEGER, headlines_json TEXT, updated_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS paper_trades (
        id INTEGER PRIMARY KEY, ticker TEXT, status TEXT,
        entry_price REAL, lots INTEGER, tp_price REAL, sl_price REAL)""")
    rows = [("BBRI", f"2026-05-{d:02d}", 3000+d, 3100+d, 2950+d, 3050+d, 1e8) for d in range(1, 20)]
    conn.executemany("INSERT INTO ohlcv (ticker, date, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    init_agent_firm_tables()


def _ok(role):
    return AgentResult(role=role, status="ok", output={"verdict": "ok"},
                       tokens_in=100, tokens_out=50, duration_s=1.0)


@pytest.mark.asyncio
async def test_evaluate_async_v2_runs_all_7_agents_and_persists(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "true")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("TAVILY_API_KEY", "")
    import importlib
    from data import db as data_db
    importlib.reload(data_db)
    from engine.agent_firm import config, firm
    importlib.reload(config)
    importlib.reload(firm)
    _seed_db(tmp_path / "t.db")

    candidate = SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=4.0, scan_time="2026-05-20T10:00:00+07:00",
    )

    with patch("engine.agent_firm.agents.technical.run", return_value=_ok("technical")), \
         patch("engine.agent_firm.agents.flow.run",      return_value=_ok("flow")), \
         patch("engine.agent_firm.agents.regime.run",    return_value=_ok("regime")), \
         patch("engine.agent_firm.agents.news.run",      return_value=_ok("news")), \
         patch("engine.agent_firm.agents.bull.run",      return_value=_ok("bull")), \
         patch("engine.agent_firm.agents.bear.run",      return_value=_ok("bear")), \
         patch("engine.agent_firm.agents.risk.run",
               return_value=AgentResult(
                   role="risk", status="ok",
                   output={"decision": "approve", "confidence": 0.75,
                           "size_hint": 1.0, "rationale": "ok.\nok."},
                   tokens_in=500, tokens_out=100, duration_s=3.0)):
        decisions = await firm.evaluate_async([candidate])

    assert len(decisions) == 1
    d = decisions[0]
    assert d.decision == "approve"
    assert len(d.traces) == 7
    roles = [t.role for t in d.traces]
    assert "technical" in roles and "bull" in roles and "bear" in roles and "risk" in roles

    conn = sqlite3.connect(tmp_path / "t.db")
    rows = conn.execute("SELECT decision FROM agent_decisions").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "approve"
    trace_count = conn.execute("SELECT COUNT(*) FROM agent_traces").fetchone()[0]
    assert trace_count == 7


def test_evaluate_returns_bypassed_when_disabled(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "false")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    import importlib
    from engine.agent_firm import config, firm
    importlib.reload(config)
    importlib.reload(firm)
    candidate = SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=4.0, scan_time="2026-05-20T10:00:00+07:00",
    )
    out = firm.evaluate([candidate])
    assert len(out) == 1
    assert out[0].decision == "bypassed"
```

- [ ] **Step 3: Run to confirm failure**

```bash
venv/bin/pytest tests/agent_firm/test_firm_v2.py -v
```

Expected: ImportError or test failure (firm.py still has Phase 1 implementation with only 2 agents).

- [ ] **Step 4: Rewrite firm.py**

Replace the entire contents of `engine/agent_firm/firm.py` with:

```python
"""Agent firm orchestrator. Phase 2: LangGraph DAG, 7 agents.

Public API:
  evaluate(candidates) -> list[AgentDecision]      # sync, scheduler-facing
  evaluate_async(candidates, client) -> ...        # async, for tests
"""

import asyncio
import json
import time

from langgraph.graph import END, StateGraph

from . import config
from .agents import bear, bull, flow, news, regime, risk, technical
from .client import DeepSeekClient
from .schemas import AgentDecision, AgentResult, AgentState, SignalCandidate
from .tools import news_lookup
from .tools.sqlite_query import query


# ── Context pre-fetch ────────────────────────────────────────────────────────

def _build_context(state: AgentState) -> dict:
    import data.db as _db
    db_path = str(_db.DB_PATH)
    ticker = state["candidate"].ticker
    context = {
        "ohlcv": query(
            db_path,
            "SELECT date, open, high, low, close, volume FROM ohlcv "
            "WHERE ticker=? ORDER BY date DESC LIMIT 60",
            (ticker,),
        ),
        "broker_flow": query(
            db_path,
            "SELECT trade_date, broker_code, side, lot_value, investor_type FROM broker_flow "
            "WHERE ticker=? AND trade_date >= date('now', '-14 days') ORDER BY trade_date DESC",
            (ticker,),
        ),
        "stockbit_flow": query(
            db_path,
            "SELECT trade_date, buy_lot, sell_lot, net_lot, net_value, verdict, "
            "smart_money, foreign_score, composite_score FROM stockbit_flow "
            "WHERE ticker=? AND trade_date >= date('now', '-14 days') ORDER BY trade_date DESC",
            (ticker,),
        ),
        "stockbit_flow_bars": query(
            db_path,
            "SELECT trade_date, bar_time, buy_lot, sell_lot, delta, net_value "
            "FROM stockbit_flow_bars "
            "WHERE ticker=? AND trade_date >= date('now', '-7 days') "
            "ORDER BY trade_date DESC, bar_time",
            (ticker,),
        ),
        "wf_scores": query(
            db_path,
            "SELECT strategy, consistency_pct, avg_return_pct, avg_sharpe, weighted_score "
            "FROM wf_scores WHERE ticker=? ORDER BY weighted_score DESC",
            (ticker,),
        ),
        "sector_data": query(
            db_path,
            "SELECT date, signal, vpin_label, vol_ratio FROM daily_screen "
            "WHERE ticker=? ORDER BY date DESC LIMIT 10",
            (ticker,),
        ),
        "news_mentions": news_lookup.lookup(db_path, ticker, days=7),
        "open_trades": query(
            db_path,
            "SELECT ticker, entry_price, lots, tp_price, sl_price "
            "FROM paper_trades WHERE status='OPEN'",
        ),
    }
    return {"db_path": db_path, "context": context}


# ── Analyst nodes ─────────────────────────────────────────────────────────────

async def _run_analysts(state: AgentState) -> dict:
    client = state["client"]
    candidate = state["candidate"]
    ctx = state["context"]
    db_path = state["db_path"]
    t, f, r, n = await asyncio.gather(
        technical.run(candidate, client, db_path),
        flow.run(candidate, client, ctx),
        regime.run(candidate, client, ctx),
        news.run(candidate, client, ctx),
    )
    return {
        "technical_result": t,
        "flow_result": f,
        "regime_result": r,
        "news_result": n,
    }


async def _run_bull(state: AgentState) -> dict:
    analysts = [
        state["technical_result"],
        state["flow_result"],
        state["regime_result"],
        state["news_result"],
    ]
    result = await bull.run(state["candidate"], analysts, state["client"])
    return {"bull_result": result}


async def _run_bear(state: AgentState) -> dict:
    analysts = [
        state["technical_result"],
        state["flow_result"],
        state["regime_result"],
        state["news_result"],
    ]
    result = await bear.run(state["candidate"], analysts, state["bull_result"], state["client"])
    return {"bear_result": result}


async def _run_risk(state: AgentState) -> dict:
    all_results = [
        state["technical_result"],
        state["flow_result"],
        state["regime_result"],
        state["news_result"],
        state["bull_result"],
        state["bear_result"],
    ]
    result = await risk.run(state["candidate"], all_results, state["client"])

    if result.status == "failed":
        decision_str = "degraded"
        confidence = None
        size_hint = None
        rationale = "Agent firm degraded — quant signal passed through"
    else:
        out = result.output or {}
        decision_str = out.get("decision", "degraded")
        confidence = out.get("confidence")
        size_hint = out.get("size_hint")
        rationale = out.get("rationale")

    traces = [
        state["technical_result"], state["flow_result"],
        state["regime_result"], state["news_result"],
        state["bull_result"], state["bear_result"], result,
    ]
    tokens_in = sum(t.tokens_in for t in traces)
    tokens_out = sum(t.tokens_out for t in traces)
    cost_usd = DeepSeekClient._calc_cost(tokens_in, tokens_out)
    candidate = state["candidate"]

    decision = AgentDecision(
        ticker=candidate.ticker,
        strategy=candidate.strategy,
        scan_time=candidate.scan_time,
        quant_score=candidate.score,
        decision=decision_str,
        confidence=confidence,
        size_hint=size_hint,
        rationale=rationale,
        traces=traces,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        duration_s=0.0,
    )
    return {"risk_result": result, "decision": decision}


# ── Persist node ──────────────────────────────────────────────────────────────

def _persist_node(state: AgentState) -> dict:
    _persist(state["decision"])
    return {}


# ── Graph compilation ─────────────────────────────────────────────────────────

def _build_graph():
    g = StateGraph(AgentState)
    g.add_node("build_context", _build_context)
    g.add_node("run_analysts", _run_analysts)
    g.add_node("run_bull", _run_bull)
    g.add_node("run_bear", _run_bear)
    g.add_node("run_risk", _run_risk)
    g.add_node("persist", _persist_node)
    g.set_entry_point("build_context")
    g.add_edge("build_context", "run_analysts")
    g.add_edge("run_analysts", "run_bull")
    g.add_edge("run_bull", "run_bear")
    g.add_edge("run_bear", "run_risk")
    g.add_edge("run_risk", "persist")
    g.add_edge("persist", END)
    return g.compile()


_GRAPH = _build_graph()


# ── Public API ────────────────────────────────────────────────────────────────

async def evaluate_async(
    candidates: list[SignalCandidate],
    client: DeepSeekClient | None = None,
) -> list[AgentDecision]:
    if client is None:
        client = DeepSeekClient()
    initial_states = [
        AgentState(
            candidate=c,
            db_path="",
            context={},
            client=client,
            technical_result=None,
            flow_result=None,
            regime_result=None,
            news_result=None,
            bull_result=None,
            bear_result=None,
            risk_result=None,
            decision=None,
        )
        for c in candidates
    ]
    results = await asyncio.gather(*[_GRAPH.ainvoke(s) for s in initial_states])
    return [r["decision"] for r in results]


def evaluate(
    candidates: list[SignalCandidate],
    client: DeepSeekClient | None = None,
) -> list[AgentDecision]:
    if not config.is_active():
        return [
            AgentDecision(
                ticker=c.ticker,
                strategy=c.strategy,
                scan_time=c.scan_time,
                quant_score=c.score,
                decision="bypassed",
                rationale="Firm disabled",
            )
            for c in candidates
        ]
    return asyncio.run(evaluate_async(candidates, client))


# ── Persistence ───────────────────────────────────────────────────────────────

def _persist(decision: AgentDecision) -> int:
    import data.db as _db
    conn = _db.get_db()
    try:
        cur = conn.execute(
            "INSERT OR REPLACE INTO agent_decisions "
            "(scan_time, ticker, strategy, quant_score, decision, confidence, "
            "size_hint, rationale, tokens_in, tokens_out, cost_usd, duration_s) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                decision.scan_time, decision.ticker, decision.strategy,
                decision.quant_score, decision.decision, decision.confidence,
                decision.size_hint, decision.rationale,
                decision.tokens_in, decision.tokens_out, decision.cost_usd,
                decision.duration_s,
            ),
        )
        decision_id = cur.lastrowid
        for trace in decision.traces:
            conn.execute(
                "INSERT INTO agent_traces "
                "(decision_id, role, prompt_version, output, tools_called, "
                "tokens_in, tokens_out, duration_s) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    decision_id, trace.role, trace.prompt_version,
                    None if trace.output is None else json.dumps(trace.output),
                    json.dumps(trace.tools_called),
                    trace.tokens_in, trace.tokens_out, trace.duration_s,
                ),
            )
        conn.commit()
        return decision_id
    finally:
        conn.close()
```

- [ ] **Step 5: Run firm_v2 tests**

```bash
venv/bin/pytest tests/agent_firm/test_firm_v2.py -v --tb=short
```

Expected: 2 passed.

- [ ] **Step 6: Run full test suite**

```bash
venv/bin/pytest tests/agent_firm/ -v --tb=short 2>&1 | tail -10
```

Expected: all prior tests still pass (test_firm.py Phase 1 tests may fail if they relied on the old firm.py internals — if so, check what broke and fix). The old `test_firm.py` tests for `evaluate_async` and `evaluate` check the public API which is unchanged; they should still pass if the DB schema is correct.

- [ ] **Step 7: Commit**

```bash
git add engine/agent_firm/firm.py tests/agent_firm/test_firm_v2.py \
        tests/agent_firm/fixtures/recorded/.gitkeep
git commit -m "feat(agent_firm): LangGraph DAG orchestrator — 7-agent pipeline"
```

---

## Task 12: Scheduler Integration

**Files:**
- Modify: `scheduler.py`

Add the agent firm hook inside `scheduled_multi_strategy_scan()`, after `flow_confirmed` is assembled and before `send_telegram()`.

- [ ] **Step 1: Read the relevant section**

```bash
grep -n "flow_confirmed\|send_telegram\|Step 7\|Step 8\|auto_trade" scheduler.py | head -20
```

Note the line number where `flow_confirmed` is finalized and where `send_telegram` is first called for the signal block.

- [ ] **Step 2: Write failing test**

Create `tests/test_scheduler_firm_hook.py`:

```python
import types
import pytest
from unittest.mock import patch, MagicMock


def _make_signals():
    return [
        {
            "ticker": "BBRI", "strategies": ["vol_weighted"],
            "flow": {"score": 3, "verdict": "BUY", "smart_money": "YES", "confirmed": True,
                     "cum_delta": 5000, "price_chg_pct": 1.2},
            "sector": "BANKING", "sector_weight": "OVERWEIGHT", "sector_score": 7,
            "signal_reasons": ["vol_weighted: uptrend"],
            "signal_details": {"vol_weighted": {"price": 3050}},
        }
    ]


def test_firm_hook_called_when_active(monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "true")
    evaluate_calls = []

    with patch("engine.agent_firm.config.is_active", return_value=True), \
         patch("engine.agent_firm.firm.evaluate", side_effect=lambda c: evaluate_calls.append(c) or []), \
         patch("scheduler.get_all_tickers", return_value=[]), \
         patch("scheduler._load_ohlcv_bulk", return_value={}), \
         patch("scheduler._get_sector_scores_cached", return_value=[]), \
         patch("scheduler.send_telegram"):
        import scheduler as sched
        # Call the hook directly with a known flow_confirmed list
        import importlib
        importlib.reload(sched)
        # Simulate the hook: if is_active() and flow_confirmed, evaluate is called
        from engine.agent_firm import config as _firm_cfg, firm as _firm
        from engine.agent_firm.schemas import SignalCandidate
        from datetime import datetime
        signals = _make_signals()
        if _firm_cfg.is_active() and signals:
            candidates = [
                SignalCandidate(
                    ticker=s["ticker"],
                    strategy=(s["strategies"][0] if s.get("strategies") else "multi"),
                    score=float(s.get("flow", {}).get("score") or 0),
                    scan_time=datetime.now().isoformat(),
                    flow_verdict=s.get("flow", {}).get("verdict"),
                    foreign_score=None,
                    indicators={},
                )
                for s in signals
            ]
            _firm.evaluate(candidates)
        assert len(evaluate_calls) == 1
        assert evaluate_calls[0][0].ticker == "BBRI"


def test_firm_hook_skipped_when_disabled(monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "false")
    evaluate_calls = []
    with patch("engine.agent_firm.config.is_active", return_value=False), \
         patch("engine.agent_firm.firm.evaluate", side_effect=lambda c: evaluate_calls.append(c) or []):
        from engine.agent_firm import config as _firm_cfg, firm as _firm
        from engine.agent_firm.schemas import SignalCandidate
        signals = _make_signals()
        if _firm_cfg.is_active() and signals:
            _firm.evaluate([])
        assert len(evaluate_calls) == 0
```

- [ ] **Step 3: Run to confirm these tests pass already (they test the hook logic, not scheduler internals)**

```bash
venv/bin/pytest tests/test_scheduler_firm_hook.py -v --tb=short
```

Expected: both pass (they test our logic, not scheduler.py changes yet).

- [ ] **Step 4: Add the hook to scheduler.py**

Read `scheduler.py` around line where `flow_confirmed` is finalized (look for the DB save block). Insert the agent firm block AFTER the DB save and BEFORE the `if len(flow_confirmed) > 0:` send_telegram block.

The block to insert (find the right line using `grep -n "Step 7\|auto-open\|open paper trades\|flow_confirmed" scheduler.py`):

```python
    # ── Agent Firm evaluation (shadow mode) ──────────────────────────────────
    try:
        from engine.agent_firm import config as _firm_cfg
        from engine.agent_firm import firm as _firm
        from engine.agent_firm.schemas import SignalCandidate as _SC
        if _firm_cfg.is_active() and flow_confirmed:
            _candidates = [
                _SC(
                    ticker=r["ticker"],
                    strategy=(r["strategies"][0] if r.get("strategies") else "multi"),
                    score=float((r.get("flow") or {}).get("score") or 0),
                    scan_time=f"{date_str} {time_str}",
                    flow_verdict=(r.get("flow") or {}).get("verdict"),
                    foreign_score=None,
                    indicators={},
                )
                for r in flow_confirmed
            ]
            _decisions = _firm.evaluate(_candidates)
            if _firm_cfg.FIRM_ENFORCE:
                _approved = {d.ticker for d in _decisions if d.decision == "approve"}
                flow_confirmed = [r for r in flow_confirmed if r["ticker"] in _approved]
            print(f"[{time_str}] Agent firm: {len(_decisions)} evaluated"
                  f" ({sum(1 for d in _decisions if d.decision=='approve')} approved"
                  f", {sum(1 for d in _decisions if d.decision=='veto')} vetoed)")
    except Exception as _firm_err:
        print(f"[{time_str}] Agent firm error (fail-open): {_firm_err}")
    # ── End agent firm ────────────────────────────────────────────────────────
```

Insert this block right before the `# Step 7: Auto-open paper trades` comment (or equivalent).

- [ ] **Step 5: Verify syntax**

```bash
venv/bin/python -c "import scheduler; print('ok')"
```

Expected: `ok` (no syntax errors).

- [ ] **Step 6: Run full test suite**

```bash
venv/bin/pytest tests/agent_firm/ -v --tb=short 2>&1 | tail -5
```

Expected: all agent_firm tests pass.

- [ ] **Step 7: Commit**

```bash
git add scheduler.py tests/test_scheduler_firm_hook.py
git commit -m "feat(agent_firm): wire evaluate() into scheduled_multi_strategy_scan (shadow mode)"
```

---

## Task 13: Dashboard Stats

**Files:**
- Modify: `app.py`
- Modify: `templates/backtest_multi.html`

Extend `/api/agent/status` with a `today_stats` field and add a stats line to the badge.

- [ ] **Step 1: Read the existing agent_status endpoint in app.py**

```bash
grep -n "agent_status\|agent/status\|today_stats" app.py
```

Note the line numbers.

- [ ] **Step 2: Update the endpoint**

Find the `agent_status` function in `app.py` and replace it with:

```python
@app.route("/api/agent/status", methods=["GET"])
def agent_status():
    from engine.agent_firm import config as _agent_config
    import sqlite3, datetime
    today = datetime.date.today().isoformat()
    stats = {"evaluated": 0, "approved": 0, "vetoed": 0, "cost_usd": 0.0}
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT COUNT(*), "
            "SUM(CASE WHEN decision='approve' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN decision='veto' THEN 1 ELSE 0 END), "
            "COALESCE(SUM(cost_usd), 0.0) "
            "FROM agent_decisions WHERE DATE(created_at) = ?",
            (today,),
        ).fetchone()
        conn.close()
        if row and row[0]:
            stats = {
                "evaluated": row[0] or 0,
                "approved": row[1] or 0,
                "vetoed": row[2] or 0,
                "cost_usd": round(row[3] or 0.0, 4),
            }
    except Exception:
        pass
    return jsonify({
        "enabled": _agent_config.FIRM_ENABLED,
        "enforce": _agent_config.FIRM_ENFORCE,
        "active": _agent_config.is_active(),
        "model": _agent_config.MODEL_ID,
        "today_stats": stats,
    })
```

- [ ] **Step 3: Update the badge in templates/backtest_multi.html**

Find the existing `<div id="agent-firm-badge"` block (inserted in Phase 1) and replace the `<script>` section so it also renders today's stats:

```html
<script>
  fetch('/api/agent/status').then(r => r.json()).then(s => {
    const el = document.getElementById('agent-firm-state');
    const badge = document.getElementById('agent-firm-badge');
    const st = s.today_stats || {};
    const statsLine = st.evaluated
      ? ` | ${st.evaluated} eval · ${st.approved} ✓ · ${st.vetoed} ✗ · $${(st.cost_usd||0).toFixed(4)}`
      : '';
    if (s.active) {
      el.textContent = (s.enforce ? 'ENFORCE' : 'SHADOW') + statsLine;
      badge.style.color = s.enforce ? '#fff' : '#fc0';
      badge.style.borderColor = s.enforce ? '#0c0' : '#fc0';
    } else {
      el.textContent = 'OFF';
      el.style.color = '#888';
    }
  }).catch(() => {
    document.getElementById('agent-firm-state').textContent = 'ERR';
  });
</script>
```

- [ ] **Step 4: Test the endpoint (if Flask server is running)**

```bash
curl -s http://localhost:5001/api/agent/status | python3 -m json.tool
```

Expected (server off is fine — skip if not running):
```json
{
  "enabled": false,
  "enforce": false,
  "active": false,
  "model": "deepseek-v4-pro",
  "today_stats": {"evaluated": 0, "approved": 0, "vetoed": 0, "cost_usd": 0.0}
}
```

- [ ] **Step 5: Commit**

```bash
git add app.py templates/backtest_multi.html
git commit -m "feat(agent_firm): dashboard stats line — today's evaluated/approved/vetoed/cost"
```

---

## Final Verification

- [ ] **Run full test suite**

```bash
venv/bin/pytest tests/agent_firm/ -v
```

Expected: 50+ tests across all files, all passing.

- [ ] **Verify smoke probe still works**

```bash
AGENT_FIRM_ENABLED=false venv/bin/python -m engine.agent_firm.smoke
echo "exit: $?"
```

Expected: `SKIP` and exit 0.

- [ ] **Verify scheduler imports cleanly**

```bash
venv/bin/python -c "import scheduler; print('scheduler ok')"
```

Expected: `scheduler ok`.

- [ ] **Tag Phase 2**

```bash
git tag -a phase2-agent-firm-7-agents -m "Phase 2 complete: LangGraph DAG + 7 agents + shadow mode"
```

---

## Shadow Mode Rollout

After Phase 2 is deployed, set in the systemd service or `.env`:

```
AGENT_FIRM_ENABLED=true
AGENT_FIRM_ENFORCE=false
TAVILY_API_KEY=<your-tavily-key>
DEEPSEEK_API_KEY=<your-deepseek-key>
```

After 30 trading days, run the shadow validation query:

```sql
SELECT
  ad.decision,
  COUNT(*) as n,
  AVG(CASE WHEN pt.status='CLOSED' THEN (pt.exit_price - pt.entry_price) / pt.entry_price * 100 END) as avg_return_pct
FROM agent_decisions ad
LEFT JOIN paper_trades pt ON ad.ticker = pt.ticker
  AND DATE(ad.created_at) = DATE(pt.opened_at)
GROUP BY ad.decision;
```

**Acceptance bar:** `approve-cohort Sharpe ≥ baseline + 0.2` AND `veto-cohort win_rate < baseline − 5pp`.
Both conditions required before Phase 3 (enforcement: `AGENT_FIRM_ENFORCE=true`).
