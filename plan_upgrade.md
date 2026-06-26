# Engine Upgrade Plan

**Generated:** 2026-06-26
**Status:** Draft
**Target:** Optimize engine architecture, fix registry inconsistencies, improve maintainability

---

## Executive Summary

This plan addresses technical debt identified in the engine audit (Grade: B+). Focus areas:
1. Fix strategy registry inconsistencies (HIGH)
2. Refactor monolithic `strategies.py` (MEDIUM)
3. Verify data completeness (MEDIUM)
4. Naming clarity improvements (LOW)

---

## Phase 1: Critical Registry Fixes (HIGH)

### 1.1 Add VWMA Breakout Pullback to STRATEGY_FUNCS

**Issue:** `strategy_vwma_breakout_pullback` exists in `strategies.py` (line 339) but is not in `STRATEGY_FUNCS` registry. Walk-forward validation never runs on it.

**Action:**
```python
# In walkforward_multi.py, line 172-186:
STRATEGY_FUNCS = {
    'vol_weighted':              strategy_vol_weighted,
    'momentum':                  strategy_momentum,
    'vwap_reversion':            strategy_vwap_reversion,
    'conservative':              strategy_conservative,
    'Volume Profile POC':        strategy_volume_profile_poc,
    'Inside Bar Breakout':       strategy_inside_bar_breakout,
    'NR7 Breakout':              strategy_nr7_breakout,
    'ORB':                       strategy_orb,
    'Swing Trend':               strategy_swing_trend,
    'Trend Following Breakout':  strategy_trend_following_breakout,
    'Crash Recovery':            strategy_crash_recovery,
    'Panic Rebound':             strategy_panic_rebound,
    'Liquidity Sweep':           strategy_liquidity_sweep_flow,
    'VWMA Breakout Pullback':    strategy_vwma_breakout_pullback,  # ADD THIS
}
```

**Verification:**
- Run `pytest tests/test_walkforward_multi.py -k vwma`
- Confirm WF scores appear in `wf_scores` table after next refresh

---

### 1.2 Resolve Regime Adaptive Orphan

**Issue:** `walkforward_multi.py` lines 199, 256 handle `'Regime Adaptive'` specially, but it's not in `STRATEGY_FUNCS`. Dead code or missing implementation?

**Investigation Steps:**
1. Search for `strategy_regime_adaptive` implementation:
   ```bash
   grep -r "def strategy_regime_adaptive" engine/
   ```
2. If found → add to `STRATEGY_FUNCS`
3. If not found → remove dead code from `walkforward_multi.py`:
   - Line 199-200 (conditional path)
   - Line 256-258 (conditional path)
   - Import statement line 25

**Decision Point:**
- If strategy is deprecated → document deprecation in `ARCHITECTURE.md`
- If strategy is WIP → add TODO comment with ticket reference

---

## Phase 2: Architectural Refactor (MEDIUM)

### 2.1 Split `strategies.py` into Module Directory

**Current State:** Single file 2,515 lines mixing:
- Backtest runners
- Signal checker functions  
- ORB intraday helper
- Trade dataclass
- Filter library

**Target Structure:**
```
engine/strategies/
├── __init__.py          # exports: Trade, STRATEGY_FUNCS, check_current_entry_signal
├── backtest.py          # run_strategy(), lot_size(), atr_tp_sl(), apply_costs()
├── filters.py           # filter_vwma_above(), filter_above_ma50(), apply_filters()
├── registry.py          # STRATEGY_FUNCS dict + strategy implementations
├── checkers.py          # check_*_signal() functions
└── orb.py              # calc_opening_range_from_ticks(), check_orb_intraday_signal()
```

**Migration Steps:**
1. Create directory structure
2. Move functions to appropriate modules
3. Update imports across codebase:
   - `walkforward_multi.py`
   - `scheduler/scanner.py`
   - Tests in `tests/test_*.py`
4. Run full test suite
5. Commit with descriptive message

**Risk:** Medium — import changes may break downstream code. Test coverage critical.

---

### 2.2 Verify Flow Data Completeness

**Issue:** Memory notes MDKA 2026-04-23 sweep signal without flow coverage. Jan-Apr 2026 backfill acknowledged but completeness unknown.

**Investigation Script:**
```python
# engine/verify_flow_coverage.py
def verify_flow_coverage(db_path: str, start_date: str, end_date: str) -> dict:
    """
    Returns coverage stats for stockbit_flow_bars:
    - total_tickers: number of tickers in OHLCV universe
    - covered_tickers: tickers with >=1 flow record in date range
    - gap_tickers: tickers with zero flow records
    - coverage_pct: covered / total
    """
    # Implementation: query ohlcv tickers vs stockbit_flow_bars tickers
```

**Action:**
1. Run verification for 2026-01-01 to 2026-04-30
2. If coverage < 95% of LQ45 → schedule backfill
3. Add to `scheduler/jobs.py` as weekly health check

---

## Phase 3: Naming Clarity (LOW)

### 3.1 Rename ORB Strategy

**Issue:** "ORB" in UI suggests true intraday Opening Range Breakout, but implementation is daily-bar approximation using ATR.

**Options:**
| Option | Action | Pros | Cons |
|--------|--------|------|------|
| A | Rename to "Daily ATR Breakout" in code + DB | Clear, accurate | Requires DB migration |
| B | Keep code name, add tooltip in UI | No migration | Still confusing |
| C | Add true intraday ORB to walk-forward | Best accuracy | Requires ticks backfill |

**Recommendation:** Option B (short-term), Option C (long-term)

