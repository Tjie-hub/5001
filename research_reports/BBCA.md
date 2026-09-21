# BBCA (Bank Central Asia Tbk) — Deep Dive Strategy Report

**Generated:** 2026-05-27
**Source:** `idx-walkforward-5001` multi-strategy backtest + live database
**Data Source:** Stockbit OHLCV + yfinance, 972 tickers IDX universe

---

## 1. Stock Profile

| Attribute | Value |
|-----------|-------|
| Ticker | BBCA |
| Sector | Banking / Financial |
| Type | Blue-chip, LQ45, IDX30 constituent |
| Market Cap | Large cap |
| Price (2026-05-26) | Rp 6,025 |
| All-Time Range | 73.5% |
| Avg Daily Range (50d) | 2.34% |
| Fundamental PE | 12.95 |
| Fundamental PBV | 2.90 |
| ROE | 22.41% |
| NPM | 49.52% |

**BBCA is the largest private bank in Indonesia by market cap. It trades with high liquidity, tight spreads, and institutional dominance. Unlike BRPT (volatile mid-cap petrochemical), BBCA is a low-volatility blue-chip — this fundamentally changes which strategies work.**

---

## 2. Walk-Forward Backtest — 4 Windows

```
Window 0: 2025-04-16 -> 2025-07-16  |  SIDEWAYS  |  ADX=22.4  |  Range=22.4%
Window 1: 2025-07-16 -> 2025-10-16  |  SIDEWAYS  |  ADX=18.7  |  Range= 8.0%
Window 2: 2025-10-16 -> 2026-01-16  |  VOLATILE  |  ADX=31.4  |  Range=10.0%
Window 3: 2026-01-16 -> 2026-04-16  |  SIDEWAYS  |  ADX=15.6  |  Range= 5.7%
```

### Window 0 — SIDEWAYS, Moderate Range (Apr–Jul 2025)

| Metric | Value |
|--------|-------|
| ADX | 22.4 (below trend threshold) |
| MA Slope | -1.1% |
| VR Mean | 1.04x |
| Close vs MA | +3.3% |
| Range | 22.4% |
| % Above MA | 30% |

| Strategy | Return | Win Rate | Verdict |
|----------|--------|----------|---------|
| Inside Bar Breakout | +0.93% | 100% | ⚠️ Marginal |
| Conservative Confirm | +0.69% | 100% | ⚠️ Marginal |
| NR7 Breakout | -0.52% | 0% | ❌ |
| Vol-Weighted | -0.77% | 0% | ❌ |
| Momentum | -0.98% | 0% | ❌ |

> 2/5 strategies barely positive. Best return +0.93% — less than BRPT's worst window.

### Window 1 — SIDEWAYS, Tight Range (Jul–Oct 2025) 🔴 WORST

| Metric | Value |
|--------|-------|
| ADX | 18.7 |
| MA Slope | -1.4% |
| VR Mean | 0.89x |
| Close vs MA | -1.3% |
| Range | **8.0%** — extremely tight |

| Strategy | Return | Win Rate |
|----------|--------|----------|
| Conservative | -0.01% | 50% |
| NR7 Breakout | -0.45% | 0% |
| TFB | -0.48% | 0% |
| VWAP Reversion | -0.81% | 33% |
| Momentum | -0.92% | 0% |
| Volume Profile POC | -1.35% | 0% |
| Inside Bar Breakout | -2.04% | 0% |
| Vol-Weighted | -2.81% | 0% |
| ORB | -5.44% | 0% |

> **0/9 strategies profitable.** When BBCA has an 8% quarterly range, the 0.40% round-trip commission alone consumes 5% of the available movement. No strategy can overcome this.

### Window 2 — VOLATILE, Best Window (Oct 2025–Jan 2026) ✅

| Metric | Value |
|--------|-------|
| ADX | 31.4 (above threshold!) |
| MA Slope | -1.8% |
| VR Mean | 0.87x |
| Close vs MA | -4.2% |
| Range | 10.0% |

| Strategy | Return | Win Rate | Verdict |
|----------|--------|----------|---------|
| Momentum | +1.16% | 100% | ✅ Best |
| Vol-Weighted | +0.54% | 50% | ⚠️ Marginal |
| Conservative | +0.32% | 50% | ⚠️ Marginal |
| ORB | +0.26% | 50% | ⚠️ Marginal |
| TFB | -0.14% | 0% | ❌ |
| Inside Bar Breakout | -0.67% | 0% | ❌ |

> 4/6 strategies profitable. ADX > 25 is the key enabler. This is BBCA's "good" window — and even then, the best return is only +1.16%.

### Window 3 — SIDEWAYS, Tightest Range (Jan–Apr 2026)

