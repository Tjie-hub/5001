# G7: Adaptive Strategy Switching by Regime — Design Spec
_2026-06-05_

## Problem

The system detects regime (BULL/BEAR/SIDEWAYS) per ticker via `detect_regime()` and stores per-strategy WF scores in `wf_scores`. But `get_ticker_best_strategies()` ignores regime — it just ranks by `weighted_score`. Result: a SIDEWAYS ticker could be assigned Trend Following Breakout (a momentum strategy that needs a trend), or a BEAR ticker still gets a strategy assigned at all.

Evidence: BRPT.md Section 5 heatmap shows VWAP Reversion and Conservative outperform in SIDEWAYS/range markets; TFB and Momentum dominate in BULL with moderate ADX.

## Design

### `adaptive_strategy_selector()` — `scheduler/scanner.py`

**Signature:**
```python
def adaptive_strategy_selector(ticker: str, df: pd.DataFrame,
                                min_consistency: float = 50.0) -> list[str]:
```

**Regime → candidate strategies mapping (hard-coded dict):**
```python
_REGIME_STRATEGY_MAP = {
    'BULL_MODERATE': ['Trend Following Breakout', 'momentum', 'Inside Bar Breakout', 'NR7 Breakout'],
    'BULL_STRONG':   ['conservative', 'momentum', 'Trend Following Breakout'],
    'BEAR':          [],   # no entry in bear regime
    'SIDEWAYS':      ['vwap_reversion', 'vol_weighted', 'VWAP Reversion', 'Vol-Weighted Entry'],
}
```

ADX sub-bands (using `calc_adx(df, 14).iloc[-1]`):
- BULL + ADX in [25, 45): `BULL_MODERATE`
- BULL + ADX ≥ 45: `BULL_STRONG`
- BEAR → `BEAR`
- SIDEWAYS → `SIDEWAYS`

**Algorithm:**
1. Detect regime via `detect_regime(df)` → BULL / BEAR / SIDEWAYS
2. For BULL: compute ADX to pick MODERATE vs STRONG sub-band
3. Get candidate strategies from `_REGIME_STRATEGY_MAP[sub_band]`
4. Query `wf_scores` for ticker: keep only candidates that have `consistency_pct >= min_consistency`
5. Sort kept strategies by `weighted_score DESC`
6. If kept list is non-empty → return it
7. Fallback: if no strategies pass WF filter → return `get_ticker_best_strategies(ticker, min_consistency)` (existing behavior)
8. BEAR always returns `[]` (no fallback)

**Note on strategy name normalization:** `wf_scores` stores strategy names as returned by `STRATEGY_FUNCS` keys (e.g., `'Trend Following Breakout'`, `'vwap_reversion'`). The mapping uses the same keys; no normalization needed.

### Integration: `scheduled_multi_strategy_scan()`

Single change — replace line ~621:
```python
# Before
best_strategies = get_ticker_best_strategies(ticker, min_wf_consistency)
# After
best_strategies = adaptive_strategy_selector(ticker, df, min_wf_consistency)
```

Also: add `'adaptive_regime'` key to the signal result dict for Telegram visibility.

### Flask Endpoint — `routes/backtest.py`

`GET /api/scanner/adaptive_strategy/<ticker>` — returns what `adaptive_strategy_selector` would pick for a ticker right now (live, using current OHLCV + wf_scores). Useful for inspection without running a full scan.

Response:
```json
{
  "ticker": "BBCA",
  "regime": "BULL",
  "adx": 31.2,
  "sub_band": "BULL_MODERATE",
  "candidates": ["Trend Following Breakout", "momentum"],
  "selected": ["Trend Following Breakout"],
  "fallback_used": false
}
```

## What is NOT changed

- `detect_regime()` — unchanged
- `get_ticker_best_strategies()` — unchanged (still used as fallback)
- `wf_scores` refresh — unchanged
- Any existing strategy or backtest logic — unchanged

## Tests (`tests/test_adaptive_strategy.py`)

1. `test_bull_moderate_prefers_tfb_momentum` — ADX=30, BULL, wf_scores has TFB at 65% consistency → TFB returned
2. `test_bear_always_returns_empty` — BEAR regime → empty list, no fallback
3. `test_sideways_prefers_vwap_volweighted` — SIDEWAYS, wf_scores has vwap_reversion → returned
4. `test_falls_back_when_no_wf_match` — BULL_MODERATE but wf_scores has no TFB/momentum → falls back to `get_ticker_best_strategies`
5. `test_bull_strong_adx_above_45` — ADX=50, BULL → BULL_STRONG sub-band, conservative/momentum preferred

## Files changed

- `scheduler/scanner.py` — add `adaptive_strategy_selector()`, update `scheduled_multi_strategy_scan()` call
- `routes/backtest.py` — add `GET /api/scanner/adaptive_strategy/<ticker>` endpoint
- `tests/test_adaptive_strategy.py` — new, 5 tests