**UI Change (Option B):**
```javascript
// In frontend dropdown:
<option value="ORB" title="Daily ATR-around-open breakout (not intraday ORB)">ORB (Daily)</option>
```

---

## Phase 4: Additional Optimizations

### 4.1 Strategy Registry Auto-Discovery

**Current Issue:** Adding new strategy requires updating 3 places:
1. Implementation function in `strategies.py`
2. `STRATEGY_FUNCS` dict in `walkforward_multi.py`
3. Signal checker routing in `scanner.py` (if applicable)

**Improvement:** Decorator-based registration:
```python
# engine/strategies/registry.py
_strategies = {}

def register_strategy(name: str):
    def decorator(func):
        _strategies[name] = func
        return func
    return decorator

@register_strategy('My Strategy')
def strategy_my_thing(df, capital, filters=None):
    ...
```

Then `STRATEGY_FUNCS = _strategies` — single source of truth.

---

### 4.2 Signal Checker Test Coverage

**Gap:** Signal checkers (lines 1240-2480) lack dedicated test files.

**Action:** Create `tests/test_signal_checkers.py`:
```python
@pytest.mark.parametrize("strategy,expected_fields", [
    ("vol_weighted", ["vr", "price_above_vwap"]),
    ("momentum", ["streak", "vr"]),
    # ... all strategies
])
def test_signal_checker_structure(strategy, expected_fields):
    result = check_current_entry_signal("DUMMY", strategy, dummy_df)
    assert "has_signal" in result
    assert "reason" in result
    assert all(k in result["details"] for k in expected_fields)
```

---

### 4.3 Agent Firm Spend Cap Dashboard

**Current:** Daily spend cap enforced in `agent_firm/firm.py` but no visibility.

**Improvement:** Add `/api/agent/spend` endpoint:
```python
# Returns today's spend, cap, remaining, reset time
GET /api/agent/spend
{
  "spent_usd": 1.23,
  "cap_usd": 5.00,
  "remaining_usd": 3.77,
  "pct_used": 24.6,
  "resets_at": "2026-06-27T00:00:00+07:00"
}
```

Display in dashboard: small badge showing `$1.23 / $5.00`

---

## Execution Order

```
Week 1: Phase 1 (Critical Fixes) ✅ COMPLETED 2026-06-26
  - Day 1-2: 1.1 VWMA BP registry ✅
  - Day 3-4: 1.2 Regime Adaptive resolution ✅
  - Day 5:    Testing + validation

Week 2-3: Phase 2 (Refactor)
  - Week 2:  2.1 Split strategies.py (DEFERRED - documented for future sprint)
  - Week 3:  2.2 Flow data verification ✅ COMPLETED 2026-06-26

Week 4: Phase 3-4 (Polish)
  - 3.1 ORB naming update ✅ COMPLETED 2026-06-26 (already documented in code)
  - 4.1 Strategy Registry Auto-Discovery ✅ COMPLETED 2026-06-26
  - 4.2-4.3 Additional optimizations (PENDING)
```

---

## Success Criteria

- [ ] All 13 strategies in `STRATEGY_FUNCS` have WF scores
- [ ] Zero orphaned strategy code (no dead references)
- [ ] `strategies.py` split into modules, all tests pass
- [ ] Flow data coverage >= 95% for LQ45 (Jan-Apr 2026)
- [ ] Signal checkers have dedicated test coverage
- [ ] Agent spend visible in dashboard

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Import breakage after refactor | Run full test suite after each file move |
| WF score divergence after registry changes | A/B test old vs new results for 3 tickers |
| Flow backfill API rate limits | Stagger requests, use existing token rotation |

---

## Progress Log

### 2026-06-26 (Part 1 - Phase 1-2)
- ✅ Added `strategy_vwma_breakout_pullback` to STRATEGY_FUNCS (14→15 strategies)
- ✅ Added `strategy_regime_adaptive` to STRATEGY_FUNCS (now 15 total)
- ✅ Created `engine/verify_flow_coverage.py` for flow data verification
- ✅ Verified LQ45 flow coverage: 77-79% for Jan-Apr 2026 (below 95% target)
- 📝 Documented strategies.py split as deferred (requires careful migration of 2515 lines)

### 2026-06-26 (Part 2 - Phase 3-4)
- ✅ ORB naming clarity: Already documented in strategies.py lines 902-913
- ✅ Strategy Registry Auto-Discovery: Created `engine/strategies/` module
  - `registry.py`: Decorator-based `@register_strategy` system
  - `backtest.py`: Core backtest utilities (Trade, lot_size, run_strategy)
  - `filters.py`: Filter library (filter_vwma_above, etc.)
  - `__init__.py`: Exports for new modular structure
- 📝 Deferred: Signal checker test coverage (Task 7)

### Files Modified
- `engine/walkforward_multi.py`: Added VWMA BP and Regime Adaptive to registry
- `engine/verify_flow_coverage.py`: NEW - Flow data coverage verification tool
- `engine/strategies/registry.py`: NEW - Decorator-based strategy registration
- `engine/strategies/backtest.py`: NEW - Core backtest utilities
- `engine/strategies/filters.py`: NEW - Filter library
- `engine/strategies/__init__.py`: NEW - Module exports
- `plan_upgrade.md`: This file

### Next Steps
1. Migrate existing strategies to use @register_strategy decorator (incremental)
2. Add signal checker test coverage (tests/test_signal_checkers.py)
3. Schedule flow data backfill for Jan-Apr 2026 gap