| Metric | Value |
|--------|-------|
| ADX | 15.6 |
| MA Slope | -0.1% |
| VR Mean | 0.95x |
| Close vs MA | -0.1% |
| Range | **5.7%** — tightest |

| Strategy | Return | Win Rate |
|----------|--------|----------|
| Vol-Weighted | +0.96% | 50% |
| Conservative | -0.41% | 0% |
| VWAP Reversion | -0.89% | 29% |
| Volume Profile POC | -1.11% | 0% |
| Momentum | -1.61% | 0% |
| ORB | -3.63% | 0% |

> 1/6 strategies profitable. 5.7% range leaves almost no room after commission.

---

## 3. Aggregate Strategy Ranking (All 4 Windows)

| Strategy | Avg Return | Profitable Windows | Best Single |
|----------|-----------|-------------------|-------------|
| **Conservative Confirm** | **+0.15%** | 2/4 | +0.69% |
| Trend Following Breakout | -0.15% | 0/4 | — |
| NR7 Breakout | -0.24% | 0/4 | — |
| VWAP Reversion | -0.43% | 0/4 | — |
| Inside Bar Breakout | -0.44% | 1/4 | +0.93% |
| Vol-Weighted | -0.52% | 2/4 | +0.96% |
| Momentum | -0.59% | 1/4 | +1.16% |
| Volume Profile POC | -0.61% | 0/4 | — |
| ORB | -2.20% | 1/4 | +0.26% |

**Only ONE strategy averages positive — and barely (+0.15%). Compare to BRPT where 5 strategies averaged >+1.4%.**

---

## 4. Strategy-by-Regime Matrix

```
                    Conservative  Momentum   Vol-Weighted   VWAP Rev   TFB
SIDEWAYS (3 windows):  +0.09%      -1.17%      -0.87%       -0.85%    -0.16%
VOLATILE (1 window):   +0.32%      +1.16%      +0.54%         —       -0.14%
```

Key insight: **Momentum is the best strategy in VOLATILE conditions but the WORST in SIDEWAYS.** BBCA needs regime-aware strategy selection more than any other stock.

---

## 5. Live Analysis — 2026-05-26

### Current State

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Close | 6,025 | -100 (-1.6%) from previous |
| Open / High / Low | 6,050 / 6,075 / 5,950 | Bearish candle, closed near low |
| Volume | 225M | Normal (VR=1.04x) |
| MA20 | 6,098 | Close below (-1.2%) |
| MA50 | 6,389 | Close well below (-5.7%) |
| VWAP60 | 6,412 | Close below (-6.0%) |
| D20 High / Low | 6,575 / 5,800 | Mid-range |
| ADX(14) | **37.5** | Strong trend — highest in any window |
| +DI / -DI | 26.1 / 17.0 | Buyers still dominant |
| ATR(14) | 157 (2.61%) | Healthy volatility |
| MA20 5-bar slope | -1.9% | Declining |
| Regime | **BEAR** | ADX > 25 + declining MA |

### All Strategy Signals: OFF

| Strategy | Signal | Missing Conditions |
|----------|--------|--------------------|
| Conservative Confirm | 🔴 | Not bullish, below MA20, VR only 1.04x (< 1.3x) |
| VWAP Reversion | 🔴 | Below VWAP-1% ✅ but VR 1.04x (< 1.3x) |
| Momentum | 🔴 | No 2-day streak (today -1.6%) |
| TFB | 🔴 | No D20 breakout, low VR, below MA50 |
| Inside Bar Breakout | 🔴 | Inside bar formed but no upside breakout |
| Vol-Weighted | 🔴 | Low VR, negative delta, below SMA10 |

> **All 6 strategies correctly give NO SIGNAL.** BBCA is in BEAR regime with ADX=37.5 — the decline has momentum. Staying out is the right call.

### Recent Price Action

```
05-01: 5,850  (low)     ← Support test
05-05: 5,950  +1.3%     
05-07: 6,125  +2.9%     ← Rally attempt
05-08: 6,225  +1.6%     ← Local high
05-11: 6,150  -1.2%     
05-12: 6,100  -0.8%     
05-13: 6,100   0.0%     
05-14: 6,100   0.0%     
05-25: 6,125  +0.4%     
05-26: 6,025  -1.6%     ← Breaking below consolidation
```

BBCA rallied from 5,850 to 6,225 in early May (+6.4%), then consolidated at 6,100 for 4 days, and is now breaking below support. Pattern: **failed rally, returning to support.**

### Fundamental Context

