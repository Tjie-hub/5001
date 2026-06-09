# Agent Firm Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the agent firm scaffolding with 2 agents (Technical Analyst + Risk Manager) end-to-end, gated by `FIRM_ENABLED=false` so production behavior is unchanged. Smoke probe proves plumbing works against live DeepSeek V4 Pro within 90s.

**Architecture:** New `engine/agent_firm/` package. Pydantic schemas, DeepSeek client (OpenAI-compatible), read-only SQLite tool, two LLM agents, asyncio orchestrator, SQLite persistence of decisions and traces.

**Deviation from spec:** The spec called for LangGraph in Phase 1. This plan defers LangGraph to Phase 2 because at 2 agents with a linear flow (Technical → Risk), a DAG library adds dependencies + a learning curve with zero payoff. LangGraph slots in cleanly when Phase 2 adds parallel analysts + Bull/Bear debate. If you prefer literal spec compliance, add a Task 10.5 to wrap the linear pipeline as a 2-node LangGraph DAG — the orchestrator code is small enough to swap without churn.

**Tech Stack:** Python 3.12, asyncio, pydantic v2, openai (Python SDK), respx (test mocks), pytest, sqlite3 (stdlib), Flask (existing).

**Reference spec:** `docs/superpowers/specs/2026-05-19-agent-firm-hybrid-stack-design.md`

---

## File Structure

**Created:**
- `engine/agent_firm/__init__.py` — re-exports `evaluate`, `SignalCandidate`, `AgentDecision`
- `engine/agent_firm/config.py` — env-var-driven config + kill switches
- `engine/agent_firm/schemas.py` — Pydantic models
- `engine/agent_firm/client.py` — `DeepSeekClient` (async)
- `engine/agent_firm/firm.py` — orchestrator + `evaluate()` + `_persist()`
- `engine/agent_firm/smoke.py` — Tier 4 daily probe
- `engine/agent_firm/agents/__init__.py`
- `engine/agent_firm/agents/technical.py`
- `engine/agent_firm/agents/risk.py`
- `engine/agent_firm/tools/__init__.py`
- `engine/agent_firm/tools/sqlite_query.py`
- `engine/agent_firm/prompts/technical_v1.md`
- `engine/agent_firm/prompts/risk_v1.md`
- `tests/agent_firm/__init__.py`
- `tests/agent_firm/conftest.py`
- `tests/agent_firm/fixtures/seed_walkforward.sql`
- `tests/agent_firm/test_config.py`
- `tests/agent_firm/test_schemas.py`
- `tests/agent_firm/test_client.py`
- `tests/agent_firm/test_sqlite_query.py`
- `tests/agent_firm/test_technical.py`
- `tests/agent_firm/test_risk.py`
- `tests/agent_firm/test_firm.py`

**Modified:**
- `requirements.txt` — add openai, pydantic, respx, pytest, pytest-asyncio
- `data/db.py` — add `init_agent_firm_tables()` and call from `init_db()`
- `app.py` — add `/api/agent/status` Flask endpoint
- `templates/backtest_multi.html` — add small badge fetching `/api/agent/status`

---

## Conventions

- **Working directory:** `/home/tjiesar/10 Projects/idx-walkforward-5001`
- **Python:** use the project venv: `venv/bin/python` and `venv/bin/pip` (or `source venv/bin/activate` then `python`/`pip`)
- **Test runner:** `venv/bin/pytest tests/agent_firm/ -v`
- **Env vars in tests:** set via `monkeypatch.setenv()`; never modify the shell environment
- **TDD:** every task is failing-test → minimal impl → passing test → commit. Run the failing test first; if it passes accidentally, the test is wrong.
- **Commit cadence:** one commit per task minimum. Use `feat:` for new code, `test:` for test-only commits, `chore:` for deps/migrations.

---

## Task 1: Add Python Dependencies

**Files:**
- Modify: `requirements.txt`

- [x] **Step 1: Read current requirements**

```bash
cat requirements.txt
```

Expected: shows existing deps (Flask, pandas, etc.)

- [x] **Step 2: Append new deps**

Append these lines to `requirements.txt`:

```
openai>=1.40.0
pydantic>=2.6.0
respx>=0.21.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
```

- [x] **Step 3: Install into venv**

```bash
venv/bin/pip install -r requirements.txt
```

Expected: installs the new packages; no errors.

- [x] **Step 4: Verify imports**

```bash
venv/bin/python -c "import openai, pydantic, respx, pytest, httpx; print('ok')"
```

Expected output: `ok`

- [x] **Step 5: Commit**

```bash
git add requirements.txt
git commit -m "chore(agent_firm): add openai, pydantic, respx, pytest deps"
```

---

## Task 2: Module Skeleton

**Files:**
- Create: `engine/agent_firm/__init__.py`
- Create: `engine/agent_firm/agents/__init__.py`
- Create: `engine/agent_firm/tools/__init__.py`
- Create: `engine/agent_firm/prompts/` (directory only — gitignored if empty, so add a `.gitkeep`)
- Create: `tests/agent_firm/__init__.py`
- Create: `tests/agent_firm/fixtures/.gitkeep`

- [x] **Step 1: Make directories**

```bash
mkdir -p engine/agent_firm/agents engine/agent_firm/tools engine/agent_firm/prompts \
         tests/agent_firm/fixtures
```

- [x] **Step 2: Create `engine/agent_firm/__init__.py`**

```python
"""Agent firm: multi-agent LLM veto-gate for IDX signals.

Phase 1: 2 agents (Technical, Risk). Gated by AGENT_FIRM_ENABLED env var.
See docs/superpowers/specs/2026-05-19-agent-firm-hybrid-stack-design.md.
"""

from .schemas import SignalCandidate, AgentDecision, AgentResult
from .firm import evaluate

__all__ = ["SignalCandidate", "AgentDecision", "AgentResult", "evaluate"]
```

- [x] **Step 3: Create empty `__init__.py` files**

`engine/agent_firm/agents/__init__.py`:
```python
```

`engine/agent_firm/tools/__init__.py`:
```python
```

`tests/agent_firm/__init__.py`:
```python
```

- [x] **Step 4: Add `.gitkeep` files for empty dirs**

```bash
touch engine/agent_firm/prompts/.gitkeep tests/agent_firm/fixtures/.gitkeep
```

- [x] **Step 5: Commit**

Note: `__init__.py` re-exports schemas and firm.evaluate which don't exist yet — this is expected. We're committing the skeleton; later tasks fill it in. The import lines will be removed temporarily in step 6.

