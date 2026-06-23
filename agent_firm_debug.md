# Agent Firm Debug — EOD Trade Plan

## Pipeline

```
4 sources → candidate_score() → top-8 → 2-stage LLM firm → rank_approved → Telegram
```

### Sources merged (longs only)
| Tag | Source | DB Table |
|-----|--------|----------|
| R | Reversal watchlist (broker-flow confirmed) | `reversal_watchlist` |
| S | Daily screen bullish signal | `daily_screen` |
| V | Volume mover (vol_ratio ≥ 5) | `daily_screen` |
| P | Premarket agent approval (same-day) | `agent_decisions` |

### Pre-firm scoring (`candidate_score`)
- R: 2.0 + conviction/50 (max ~4)
- P: 2.0 + premkt_conf × 2 (max ~4)
- S: 1.0
- V: min(vol_ratio/50, 1.0)
- R and P dominate; S+V from same daily_screen row = not independent

## Agent Firm Architecture

7-agent LangGraph DAG using DeepSeek (`deepseek-v4-pro`):

```
build_context → analysts (technical|flow|regime|news) → bull → bear → risk[+guardrails] → persist
```

### Stage 1 (cheap pre-scan)
- Technical + Regime LLM calls in parallel (~$0.004/candidate)
- Both bearish → auto-VETO (saves ~$0.011/candidate)
- Otherwise → Stage 2 full pipeline

### Stage 2 (full 7-agent)
- Risk Manager is the final judge; receives all 6 upstream outputs
- **Post-LLM guardrails** (`_run_risk` in firm.py) override the LLM decision deterministically:
  - Bearish flow not offset by bullish technical → veto
  - Confidence < 0.55 in SIDEWAYS/BEAR regime → veto
  - Guardrails **never** upgrade (veto stays veto)
- If Risk Manager call fails → `degraded` (pass-through)

### Star ratings (visual encoding of confidence)
- ⭐⭐⭐ ≥ 0.70
- ⭐⭐ ≥ 0.55
- ⭐ < 0.55

## 2026-06-23 — YELLOW Regime (pre-fix)

Regime: **YELLOW** (39/100). All picks have **TOXIC** VPIN. Old fail-open logic active.

| # | Ticker | Price | Stars | Conf | Tags | Verdict |
|---|--------|-------|-------|------|------|---------|
| 1 | TLKM | 2,540 | ⭐⭐⭐ | 0.70 | [R] | Cleanest pick — STRONG_BUY, 41.7B net |
| 2 | INTP | 4,190 | ⭐⭐ | 0.65 | [RS] | Solid — foreign buying + buyback vs false breakout risk |
| 3 | ISAT | 1,765 | ⭐⭐ | 0.60 | [R] | OK — support at 1700, foreign inflows |
| 4 | CPIN | 3,150 | ⭐⭐ | 0.55 | [R] | Mixed — bearish tech, bullish accumulation |
| 5 | OASA | — | ⭐⭐ | 0.55 | [P] | **Weak** — flow is BEARISH/MORNING_TRAP (-3), contradicts approval |
| 6 | ASII | 4,680 | ⭐ | 0.50 | [R] | Mixed — bearish tech + regime, strong flow |
| 7 | AKRA | 1,275 | ⭐ | 0.45 | [SP] | **Noise** — quant score 0.0, bearish news, long-term downtrend |

## 2026-06-24 — ORANGE Regime (post-fix) ✅

Regime: **ORANGE** (risk-off). Guardrails active. **All 8 candidates vetoed.**

| # | Ticker | Verdict | Guardrail Hit |
|---|--------|---------|---------------|
| 1 | TLKM | Stage 1 pre-screen | technical BEARISH + regime BEAR |
| 2 | ISAT | Stage 1 pre-screen | technical BEARISH + regime BEAR |
| 3 | NCKL | Veto | SIDEWAYS regime, high macro risk |
| 4 | INTP | Veto | SIDEWAYS regime, toxic VPIN, low quant |
| 5 | AKRA | Veto | SIDEWAYS regime, quant_score=0.0, bearish news |
| 6 | CPIN | Veto | High-conviction bearish tech (0.9) + BEAR regime |
| 7 | ASII | Veto | SIDEWAYS regime, high macro risk, downtrend |
| 8 | OASA | Veto | **guardrail: flow DISTRIBUTING not offset by bullish tech** |

