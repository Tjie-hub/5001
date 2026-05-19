# Agent Firm Hybrid Stack — Design Spec

**Date:** 2026-05-19
**Status:** Approved for implementation planning
**Author:** Sarjono + Claude (brainstorming session)
**Target system:** `idx-walkforward-5001` (Flask + SQLite + APScheduler IDX trading platform)

---

## 1. Motivation

The IDX walkforward system has a mature quant pipeline: 10 strategies, walk-forward backtest harness, foreign-flow scoring, regime classification, Stockbit order-flow integration, Telegram alerts, APScheduler jobs. What it lacks is **multi-source qualitative reasoning** — synthesizing news, macro context, fundamentals, and flow narrative into a conviction call.

A NotebookLM comparative study of five open-source frameworks (AI-Trader, Vibe-Trading, TradingAgents, OpenBB, freqtrade) confirmed that no single framework is a drop-in fit for IDX. The report's recommendation (Vibe-Trading + OpenBB) overweights regional features that target A-share/HK markets, not IDX specifically.

This spec adopts a **hybrid stack**:

1. **Keep** the existing IDX quant pipeline unchanged (it is the moat).
2. **Add** a TradingAgents-inspired multi-agent firm as a *synchronous veto gate* before Telegram dispatch.
3. **Borrow** Vibe-Trading's statistical validation methods (Monte Carlo, bootstrap CIs) into the existing walk-forward harness in Phase 3.
4. **Defer** wholesale framework adoption, OpenBB workspace, and live broker integration.

The agent firm's authority: **veto gate** — it can block quant signals from reaching Telegram, but cannot generate independent signals or modify the underlying strategies.

---

## 2. Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Adoption pattern | Hybrid (augment, not replace) | Existing pipeline works; only adding what's missing |
| Agent authority | Veto gate (synchronous) | Cleanest semantics; no signal escapes unreviewed |
| Committee size | Full firm (7 agents) | Per user direction; cost remains <$25/mo at full firm |
| LLM provider | DeepSeek V4 Pro (uniform) | $0.435/M input promo, $0.87/M output; 1M context; designed for agent workflows |
| DAG library | LangGraph | Matches TradingAgents reference; debuggable; Apache-2.0 |
| Trigger | Synchronous in scheduler jobs | Veto requires nothing to escape; adds ~3–8 min to daily 16:00 scan |
| Deployment | In-process module (`engine/agent_firm/`) | One Python process; asyncio for parallel agent calls; shared SQLite |
| News data source | `news_mentions` + Tavily web search at runtime | Structured baseline + agent-fetched context |
| Failure semantics | Fail-open on Risk Manager errors | Better noisy Telegram than missed entries on working days |

---

## 3. Architecture

```
scheduler.py (APScheduler, jobs unchanged)
   │
   ├─ daily_signal_scan (16:00 Mon–Fri)
   ├─ scheduled_multi_strategy_scan (10:00, 13:00)
   └─ _run_screener_intraday (9:30…15:00)
        │
        ▼  candidates: list[SignalCandidate]
   ┌──────────────────────────────────────┐
   │ engine/agent_firm/firm.py            │
   │   .evaluate(candidates) → results    │
   │                                      │
   │   LangGraph DAG, asyncio.gather()    │
   │   across 4 analysts in parallel,     │
   │   then Bull/Bear, then Risk Manager  │
   └──────────────┬───────────────────────┘
                  ▼ DeepSeek API (OpenAI SDK)
            7-agent debate
                  ▼
        ApprovedSignals / Vetoed (all logged)
                  ▼
            Telegram + paper_trade
```

### 3.1 Module layout

