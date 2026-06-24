# Flow-Confirmed Liquidity Sweep — Design

**Date:** 2026-06-24
**Status:** APPROVED — ready for implementation plan
**Branch:** `feat/flow-confirmed-sweep`

---

## Goal

A long-only liquidity-sweep entry that fires on a structural PDL/PWL stop-hunt **and** is confirmed by order flow when flow data exists. Validated on full OHLCV history for the structural edge; the flow-confirmation uplift is measured on the recent 30–41-day window as a shadow test, not a walk-forward claim.

## Background & Findings

### What already exists
- **`engine/smc.py`** (complete, created 2026-06-24, wired into nothing): `detect_liquidity_sweep`, `calc_sweep_signal`, FVG, premium/discount, composite. The sweep logic is correct — PDL/PWL bullish trap = break below prior low, wick ≥30% of bar range, close back above → `signal=1`.
- **Flow-confirmation layer already in the engine** (the pasted cross-session analysis missed this):
  - `engine/edge_score.py` — `norm_flow(composite_score)`, weighted edge score (expectancy + consistency + flow + regime + technical votes).
  - `engine/edge_enrich.py` — `_flow_direction` / `_latest_flow` per-ticker verdict.
  - `engine/premover_detector.py` — `score_ticker(..., flow_score=...)` with `FLOW_POS`.
- **`engine/delta_flow.py`** — intraday 1-min delta/CVD/footprint reader over `stockbit_flow_bars`: `session_delta_stats`, `stacked_imbalances`, `cvd`, `delta_by_price`.

The real gap is narrow: **SMC structure is not joined to the existing flow layer.** A wiring problem, not a missing capability.

### Data constraints (decisive)
| Source | Granularity | Coverage | Span |
|---|---|---|---|
| `stockbit_flow_bars` | 1-min delta/CVD | 867 tickers | 2026-04-20 → 06-23 (**30 days**) |
| `stockbit_flow` | daily `composite_score` ∈ [−8,+8] + verdict | 972 tickers | 2026-04-10 → 06-24 (**41 days**) |
| OHLCV | daily | full universe | years |

**There is no flow data before April 2026.** A 5-year flow-confirmed backtest is impossible. Validation must split: structural edge on full history (price-only), flow uplift on the 30–41-day window only.

### Debug findings (not addressed by this plan unless noted)
1. **FVG signal is direction-agnostic** — `calc_fvg_signal` (smc.py:236) fires True for any unfilled FVG, bullish or bearish, but `strategy_fvg_fill` is long-only → would buy bearish-FVG fills (overhead supply). **Decision: do not build the FVG strategy; add a one-line deprecation note to `calc_fvg_signal`.**
2. **`filter_in_discount` (`close < open`)** is just "red candle today," not a premium/discount reference. **Decision: not built.**
3. **Operational** (`docs/update.md`): scheduler down, `openai` missing (agent firm + bear watchlist fail silently), VPIN/keystats stale. **Out of scope** for this plan.

## Architecture

One strategy, one code path; behavior diverges only on data availability.

```
calc_sweep_signal(df)  ──True──▶  confirm_sweep_flow(ticker, date)  ──not-rejected──▶  ENTER (long, ATR SL×1.0 / TP×2.5)
   (full OHLCV history)              (daily tier / intraday tier / none)
```

### Components

**1. `engine/smc_flow.py`** (new) — the flow-confirmation gate.
```
confirm_sweep_flow(ticker, date, db_path=DB_PATH)
    -> {'confirmed': bool, 'source': 'daily'|'intraday'|'none', 'reason': str, 'score': float|None}
```
- **Daily tier** (`stockbit_flow`): `composite_score > 0` on the sweep day → smart money accumulating into the trap, not distributing.
- **Intraday tier** (`stockbit_flow_bars` via `delta_flow`): absorption (above-average session volume + `total_delta` not strongly negative) OR positive net delta on the sweep day → reversal-absorption / trapped-traders confirmation.
- **Gate semantics — the crux:**
  - **Fail-open on missing data** — no flow row for (ticker, date), or date < 2026-04-10 → `source='none'`, `confirmed=True` (passthrough). Lets the full-history backtest run price-only.
  - **Fail-closed on negative flow** — flow present and `composite_score <= 0` (daily) or strongly negative delta (intraday) → `confirmed=False`. Live trades are gated by real flow.

**2. `engine/strategies.py`** — `strategy_liquidity_sweep_flow(df, ticker, ...)` + `check_sweep_flow_signal(df, ticker)`.
- Entry: `calc_sweep_signal(df)` True AND `confirm_sweep_flow(...)['confirmed']`. Long-only, ATR SL×1.0 / TP×2.5 (RR 2.5), via `run_strategy`. Registered in the strategy registry for WF + scanner pickup. `check_sweep_flow_signal` returns the live last-bar signal for scanner/Telegram.

**3. `scheduler/scanner.py`** — sweep+flow candidate in the multi-strategy scan, behind the existing Rp 5B value-liquidity gate and WF consistency ≥50% gate.

**4. Validation harness** (`scratchpad/` script → results into a markdown report; not committed runtime code):
- **(a) Structural backtest** — price-only sweep across LQ45 full history → expectancy / consistency / Sharpe / max-DD vs existing strategies. The real WF claim.
- **(b) Flow A/B** — same sweep signals on the 30–41-day window, with vs without the flow gate → win-rate & expectancy delta, reported with explicit small-sample caveat.

### Data flow
- Old-date backtest → `confirm_sweep_flow` returns `source='none'` → price-only sweep.
- Recent / live → flow gate active → `composite_score>0` and/or intraday absorption required.

## Error handling
- Missing flow table / date / ticker → passthrough (`source='none'`, `confirmed=True`).
- Decimal/string types from SQLite rows → explicit `float()` conversion with try/except (per the `_get_poc_hvn` bug in update.md).
- `calc_sweep_signal` date-string matching: ensure `df['date']` is normalized to `YYYY-MM-DD` before compare.

## Testing
- Golden tests on `detect_liquidity_sweep` with synthetic PDL/PWL sweep bars (known wick %, known signal).
- `confirm_sweep_flow` unit tests: daily-positive (confirmed), daily-negative (rejected), intraday-absorption (confirmed), missing-data (passthrough), pre-April date (passthrough).
- `strategy_liquidity_sweep_flow` integration test: sweep+positive flow enters; sweep+negative flow does not.
- A/B harness sanity test.
- All via `./venv/bin/python -m pytest` (system `pytest` uses the wrong interpreter — missing `feedparser` → false collection errors).

## Out of scope (YAGNI)
- FVG strategy, `filter_in_discount` strategy.
- Operational fixes (scheduler, `openai`, stale VPIN/keystats).
- Dashboard overlays, Telegram formatting (can follow once the strategy is validated).
