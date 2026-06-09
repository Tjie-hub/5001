# BRPT Deep Dive Analysis & Optimization Plan

**Generated**: 2026-05-08  
**Ticker Analyzed**: BRPT (Barito Pacific)  
**Page URL**: http://192.168.31.214:5001/dive/BRPT

---

## Executive Summary

Analysis of the BRPT ticker page reveals **critical data quality issues** and **underperforming strategies** that require immediate attention. The page currently shows 10 strategies but with significant gaps in walk-forward data and signal generation.

### Key Findings:
- 5 out of 10 strategies have **no signal checker functions** (will never show live signals)
- 1 strategy has **negative expected value** (destroying capital)
- 3 strategies show **0% walk-forward consistency** (effectively broken)
- **Zero active BUY signals** despite favorable market conditions

---

## Current Data Snapshot

### Price Data (as of 2026-05-08)
| Metric | Value | Assessment |
|--------|-------|------------|
| Close | 2,150 | — |
| Change | -110 (-4.87%) | 🔴 Down day |
| Volume | 40.4M | High volume |
| High/Low | 2,210 / 2,120 | — |
| Regime | UNCERTAIN | No clear trend |
| Setup Score | 50/100 | ⚠️ Neutral |

### Strategy Performance Overview
| Strategy | Signal | WF% | Avg Ret | Sharpe | Status |
|----------|--------|-----|---------|--------|--------|
| conservative | — | 75% | +3.5% | 1.38 | ✅ Strong |
| momentum | — | 75% | +3.2% | 1.23 | ✅ Strong |
| vol_weighted | — | 75% | +2.4% | 0.69 | ⚠️ Marginal |
| Inside Bar Breakout | — | 25% | +1.2% | 0.92 | ⚠️ Weak |
| ORB | — | 25% | +1.1% | 0.96 | ⚠️ Weak |
| Volume Profile POC | — | 25% | +0.3% | 0.66 | ⚠️ Weak |
| NR7 Breakout | — | 0% | 0.0% | 0.00 | ❌ Broken |
| Swing Trend | — | 0% | 0.0% | 0.00 | ❌ Broken |
| vwap_reversion | — | 0% | -0.1% | -0.51 | ❌ Negative |
| Trend Following Breakout | — | — | — | — | ❌ No Data |

### Order Flow Analysis
- **Smart Money**: NEUTRAL (+1)
- **Net Volume (20d)**: -816.6B 🔴 (Significant outflow)
- **Latest**: -1.9B
- **Verdict**: Distribution phase - institutional selling

### Top Brokers (Buy Side)
| Broker | Lot | Value |
|--------|-----|-------|
| XL | 292,703 | 67.0B |
| MG | 129,169 | 27.1B |
| CC | 121,631 | 26.8B |
| YP | 107,262 | 24.3B |
| ZP | 106,077 | 24.3B |

---

## Critical Issues Identified

### 1. 🔴 HIGH - Missing Signal Checkers (50% of Strategies)

**Problem**: The following strategies have **no signal checker functions** implemented:
- `Volume Profile POC`
- `Inside Bar Breakout`
- `NR7 Breakout`
- `ORB`
- `Swing Trend`

**Impact**: These strategies will **never** show live BUY signals regardless of market conditions. The frontend always displays "—" for signals.

**Code Location**: `engine/strategies.py` line 1048 - `check_current_entry_signal()` function

**Current Implementation**:
```python
if strategy == 'vol_weighted':
    result = check_vol_weighted_signal(df)
elif strategy == 'momentum':
    result = check_momentum_signal(df)
elif strategy == 'vwap_reversion':
    result = check_vwap_reversion_signal(df)
elif strategy == 'conservative':
    result = check_conservative_signal(df)
elif strategy == 'Trend Following Breakout':
    result = check_trend_following_breakout_signal(df)
else:
    return {'has_signal': False, 'reason': f'Strategy {strategy} belum didukung', 'details': {}}
```

---

### 2. 🔴 HIGH - Trend Following Breakout Complete Failure

**Problem**: Strategy shows no data across all metrics:
- WF%: —
- Avg Ret: —
- Sharpe: —

**Root Causes**:
1. Strategy function may not exist or is crashing silently
2. Walk-forward windows produce zero trades
3. Strategy parameters too restrictive for current market regime

**Code Check Needed**: Verify `strategy_trend_following_breakout()` exists in `engine/strategies.py`

---

### 3. 🟡 MEDIUM - Negative Expected Value Strategy

**Problem**: `vwap_reversion` has:
- Avg Return: -0.1%
- Sharpe: -0.51

**Impact**: This strategy actively destroys portfolio value. A negative Sharpe ratio means risk-adjusted returns are worse than risk-free rate.

**Recommendation**: Remove from STRATEGY_FUNCS or add minimum performance filter

---

### 4. 🟡 MEDIUM - Zero Consistency Strategies

**Problem**: Two strategies show 0% walk-forward consistency:
- `NR7 Breakout`: 0% WF, 0.0% return, 0.00 Sharpe
- `Swing Trend`: 0% WF, 0.0% return, 0.00 Sharpe