```
engine/agent_firm/
├── __init__.py          # Public API: firm, AgentDecision, SignalCandidate
├── firm.py              # LangGraph orchestrator + evaluate() entry point
├── config.py            # FIRM_ENABLED, FIRM_ENFORCE, spend cap, model IDs
├── client.py            # DeepSeek client wrapper (OpenAI SDK), prompt caching
├── schemas.py           # Pydantic models for all agent I/O
├── agents/
│   ├── technical.py
│   ├── flow.py
│   ├── regime.py
│   ├── news.py
│   ├── bull.py
│   ├── bear.py
│   └── risk.py
├── tools/
│   ├── sqlite_query.py  # Read-only SQL against walkforward.db
│   ├── web_search.py    # Tavily API
│   └── news_lookup.py   # news_mentions table read
├── prompts/
│   ├── technical_v1.md
│   ├── flow_v1.md
│   └── ... (one per agent role, versioned)
└── smoke.py             # Tier 4 production probe
```

### 3.2 Agent firm composition

| # | Agent | Reads | Produces | Tools |
|---|-------|-------|----------|-------|
| 1 | Technical Analyst | Candidate signal, OHLCV 60d, strategy name, indicators | Technical conviction + key levels | `sqlite_query(ohlcv)` |
| 2 | Flow Specialist | foreign_score, broker_flow, stockbit_flow, stockbit_flow_bars | Flow narrative + smart-money verdict | `sqlite_query(flow tables)` |
| 3 | Regime Analyst | regime_filter output, IHSG state, sector rotation weights | Macro regime call + sector tailwind/headwind | `sqlite_query`, `regime_query` |
| 4 | News/Sentiment Analyst | news_mentions (last 7d) + Tavily web search | News summary, sentiment, catalyst flags | `news_lookup`, `web_search` |
| 5 | Bull Researcher | All four analyst reports | Steelman bull case | Read-only (synthesis) |
| 6 | Bear Researcher | All four analyst reports | Steelman bear case | Read-only (synthesis) |
| 7 | Risk Manager / PM (final) | All above + open paper_trades | Veto decision + size hint + 2-line rationale | `sqlite_query(paper_trades)` |

### 3.3 DAG topology (LangGraph)

```
        [Candidate signal]
              │
   ┌──────────┼──────────┬──────────┐
   ▼          ▼          ▼          ▼
Technical  Flow      Regime    News
   └──────────┬──────────┴──────────┘
              ▼
        Bull → Bear (Bull writes case; Bear writes rebuttal reading Bull's output; no second exchange)
              ▼
       Risk Manager / PM
              ▼
     {approve | veto, rationale, size_hint}
```

### 3.4 Model & cost

- **Model:** `deepseek-v4-pro` uniformly across all 7 roles.
- **Token budget per signal:** ~16k input + ~4k output = ~20k tokens.
- **Volume:** 15 signals/day × 20k tokens × 30 days = ~9M tokens/month.
- **Cost (promo, until 2026-05-31):** ~$6/month. **Cost (list price after):** ~$23/month.
- **Prompt caching strategy:** system prompts (~7k tokens cached prefix), daily IHSG/macro context cached across signals → expected 70% cache hit rate → real cost ~$2–8/month.
- **Per-call timeout:** 45s, retry once on 5xx/ReadTimeout.

---

## 4. Data Flow & Schema Changes

### 4.1 Per-signal flow

```
1. Scheduler job builds SignalCandidate (existing code, unchanged):
     {ticker, strategy, score, regime, flow_verdict, foreign_score, scan_time}

2. firm.evaluate([candidate]) called inline:
     ├─ Pre-fetch context (one SQLite read, batched):
     │    - OHLCV last 90d, flow last 14d, news_mentions last 7d, open paper_trades
     ├─ asyncio.gather() over 4 parallel analyst calls
     ├─ Bull/Bear sequential (each reads analyst outputs)
     └─ Risk Manager final call → AgentDecision

3. Persist AgentDecision to agent_decisions table (regardless of approve/veto).

4. Dispatch:
     - approve → existing Telegram + paper_trade flow, enriched with rationale
     - veto    → no Telegram (or muted summary if AGENT_FIRM_LOG_VETOES=true)
```

### 4.2 New tables