Replace the body of `engine/agent_firm/__init__.py` with just the docstring for now (the imports break since target files don't exist yet):

```python
"""Agent firm: multi-agent LLM veto-gate for IDX signals.

Phase 1: 2 agents (Technical, Risk). Gated by AGENT_FIRM_ENABLED env var.
See docs/superpowers/specs/2026-05-19-agent-firm-hybrid-stack-design.md.
"""
```

We will re-add the re-exports in Task 10 once the modules exist.

```bash
git add engine/agent_firm tests/agent_firm
git commit -m "feat(agent_firm): module skeleton"
```

---

## Task 3: Pydantic Schemas

**Files:**
- Create: `engine/agent_firm/schemas.py`
- Test: `tests/agent_firm/test_schemas.py`

- [x] **Step 1: Write the failing test**

Create `tests/agent_firm/test_schemas.py`:

```python
from engine.agent_firm.schemas import SignalCandidate, AgentResult, AgentDecision


def test_signal_candidate_minimal():
    c = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    assert c.ticker == "BBRI"
    assert c.regime is None
    assert c.indicators == {}


def test_signal_candidate_full():
    c = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
        regime="TRENDING", flow_verdict="STRONG_BUY",
        foreign_score=3.42, indicators={"vwma_above": True},
    )
    assert c.regime == "TRENDING"
    assert c.indicators["vwma_above"] is True


def test_agent_result_defaults():
    r = AgentResult(role="technical", status="ok")
    assert r.tokens_in == 0
    assert r.tokens_out == 0
    assert r.duration_s == 0.0
    assert r.tools_called == []
    assert r.error is None


def test_agent_decision_required_fields():
    d = AgentDecision(
        ticker="BBRI", strategy="momentum_following",
        scan_time="2026-05-19T16:00:00+07:00",
        quant_score=4.2, decision="approve",
    )
    assert d.decision == "approve"
    assert d.confidence is None
    assert d.traces == []


def test_agent_decision_rejects_invalid_decision():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AgentDecision(
            ticker="BBRI", strategy="momentum_following",
            scan_time="2026-05-19T16:00:00+07:00",
            quant_score=4.2, decision="maybe",
        )
```

- [x] **Step 2: Run test to verify it fails**

```bash
venv/bin/pytest tests/agent_firm/test_schemas.py -v
```

Expected: ImportError or ModuleNotFoundError on `engine.agent_firm.schemas`.

- [x] **Step 3: Write minimal implementation**

Create `engine/agent_firm/schemas.py`:

```python
"""Pydantic schemas for the agent firm.

Decision lifecycle:
  approve  — Risk Manager approved; signal proceeds to Telegram
  veto     — Risk Manager blocked; signal does not proceed (Phase 3+)
  bypassed — Firm was disabled or kill-switched; signal proceeds unevaluated
  degraded — Risk Manager call failed; signal proceeds (fail-open)
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class SignalCandidate(BaseModel):
    ticker: str
    strategy: str
    score: float
    scan_time: str
    regime: Optional[str] = None
    flow_verdict: Optional[str] = None
    foreign_score: Optional[float] = None
    indicators: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    role: str
    status: Literal["ok", "failed"]
    output: Optional[dict[str, Any]] = None
    prompt_version: str = "v1"
    tokens_in: int = 0
    tokens_out: int = 0
    duration_s: float = 0.0
    tools_called: list[dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class AgentDecision(BaseModel):
    ticker: str
    strategy: str
    scan_time: str
    quant_score: float
    decision: Literal["approve", "veto", "bypassed", "degraded"]
    confidence: Optional[float] = None
    size_hint: Optional[float] = None
    rationale: Optional[str] = None
    traces: list[AgentResult] = Field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    duration_s: float = 0.0
```

- [x] **Step 4: Run test to verify it passes**

```bash
venv/bin/pytest tests/agent_firm/test_schemas.py -v
```

Expected: 5 passed.

- [x] **Step 5: Commit**

```bash
git add engine/agent_firm/schemas.py tests/agent_firm/test_schemas.py
git commit -m "feat(agent_firm): pydantic schemas for candidate/result/decision"
```

---

## Task 4: Config Module

**Files:**
- Create: `engine/agent_firm/config.py`
- Test: `tests/agent_firm/test_config.py`

- [x] **Step 1: Write the failing test**

Create `tests/agent_firm/test_config.py`:

```python
import importlib
import os
from pathlib import Path

import pytest


def reload_config():
    from engine.agent_firm import config
    return importlib.reload(config)


def test_default_disabled(monkeypatch):
    monkeypatch.delenv("AGENT_FIRM_ENABLED", raising=False)
    cfg = reload_config()
    assert cfg.FIRM_ENABLED is False
    assert cfg.is_active() is False


def test_enabled_via_env(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "true")
    monkeypatch.setattr("engine.agent_firm.config.KILL_SWITCH_FILE", tmp_path / "missing")
    cfg = reload_config()
    monkeypatch.setattr(cfg, "KILL_SWITCH_FILE", tmp_path / "missing")
    assert cfg.FIRM_ENABLED is True
    assert cfg.is_active() is True


def test_kill_switch_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "true")
    kill = tmp_path / "agent_firm.disable"
    kill.write_text("")
    cfg = reload_config()
    monkeypatch.setattr(cfg, "KILL_SWITCH_FILE", kill)
    assert cfg.is_active() is False


def test_pricing_defaults(monkeypatch):
    monkeypatch.delenv("AGENT_FIRM_PRICE_IN", raising=False)
    monkeypatch.delenv("AGENT_FIRM_PRICE_OUT", raising=False)
    cfg = reload_config()
    assert cfg.PRICE_INPUT_PER_M == pytest.approx(0.435)
    assert cfg.PRICE_OUTPUT_PER_M == pytest.approx(0.870)
    assert cfg.MODEL_ID == "deepseek-v4-pro"
```

- [x] **Step 2: Run test to verify it fails**

```bash
venv/bin/pytest tests/agent_firm/test_config.py -v
```

Expected: ModuleNotFoundError on `engine.agent_firm.config`.

- [x] **Step 3: Write minimal implementation**

Create `engine/agent_firm/config.py`:

```python
"""Agent firm configuration via environment variables.

All settings have sensible defaults. The firm is OFF by default to ensure
Phase 1 production deploy has zero behavioral impact.
"""

import os
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


FIRM_ENABLED = _env_bool("AGENT_FIRM_ENABLED", False)
FIRM_ENFORCE = _env_bool("AGENT_FIRM_ENFORCE", False)

DAILY_SPEND_CAP_USD = float(os.getenv("AGENT_FIRM_DAILY_CAP", "5.0"))
KILL_SWITCH_FILE = Path(os.getenv("AGENT_FIRM_KILL_FILE", "/tmp/agent_firm.disable"))

MODEL_ID = os.getenv("AGENT_FIRM_MODEL", "deepseek-v4-pro")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

PRICE_INPUT_PER_M = float(os.getenv("AGENT_FIRM_PRICE_IN", "0.435"))
PRICE_OUTPUT_PER_M = float(os.getenv("AGENT_FIRM_PRICE_OUT", "0.870"))

PER_AGENT_TIMEOUT_S = float(os.getenv("AGENT_FIRM_AGENT_TIMEOUT", "45"))


def is_active() -> bool:
    if not FIRM_ENABLED:
        return False
    if KILL_SWITCH_FILE.exists():
        return False
    return True
```

- [x] **Step 4: Run test to verify it passes**

```bash
venv/bin/pytest tests/agent_firm/test_config.py -v
```

Expected: 4 passed.

- [x] **Step 5: Commit**

```bash
git add engine/agent_firm/config.py tests/agent_firm/test_config.py
git commit -m "feat(agent_firm): config module with env-driven kill switches"
```

---

## Task 5: SQLite Schema Migration

**Files:**
- Modify: `data/db.py`
- Test: extend `tests/agent_firm/conftest.py` (created here) and `tests/agent_firm/test_schemas.py` (no — keep separate)
- Test: `tests/agent_firm/test_migration.py`

- [x] **Step 1: Read current `data/db.py`**

```bash
venv/bin/python -c "from data import db; print(dir(db))"
```

Note location of `init_db()` and `get_db()`.

- [x] **Step 2: Write the failing test**

Create `tests/agent_firm/conftest.py`:

```python
"""Shared fixtures for agent_firm tests."""
import os
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Empty SQLite DB at a temp path with agent firm tables created."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    # Reload the data.db module so DB_PATH is picked up
    import importlib
    from data import db
    importlib.reload(db)
    db.init_db()
    yield db_path
```

Create `tests/agent_firm/test_migration.py`:

```python
import sqlite3


def test_agent_decisions_table_exists(tmp_db):
    conn = sqlite3.connect(tmp_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(agent_decisions)")}
    expected = {
        "id", "scan_time", "ticker", "strategy", "quant_score",
        "decision", "confidence", "size_hint", "rationale",
        "overridden", "tokens_in", "tokens_out", "cost_usd",
        "duration_s", "created_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_agent_traces_table_exists(tmp_db):
    conn = sqlite3.connect(tmp_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(agent_traces)")}
    expected = {
        "id", "decision_id", "role", "prompt_version",
        "output", "tools_called", "tokens_in", "tokens_out",
        "duration_s", "created_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_scheduled_signals_has_agent_decision_id(tmp_db):
    conn = sqlite3.connect(tmp_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(scheduled_signals)")}
    assert "agent_decision_id" in cols


def test_indexes_exist(tmp_db):
    conn = sqlite3.connect(tmp_db)
    idx = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert "idx_agent_decisions_ticker_date" in idx
    assert "idx_agent_traces_decision" in idx
```

- [x] **Step 3: Run test to verify it fails**

```bash
venv/bin/pytest tests/agent_firm/test_migration.py -v
```

Expected: failures because tables don't exist yet.

- [x] **Step 4: Modify `data/db.py` to add the migration**

Add this function to `data/db.py` (append after existing functions, before any `if __name__` block):

```python
def init_agent_firm_tables():
    """Idempotent migration for Phase 1 agent firm tables. Safe to call repeatedly."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agent_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT NOT NULL,
            ticker TEXT NOT NULL,
            strategy TEXT NOT NULL,
            quant_score REAL,
            decision TEXT NOT NULL,
            confidence REAL,
            size_hint REAL,
            rationale TEXT,
            overridden INTEGER DEFAULT 0,
            tokens_in INTEGER,
            tokens_out INTEGER,
            cost_usd REAL,
            duration_s REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(scan_time, ticker, strategy)
        );
        CREATE INDEX IF NOT EXISTS idx_agent_decisions_ticker_date
            ON agent_decisions(ticker, scan_time);

        CREATE TABLE IF NOT EXISTS agent_traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id INTEGER REFERENCES agent_decisions(id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            prompt_version TEXT,
            output TEXT,
            tools_called TEXT,
            tokens_in INTEGER,
            tokens_out INTEGER,
            duration_s REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_agent_traces_decision
            ON agent_traces(decision_id);

        CREATE TABLE IF NOT EXISTS scheduled_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT NOT NULL,
            ticker TEXT NOT NULL
        );
    """)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(scheduled_signals)")}
    if "agent_decision_id" not in cols:
        conn.execute(
            "ALTER TABLE scheduled_signals ADD COLUMN agent_decision_id INTEGER "
            "REFERENCES agent_decisions(id)"
        )
    conn.commit()
    conn.close()
```

Then modify the existing `init_db()` to call `init_agent_firm_tables()` at the end. Find the line in `init_db()` where the existing `conn.commit()` happens and append before/after the close:

In `data/db.py`, locate the `init_db()` function and append a call to `init_agent_firm_tables()` immediately after the existing `conn.commit()` and `conn.close()` calls in that function. If `init_db()` does not currently close `conn` before returning, add the call as the last line of `init_db()` before its `return` or end-of-function.

Concrete change: at the end of `init_db()` (after `conn.commit()` and `conn.close()`), add:

```python
    init_agent_firm_tables()
```

- [x] **Step 5: Run test to verify it passes**

```bash
venv/bin/pytest tests/agent_firm/test_migration.py -v
```

Expected: 4 passed.

- [x] **Step 6: Apply migration to dev DB**

```bash
venv/bin/python -c "from data.db import init_agent_firm_tables; init_agent_firm_tables(); print('migrated')"
```

Expected output: `migrated`

Confirm the dev DB now has the tables:

```bash
sqlite3 "data/walkforward.db" "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'agent_%';"
```

Expected output:
```
agent_decisions
agent_traces
```

- [x] **Step 7: Commit**

```bash
git add data/db.py tests/agent_firm/conftest.py tests/agent_firm/test_migration.py
git commit -m "feat(agent_firm): SQLite migration for agent_decisions, agent_traces"
```

---

## Task 6: sqlite_query Tool

**Files:**
- Create: `engine/agent_firm/tools/sqlite_query.py`
- Test: `tests/agent_firm/test_sqlite_query.py`

- [x] **Step 1: Write the failing test**

Create `tests/agent_firm/test_sqlite_query.py`:

```python
import sqlite3

import pytest

from engine.agent_firm.tools.sqlite_query import query


def _seed_ohlcv(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT, date TEXT, open REAL, high REAL,
            low REAL, close REAL, volume REAL
        )
    """)
    conn.executemany(
        "INSERT INTO ohlcv (ticker, date, open, high, low, close, volume) "
        "VALUES (?,?,?,?,?,?,?)",
        [
            ("BBRI", "2026-05-19", 5000, 5100, 4950, 5050, 1000000),
            ("BBRI", "2026-05-16", 4900, 5000, 4880, 5000, 950000),
            ("BMRI", "2026-05-19", 7000, 7100, 6950, 7080, 800000),
        ],
    )
    conn.commit()
    conn.close()


def test_query_returns_rows_as_dicts(tmp_path):
    db = tmp_path / "t.db"
    _seed_ohlcv(db)
    rows = query(db, "SELECT ticker, close FROM ohlcv WHERE ticker = ?", ("BBRI",))
    assert len(rows) == 2
    assert rows[0] == {"ticker": "BBRI", "close": 5050}


def test_query_rejects_non_select(tmp_path):
    db = tmp_path / "t.db"
    _seed_ohlcv(db)
    with pytest.raises(ValueError, match="SELECT"):
        query(db, "DELETE FROM ohlcv", ())


def test_query_rejects_select_with_destructive_chain(tmp_path):
    db = tmp_path / "t.db"
    _seed_ohlcv(db)
    with pytest.raises(ValueError):
        query(db, "  drop table ohlcv  ", ())


def test_query_with_no_params(tmp_path):
    db = tmp_path / "t.db"
    _seed_ohlcv(db)
    rows = query(db, "SELECT COUNT(*) AS c FROM ohlcv")
    assert rows[0]["c"] == 3
```

- [x] **Step 2: Run test to verify it fails**

```bash
venv/bin/pytest tests/agent_firm/test_sqlite_query.py -v
```

Expected: ModuleNotFoundError on `engine.agent_firm.tools.sqlite_query`.

- [x] **Step 3: Write minimal implementation**

Create `engine/agent_firm/tools/sqlite_query.py`:

```python
"""Read-only SQLite query tool exposed to agents.

Agents call this with a SELECT statement and parameters. Anything that is not
a SELECT raises ValueError — this is a defense-in-depth against prompt-injection
attempts that try to mutate state via the tool.
"""

import sqlite3
from pathlib import Path
from typing import Any


def query(db_path: Path | str, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    cleaned = sql.strip().upper()
    if not cleaned.startswith("SELECT"):
        raise ValueError(f"sqlite_query only allows SELECT statements, got: {sql[:80]!r}")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
```

- [x] **Step 4: Run test to verify it passes**

```bash
venv/bin/pytest tests/agent_firm/test_sqlite_query.py -v
```

Expected: 4 passed.

- [x] **Step 5: Commit**

```bash
git add engine/agent_firm/tools/sqlite_query.py tests/agent_firm/test_sqlite_query.py
git commit -m "feat(agent_firm): sqlite_query read-only tool"
```

---

## Task 7: DeepSeek Client Wrapper

**Files:**
- Create: `engine/agent_firm/client.py`
- Test: `tests/agent_firm/test_client.py`

- [x] **Step 1: Write the failing test**

Create `tests/agent_firm/test_client.py`:

```python
import httpx
import pytest
import respx

from engine.agent_firm.client import DeepSeekClient


@pytest.mark.asyncio
async def test_chat_returns_content_tokens_cost():
    client = DeepSeekClient(api_key="sk-test", base_url="https://api.test.com/v1", model="deepseek-v4-pro")
    with respx.mock(base_url="https://api.test.com/v1") as router:
        router.post("/chat/completions").mock(return_value=httpx.Response(
            200,
            json={
                "id": "test",
                "object": "chat.completion",
                "created": 0,
                "model": "deepseek-v4-pro",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            },
        ))
        result = await client.chat([{"role": "user", "content": "ping"}])
    assert result["content"] == "hi"
    assert result["tokens_in"] == 100
    assert result["tokens_out"] == 50
    assert result["cost_usd"] == pytest.approx((100 / 1_000_000 * 0.435) + (50 / 1_000_000 * 0.870), rel=1e-9)


@pytest.mark.asyncio
async def test_chat_retries_on_500_then_succeeds():
    client = DeepSeekClient(api_key="sk-test", base_url="https://api.test.com/v1")
    with respx.mock(base_url="https://api.test.com/v1") as router:
        route = router.post("/chat/completions")
        route.side_effect = [
            httpx.Response(500, json={"error": "server"}),
            httpx.Response(200, json={
                "id": "x", "object": "chat.completion", "created": 0,
                "model": "deepseek-v4-pro",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }),
        ]
        result = await client.chat([{"role": "user", "content": "ping"}])
    assert result["content"] == "ok"
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_chat_raises_after_retries_exhausted():
    client = DeepSeekClient(api_key="sk-test", base_url="https://api.test.com/v1")
    with respx.mock(base_url="https://api.test.com/v1") as router:
        router.post("/chat/completions").mock(return_value=httpx.Response(500, json={"error": "server"}))
        with pytest.raises(Exception):
            await client.chat([{"role": "user", "content": "ping"}], max_retries=1)


def test_cost_calc_zero_when_no_tokens():
    assert DeepSeekClient._calc_cost(0, 0) == 0.0
```

For `@pytest.mark.asyncio` to work without per-test boilerplate, create `pytest.ini` at the repo root:

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [x] **Step 2: Run test to verify it fails**

```bash
venv/bin/pytest tests/agent_firm/test_client.py -v
```

Expected: ModuleNotFoundError on `engine.agent_firm.client`.

- [x] **Step 3: Write minimal implementation**

Create `engine/agent_firm/client.py`:

```python
"""DeepSeek client wrapper. OpenAI SDK pointed at api.deepseek.com.

Adds:
- per-call timeout
- retry-once on 5xx / rate limit
- token + cost accounting on every call
"""

import asyncio
import time

from openai import AsyncOpenAI, APIError, RateLimitError, APIStatusError

from . import config


class DeepSeekClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.client = AsyncOpenAI(
            api_key=api_key or config.DEEPSEEK_API_KEY or "missing",
            base_url=base_url or config.DEEPSEEK_BASE_URL,
        )
        self.model = model or config.MODEL_ID

    async def chat(
        self,
        messages: list[dict],
        timeout: float | None = None,
        max_retries: int = 1,
    ) -> dict:
        timeout = timeout if timeout is not None else config.PER_AGENT_TIMEOUT_S
        start = time.monotonic()
        last_err: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                resp = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    timeout=timeout,
                )
                content = resp.choices[0].message.content
                usage = resp.usage
                tokens_in = getattr(usage, "prompt_tokens", 0) if usage else 0
                tokens_out = getattr(usage, "completion_tokens", 0) if usage else 0
                cost = self._calc_cost(tokens_in, tokens_out)
                return {
                    "content": content,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost_usd": cost,
                    "duration_s": time.monotonic() - start,
                }
            except (APIStatusError, APIError, RateLimitError) as err:
                last_err = err
                if attempt < max_retries:
                    await asyncio.sleep(4 * (2 ** attempt))
                    continue
                raise
        assert last_err is not None
        raise last_err

    @staticmethod
    def _calc_cost(tokens_in: int, tokens_out: int) -> float:
        return (
            tokens_in / 1_000_000 * config.PRICE_INPUT_PER_M
            + tokens_out / 1_000_000 * config.PRICE_OUTPUT_PER_M
        )
```

- [x] **Step 4: Run test to verify it passes**

```bash
venv/bin/pytest tests/agent_firm/test_client.py -v
```

Expected: 4 passed (test_chat_returns_content_tokens_cost, test_chat_retries_on_500_then_succeeds, test_chat_raises_after_retries_exhausted, test_cost_calc_zero_when_no_tokens).

- [x] **Step 5: Commit**

```bash
git add engine/agent_firm/client.py tests/agent_firm/test_client.py pytest.ini
git commit -m "feat(agent_firm): DeepSeek async client with cost tracking and retry"
```

---

## Task 8: Technical Analyst Agent

**Files:**
- Create: `engine/agent_firm/prompts/technical_v1.md`
- Create: `engine/agent_firm/agents/technical.py`
- Test: `tests/agent_firm/test_technical.py`

- [x] **Step 1: Write the prompt file**

Create `engine/agent_firm/prompts/technical_v1.md`:

```markdown
You are the Technical Analyst in a trading agent firm evaluating Indonesian Stock Exchange (IDX) signals.

You will receive:
- A SignalCandidate from a systematic strategy (ticker, strategy name, score, regime, foreign_score)
- Recent OHLCV data for the ticker (up to 60 daily bars, most recent first)

Your job: produce a technical conviction call and identify key support / resistance levels.

Output strictly as JSON. Do not include markdown, code fences, or commentary outside the JSON:

```json
{
  "verdict": "BULLISH" | "NEUTRAL" | "BEARISH",
  "conviction": 0.0-1.0,
  "key_levels": {"support": <float>, "resistance": <float>},
  "reasoning": "1-2 sentences explaining your call"
}
```

Conviction guidance:
- 0.8+: clear trend with confirmation (price above key MAs, volume support, no divergence)
- 0.5-0.7: mixed signals; one side has slight edge
- 0.0-0.4: signal is weak or contradicted by price action

If OHLCV data is insufficient (fewer than 10 bars), return verdict NEUTRAL with conviction 0.0 and reasoning "insufficient data".
```

- [x] **Step 2: Write the failing test**

Create `tests/agent_firm/test_technical.py`:

```python
import json
import sqlite3

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import technical
from engine.agent_firm.schemas import SignalCandidate


def _seed(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT, date TEXT, open REAL, high REAL,
            low REAL, close REAL, volume REAL
        )
    """)
    rows = [("BBRI", f"2026-05-{d:02d}", 5000+d, 5100+d, 4950+d, 5050+d, 1e6) for d in range(1, 20)]
    conn.executemany(
        "INSERT INTO ohlcv (ticker, date, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()


@pytest.mark.asyncio
async def test_technical_returns_ok_result_on_success(tmp_path):
    db = tmp_path / "t.db"
    _seed(db)
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": json.dumps({
            "verdict": "BULLISH",
            "conviction": 0.75,
            "key_levels": {"support": 5000, "resistance": 5200},
            "reasoning": "Higher highs and rising volume",
        }),
        "tokens_in": 1200, "tokens_out": 80, "cost_usd": 0.0006, "duration_s": 3.2,
    }
    result = await technical.run(candidate, fake_client, str(db))
    assert result.role == "technical"
    assert result.status == "ok"
    assert result.output["verdict"] == "BULLISH"
    assert result.tokens_in == 1200
    assert result.tools_called[0]["tool"] == "sqlite_query"
    assert result.tools_called[0]["rows"] == 19


@pytest.mark.asyncio
async def test_technical_returns_failed_on_invalid_json(tmp_path):
    db = tmp_path / "t.db"
    _seed(db)
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": "not valid json",
        "tokens_in": 100, "tokens_out": 5, "cost_usd": 0.0, "duration_s": 1.0,
    }
    result = await technical.run(candidate, fake_client, str(db))
    assert result.status == "failed"
    assert "json" in result.error.lower() or "decode" in result.error.lower()


@pytest.mark.asyncio
async def test_technical_returns_failed_on_client_exception(tmp_path):
    db = tmp_path / "t.db"
    _seed(db)
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    fake_client = AsyncMock()
    fake_client.chat.side_effect = RuntimeError("network down")
    result = await technical.run(candidate, fake_client, str(db))
    assert result.status == "failed"
    assert "network down" in result.error
```

- [x] **Step 3: Run test to verify it fails**

```bash
venv/bin/pytest tests/agent_firm/test_technical.py -v
```

Expected: ModuleNotFoundError on `engine.agent_firm.agents.technical`.

- [x] **Step 4: Write minimal implementation**

Create `engine/agent_firm/agents/technical.py`:

```python
"""Technical Analyst agent. Reads OHLCV, returns technical conviction call."""

import json
import time
from pathlib import Path

from ..client import DeepSeekClient
from ..schemas import AgentResult, SignalCandidate
from ..tools.sqlite_query import query

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "technical_v1.md"
PROMPT_VERSION = "v1"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()


async def run(
    candidate: SignalCandidate,
    client: DeepSeekClient,
    db_path: str,
) -> AgentResult:
    start = time.monotonic()
    tools_called: list[dict] = []
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
        resp = await client.chat([
            {"role": "system", "content": _load_prompt()},
            {"role": "user", "content": user_msg},
        ])
        output = json.loads(resp["content"])
        return AgentResult(
            role="technical",
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
            role="technical",
            status="failed",
            prompt_version=PROMPT_VERSION,
            error=str(err),
            duration_s=time.monotonic() - start,
            tools_called=tools_called,
        )
```

- [x] **Step 5: Run test to verify it passes**

```bash
venv/bin/pytest tests/agent_firm/test_technical.py -v
```

Expected: 3 passed.

- [x] **Step 6: Commit**

```bash
git add engine/agent_firm/prompts/technical_v1.md \
        engine/agent_firm/agents/technical.py \
        tests/agent_firm/test_technical.py
git commit -m "feat(agent_firm): Technical Analyst agent (v1 prompt + run loop)"
```

---

## Task 9: Risk Manager Agent

**Files:**
- Create: `engine/agent_firm/prompts/risk_v1.md`
- Create: `engine/agent_firm/agents/risk.py`
- Test: `tests/agent_firm/test_risk.py`

- [x] **Step 1: Write the prompt file**

Create `engine/agent_firm/prompts/risk_v1.md`:

```markdown
You are the Risk Manager in a trading agent firm. You make the FINAL veto-or-approve call for an IDX trade signal.

You will receive:
- The original SignalCandidate (ticker, strategy, quant score, regime, flow_verdict, foreign_score)
- Analyst reports (Technical Analyst at minimum in Phase 1; more roles in Phase 2)

Your job: decide approve or veto, with a confidence score and a short rationale.

Output strictly as JSON. Do not include markdown, code fences, or commentary outside the JSON:

```json
{
  "decision": "approve" | "veto",
  "confidence": 0.0-1.0,
  "size_hint": 0.0-1.5,
  "rationale": "Two short lines, e.g. 'Risk: ...\\nBull/Bear: ...'"
}
```

Phase 1 decision rules (with only Technical Analyst input):
- Veto if technical verdict is BEARISH and quant score < 3.0
- Veto if technical conviction < 0.3 (signal is contradicted by price action)
- Approve with size_hint 0.5 when technical verdict is NEUTRAL
- Approve with size_hint 1.0 when technical verdict is BULLISH and conviction >= 0.6
- Approve with size_hint 1.2 (light overweight) when technical verdict is BULLISH with conviction >= 0.8 AND quant score >= 4.0

Confidence guidance:
- 0.8+: clear, defensible decision
- 0.5-0.7: leaning, but acknowledging counterarguments
- 0.0-0.4: thin basis (e.g., missing analyst input). Prefer approve at low size_hint over veto in low-confidence cases — fail-open principle.

If a required analyst report is missing (status="failed"), treat it as neutral and lower your confidence accordingly.
```

- [x] **Step 2: Write the failing test**

Create `tests/agent_firm/test_risk.py`:

```python
import json

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import risk
from engine.agent_firm.schemas import AgentResult, SignalCandidate


@pytest.mark.asyncio
async def test_risk_approve_on_bullish_input():
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    technical = AgentResult(
        role="technical", status="ok",
        output={
            "verdict": "BULLISH", "conviction": 0.75,
            "key_levels": {"support": 5000, "resistance": 5200},
            "reasoning": "Higher highs",
        },
    )
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": json.dumps({
            "decision": "approve",
            "confidence": 0.7,
            "size_hint": 1.0,
            "rationale": "Risk: trend intact.\nBull/Bear: bull case dominates",
        }),
        "tokens_in": 1500, "tokens_out": 90, "cost_usd": 0.0007, "duration_s": 4.0,
    }
    result = await risk.run(candidate, [technical], fake_client)
    assert result.role == "risk"
    assert result.status == "ok"
    assert result.output["decision"] == "approve"
    assert result.output["size_hint"] == 1.0


@pytest.mark.asyncio
async def test_risk_veto_on_bearish_input():
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=2.5, scan_time="2026-05-19T16:00:00+07:00",
    )
    technical = AgentResult(
        role="technical", status="ok",
        output={
            "verdict": "BEARISH", "conviction": 0.8,
            "key_levels": {"support": 4800, "resistance": 5050},
            "reasoning": "Lower lows",
        },
    )
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": json.dumps({
            "decision": "veto",
            "confidence": 0.85,
            "size_hint": 0.0,
            "rationale": "Risk: clear downtrend.\nBull/Bear: bear case dominant",
        }),
        "tokens_in": 1400, "tokens_out": 80, "cost_usd": 0.0006, "duration_s": 3.8,
    }
    result = await risk.run(candidate, [technical], fake_client)
    assert result.status == "ok"
    assert result.output["decision"] == "veto"


@pytest.mark.asyncio
async def test_risk_returns_failed_on_invalid_json():
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": "garbage",
        "tokens_in": 100, "tokens_out": 5, "cost_usd": 0.0, "duration_s": 1.0,
    }
    result = await risk.run(candidate, [], fake_client)
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_risk_propagates_analyst_failures_in_payload():
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    failed_technical = AgentResult(role="technical", status="failed", error="network")
    captured_messages = {}
    async def capture_chat(messages, **kwargs):
        captured_messages["body"] = messages
        return {
            "content": json.dumps({
                "decision": "approve", "confidence": 0.3, "size_hint": 0.5,
                "rationale": "Risk: analyst down, low conviction.\nBull/Bear: n/a",
            }),
            "tokens_in": 50, "tokens_out": 30, "cost_usd": 0.0, "duration_s": 1.0,
        }
    fake_client = AsyncMock()
    fake_client.chat.side_effect = capture_chat
    result = await risk.run(candidate, [failed_technical], fake_client)
    assert result.status == "ok"
    payload = captured_messages["body"][1]["content"]
    assert "failed" in payload
    assert result.output["confidence"] == 0.3
```

- [x] **Step 3: Run test to verify it fails**

```bash
venv/bin/pytest tests/agent_firm/test_risk.py -v
```

Expected: ModuleNotFoundError on `engine.agent_firm.agents.risk`.

- [x] **Step 4: Write minimal implementation**

Create `engine/agent_firm/agents/risk.py`:

```python
"""Risk Manager agent. Final approve/veto decision."""

import json
import time
from pathlib import Path

from ..client import DeepSeekClient
from ..schemas import AgentResult, SignalCandidate

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "risk_v1.md"
PROMPT_VERSION = "v1"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()


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
            {"role": "system", "content": _load_prompt()},
            {"role": "user", "content": user_msg},
        ])
        output = json.loads(resp["content"])
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
```

- [x] **Step 5: Run test to verify it passes**

```bash
venv/bin/pytest tests/agent_firm/test_risk.py -v
```

Expected: 4 passed.

- [x] **Step 6: Commit**

```bash
git add engine/agent_firm/prompts/risk_v1.md \
        engine/agent_firm/agents/risk.py \
        tests/agent_firm/test_risk.py
git commit -m "feat(agent_firm): Risk Manager agent (v1 prompt + run loop)"
```

---

## Task 10: Firm Orchestrator + evaluate() + Persistence

**Files:**
- Create: `engine/agent_firm/firm.py`
- Modify: `engine/agent_firm/__init__.py` (re-add re-exports)
- Test: `tests/agent_firm/test_firm.py`

- [x] **Step 1: Write the failing test**

Create `tests/agent_firm/test_firm.py`:

```python
import json
import sqlite3
from unittest.mock import AsyncMock, patch

import pytest

from engine.agent_firm.schemas import SignalCandidate


def _seed(db_path):
    """Seed minimal ohlcv rows and create agent_firm tables."""
    from data.db import init_agent_firm_tables
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT, date TEXT, open REAL, high REAL,
            low REAL, close REAL, volume REAL
        )
    """)
    rows = [("BBRI", f"2026-05-{d:02d}", 5000+d, 5100+d, 4950+d, 5050+d, 1e6) for d in range(1, 20)]
    conn.executemany(
        "INSERT INTO ohlcv (ticker, date, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    init_agent_firm_tables()


def test_evaluate_returns_bypassed_when_disabled(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "false")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    import importlib
    from engine.agent_firm import config, firm
    importlib.reload(config); importlib.reload(firm)
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    out = firm.evaluate([candidate])
    assert len(out) == 1
    assert out[0].decision == "bypassed"


@pytest.mark.asyncio
async def test_evaluate_async_runs_full_pipeline_and_persists(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "true")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    import importlib
    from data import db as data_db
    importlib.reload(data_db)
    from engine.agent_firm import config, firm
    importlib.reload(config); importlib.reload(firm)

    _seed(tmp_path / "t.db")

    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    fake_client = AsyncMock()
    fake_client.chat.side_effect = [
        # Technical
        {"content": json.dumps({
            "verdict": "BULLISH", "conviction": 0.7,
            "key_levels": {"support": 5000, "resistance": 5200},
            "reasoning": "uptrend",
        }), "tokens_in": 1200, "tokens_out": 60, "cost_usd": 0.0006, "duration_s": 3.0},
        # Risk
        {"content": json.dumps({
            "decision": "approve", "confidence": 0.7, "size_hint": 1.0,
            "rationale": "Risk: ok.\nBull/Bear: bull edges out",
        }), "tokens_in": 1500, "tokens_out": 80, "cost_usd": 0.0007, "duration_s": 4.0},
    ]
    decisions = await firm.evaluate_async([candidate], client=fake_client)
    assert len(decisions) == 1
    d = decisions[0]
    assert d.decision == "approve"
    assert d.confidence == 0.7
    assert d.tokens_in == 2700
    assert d.tokens_out == 140
    assert d.cost_usd == pytest.approx(0.0013, abs=1e-4)
    assert len(d.traces) == 2

    conn = sqlite3.connect(tmp_path / "t.db")
    rows = conn.execute("SELECT decision, confidence FROM agent_decisions").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "approve"
    trace_count = conn.execute("SELECT COUNT(*) FROM agent_traces").fetchone()[0]
    assert trace_count == 2


@pytest.mark.asyncio
async def test_evaluate_async_marks_degraded_when_risk_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "true")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    import importlib
    from data import db as data_db
    importlib.reload(data_db)
    from engine.agent_firm import config, firm
    importlib.reload(config); importlib.reload(firm)

    _seed(tmp_path / "t.db")

    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    fake_client = AsyncMock()
    fake_client.chat.side_effect = [
        # Technical ok
        {"content": json.dumps({
            "verdict": "BULLISH", "conviction": 0.7,
            "key_levels": {"support": 5000, "resistance": 5200},
            "reasoning": "uptrend",
        }), "tokens_in": 1200, "tokens_out": 60, "cost_usd": 0.0006, "duration_s": 3.0},
        # Risk fails: raises
        RuntimeError("deepseek 500"),
    ]
    decisions = await firm.evaluate_async([candidate], client=fake_client)
    assert decisions[0].decision == "degraded"
    assert "degraded" in (decisions[0].rationale or "").lower()
```

- [x] **Step 2: Run test to verify it fails**

```bash
venv/bin/pytest tests/agent_firm/test_firm.py -v
```

Expected: ModuleNotFoundError on `engine.agent_firm.firm`.

- [x] **Step 3: Write minimal implementation**

Create `engine/agent_firm/firm.py`:

```python
"""Agent firm orchestrator. Phase 1: Technical -> Risk.

Public API:
  evaluate(candidates) -> list[AgentDecision]     # sync, scheduler-facing
  evaluate_async(candidates, client) -> ...       # async, for tests
"""

import asyncio
import json
import time

from data.db import DB_PATH, get_db

from . import config
from .agents import risk, technical
from .client import DeepSeekClient
from .schemas import AgentDecision, AgentResult, SignalCandidate


async def _evaluate_one(
    candidate: SignalCandidate,
    client: DeepSeekClient,
) -> AgentDecision:
    start = time.monotonic()
    technical_result = await technical.run(candidate, client, str(DB_PATH))
    risk_result = await risk.run(candidate, [technical_result], client)

    if risk_result.status == "failed":
        decision_str = "degraded"
        confidence = None
        size_hint = None
        rationale = "Agent firm degraded — quant signal passed through"
    else:
        out = risk_result.output or {}
        decision_str = out.get("decision", "degraded")
        confidence = out.get("confidence")
        size_hint = out.get("size_hint")
        rationale = out.get("rationale")

    traces = [technical_result, risk_result]
    tokens_in = sum(t.tokens_in for t in traces)
    tokens_out = sum(t.tokens_out for t in traces)
    cost_usd = DeepSeekClient._calc_cost(tokens_in, tokens_out)

    return AgentDecision(
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
        duration_s=time.monotonic() - start,
    )


async def evaluate_async(
    candidates: list[SignalCandidate],
    client: DeepSeekClient | None = None,
) -> list[AgentDecision]:
    if client is None:
        client = DeepSeekClient()
    decisions = await asyncio.gather(
        *[_evaluate_one(c, client) for c in candidates]
    )
    for d in decisions:
        _persist(d)
    return list(decisions)


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


def _persist(decision: AgentDecision) -> int:
    conn = get_db()
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

- [x] **Step 4: Re-add re-exports to `engine/agent_firm/__init__.py`**

Replace the body of `engine/agent_firm/__init__.py` with:

```python
"""Agent firm: multi-agent LLM veto-gate for IDX signals.

Phase 1: 2 agents (Technical, Risk). Gated by AGENT_FIRM_ENABLED env var.
See docs/superpowers/specs/2026-05-19-agent-firm-hybrid-stack-design.md.
"""

from .firm import evaluate
from .schemas import AgentDecision, AgentResult, SignalCandidate

__all__ = ["SignalCandidate", "AgentDecision", "AgentResult", "evaluate"]
```

- [x] **Step 5: Run all firm tests**

```bash
venv/bin/pytest tests/agent_firm/ -v
```

Expected: all previous tests still pass; new `test_firm.py` shows 3 passed.

- [x] **Step 6: Commit**

```bash
git add engine/agent_firm/firm.py engine/agent_firm/__init__.py tests/agent_firm/test_firm.py
git commit -m "feat(agent_firm): firm orchestrator with evaluate(), evaluate_async(), persistence"
```

---

## Task 11: Smoke Probe (Live DeepSeek)

**Files:**
- Create: `engine/agent_firm/smoke.py`

This task hits the real DeepSeek API. It needs `DEEPSEEK_API_KEY` set in the environment.

- [x] **Step 1: Write the smoke probe**

Create `engine/agent_firm/smoke.py`:

```python
"""Tier 4 daily smoke probe for the agent firm.

Runs one canned signal through the full pipeline and asserts:
- Response within 90s
- Decision is one of: approve, veto, degraded
- Cost is reasonable (between $0.0001 and $0.05 for one signal)

Usage:
    AGENT_FIRM_ENABLED=true DEEPSEEK_API_KEY=sk-... \\
      venv/bin/python -m engine.agent_firm.smoke

Exits 0 on success, 2 on duration timeout, 3 on invalid decision,
4 on cost out of range, 1 on any other error.
"""

import asyncio
import sys
from datetime import datetime, timezone

from . import config
from .firm import evaluate_async
from .schemas import SignalCandidate

_CANNED = SignalCandidate(
    ticker="BBRI",
    strategy="momentum_following",
    score=4.2,
    scan_time=datetime.now(timezone.utc).isoformat(),
    regime="TRENDING",
    flow_verdict="STRONG_BUY",
    foreign_score=3.42,
    indicators={"vwma_above": True, "ma50_above": True},
)

_MAX_DURATION_S = 90.0
_COST_MIN = 0.0001
_COST_MAX = 0.05


def main() -> int:
    if not config.is_active():
        print("SKIP: agent firm not active (FIRM_ENABLED=false or kill switch set)")
        return 0
    try:
        decisions = asyncio.run(evaluate_async([_CANNED]))
    except Exception as err:
        print(f"FAIL: pipeline raised {type(err).__name__}: {err}")
        return 1

    if not decisions:
        print("FAIL: no decisions returned")
        return 1

    d = decisions[0]
    print(
        f"decision={d.decision} conf={d.confidence} "
        f"size={d.size_hint} cost=${d.cost_usd:.4f} dur={d.duration_s:.1f}s"
    )
    if d.duration_s > _MAX_DURATION_S:
        print(f"FAIL: duration {d.duration_s:.1f}s exceeds {_MAX_DURATION_S}s budget")
        return 2
    if d.decision not in ("approve", "veto", "degraded"):
        print(f"FAIL: invalid decision {d.decision}")
        return 3
    if d.decision != "degraded" and not (_COST_MIN <= d.cost_usd <= _COST_MAX):
        print(f"FAIL: cost ${d.cost_usd:.4f} outside [{_COST_MIN}, {_COST_MAX}]")
        return 4
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [x] **Step 2: Run smoke probe disabled (verify SKIP path)**

```bash
AGENT_FIRM_ENABLED=false venv/bin/python -m engine.agent_firm.smoke
echo "exit code: $?"
```

Expected output:
```
SKIP: agent firm not active (FIRM_ENABLED=false or kill switch set)
exit code: 0
```

- [x] **Step 3: Run smoke probe enabled (live DeepSeek call)**

First confirm `DEEPSEEK_API_KEY` is set in your shell:

```bash
echo "${DEEPSEEK_API_KEY:0:7}..."
```

Expected output starts with `sk-` then truncated.

If not set, get a key from <https://platform.deepseek.com>, export it:

```bash
export DEEPSEEK_API_KEY="sk-your-key-here"
```

Then run:

```bash
AGENT_FIRM_ENABLED=true venv/bin/python -m engine.agent_firm.smoke
echo "exit code: $?"
```

Expected output (within ~30s):
```
decision=approve conf=0.7 size=1.0 cost=$0.00XX dur=XX.Xs
OK
exit code: 0
```

If decision is `degraded` or duration is high, investigate before continuing.

- [x] **Step 4: Verify SQLite persistence**

```bash
sqlite3 "data/walkforward.db" "SELECT ticker, decision, confidence, cost_usd, duration_s FROM agent_decisions ORDER BY id DESC LIMIT 1;"
sqlite3 "data/walkforward.db" "SELECT role, prompt_version, tokens_in, tokens_out FROM agent_traces WHERE decision_id = (SELECT MAX(id) FROM agent_decisions);"
```

Expected: one row in `agent_decisions` with `decision='approve'` (or `veto`), and two rows in `agent_traces` (`technical` and `risk`).

- [x] **Step 5: Commit**

```bash
git add engine/agent_firm/smoke.py
git commit -m "feat(agent_firm): tier 4 smoke probe for live DeepSeek heartbeat"
```

---

## Task 12: Dashboard Status Badge

**Files:**
- Modify: `app.py` (add Flask endpoint)
- Modify: `templates/backtest_multi.html` (add badge div + fetch script)

- [x] **Step 1: Inspect current dashboard template head**

```bash
head -50 templates/backtest_multi.html
```

Note the location of the page `<body>` open tag and any existing top-of-page header element. Pick a stable anchor near the top of `<body>` where the badge can be inserted (look for a wrapping `<div class="container">` or similar).

- [x] **Step 2: Add the Flask endpoint**

Modify `app.py`. Find a stable region near the other `@app.route` declarations (e.g., next to `@app.route("/api/signals/today")`) and add:

```python
@app.route("/api/agent/status", methods=["GET"])
def agent_status():
    from engine.agent_firm import config as _agent_config
    return jsonify({
        "enabled": _agent_config.FIRM_ENABLED,
        "enforce": _agent_config.FIRM_ENFORCE,
        "active": _agent_config.is_active(),
        "model": _agent_config.MODEL_ID,
    })
```

- [x] **Step 3: Restart the Flask app & test the endpoint**

```bash
curl -s http://localhost:5001/api/agent/status | python3 -m json.tool
```

Expected output:
```json
{
    "enabled": false,
    "enforce": false,
    "active": false,
    "model": "deepseek-v4-pro"
}
```

(If Flask is managed by systemd, restart with `sudo systemctl restart idx-walkforward-5001.service` first.)

- [x] **Step 4: Add badge HTML + script to template**

Open `templates/backtest_multi.html`. Insert this fragment immediately AFTER the opening `<body>` tag (or after the existing top-of-page header if one exists):

```html
<div id="agent-firm-badge" style="position:fixed;top:8px;right:8px;z-index:9999;
     font:12px/1.4 system-ui,sans-serif;padding:4px 8px;border-radius:6px;
     background:#222;color:#888;border:1px solid #444;">
  Agent firm: <span id="agent-firm-state">…</span>
</div>
<script>
  fetch('/api/agent/status').then(r => r.json()).then(s => {
    const el = document.getElementById('agent-firm-state');
    const badge = document.getElementById('agent-firm-badge');
    if (s.active) {
      el.textContent = s.enforce ? 'ENFORCE' : 'SHADOW';
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

- [x] **Step 5: Reload dashboard in browser**

Visit `http://localhost:5001/` and confirm a small dark badge appears top-right reading `Agent firm: OFF`. Page layout should not shift.

- [x] **Step 6: Test enabled state**

```bash
AGENT_FIRM_ENABLED=true sudo systemctl restart idx-walkforward-5001.service
# wait 3 seconds
curl -s http://localhost:5001/api/agent/status
```

Expected: `"active": true`. Reload dashboard; badge should read `Agent firm: SHADOW` in yellow.

Reset to OFF before committing so production deploy stays neutral:

```bash
# remove the env var override or restart with default
sudo systemctl restart idx-walkforward-5001.service
```

- [x] **Step 7: Commit**

```bash
git add app.py templates/backtest_multi.html
git commit -m "feat(agent_firm): dashboard status badge + /api/agent/status endpoint"
```

> **Note on conflicting unstaged work:** the repo had a pre-existing modification to `templates/backtest_multi.html` at the start of this plan. If the badge insertion conflicts with that work, resolve manually — the badge is a small isolated div and should slot in alongside other top-of-body markup.

---

## Final Verification

- [x] **Run the full test suite**

```bash
venv/bin/pytest tests/agent_firm/ -v
```

Expected: all tests pass. Suggested count: 25+ tests across 8 files.

- [x] **Confirm production behavior unchanged**

```bash
AGENT_FIRM_ENABLED=false venv/bin/python -m engine.agent_firm.smoke
```

Expected: `SKIP` and exit 0 (firm doesn't run when disabled).

- [x] **Confirm DB schema is correct**

```bash
sqlite3 "data/walkforward.db" ".schema agent_decisions"
sqlite3 "data/walkforward.db" ".schema agent_traces"
```

Expected: both schemas match the spec.

- [x] **Confirm dashboard shows OFF badge in browser**

Visit `http://localhost:5001/` → small badge top-right reads `Agent firm: OFF`.

- [x] **Smoke test against live DeepSeek (one-time validation)**

```bash
AGENT_FIRM_ENABLED=true venv/bin/python -m engine.agent_firm.smoke
```

Expected: `OK` and exit 0, with a row added to `agent_decisions` and 2 rows in `agent_traces`.

- [x] **Mark Phase 1 complete**

If all verifications pass, Phase 1 is done. Add a `git tag`:

```bash
git tag -a phase1-agent-firm-scaffolding -m "Phase 1 complete: scaffolding + 2 agents + smoke probe"
```

Next step: Phase 2 — scheduler integration, remaining 5 agents (Flow, Regime, News, Bull, Bear), LangGraph DAG, Tavily web search, recorded-replay tests, shadow mode rollout (FIRM_ENABLED=true, FIRM_ENFORCE=false).

---

## What Phase 1 Does NOT Do

These are deliberately out of scope and deferred to Phase 2 / Phase 3:

- Scheduler integration (no call site added to `scheduler.py` yet)
- The other 5 agents (Flow, Regime, News, Bull, Bear)
- LangGraph DAG (Phase 1 uses linear asyncio: Technical → Risk)
- Tavily web search for News Analyst
- Recorded-replay (Tier 2) tests
- Circuit breaker + daily spend cap (Phase 3)
- Override Flask endpoint (Phase 3)
- Monte Carlo + bootstrap CIs in walkforward harness (Phase 3 bonus)
- Telegram alert format change (Phase 3)
