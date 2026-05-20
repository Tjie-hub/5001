# Agent Firm Phase 2 — Design Spec

**Date:** 2026-05-20
**Status:** Approved for implementation planning
**Author:** Sarjono + Claude (brainstorming session)
**Prerequisite:** Phase 1 complete (tag: `phase1-agent-firm-scaffolding`)

---

## 1. Goals

1. Replace Phase 1's linear `asyncio` orchestrator with a **LangGraph DAG**.
2. Add **5 new agents**: Flow, Regime, News (Tavily-enabled), Bull, Bear.
3. Add **3 tools**: `web_search` (Tavily), `news_lookup` (news_mentions table), extend context pre-fetch.
4. **Wire `scheduled_multi_strategy_scan()`** as the first scheduler call site (skip `daily_signal_scan` for now).
5. Deploy in **shadow mode** (`FIRM_ENFORCE=false`): agents run and log, signals reach Telegram unchanged.
6. Establish **Tier 2 recorded-replay fixtures** after first live shadow run.

Phase 3 (enforcement, circuit breaker, override endpoint, Monte Carlo) is out of scope.

---

## 2. Approach

**B — LangGraph first, then agents, then scheduler.**

Order of implementation:
1. LangGraph refactor of `firm.py` (existing 2 agents, same public API)
2. Tools: `web_search`, `news_lookup`, context pre-fetch helper
3. Four parallel analysts: Flow, Regime, News, Bull/Bear
4. Risk Manager v2 (extended prompt reading all 6 upstream results)
5. Scheduler wiring + shadow mode
6. Dashboard stats line

---

## 3. Architecture

### 3.1 LangGraph DAG

```
[START]
   │
   ▼
build_context        ← one batched SQLite read
   │
   ├──────────────────────────────────────┐
   ▼          ▼          ▼               ▼
technical   flow      regime           news       ← parallel (asyncio.gather inside node)
   └──────────┴──────────┴───────────────┘
                         │
                         ▼
                        bull              ← reads all 4 analyst AgentResults
                         │
                         ▼
                        bear              ← reads all 4 analyst outputs + bull case
                         │
                         ▼
                        risk              ← reads all 6; emits approve/veto + size_hint
                         │
                         ▼
                      persist             ← writes agent_decisions + agent_traces rows
                         │
                         ▼
                       [END]
```

**`AgentState` (TypedDict):**
```python
class AgentState(TypedDict):
    candidate: SignalCandidate
    db_path: str
    context: dict                  # pre-fetched ohlcv, flow, news, trades
    technical_result: AgentResult
    flow_result: AgentResult
    regime_result: AgentResult
    news_result: AgentResult
    bull_result: AgentResult
    bear_result: AgentResult
    risk_result: AgentResult
    decision: AgentDecision
```

**Public API unchanged:** `evaluate(candidates)` and `evaluate_async(candidates, client)` keep the same signatures. Scheduler and tests need no changes when `firm.py` is swapped.

### 3.2 Module layout (additions)

```
engine/agent_firm/
├── firm.py                  # MODIFIED: LangGraph StateGraph replaces asyncio
├── schemas.py               # MODIFIED: AgentState TypedDict added
├── config.py                # MODIFIED: TAVILY_API_KEY, TAVILY_MAX_RESULTS added
├── agents/
│   ├── flow.py              # NEW
│   ├── regime.py            # NEW
│   ├── news.py              # NEW (uses web_search + news_lookup)
│   ├── bull.py              # NEW
│   ├── bear.py              # NEW
│   └── risk.py              # MODIFIED: risk_v2.md prompt
├── tools/
│   ├── web_search.py        # NEW: Tavily async wrapper
│   └── news_lookup.py       # NEW: news_mentions table read
├── prompts/
│   ├── flow_v1.md           # NEW
│   ├── regime_v1.md         # NEW
│   ├── news_v1.md           # NEW
│   ├── bull_v1.md           # NEW
│   ├── bear_v1.md           # NEW
│   └── risk_v2.md           # NEW (risk_v1.md kept for replay continuity)
tests/agent_firm/
├── test_flow.py             # NEW
├── test_regime.py           # NEW
├── test_news.py             # NEW (respx mocks for Tavily)
├── test_bull.py             # NEW
├── test_bear.py             # NEW
├── test_firm_v2.py          # NEW: full 7-agent DAG with MockLLMClient
└── fixtures/
    └── recorded/            # NEW dir: populated after first live shadow run
```

**Modified files:**
- `scheduler.py` — add agent firm hook inside `scheduled_multi_strategy_scan()`
- `app.py` — extend `/api/agent/status` with `today_stats` field
- `templates/backtest_multi.html` — add today's stats line below existing badge

---

## 4. Agent Composition

| # | Agent | Reads | Tools | Key output fields |
|---|-------|-------|-------|-------------------|
| 1 | Technical | OHLCV 60d | `sqlite_query` | `verdict`, `conviction`, `key_levels` |
| 2 | Flow | `broker_flow` (14d), `stockbit_flow` (14d), `stockbit_flow_bars` | `sqlite_query` | `flow_verdict`, `smart_money_signal`, `net_foreign_14d` |
| 3 | Regime | `wf_scores`, IHSG state, `daily_screen` sector data | `sqlite_query` | `regime_call`, `sector_tailwind`, `macro_risk` |
| 4 | News | `news_mentions` (7d) + Tavily live search | `news_lookup`, `web_search` | `sentiment`, `catalyst`, `summary` |
| 5 | Bull | All 4 analyst outputs | none | `bull_case` (2–3 sentences) |
| 6 | Bear | All 4 analyst outputs + Bull's `bull_case` | none | `bear_case`, `key_risk` |
| 7 | Risk | All 6 upstream results + open paper_trades | `sqlite_query` | `decision`, `confidence`, `size_hint`, `rationale` |