```sql
-- One row per signal evaluated by the firm
CREATE TABLE agent_decisions (
    id INTEGER PRIMARY KEY,
    scan_time TEXT NOT NULL,
    ticker TEXT NOT NULL,
    strategy TEXT NOT NULL,
    quant_score REAL,
    decision TEXT NOT NULL,       -- 'approve' | 'veto' | 'bypassed' | 'degraded'
    confidence REAL,              -- 0.0 to 1.0 from Risk Manager
    size_hint REAL,               -- suggested position multiplier 0.0–1.5
    rationale TEXT,               -- 2-line summary for Telegram
    overridden INTEGER DEFAULT 0, -- 1 if user forced through veto
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_usd REAL,
    duration_s REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(scan_time, ticker, strategy)
);
CREATE INDEX idx_agent_decisions_ticker_date ON agent_decisions(ticker, scan_time);

-- One row per agent invocation
CREATE TABLE agent_traces (
    id INTEGER PRIMARY KEY,
    decision_id INTEGER REFERENCES agent_decisions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,           -- 'technical' | 'flow' | 'regime' | 'news' | 'bull' | 'bear' | 'risk'
    prompt_version TEXT,          -- e.g., 'v1.2' for prompt iteration tracking
    output TEXT,                  -- full agent response (JSON)
    tools_called TEXT,            -- JSON array of tool calls
    tokens_in INTEGER,
    tokens_out INTEGER,
    duration_s REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_agent_traces_decision ON agent_traces(decision_id);
```

### 4.3 Existing table change

```sql
ALTER TABLE scheduled_signals ADD COLUMN agent_decision_id INTEGER REFERENCES agent_decisions(id);
```

### 4.4 Telegram alert format (approved signals)

```
🟢 BBRI · Momentum Following · score 4.2
Foreign flow: STRONG_BUY (+342%)
Regime: TRENDING / Sector: Banking +
─ Agent verdict (conf 0.78) ─
Risk: News-aware. BI rate hold reduces NIM risk.
Bull: Foreign accumulation 5-day, IDR-stable narrative.
Bear: Sector rotation away from banks if commodities rally.
Size: 1.0x base.
```

Vetoed signals are logged but not sent (unless `AGENT_FIRM_LOG_VETOES=true` env flag, then sent as a muted single-line summary).

### 4.5 Override mechanism

- Flask endpoint: `POST /api/agent/override/<decision_id>` — marks `overridden=1` and re-emits as Telegram alert.
- Surfaced in dashboard as "Agent Vetoes Today" panel with one-click override.

---

## 5. Error Handling & Operational Safety

Synchronous veto means **agent firm failure = blocked signals**. Three layers of safety.

### 5.1 Per-agent timeouts & fallbacks

- Each agent call: 45s timeout, retry once on `httpx.ReadTimeout` or 5xx.
- Analyst agent fails after retry → its slot returns `AgentResult(role, status='failed', output=None)`. Risk Manager treats missing analyst as neutral, not blocking.
- Risk Manager itself fails → **fail-open**: approve the signal with `decision='degraded'`, `confidence=null`, `rationale='Agent firm degraded — quant signal passed through'`.
- Fail-open rationale: better a slightly-louder Telegram than missed entries on a working market day.

### 5.2 Circuit breaker per scan batch

- Track failure rate across the current scan batch in memory.
- If >50% of candidates hit Risk Manager failures → flip global `FIRM_DEGRADED` flag for the rest of the batch, skip remaining firm calls, pass quant signals through with `decision='bypassed'`. One admin Telegram alert per degraded scan.
- Auto-clears at next scan start.

### 5.3 Kill switches

- `FIRM_ENABLED=os.getenv('AGENT_FIRM_ENABLED', 'true')` — set to `false` to make `evaluate()` a no-op pass-through.
- Emergency disable without redeploy: `touch /tmp/agent_firm.disable` checked at start of each `evaluate()`.
- `FIRM_ENFORCE` separate flag: when `false`, decisions are logged but quant signals proceed regardless. Used in shadow mode.

### 5.4 Cost / quota guards

