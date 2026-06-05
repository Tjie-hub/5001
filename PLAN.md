# PLAN.md — Agent Firm Optimization

**Date**: 2026-06-04
**Status**: Phase 1 SHIPPED (2026-06-05, commit 3616700) — Phase 2 ready to start
**Source**: Full agent firm audit (session 2026-06-04) + macro_idx.md crash analysis

---

## Problem Statement

The agent firm (`engine/agent_firm/`) — a 7-agent LLM pipeline for IDX signal evaluation — shipped May 27 (Sprint 11) but has never evaluated a single live signal. Three root causes:

1. **The flow filter starves it.** `scheduler/scanner.py` line 776 gates the agent behind `flow_confirmed`, a list of tickers with Stockbit flow score ≥ 2. In the current bear market (IHSG -34.84%, ARB cascades, Rp 1.5T foreign outflow), zero tickers pass this threshold. The agent is active but idle.

2. **It duplicates existing gates.** The flow filter and trend filter already gate entries. The monitor (`monitor.py`) already handles exits with hardcoded R1-R7 rules every 5 minutes. The agent has no unique role — it's an expensive ($0.01-0.03/signal) observer that never observes.

3. **It's downstream of decisions, not integrated.** Paper trades open/close without the agent. Even in enforce mode, the agent can only remove candidates the flow filter already approved. It cannot promote a rejected ticker, size a position, or override a monitor exit signal.

---

## Current Architecture (Problem)

```
Strategy signals → Flow filter (score ≥ 2) → Trend filter → open_trade()
                         ↓
                    Agent Firm ← [NEVER REACHED — flow_confirmed is empty]
                         
                    monitor.py → R1-R7 rules → close_trade()  [no agent]
```

| Decision | Who makes it | Agent involved? |
|----------|-------------|-----------------|
| Entry gate | Flow filter + Trend filter | ❌ Blocked by empty flow_confirmed |
| Position size | `open_trade()` default lots | ❌ |
| Exit (TP/SL) | `monitor.py` hardcoded | ❌ |
| Exit (regime) | `monitor.py` R1-R6 rules | ❌ |
| Watchlist ranking | None — binary quality gate only | ❌ |

---

## Target Architecture

```
Strategy signals ──→ Agent Firm (2-stage)
                       │
                       ├── Stage 1: Technical + Regime (cheap, $0.004)
                       │      └── Both bearish? → VETO, skip rest
                       │
                       ├── Stage 2: Full 7-agent pipeline ($0.011)
                       │      └── Output: approve/veto + size_hint + conviction
                       │
                       ▼
                  Paper Trade (sized by agent conviction)
                       │
                       ▼
                  Monitor (R1-R7 rules)
                       │
                       ├── Exit signal? → Agent Firm (exit review)
                       │      └── Agent can: confirm exit / override (hold) / reduce size
                       │
                       ▼
                  close_trade() or size adjustment
```

