# Agent Firm Debug — EOD Trade Plan (2026-06-23)

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
build_context → analysts (technical|flow|regime|news) → bull → bear → risk → persist
```

### Stage 1 (cheap pre-scan)
- Technical + Regime LLM calls in parallel (~$0.004/candidate)
- Both bearish → auto-VETO (saves ~$0.011/candidate)
- Otherwise → Stage 2 full pipeline

### Stage 2 (full 7-agent)
- Risk Manager is the final judge; receives all 6 upstream outputs
- **Fail-open rule**: if uncertain (confidence < 0.5), prefer approve at size_hint 0.5
- If Risk Manager call fails → `degraded` (pass-through)

### Star ratings (visual encoding of confidence)
- ⭐⭐⭐ ≥ 0.70
- ⭐⭐ ≥ 0.55
- ⭐ < 0.55

## Today's Output (2026-06-23)

Regime: **YELLOW** (39/100). All picks have **TOXIC** VPIN.

| # | Ticker | Price | Stars | Conf | Tags | Verdict |
|---|--------|-------|-------|------|------|---------|
| 1 | TLKM | 2,540 | ⭐⭐⭐ | 0.70 | [R] | Cleanest pick — STRONG_BUY, 41.7B net |
| 2 | INTP | 4,190 | ⭐⭐ | 0.65 | [RS] | Solid — foreign buying + buyback vs false breakout risk |
| 3 | ISAT | 1,765 | ⭐⭐ | 0.60 | [R] | OK — support at 1700, foreign inflows |
| 4 | CPIN | 3,150 | ⭐⭐ | 0.55 | [R] | Mixed — bearish tech, bullish accumulation |
| 5 | OASA | — | ⭐⭐ | 0.55 | [P] | **Weak** — flow is BEARISH/MORNING_TRAP (-3), contradicts approval |
| 6 | ASII | 4,680 | ⭐ | 0.50 | [R] | Mixed — bearish tech + regime, strong flow |
| 7 | AKRA | 1,275 | ⭐ | 0.45 | [SP] | **Noise** — quant score 0.0, bearish news, long-term downtrend |

## Key Issues Found

### 1. OASA is a firm hallucination
Underlying flow is **BEARISH** (`MORNING_TRAP`, composite -3). The rationale admits "heavy foreign selling and low quant score" yet the firm approved at 0.55. The bull agent's narrative overrode hard flow data.

### 2. AKRA should not be in the long book
Quant score 0.0, bearish news, TOXIC VPIN, long-term downtrend. The rationale itself says "long-term downtrend limits upside." This is below any reasonable confidence floor.

### 3. Confidence band is suspiciously compressed
0.45–0.70 across 7 picks. In YELLOW/TOXIC with conflicting signals, the fail-open rule means the risk judge defaults to approve-with-warning rather than veto. Result: everything passes in a narrow band.

### 4. Edge score vetoes don't apply here
The Tier A (directional) + Tier B (statistical) vetoes from `engine/veto.py` run in the multi-strategy scanner and premarket firm scan, **not** in the EOD trade plan. The trade plan uses only `candidate_score()`, which is more permissive. AKRA would likely not survive `EDGE_SCORE_MODE=enforce`.

## Possible Fixes

1. **Raise confidence floor in sideways regimes** — reject < 0.55 when regime is YELLOW or BEAR
2. **Wire flow veto into trade plan** — if flow is BEARISH/DISTRIBUTING and confidence < 0.55, auto-veto even if the firm approved
3. **Apply edge score gate to EOD trade plan** — run `Tier A` directional vetoes before the firm to catch OASA-type contradictions
4. **Tighten the fail-open rule** — change from "prefer approve at 0.5" to "veto at 0.5 size_hint" when flow direction contradicts the approval
5. **Add a VPIN gate** — if VPIN is TOXIC across all picks (today), flag the entire report as degraded/high-risk

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