**Key**: OASA would have been approved under the old fail-open logic (same as 23/06). The guardrail caught the bearish-flow-not-offset condition precisely. Old system would have shipped 6-7 junk approvals in a risk-off tape.

## Resolution

**Root cause:** `quant_score` was passed to the Risk prompt on inconsistent scales
(flow composite −5..+5, premarket strength 0-100, EOD conviction 0-100/0.0), so the
prompt veto gate `quant score < 3.0` was dead code for premarket/EOD callers. With
the veto gate dead, only the fail-open bias remained → approve-with-warning band.

**Fixed:** (committed on `feat/edge-score-system`, not yet merged)
1. `engine/agent_firm/guardrails.py` — deterministic post-LLM guardrail in `_run_risk`,
   keyed on analyst VERDICTS (consistent), only downgrades approve→veto:
   - bearish flow (BEARISH/DISTRIBUTING/MORNING_TRAP) not offset by a bullish technical → veto
   - confidence < 0.55 in SIDEWAYS/BEAR regime → veto (kills fail-open band)
2. `normalize_quant()` rescales every caller's score to 0-1; `risk.py` sends the
   normalized `quant_score`; `risk_v2.md` thresholds rewritten to the 0-1 scale + a
   "don't approve <0.55 in SIDEWAYS/BEAR" rule.
3. `edge_enrich.py` — stale wf_edge detection (>7d) logs warning + market_regime
   fallback now logs the exception (was silent).
4. `scheduler/scanner.py` — fixed `sources=()` → `sources=()` in enrich_candidate
   (was passing strategies as both sources and strategies, duplicating MR detection).

**Verified:** 15 guardrail tests + 85 agent_firm tests green. Real-data replay
vetoed MPIX (0.35) and VISI (0.50) fail-open approvals while keeping flow-NEUTRAL
approvals. Live since 21:xx restart 2026-06-23; 24/06 ORANGE regime = all 8 vetoed
(0 false positives).

**Optimizations applied (2026-06-23):**
- `firm.py`: guardrails import moved from inside `_run_risk()` hot path to module level
- `risk.py`: `normalize_quant` import moved to module level
- `guardrails.py`: type annotations tightened (`list` → `Sequence[Any]`), docstrings added

## Still Open

### Apply edge score gate to EOD trade plan
Run `Tier A` directional vetoes before the firm to catch OASA-type contradictions earlier (saves LLM cost on dead candidates). Not urgent — guardrails catch it at the Risk stage now, but pre-screening would skip the $0.015 full pipeline.

### Add a VPIN gate
If VPIN is TOXIC across all picks, flag the entire report as degraded/high-risk. Today the report correctly shows "🟠 Regime ORANGE — risk-off" but a VPIN-based degradation would add another layer.

## Key Files

| File | Role |
|------|------|
| `engine/trade_plan.py` | Gather, score, select top-8, rank approved, build Telegram message |
| `engine/agent_firm/firm.py` | 7-agent LangGraph DAG, 2-stage evaluation, fail-open logic |
| `engine/agent_firm/prompts/risk_v2.md` | Risk Manager prompt — confidence tiers, veto rules, fail-open |
| `engine/agent_firm/agents/risk.py` | Risk Manager agent — returns confidence + decision |
| `engine/edge_enrich.py` | Builds veto-ready candidate dicts (WF edge + flow + regime) |
| `engine/veto.py` | Tier A directional + Tier B statistical vetoes (not in EOD path) |
| `engine/edge_score.py` | Composite edge score (expectancy 40%, flow 20%, consistency 20%, etc.) |
| `scheduler/jobs.py:679` | `run_eod_trade_plan()` orchestrator — runs at 16:40 WIB |
| `screener/reversal_filter.py` | Reversal conviction scoring (40 base + broker/IDX30/depth/delta bonuses) |