| Metric | Value | Assessment |
|--------|-------|------------|
| PE (TTM) | 12.95 | Reasonable for Indonesian bank |
| PBV | 2.90 | Premium but justified by ROE |
| ROE | 22.41% | Excellent — above 20% threshold |
| NPM | 49.52% | Outstanding net margin |
| DER | — | Bank leverage not comparable |
| Data Freshness | May 26, 2026 | Current ✅ |

> **Fundamentals are strong.** The price decline is technical, not fundamental. This is a high-quality stock in a temporary downtrend.

---

## 6. Why BRPT Methods Fail on BBCA

### Issue #1: Range Mismatch (THE core problem)

```
BRPT quarterly range:  41-81%
BBCA quarterly range:   5.7-22.4%

BRPT TP targets (2-3.5%) = 2.5-8.5% of quarterly range
BBCA TP targets (2-3.5%) = 12-61% of quarterly range  ← IMPOSSIBLE
```

BBCA's **entire** quarterly move in Window 1 was 8%. BRPT's smallest TP target (1.5%) would require capturing 19% of BBCA's available movement. In the tightest window (5.7% range), even 1% TP is ambitious. The strategies were designed for stocks that move 40-80% per quarter — BBCA moves 6-22%.

### Issue #2: Commission Drag

```
Round-trip commission: 0.40% (buy 0.15% + sell 0.25%)
BBCA avg daily range:  2.34%

Commission as % of daily range: 17%
Net room after commission:      1.94%
```

A strategy must capture >17% of the daily range just to break even. When ADX < 25, BBCA's intra-range movement shrinks further, making profit extraction nearly impossible.

**Window 1 proof:** 8% quarterly range / ~64 trading days = 0.125% avg range per day. Commission alone (0.40%) is **3x the average daily movement.** 0/9 strategies profitable.

### Issue #3: VR Thresholds Are Unreachable

```
BRPT mean VR:  0.76-1.10x
BBCA mean VR:  0.87-1.04x

Strategies requiring VR > 1.3x: Conservative, VWAP Rev, Momentum
Strategies requiring VR > 1.8x: Vol-Weighted, TFB
```

BBCA's VR **never** exceeded 1.10x in any backtest window. The strategies requiring VR > 1.3x are mathematically impossible to trigger. The strategies requiring VR > 1.8x are science fiction for BBCA.

**The VR thresholds filter out BBCA entirely.** This is intentional — these strategies were designed for momentum/volume-driven stocks. BBCA is an institutional stock where volume is steady but never "spikes."

### Issue #4: ADX Profile Is Different

```
BRPT ADX range: 23-58 (mean ~42)
BBCA ADX range: 15.6-31.4 (mean ~22)

Windows where ADX > 25:  BRPT 3/4,  BBCA 1/4
Windows where strategies work: BRPT 3/4,  BBCA 1/4 (same window!)
```

**ADX > 25 is the single best predictor of whether ANY strategy works on BBCA.** When ADX < 25, strategies are essentially coin flips with negative expected value due to commission.

### Issue #5: Volatility vs Noise Ratio

BBCA's daily noise (random walk) is a large fraction of its total movement:
- Avg daily range: 2.34%
- Quarterly range: 5.7-22.4%
- Signal-to-noise: quarterly_move / daily_noise ≈ 2.4-9.6x

BRPT's signal-to-noise is much higher:
- Avg daily range: ~4%
- Quarterly range: 41-81%
- Signal-to-noise: 10-20x

BBCA needs a MUCH higher signal confidence to overcome the noise floor.

---

## 7. What ACTUALLY Works for BBCA

### The One Condition That Matters

```
ADX > 25 → trade
ADX < 25 → stay out
```

This single filter would have:
- Skipped 3/4 losing windows
- Captured the 1/4 profitable window
- Turned aggregate return from +0.15% to +1.16% (Momentum) or +0.54% (Vol-Weighted)

### BBCA-Specific Parameter Tuning

| Parameter | BRPT Default | BBCA Optimal | Rationale |
|-----------|-------------|--------------|-----------|
| VR Threshold | 1.3x | **1.0x** | BBCA never spikes above 1.3x |
| TP Target | 2.0-3.5% | **0.8-1.5%** | BBCA quarterly range is 6-22% |
| SL | 1.0-2.5% | **1.0-1.5%** | Tighten to preserve thin margins |
| Min ADX | (none) | **25** | Hard gate — skip 75% of windows otherwise |
| Min Quarterly Range | (none) | **8%** | Below this, commission dominates |
| Best Strategy (SIDEWAYS) | VWAP Reversion | **Conservative Confirm** | Only strategy with +0.09% avg |
| Best Strategy (VOLATILE) | TFB | **Momentum** | +1.16% in Window 2 |
| Position Size | 30% capital | **15% capital** | Lower conviction, lower allocation |

### Strategy Selection Flow