- Daily spend cap (default $5) tracked from `agent_decisions.cost_usd` rollup. When exceeded, behaves like kill switch for remaining day.
- DeepSeek 429 rate-limit → exponential backoff (4s, 8s, 16s), then circuit-breaker.

### 5.5 Logging & observability

- Every `evaluate()` writes one `agent_decisions` row + N `agent_traces` rows even on failure.
- Structured JSON logging to `logs/agent_firm.log`, rotated daily.
- Dashboard additions:
  1. Badge: "Agent firm: ON / DEGRADED / OFF"
  2. Today's stats line: `12 evaluated · 8 approved · 4 vetoed · 0 failed · $0.14 spent`
  3. Link: `/agent/decisions/today` full audit table

---

## 6. Testing Strategy

Four tiers, each answering a different question.

### Tier 1 — Unit & deterministic tests (CI, $0/run)

- Real SQLite fixture (`tests/fixtures/walkforward_seed.db`) for `sqlite_query` tools.
- `respx` mocks for Tavily `web_search`.
- `MockLLM` returning hardcoded JSON per role for `firm.evaluate()` plumbing.
- Snapshot test on Telegram alert formatter.
- Flask test client for override endpoint (asserts `overridden=1`).
- Circuit-breaker test: inject 6/10 failures, assert remaining bypassed.

### Tier 2 — Recorded-replay tests (CI, $0/run after one-time recording)

- One-time: capture ~30 real decisions across bull/bear/mixed cases → save full prompt+output traces to `tests/recorded_decisions/*.json`.
- Replay test feeds recorded inputs through firm with `RecordedLLM` returning saved outputs. Asserts decision matches.
- Catches schema regressions, DAG flow regressions, prompt-template breakages.
- Re-record quarterly or on DeepSeek model upgrade.

### Tier 3 — Walk-forward validation (the alpha test)

The only test that proves the firm is worth keeping.

- **Mode 1 — Shadow mode (30 days, run before enforcement):** All signals reach Telegram regardless of agent verdict; decisions logged only. After 30 days, compute approve-cohort vs veto-cohort outcomes from `paper_trades`.
- **Mode 2 — Historical replay:** Replay last 12 months of trades against the firm using only news/data available at trade date (no leakage). Compare counterfactual portfolio metrics.
- **Mode 3 — Quarterly A/B:** Split tickers by hash; half firm-gated, half raw. Run a quarter; compare PnL. Catches regime drift.

**Acceptance bar for proceeding from shadow to enforcement:**
- `approve-cohort Sharpe ≥ baseline + 0.2` AND `veto-cohort win_rate < baseline - 5pp`.
- Both conditions required to confirm the firm is signaling, not randomly partitioning.

### Tier 4 — Smoke probe (production heartbeat)

- 17:00 daily cron: `python -m engine.agent_firm.smoke` runs one canned BBRI signal.
- Asserts response within 90s, valid decision schema, cost within ±50% of expected.
- Two consecutive failures → admin Telegram alert.

---

## 7. Phasing & Rollout

| Phase | Duration | Risk | Goal |
|-------|----------|------|------|
| 1 — Scaffolding + 2 agents | 1–2 weeks | Low | Plumbing works end-to-end |
| 2 — Full firm shadow mode | 2–3 weeks + 30d observation | Medium | 30-day data + validation gate |
| 3 — Enforcement + MC stats | 1–2 weeks | Low | Veto live + Monte Carlo CIs |

### Phase 1 — Scaffolding + 2 agents (shadow mode, FIRM_ENABLED=false)

Ship: module structure, DeepSeek V4 Pro client, prompt caching, 2 agents (Technical + Risk), LangGraph DAG, new SQLite tables, Tier 1 unit tests, Tier 4 smoke probe, dashboard "OFF" badge.

Gate: `python -m engine.agent_firm.smoke` returns valid decision within 90s; cost logged correctly.

### Phase 2 — Full firm shadow mode (FIRM_ENABLED=true, FIRM_ENFORCE=false)