**Bull/Bear ordering:** Bull writes first (no prior context). Bear reads Bull's output and writes a rebuttal. One pass each — no second exchange.

**Risk Manager v2:** Prompt updated to `risk_v2.md`. Reads full 6-role input. `risk_v1.md` kept on disk for Tier 2 recorded-replay continuity.

---

## 5. Tools

### 5.1 `web_search.py`

```python
async def search(query: str, max_results: int = 5) -> list[dict]:
    # Returns: [{title, url, content, score}]
    # Falls back to [] with logged warning if TAVILY_API_KEY absent
```

- Called only by News agent.
- Results capped at `TAVILY_MAX_RESULTS` (default 5) to control token spend.
- Uses `httpx.AsyncClient` with Tavily REST API.

### 5.2 `news_lookup.py`

```python
def lookup(db_path: str, ticker: str, days: int = 7) -> list[dict]:
    # SELECT headline, source, sentiment, published_at FROM news_mentions
    # WHERE ticker=? AND published_at >= date('now', '-N days')
    # ORDER BY published_at DESC LIMIT 20
```

- Sync, wraps existing `sqlite_query`.
- Returns at most 20 rows to bound token input.

### 5.3 Config additions

```python
TAVILY_API_KEY   = os.getenv("TAVILY_API_KEY", "")
TAVILY_MAX_RESULTS = int(os.getenv("AGENT_FIRM_TAVILY_MAX", "5"))
```

---

## 6. Scheduler Integration

**Hook location:** `scheduled_multi_strategy_scan()` in `scheduler.py`, after signals are assembled, before `send_telegram()`.

```python
from engine.agent_firm import evaluate
from engine.agent_firm.schemas import SignalCandidate
from engine.agent_firm import config as _firm_cfg

if _firm_cfg.is_active() and signals:
    candidates = [
        SignalCandidate(
            ticker=s["ticker"],
            strategy=s.get("strategy", "multi"),
            score=s.get("score", 0.0),
            scan_time=datetime.now(WIB).isoformat(),
            regime=s.get("regime"),
            flow_verdict=s.get("flow_verdict") or s.get("vpin_signal"),
            foreign_score=s.get("flow_score"),
            indicators={k: s[k] for k in ("vol_ratio", "rs", "votes") if k in s},
        )
        for s in signals
    ]
    decisions = evaluate(candidates)

    if _firm_cfg.FIRM_ENFORCE:           # Phase 3 gate
        approved = {d.ticker for d in decisions if d.decision == "approve"}
        signals = [s for s in signals if s["ticker"] in approved]
    # shadow mode: decisions logged, signals unchanged
```

**Shadow rollout:** Deploy with `AGENT_FIRM_ENABLED=true`, `AGENT_FIRM_ENFORCE=false`. Signals reach Telegram unchanged. Decisions accumulate in `agent_decisions` for 30-day validation.

**Enforcement gate (Phase 3):** The `if FIRM_ENFORCE` block is already present — flipping `AGENT_FIRM_ENFORCE=true` activates enforcement with no code change.

---

## 7. Dashboard Update

Add a stats line below the existing badge in `templates/backtest_multi.html`:

```
Agent firm: SHADOW | Today: 8 evaluated · 6 approved · 2 vetoed · $0.18 spent
```

Fetched from `/api/agent/status` (already exists) extended with a `today_stats` field:
```json
{
  "enabled": true, "enforce": false, "active": true, "model": "deepseek-v4-pro",
  "today_stats": {"evaluated": 8, "approved": 6, "vetoed": 2, "cost_usd": 0.18}
}
```

---

## 8. Testing Strategy

### Tier 1 — Unit tests (TDD, $0/run)
- `test_flow.py`, `test_regime.py`, `test_news.py`, `test_bull.py`, `test_bear.py` — each with 3 tests: ok result, invalid JSON, client exception.
- `test_news.py` additionally: Tavily fallback on missing key (returns `[]`), respx mock for live call.
- `test_firm_v2.py` — full 7-agent DAG with `MockLLMClient`; asserts state flows, persist writes correct rows.

### Tier 2 — Recorded-replay (one-time, after first live run)
- Capture 5–10 real traces to `tests/agent_firm/fixtures/recorded/*.json`.
- `test_replay.py` feeds recorded inputs through firm with `RecordedLLMClient`. Asserts decision matches.
- Re-record on model upgrade or major prompt change.

### Tier 3 — Shadow validation (30 trading days)
- Query `agent_decisions JOIN paper_trades` after 30 days.
- **Acceptance bar:** `approve-cohort Sharpe ≥ baseline + 0.2` AND `veto-cohort win_rate < baseline − 5pp`.
- Both conditions required before Phase 3 (enforcement).

---

## 9. What Phase 2 Does NOT Do

- `FIRM_ENFORCE=true` — Phase 3 only
- Override Flask endpoint (`POST /api/agent/override/<id>`) — Phase 3
- Circuit breaker enhancements — Phase 3
- Monte Carlo / bootstrap CIs in walkforward harness — Phase 3
- `daily_signal_scan()` wiring — explicitly deferred
- Recorded-replay recording (one-time manual step post-deployment, not an implementation task)