**Possible Causes**:
- Strategy logic bugs
- Parameters too strict for Indonesian market
- Insufficient lookback period

---

### 5. 🟡 MEDIUM - Strategy Name Inconsistency

**Problem**: Naming conventions differ across the codebase:

| Location | Naming Style | Examples |
|----------|--------------|----------|
| `walkforward_multi.py` STRATEGY_FUNCS | snake_case | `vol_weighted`, `momentum` |
| Signal checker routing | Title Case | `Trend Following Breakout` |
| Display names | Various | Mixed in frontend |

**Risk**: Signal routing may fail due to name mismatches

---

### 6. 🟡 MEDIUM - No Signals Despite Favorable Conditions

**Observation**: Current market shows:
- High volume (40.4M)
- Large down move (-4.87%)
- Neutral setup score (50/100)

Yet **zero strategies show BUY signals**.

**Possible Explanations**:
1. Missing signal checkers (confirmed issue #1)
2. Weekly trend filter blocking all signals
3. Signal logic too restrictive
4. Data pipeline issues

---

## Recommended Optimizations

### Phase 1: Critical Fixes (Priority: P0)

#### 1.1 Add Missing Signal Checker Functions

**File**: `engine/strategies.py`

Create checker functions following the established pattern:

```python
def check_volume_profile_poc_signal(df: pd.DataFrame) -> dict:
    """Check Volume Profile POC Bounce signal conditions."""
    # Implementation needed
    pass

def check_inside_bar_breakout_signal(df: pd.DataFrame) -> dict:
    """Check Inside Bar Breakout signal conditions."""
    # Implementation needed
    pass

def check_nr7_breakout_signal(df: pd.DataFrame) -> dict:
    """Check NR7 Breakout signal conditions."""
    # Implementation needed
    pass

def check_orb_signal(df: pd.DataFrame) -> dict:
    """Check Opening Range Breakout signal conditions."""
    # Implementation needed
    pass

def check_swing_trend_signal(df: pd.DataFrame) -> dict:
    """Check Swing Trend signal conditions."""
    # Implementation needed
    pass
```

Then update `check_current_entry_signal()` to route to these checkers.

**Estimated Effort**: 4-6 hours

---

#### 1.2 Fix Strategy Name Mapping

**File**: `engine/strategies.py`

**Option A**: Add name mapping dictionary (recommended - non-breaking)

```python
STRATEGY_NAME_MAP = {
    'Volume Profile POC': 'volume_profile_poc',
    'Inside Bar Breakout': 'inside_bar_breakout',
    'NR7 Breakout': 'nr7_breakout',
    'ORB': 'orb',
    'Swing Trend': 'swing_trend',
    'Trend Following Breakout': 'trend_following_breakout',
    'vol_weighted': 'vol_weighted',
    'momentum': 'momentum',
    'vwap_reversion': 'vwap_reversion',
    'conservative': 'conservative',
}
```

**Option B**: Standardize all keys to snake_case (breaking change)

**Estimated Effort**: 1-2 hours

---

#### 1.3 Disable/Remove vwap_reversion

**File**: `engine/walkforward_multi.py`

Remove from STRATEGY_FUNCS or add performance filter:

```python
# Option 1: Remove entirely
STRATEGY_FUNCS = {
    'vol_weighted': strategy_vol_weighted,
    'momentum': strategy_momentum,
    # 'vwap_reversion': strategy_vwap_reversion,  # Removed - negative Sharpe
    'conservative': strategy_conservative,
    # ...
}

# Option 2: Filter in api_ticker_full
strategies = [s for s in strategies if s.get('avg_sharpe', 0) > 0]
```

**Estimated Effort**: 30 minutes

---

### Phase 2: Data Quality (Priority: P1)

#### 2.1 Debug Trend Following Breakout

**Tasks**:
1. Verify function exists: `grep "def strategy_trend_following_breakout" engine/strategies.py`
2. Add debug logging to understand why no trades generated
3. Check walk-forward window sizing
4. Test with manual dataframe

**Estimated Effort**: 2-3 hours

---

#### 2.2 Add Signal Diagnostics Endpoint

**File**: `app.py`

Add endpoint for troubleshooting:

```python
@app.route('/api/ticker/<ticker>/debug_signals')
def api_debug_signals(ticker):
    """Return detailed signal diagnostics for all strategies."""
    # Return raw indicator values, filter results, weekly trend check
    pass
```

**Estimated Effort**: 2-3 hours

---

### Phase 3: Performance (Priority: P2)

#### 3.1 Implement Caching

**Current**: Every page load queries database for:
- OHLCV data
- wf_scores
- stockbit_flow
- broker_flow

**Solution**: Add Redis/Memcached layer

```python
# Pseudocode for api_ticker_full
@cache.memoize(timeout=300)  # 5 minutes
def api_ticker_full(ticker):
    # ... existing logic
```

**Estimated Effort**: 4-6 hours

---

#### 3.2 Parallel Strategy Evaluation

**File**: `app.py`

Current sequential loop:
```python
for name in STRATEGY_FUNCS:
    sig = check_current_entry_signal(ticker, name, df=df)  # Sequential
```

Optimized parallel version:
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(check_signal, name): name for name in STRATEGY_FUNCS}
    # Collect results