```
1. Is ADX > 25?
   NO  → ⛔ STAY OUT
   YES → Continue

2. Is quarterly range > 8%?
   NO  → ⛔ STAY OUT (commission will eat profits)
   YES → Continue

3. What regime?
   VOLATILE (ADX>25, flat MA) → Momentum (+1.16% in Window 2)
   BULL (ADX>25, rising MA)   → Conservative Confirm (no data yet — never occurred)
   BEAR (ADX>25, falling MA)  → ⛔ STAY OUT (current condition)

4. Execute with BBCA parameters:
   TP: 0.8-1.5%, SL: 1.0-1.5%, Size: 15% capital
```

---

## 8. Gap Analysis — What the System Misses for BBCA

### Gaps Already in TODO.md

| Gap | TODO Item | BBCA Relevance |
|-----|-----------|----------------|
| No parameter optimization per ticker | **R7** (Sprint 13) | BBCA needs different VR/TP/SL than BRPT |
| No adaptive strategy switching | **G7** (Sprint 17) | BBCA needs regime-gated strategy selection |
| Backtest doesn't auto-roll | **G1** (Sprint 17) | Live ADX=37.5 not in any backtest window |
| PLAN.md not implemented | **R1** (Sprint 12) | Can't visually compare BBCA strategy markers |

### BBCA-Specific Gaps NOT in TODO.md

**B1. Blue-Chip Low-Vol Strategy Profile**

The system has one parameter set for all 972 tickers. BBCA needs its own profile with lower TP, lower VR threshold, and an ADX hard gate. No mechanism exists for per-ticker strategy calibration.

**Fix:** Extend R7 to store per-ticker optimal parameters in a `strategy_params` table. Query at scan time.

**B2. ADX Gate as Strategy-Level Filter**

The 9-layer filter has a regime gate (blocks BEAR) but no ADX gate. BBCA's data proves ADX > 25 is the single best predictor of strategy success. The system should allow per-strategy minimum ADX thresholds.

**Fix:** Add `min_adx` column to strategy config. Wire into `check_current_entry_signal()`.

**B3. Range/Commission Viability Check**

Window 1 (8% range, 0/9 profitable) should have been flagged as "untradeable" before any strategy ran. The system needs a pre-flight check: if quarterly range < 10x commission, skip all strategies for that ticker.

**Fix:** Add `is_tradeable()` check in `scheduled_multi_strategy_scan()`. Quarterly range < 4% (10x 0.40% commission) = skip.

**B4. Noise-to-Signal Ratio Filter**

BBCA's daily noise (2.34%) is too high relative to its quarterly range. A noise-to-signal ratio > 0.3 means random walk dominates. The system should measure this and adjust position sizing accordingly.

**Fix:** Compute `noise_ratio = avg_daily_range / quarterly_range`. If > 0.25, reduce position size or skip.

---

## 9. Live Recommendation

**BBCA — HOLD, DO NOT TRADE**

| Factor | Assessment |
|--------|------------|
| Regime | BEAR (ADX=37.5, declining MA) |
| Strategy Signals | 0/6 active |
| Fundamental | Strong (PE=12.95, ROE=22.4%) |
| Technical | Breaking below 6,100 consolidation |
| Next Support | 5,850 (May 1 low) |
| Next Resistance | 6,225 (May 8 high) |

**Entry trigger:** Wait for ADX to stay > 25 AND MA20 slope to turn positive AND close > MA20. This combination has not occurred in any live data.

**If forced to trade:** Conservative Confirm with BBCA parameters (TP=1.0%, SL=1.5%, size=15%). Expected return: +0.15% avg per trade. Not worth the risk.

**Better use of capital:** BBCA is a hold for fundamentals, not a trade for technicals. Allocate trading capital to higher-volatility stocks where the strategy suite has proven edge (BRPT: +4.1% avg, WINS, ASPR, etc.).

---

## 10. Comparison: BRPT vs BBCA

| Dimension | BRPT | BBCA |
|-----------|------|------|
| Stock Type | Mid-cap, volatile | Blue-chip, stable |
| Quarterly Range | 41-81% | 6-22% |
| Best Strategy Avg Return | +4.1% (Conservative) | +0.15% (Conservative) |
| Profitable Windows | 3/4 (75%) | 2/4 (50%) |
| Strategies with +Return | 5/10 | 1/9 |
| VR Profile | 0.76-1.10x | 0.87-1.04x |
| ADX Profile | 23-58 (trending) | 15-31 (sideways) |
| Strategy Fit | ✅ Multiple strategies work | ❌ Only one barely works |
| Recommended Action | TRADE (when in cycle) | HOLD (fundamentals) |

---

*Report generated from idx-walkforward-5001 engine backtest data and live database analysis.*