Key changes:
- Agent sits **between** signals and execution, not behind a gate
- Agent receives flow score as **input**, not as a pre-filter
- Agent can **size** positions (the rules can't)
- Agent gets **final say on exits** when monitor rules conflict
- 2-stage pre-scan cuts cost 60-80% in bear markets

---

## ~~Phase 1: Make the Agent Run~~ ✅ SHIPPED (2026-06-05, commit 3616700)

**Goal**: Agent evaluates live signals within cost budget. Ship today. **DONE.**

### 1.1 Remove flow-filter dependency

File: `scheduler/scanner.py`, line 776

```python
# BEFORE
if _firm_cfg.is_active() and flow_confirmed:
    _candidates = [... for r in flow_confirmed]

# AFTER
if _firm_cfg.is_active() and intersection_results:
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
        for r in intersection_results[:20]  # cap at 20 for cost control
    ]
    _decisions = _firm.evaluate(_candidates)
    ...
else:
    print(f"[{time_str}] Agent firm: 0 candidates (intersection_results empty)")
```

Flow score arrives in `SignalCandidate.score` — the Risk Manager sees it as evidence, not as a gate. A score of -5 becomes a reason to veto, not a reason to skip evaluation.

### 1.2 Add idle logging

When `intersection_results` is empty (no strategy signals at all), log it:

```python
if _firm_cfg.is_active() and not intersection_results:
    print(f"[{time_str}] Agent firm: idle (no strategy signals generated)")
```

### 1.3 Cost projection

| Scenario | Candidates | Cost/scan | 5 scans/day |
|----------|-----------|-----------|-------------|
| Bull market | 15-20 | $0.22-0.30 | $1.10-1.50 |
| Bear market | 3-8 | $0.04-0.12 | $0.20-0.60 |
| Dead market | 0 | $0.00 | $0.00 |

All within the $5 daily cap (`AGENT_FIRM_DAILY_CAP`).

---

## Phase 2: Give the Agent Unique Jobs (3-4 hours)

**Goal**: Agent does things the rule-based systems can't.

### 2.1 Position sizing by conviction

File: `scheduler/scanner.py`, after agent evaluation

```python
for d in _decisions:
    if d.decision == "approve" and d.size_hint:
        # Pass size_hint to paper_trade.open_trade()
        # 0.5 = half size, 1.0 = normal, 1.2 = aggressive
        ...
```

The Risk Manager already outputs `size_hint`. It's just never consumed. Wire it into `paper_trade.open_trade()` as an optional `lots_multiplier` parameter.

### 2.2 Bear-watchlist ranking digest

File: new `scheduler/jobs.py` job, runs after daily scan

The scanner already maintains a watchlist of oversold BEAR tickers with quality gates. The agent firm ranks them:

```python
# After the scan, if watchlist has entries:
_candidates = [_SC(ticker=t, strategy="watchlist", score=0, ...) for t in watchlist_tickers]
_decisions = _firm.evaluate(_candidates)
# Sort by confidence descending, send Telegram:
# "🐻 Bear Watchlist — Agent Ranking"
# "1. BBCA (conviction 0.82): strong bull case when BULL regime flips — key support 8,200"
# "2. BBRI (conviction 0.71): oversold, foreign starting to accumulate"
```

### 2.3 Exit review on monitor alerts

File: `monitor.py`, for R2 (ADX-TOPPING) and R4 (DISTRIBUTION) alerts

These rules currently fire alerts but don't auto-close (only R1, R3, R5, R6 auto-close for Swing Trend). When R2 or R4 fires, give the agent a chance to weigh in:

```python
if result['alert_type'] in ('R2_ADX_TOPPING', 'R4_DISTRIBUTION'):
    _decision = _firm.evaluate([_SC(...)])  # single-candidate exit review
    if _decision.decision == "approve":     # agent says "approve the exit"
        close_trade(...)
    else:
        # Agent overrides — hold position, log rationale
```

---

## Phase 3: Cost Optimization (2 hours)

**Goal**: Cut per-signal cost 60-80% without losing decision quality.

### 3.1 Two-stage agent pre-scan

File: `engine/agent_firm/firm.py` — new function `evaluate_staged()`

```
Candidate → Stage 1: Technical + Regime (parallel, ~$0.004)
    ├── Both bearish → auto-VETO, skip remaining 5 agents
    └── At least one bullish → Stage 2: Flow + News + Bull + Bear + Risk (~$0.011)
                                → Final approve/veto + size_hint
```

In bear markets, 60-80% of candidates will fail Stage 1. Cost per 20-candidate scan drops from $0.30 to $0.08-0.12.

### 3.2 Shared market context

File: `engine/agent_firm/firm.py` — `_build_context()`

Currently fetches 8 per-ticker queries for every candidate. Market-wide data (open_trades, IHSG) is re-fetched N times. Cache once per scan:

```python
_market_ctx = None  # module-level, reset each scan

def _build_context(state):
    global _market_ctx
    if _market_ctx is None:
        _market_ctx = {
            "open_trades": query("SELECT ... FROM paper_trades WHERE status='OPEN'"),
            "ihsg": query("SELECT ... FROM ohlcv WHERE ticker='IHSG' ..."),
        }
    return {**state, "market": _market_ctx}
```

Saves 2 redundant queries per candidate (40 queries saved on a 20-candidate scan).

---

## Phase 4: Feedback Loop (future, 4-5 hours)

**Goal**: Agent learns from outcomes. Depends on Phase 1-2 shipping and accumulating ≥50 closed paper trades with agent decisions.

### 4.1 Automated cohort analysis

Weekly cron job: run `analytics.py` cohort_summary + agent_agreement, persist to `agent_performance` table. Telegram digest:

```
📊 Agent Firm Weekly — Jun 1-7
Approve: 12 trades, 58% win, +1.2% avg
Veto:    8 trades (would have been -2.3% avg) ← agent saved Rp XM
```

### 4.2 Confidence threshold tuning

If approval win rate drops below 45%, automatically raise the confidence threshold by 0.1. Persist to `paper_config`. Agent becomes more conservative when it's wrong.

---

## What NOT to Build

- **SELL/short signal path (TODO C1).** IDX has no retail short-selling. A SELL alert you can't act on is noise. Drop from Sprint 18.
- **Full macro context for all 7 agents (TODO C8).** The 2-stage pre-scan (Phase 3.1) achieves 80% of the benefit. Ship that first, then evaluate whether the remaining 5 agents need IHSG/VPIN/breadth context.
- **Enforce mode (TODO C12).** Don't flip `AGENT_FIRM_ENFORCE=true` until Phase 1-2 ship and the agent has evaluated ≥100 live signals in shadow. Premature enforcement = premature optimization.

---

## Success Metrics

| Metric | Current | Target (after Phase 2) |
|--------|---------|------------------------|
| Signals evaluated/day | 0 | 15-100 (market-dependent) |
| Daily API cost | $0.00 | $0.20-1.50 |
| Veto rate (bear market) | N/A | 60-90% |
| Approve win rate | N/A | ≥50% (tracked via cohort) |
| Exit overrides (agent vs monitor) | 0 | ≥1/week with documented rationale |
| Watchlist ranking digest | None | Daily Telegram |

---

## Dependencies

```
Phase 1 (run) ────── no dependencies, ship today
Phase 2 (jobs) ───── depends on Phase 1
Phase 3 (cost) ───── depends on Phase 1, can ship in parallel with Phase 2
Phase 4 (feedback) ─ depends on Phase 2 accumulating ≥50 closed trades (~2-4 weeks)
```