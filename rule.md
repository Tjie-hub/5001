# Paper Trade SL & TP Rules

## Overview
Paper trades are automatically managed with **Stop Loss (SL)** and **Take Profit (TP)** levels that trigger auto-close on hit. Additionally, **Swing Trend** trades are governed by 7 exit rules (R1–R7) that take precedence over price-based exits.

---

## Stop Loss (SL) Rules

### SL Calculation at Entry

**Primary Method (ATR-based):**
- `SL = Entry Price - (2 × ATR14)`
- ATR14 is calculated from recent 14-period data
- Provides volatility-adjusted stops

**Fallback Method (Explicit or Config-based):**
- If explicit SL provided (e.g., from screener): use it directly
- Otherwise use config default: `sl_pct = 2.5%`
- `SL = Entry Price × (1 - 0.025)`

### SL Auto-Close Trigger
- **Condition:** `Current Price ≤ SL Price`
- **Action:** Immediately close trade at or below SL
- **Alert:** 🚨 STOP LOSS HIT — AUTO-CLOSED
- **Severity:** CRITICAL

### SL Trailing (Dynamic Adjustment)
Trailing stops only activate **after profitable entries**:

1. **At +1 ATR profit (Entry + 1×ATR14):**
   - Move SL to **breakeven** (Entry Price)
   - Locks in 0% loss protection

2. **At +2 ATR profit (Entry + 2×ATR14):**
   - Move SL to **1 ATR below highest seen**
   - Protects gains while allowing upside room
   - Formula: `New SL = max(Original SL, Highest Price - ATR14)`

3. **SL Moving Rules:**
   - SL **only moves UP** (never lowers)
   - `New SL = max(Current SL, Calculated SL)`
   - If highest seen drops, SL does **NOT move down**

### Near SL Warning
- **Condition:** `Current Price ≤ SL × 1.005` (within 0.5% of SL)
- **Alert:** ⛔ APPROACHING SL
- **Severity:** HIGH
- **Action:** Manual review suggested; consider cutting loss

---

## Take Profit (TP) Rules

### TP Calculation at Entry

**For Momentum Following Strategy:**
- **Primary:** `TP = Entry Price + (3 × ATR14)`
- **Fallback:** `TP = Entry Price × 1.06` (6%) if no ATR
- **Minimum Enforced:** 2:1 Risk-to-Reward ratio
  - Ensures `TP - Entry ≥ 2 × (Entry - SL)`

**For Swing Trend Strategy:**
- **Display Target:** `TP = Entry + (3 × SL Distance)` (display only)
- **Real Exit:** Via **R1–R7 rules** (not price-based)
- TP price is informational; actual exit determined by technical rules

**For Swing High Detection (calc_swing_tp):**
- Detects swing highs: `high > 2 bars left AND 2 bars right`
- Selects closest swing high above entry (with 0.5% margin)
- Applies -0.5% discount: `TP = Swing High × 0.995`
- Enforces minimum 2:1 R/R ratio
- Fallback: `TP = Entry + (2 × ATR14)` with minimum 2% if no swing

### TP Auto-Close Trigger
- **Condition:** `Current Price ≥ TP Price`
- **Action:** Immediately close trade at or above TP
- **Alert:** ✅ TAKE PROFIT HIT — AUTO-CLOSED
- **Severity:** INFO
- Partial fills beyond TP price still auto-close

---

## Swing Trend Exit Rules (R1–R7)

For trades with strategy **"Swing Trend"**, 7 technical rules override pure price-based exits:

### R1: MA Break
- Exit if price breaks below 20-MA (downtrend confirmation)
- Suggests trend momentum collapse

### R2: Lower Low
- Exit on lower low (new swing low below recent pivot)
- Signals structural weakness

### R3: ADX Fade
- Exit if ADX drops below threshold (trend strength collapsed)
- Indicates loss of directional conviction

### R4: Distribution
- Exit on volume-based distribution pattern
- Suggests accumulation exhaustion

### R5: Flow Flip
- Exit if smart money flow reverses bearish
- Tracks large trader positions

### R6: Bear Engulf
- Exit on bearish engulfing candle (open above, close below prior close)
- Signals strong rejection

### R7: Trail SL
- Exit if trailed stop loss is hit
- Combined with ATR-based trailing (see SL Trailing above)
- Allows 1+ ATR room above entry before activation

---

## Position Sizing

### Lot Calculation
- **Risk Budget:** `Capital × Risk% (default 2%)`
- **Volatility Adjustment:** `Lots = Risk Budget / (ATR14 × 100)`
- **Constraint:** Max 30% of total capital per trade
- **Minimum:** 1 lot

### Capital Management
- `Capital Used = Lots × Entry Price × 100`
- Max open positions: 5 (configurable)
- Only 1 position per ticker allowed

---

## Config Defaults

| Parameter | Value | Use |
|-----------|-------|-----|
| `capital` | 50,000,000 | Total account capital |
| `tp_pct` | 3.5% | TP % (legacy, ATR-based preferred) |
| `sl_pct` | 2.5% | SL % fallback |
| `risk_pct` | 2% | Risk per trade |
| `max_open` | 5 | Max concurrent open trades |

---

## Alert Summary

| Alert Type | Trigger | Action | Severity |
|------------|---------|--------|----------|
| **TARGET_REACHED** | Price ≥ TP | Auto-close | INFO |
| **STOPPED_OUT** | Price ≤ SL | Auto-close | CRITICAL |
| **NEAR_SL** | Price ≤ SL × 1.005 | Monitor | HIGH |
| **MOMENTUM_REVERSAL** | 2 consecutive bearish bars | Review | MEDIUM |
| **FLOW_REVERSAL** | Smart money turns bearish | Review | HIGH |
| **VPIN_SPIKE** | Liquidity event | Monitor | MEDIUM |

---

## Trade Lifecycle Summary

1. **Open:** Calculate ATR14 → Set SL (ATR or explicit) → Set TP (ATR or swing) → Size lots
2. **Active:** Monitor price vs SL/TP, trail SL on profit, scan for R1–R7
3. **Close:** Auto-close on SL/TP hit **OR** R1–R7 trigger (Swing only)
4. **Record:** Store exit_price, exit_reason, P&L (Rp & %)