Ship: remaining 5 agents (Flow, Regime, News, Bull, Bear), Tavily wired into News, full DAG, prompts iterated to v1, Tier 2 recorded-replay tests, dashboard decisions panel, Telegram unchanged (no rationale yet).

Gate (the important one): After 30 calendar days in shadow:
- If approve-cohort Sharpe ≥ baseline + 0.2 AND veto-cohort win_rate < baseline - 5pp → proceed.
- Otherwise: analyze (agents too agreeable? News noisy? Risk too lenient?) and iterate prompts before re-attempting gate.

### Phase 3 — Enforcement + Monte Carlo (FIRM_ENFORCE=true)

Ship: enforcement on, override endpoint live, enriched Telegram format, circuit breaker + spend cap live.

Bonus: borrow Vibe-Trading methodology — add Monte Carlo simulation + bootstrap CIs to `engine/walkforward_multi.py`. New columns in `backtest_cache`: `monte_carlo_p05_return`, `bootstrap_ci_lower`. Surfaces in existing backtest dashboard.

Gate: First 2 weeks of enforcement: total signals/day drops 30–50% (firm is actually vetoing meaningfully); no week with zero alerts; spend under daily cap.

---

## 8. Out of Scope (deferred)

- Independent agent-generated signals (chose veto, not generator).
- Live broker order submission. Paper-trade boundary stays.
- OpenBB workspace integration. Useful later, not core.
- Fine-tuning DeepSeek on historical decisions. Revisit after 6+ months of `agent_decisions` data.
- Portfolio-level optimization. Risk Manager only considers per-signal sizing.
- IDX-specific news scraper (Kontan, Bisnis.com, KSEI). Tavily is sufficient for MVP.

---

## 9. Open Questions

1. **Tavily vs Brave** for the News Analyst web search tool. Tavily is LLM-optimized; Brave is cheaper. Default to Tavily; revisit if cost matters.
2. **Recorded-replay corpus refresh cadence.** Quarterly is a starting point; may need monthly if prompts iterate fast.
3. **News Analyst Indonesian language handling.** DeepSeek V4 Pro handles Bahasa well, but Tavily results may be English-biased. Test in Phase 2.
4. **Daily spend cap value.** $5 is conservative; may bump to $10 once volume is known.

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Firm vetoes good trades | Shadow mode 30d before enforcement; override endpoint live in Phase 3 |
| DeepSeek API outage during scan | Fail-open Risk Manager, circuit breaker, kill switch |
| LLM costs spiral | Daily spend cap, prompt caching, model pinned in config |
| Prompt regressions silently degrade quality | Tier 2 recorded-replay + Tier 4 daily smoke probe |
| Synchronous calls slow 16:00 scan | asyncio parallel calls; budget ~9 min total acceptable |
| China-routed API for sensitive data | Only public market data + own signals sent; no PII |
| Agents agree on everything (no real debate) | Bull/Bear roles explicitly prompted for dissent; monitored via traces |

---

## 11. Success Criteria

The hybrid stack is a success if, six months after enforcement:

1. **Quantitative:** approve-cohort Sharpe ≥ baseline + 0.2 AND veto-cohort win_rate < baseline (durable, not just shadow-period).
2. **Operational:** ≥99% scan-day uptime for firm; ≤1 admin alert per month for degraded mode.
3. **Cost:** Monthly LLM spend ≤ $25.
4. **Usefulness:** Override rate < 20% (you trust the firm's vetoes most of the time).

If any of these fail at month 6, consider rolling back to FIRM_ENFORCE=false (still log decisions, don't gate) and iterate.

---

## 12. References

- NotebookLM comparative analysis: `research_reports/ai_trading_frameworks_idx_fit.md` (2026-05-19)
- TradingAgents paper: arXiv 2412.20138 (multi-agent LLM trading firm architecture)
- DeepSeek V4 Pro docs: <https://api-docs.deepseek.com>
- LangGraph: <https://langchain-ai.github.io/langgraph/>
- Current IDX walkforward architecture: see codebase map produced 2026-05-19