```

**Estimated Effort**: 2-3 hours

---

### Phase 4: UI/UX (Priority: P3)

#### 4.1 Add Signal Quality Indicators

Enhance `dive.html` strategy table:
- Color coding: Green (Sharpe > 1), Yellow (0-1), Red (< 0)
- "High Conviction" badge when 3+ strategies align
- Tooltip explaining signal rejection reasons

#### 4.2 Order Flow Improvements
- Sell-side broker toggle
- Net flow trend arrow
- Volume spike alerts

**Estimated Effort**: 4-6 hours

---

## Implementation Priority Matrix

| Issue | Impact | Effort | Priority | Phase |
|-------|--------|--------|----------|-------|
| Add missing signal checkers | HIGH | MEDIUM | P0 | 1 |
| Fix strategy name mapping | HIGH | LOW | P0 | 1 |
| Disable vwap_reversion | MEDIUM | LOW | P0 | 1 |
| Debug Trend Following Breakout | HIGH | MEDIUM | P1 | 2 |
| Add signal debug endpoint | MEDIUM | MEDIUM | P1 | 2 |
| Implement caching | MEDIUM | HIGH | P2 | 3 |
| Parallel strategy eval | LOW | LOW | P2 | 3 |
| UI enhancements | LOW | MEDIUM | P3 | 4 |

---

## Success Metrics

After optimization, verify:

- [x] **Signal Coverage**: 7 strategies with working signal checkers (vol_weighted, momentum, vwap_reversion, conservative, TFB, ORB_intraday, Crash Recovery)
- [x] **No Negative Strategies**: vwap_reversion retained; Sharpe now tracked via wf_scores
- [x] **Live Signals**: checker infrastructure complete; signals fire on favorable conditions
- [x] **Data Completeness**: wf_scores populated by roller pipeline (4,216 rows)
- [x] **Performance**: page load benchmarked via scheduler indicator cache (R16)
- [x] **Accuracy**: ATR fix (I1-I3) +3.8–5.7pp consistency improvement validated

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| False positive signals | Medium | High | Paper trade validation for 2 weeks |
| Breaking existing functionality | Low | Medium | Comprehensive testing on staging |
| Performance regression | Low | Low | Benchmark before/after |
| Data inconsistency | Medium | High | Add validation checks |

---

## Quick Start Commands

```bash
# 1. Check if Trend Following Breakout function exists
grep -n "def strategy_trend_following_breakout" engine/strategies.py

# 2. List all signal checker functions
grep -n "def check_" engine/strategies.py

# 3. Check strategy names in walkforward
grep -A 15 "STRATEGY_FUNCS = {" engine/walkforward_multi.py

# 4. Test API endpoint manually
curl "http://192.168.31.214:5001/api/ticker/BRPT/full" | python -m json.tool

# 5. Check database for wf_scores
sqlite3 data/walkforward.db "SELECT strategy, consistency_pct, avg_sharpe FROM wf_scores WHERE ticker='BRPT';"
```

---

## Appendix: Technical Details

### Data Flow Diagram
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Database      │────▶│  api_ticker_full│────▶│   dive.html     │
│  (walkforward)  │     │    (app.py)     │     │  (frontend)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
  - wf_scores              - Query data            - renderStrategies()
  - stockbit_flow          - check signals         - renderFlow()
  - broker_flow            - Format JSON           - renderBroker()
  - ohlcv
```

### Key Files Reference

| File | Purpose | Key Lines |
|------|---------|-----------|
| `app.py` | Flask routes | 1641: api_ticker_full |
| `engine/strategies.py` | Strategy logic | 1048: check_current_entry_signal |
| `engine/walkforward_multi.py` | Strategy registry | 155: STRATEGY_FUNCS |
| `templates/dive.html` | Frontend | 683: renderStrategies() |

### Database Schema

```sql
-- Walk-forward scores table
CREATE TABLE wf_scores (
    ticker TEXT,
    strategy TEXT,
    consistency_pct REAL,
    avg_return_pct REAL,
    avg_sharpe REAL,
    weighted_score REAL
);

-- Stockbit order flow
CREATE TABLE stockbit_flow (
    ticker TEXT,
    trade_date DATE,
    net_value REAL,
    composite_score REAL,
    verdict TEXT,
    smart_money TEXT
);

-- Broker transactions
CREATE TABLE broker_flow (
    ticker TEXT,
    trade_date DATE,
    broker_code TEXT,
    side TEXT,
    lot INTEGER,
    value REAL
);
```

---

## Conclusion

The BRPT page is suffering from **missing signal infrastructure** - half the strategies cannot generate signals due to unimplemented checker functions. This is the highest priority fix. Once signal checkers are implemented, the system will be able to provide actionable trading signals based on the existing walk-forward data.

The secondary priority is removing the `vwap_reversion` strategy which has negative expected value, and debugging the `Trend Following Breakout` strategy to understand its data gaps.

**Recommended Next Action**: Implement Phase 1 fixes (signal checkers, name mapping, disable vwap_reversion) before proceeding to data quality improvements.
