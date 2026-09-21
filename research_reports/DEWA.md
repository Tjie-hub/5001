# DEWA (Darma Henwa Tbk) — Deep Dive Strategy Report

**Generated:** 2026-05-27
**Source:** `idx-walkforward-5001` multi-strategy backtest + live database
**Data Source:** Stockbit OHLCV + yfinance, 972 tickers IDX universe
**Filter Rank:** #6 overall, #3 in VIABLE tier (Composite 55.5)

---

## 1. Stock Profile

| Attribute | Value |
|-----------|-------|
| Ticker | DEWA |
| Sector | Mining Services / Coal Contractor |
| Type | Mid-cap, high-volume, non-index |
| Market Cap | N/A (DB missing) |
| Price (2026-05-26) | Rp 336 |
| All-Time Range (1Y) | >600% |
| Avg Daily Range (50d) | 11.14% (ATR) |
| Avg Daily Volume (20d) | 649M (HIGHEST in IDX universe) |
| Fundamental PE | 4.77 (suspiciously low) |
| Fundamental PBV | 2.40 |
| ROE | 50.22% (likely inflated by one-time gains) |
| NPM | 233.45% (data anomaly) |
| Index Membership | None (not IDX30/LQ45/IDX80) |

**DEWA is the most liquid stock in the entire IDX universe by average daily volume (649M). It's a mining services company with extreme volatility — daily ATR of 11% means it can swing 35+ points in a single session. Unlike BRPT (petrochemical) or BBCA (banking), DEWA is a pure volume/liquidity play with penny-stock characteristics. The fundamentals are suspicious — NPM 233% and ROE 50% suggest one-time gains or data quality issues.**

---

## 2. Walk-Forward Backtest — 4 Windows

```
Window 0: 2025-04-16 -> 2025-07-16  |  EARLY UPTREND  |  Range=92.5%  |  ATR=5.34%
Window 1: 2025-07-16 -> 2025-10-16  |  STRONG UPTREND  |  Range=122.2% |  ATR=5.72%
Window 2: 2025-10-16 -> 2026-01-16  |  PARABOLIC RALLY |  Range=202.4% |  ATR=5.67%
Window 3: 2026-01-16 -> 2026-04-16  |  EXHAUSTION/CORR |  Range=116.4% |  ATR=8.87%
```

### Window 0 — Early Uptrend (Apr–Jul 2025) — Price: 109 → 190 (+74%)

| Metric | Value |
|--------|-------|
| Close | 190 |
| MA20 | 180 |
| Close vs MA | +5.6% (above, trending) |
| Range | 92.5% |
| ATR | 5.34% |
| Avg Volume | 496M |

Pattern: Strong rally from base. 92.5% range with ATR 5.34% means daily swings of ~10 points. Breakout strategies should work here.

### Window 1 — Strong Uptrend (Jul–Oct 2025) — Price: 180 → 326 (+81%)

| Metric | Value |
|--------|-------|
| Close | 326 |
| MA20 | 308 |
| Close vs MA | +5.9% |
| Range | 122.2% |
| ATR | 5.72% |
| Avg Volume | 612M |

Pattern: Acceleration phase. Range expands to 122%, volume increases 23%. Trend-following strategies should dominate.

### Window 2 — Parabolic Rally (Oct 2025–Jan 2026) — Price: 325 → 765 (+136%) ✅

| Metric | Value |
|--------|-------|
| Close | 765 |
| MA20 | 677 |
| Close vs MA | +13.0% (extended) |
| Range | 202.4% |
| ATR | 5.67% |
| Avg Volume | 1,346M (MASSIVE) |

Pattern: Parabolic. Price more than doubles. Volume triples from Window 1. Close is 13% above MA — getting extended. This is where momentum and conservative strategies both print.

### Window 3 — Exhaustion/Correction (Jan–Apr 2026) — Price: 775 → 555 (-28%) 🔴

| Metric | Value |
|--------|-------|
| Close | 555 |
| MA20 | 476 |
| Close vs MA | +16.7% (but declining from higher) |
| Range | 116.4% |
| ATR | 8.87% (HIGHEST — volatility explosion) |
| Avg Volume | 953M |

Pattern: Exhaustion. Range stays high (116%) but the trend has reversed. ATR spikes to 8.87% — volatility without direction = mean-reversion territory. This is where VWAP Reversion and Volume Profile POC should work.

---

## 3. Aggregate Strategy Ranking (All 4 Windows)

| Strategy | Avg Return | Consistency | Profitable Windows | Best Single |
|----------|-----------|-------------|-------------------|-------------|
| **Vol-Weighted** | **+1.17%** | **75%** | 3/4 | — |
| Inside Bar Breakout | +0.90% | 25% | 1/4 | — |
| ORB | +0.66% | 25% | 1/4 | — |
| **Conservative Confirm** | **+0.56%** | **75%** | 3/4 | +11.69% |
| NR7 Breakout | 0.00% | 0% | 0/4 | — |
| Swing Trend | 0.00% | 0% | 0/4 | — |
| TFB | 0.00% | 0% | 0/4 | — |
| VWAP Reversion | 0.00% | 0% | 0/4 | — |
| Volume Profile POC | -1.18% | 0% | 0/4 | — |
| Momentum | -2.28% | 0% | 0/4 | — |

**4/10 strategies average positive. Two strategies (Vol-Weighted, Conservative) have 75% consistency — strong signal. Compare to BRPT (6/10 positive) and BBCA (1/10 positive). DEWA sits between them.**

---

## 4. Strategy-by-Regime Matrix

```
                     Vol-Weighted  Conservative  Inside Bar   ORB    Momentum
EARLY UPTREND (W0):     ✅             ✅           ✅        ✅       ❌
STRONG UPTREND (W1):    ✅             ✅           ❌        ❌       ❌
PARABOLIC (W2):         ✅             ✅           ❌        ❌       ❌  
EXHAUSTION (W3):        ❌             ❌           ❌        ❌       ❌
```

Key insight: **Vol-Weighted and Conservative Confirm work in 3/4 windows.** They fail only in Window 3 (exhaustion) — the same window where EVERY strategy fails. The breakout strategies (Inside Bar, ORB) only work in the early window. Momentum is a disaster across all windows.

---

## 5. Live Analysis — 2026-05-26

### Current State — POST-CRASH

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Close | 336 | -42% from April peak (580) |
| Open / High / Low | 352 / 366 / 332 | Wide range, closed near low |
| Volume | 861M | Elevated (VR=1.33x) |
| MA20 | 488 | Close -31.2% below — DEEPLY OVERSOLD |
| MA50 | 481 | Close -30.1% below |
| VWAP60 | ~341 | Close near session VWAP |
| D20 High / Low | 570 / 332 | AT the absolute bottom of 20-day range |
| ATR(14) | 37 (11.14%) | Extreme daily volatility |
| MA20 5-bar slope | -6.3% | Steep decline |
| Regime | UNCERTAIN | System can't classify post-crash |

### Recent Price Action — THE CRASH

```
04-14: 580  (peak)     ← Window 2/3 transition high
04-23: 515  -11.2%     ← First break
04-24: 486  -5.6%      ← Accelerating down
05-06: 525  +8.0%      ← Dead cat bounce
05-08: 484  -7.8%      ← Resumes decline
05-11: 468  -3.3%      
05-12: 466  -0.4%      ← Consolidation
05-13: 486  +4.3%      ← Bounce attempt
05-14: 484  -0.4%      ← Last close before SUSPENSION

── 11-DAY GAP (May 14 → May 25) ── LIKELY TRADING SUSPENSION ──

05-25: 360  -25.6%     ← GAP DOWN on resume, MASSIVE volume (1.17B)
05-26: 336  -6.7%      ← Continued selling, still near D20 low
```

**DEWA experienced a 42% crash from its April peak, including an 11-day trading suspension with a -25.6% gap-down on resume. This is nearly identical to BRPT's pattern (35% crash, 11-day suspension, gap-down). The stock is at the absolute bottom of its 20-day Donchian channel. Volume exploded on the gap-down day (1.17B).**

### Strategy Signals: Mostly OFF

| Strategy | Signal | Why |
|----------|--------|-----|
| Vol-Weighted | 🔴 | Close below SMA10, VR only 1.33x (post-crash, not accumulation) |
| Conservative Confirm | 🔴 | Bearish candle, below MA20, VR < 1.3x threshold |
| Inside Bar Breakout | 🔴 | No inside bar pattern on daily |
| ORB | 🔴 | Not applicable post-crash |
| Momentum | 🔴 | No 2-day streak, consecutive down (-3 days) |
| VWAP Reversion | 🟡 | Close below VWAP but VR borderline |

> **All strategies are correctly OFF.** The post-crash environment is not suitable for any standard entry. Wait for stabilization.

### Flow & Order Book

| Metric | Value |
|--------|-------|
| Flow Score | -5 (BEARISH) |
| Smart Money | MORNING_TRAP |
| Net Lot | -168M (heavy selling) |
| Top Broker (Sell) | AZ: 1.38M lots sold (-46.5B IDR) — LOCAL |
| Top Broker (Buy) | BK: 676K lots bought (+22.8B) — FOREIGN |

**Local smart money is dumping. Foreign is buying the dip. Classic divergence — foreigners see value, locals see continued risk.**

### Fundamental Context

| Metric | Value | Assessment |
|--------|-------|------------|
| PE (TTM) | 4.77 | Suspiciously low — likely earnings anomaly |
| PBV | 2.40 | Moderate premium |
| ROE | 50.22% | Inflated (one-time gains?) |
| NPM | 233.45% | Data anomaly — not real operating margin |
| DER | 0.41 | Low leverage — clean balance sheet |
| Earnings Growth | 24,383% | Data anomaly |
| Data Freshness | Apr 27, 2026 | 4 weeks stale ⚠️ |

> **Fundamentals are UNRELIABLE.** The NPM 233% and earnings growth 24,383% indicate one-time accounting items inflating the numbers. PE 4.77 is not actionable. Use technicals only for DEWA.

---

## 6. Why Some Strategies Work (and Others Fail) on DEWA

### Issue #1: Vol-Weighted is the King Strategy

DEWA's profile is perfectly suited for the Vol-Weighted strategy:
- **VR thresholds reachable**: DEWA frequently spikes above 1.3x (6/60 days > 1.3x, 3/60 > 1.8x)
- **Delta-positive moves**: When DEWA rallies, it rallies hard with volume confirmation
- **Trend persistence**: 3/4 windows show clear trending behavior

### Issue #2: Momentum Fails Catastrophically (-2.28%)

DEWA's rallies are fast and vertical, but they don't form clean 2-day streaks. The stock gaps up 10% then consolidates for days. Momentum's 2-day streak requirement misses DEWA's pattern entirely. **Momentum is the worst strategy for DEWA — avoid.**

### Issue #3: Breakout Strategies Are Window-Dependent

Inside Bar (+0.90%) and ORB (+0.66%) only work in Window 0 when the base was forming. Once the parabolic rally starts (Windows 1-2), the breakout patterns are already "in motion" and the strategies chase entries too late. **Use breakouts only in early-stage trends, not parabolic ones.**

### Issue #4: VWAP Reversion Has Zero Data

Despite DEWA's massive mean-reverting moves (Window 3: 116% range), VWAP Reversion shows 0% consistency. The strategy may be failing due to the VR threshold requirement (1.3x) not aligning with reversion entry points. **Potential strategy improvement: lower VR threshold for reversion trades on DEWA.**

### Issue #5: Commission is Irrelevant

With ATR of 11.14% daily, DEWA's round-trip commission (0.40%) is only 3.6% of the daily range — completely manageable. Compare to BBCA where commission is 17% of daily range. **DEWA is commission-proof.**

---

## 7. DEWA Trading Playbook

### The One Condition That Matters

```
DAILY ATR > 5% → trade
DAILY ATR < 5% → stay out
```

DEWA needs volatility. When ATR compresses below 5%, the stock is consolidating and strategies produce noise. When ATR expands above 8%, trend-following strategies excel.

### DEWA-Specific Parameter Tuning

| Parameter | BRPT Default | DEWA Optimal | Rationale |
|-----------|-------------|--------------|-----------|
| Best Strategy | TFB / Conservative | **Vol-Weighted** | +1.17% avg, 75% consistency |
| Backup Strategy | — | **Conservative Confirm** | +0.56% avg, 75% consistency, +11.69% best window |
| VR Threshold | 1.3x | **1.3x** | DEWA reaches this 6/60 days — keep it |
| TP Target | 2.0-3.5% | **3.0-5.0%** | ATR 11% supports wider targets |
| SL | 1.0-2.5% | **2.0-3.5%** | Wider to accommodate 11% daily swings |
| Min ATR | (none) | **5%** | Below 5% ATR, stay out |
| Position Size | 30% capital | **20% capital** | Extreme volatility demands smaller size |
| Max Holding Days | — | **5 days** | DEWA moves fast — don't overstay |

### Strategy Selection Flow

```
1. Is ATR(14) > 5%?
   NO  → ⛔ STAY OUT (consolidation, noise dominates)
   YES → Continue

2. What regime?
   EARLY UPTREND (price near MA, ATR 5-6%)   → Vol-Weighted + Inside Bar Breakout
   STRONG UPTREND (price > MA, ATR 5-7%)     → Vol-Weighted + Conservative Confirm
   PARABOLIC (price > MA20+10%, ATR < 8%)    → Conservative Confirm ONLY (trailing stop tight)
   EXHAUSTION (price declining, ATR > 8%)     → ⛔ STAY OUT (all strategies fail)
   POST-CRASH (current)                       → ⛔ STAY OUT (wait for stabilization)

3. Execute with DEWA parameters:
   TP: 3.0-5.0%, SL: 2.0-3.5%, Size: 20% capital, Max Hold: 5 days
```

---

## 8. Gap Analysis — What the System Misses for DEWA

### G1. Post-Suspension Crash Detection 🔴🔴

DEWA has the exact same 11-day gap + -25% gap-down pattern as BRPT. The system has no awareness of trading suspensions. All technical calculations (MA, ATR, Donchian) assume continuity that doesn't exist.

**Fix:** Same as BRPT Gap #2 — detect gaps > 5 trading days, flag as suspension, adjust all indicators.

### G2. Fundamental Data Unreliability 🟡

NPM 233%, earnings growth 24,383% — these are clearly one-time items. The fundamental filter in the 9-layer system would pass DEWA with flying colors, which is misleading.

**Fix:** Add outlier detection to keystats. If NPM > 100% or earnings_growth > 1000%, flag as "unreliable" and rely on technicals only.

### G3. Momentum Strategy Mismatch 🟡

Momentum (-2.28% avg) is the worst strategy for DEWA, yet it would still fire signals in trending windows. The system should learn from walk-forward data and disable strategies that are proven losers on a per-ticker basis.

**Fix:** Per-ticker strategy blacklist. If avg_return < -1% and consistency = 0%, disable that strategy for this ticker.

### G4. ATR-Based Regime Detection 🟡

DEWA's regime is currently "UNCERTAIN" — the ML model can't classify post-crash. But ATR alone tells the story: ATR > 8% = exhaustion, ATR 5-7% = trending, ATR < 5% = sideways.

**Fix:** Add ATR-based regime as fallback when ML model is UNCERTAIN.

---

## 9. Live Recommendation

**DEWA — WAIT FOR STABILIZATION, THEN TRADE**

| Factor | Assessment |
|--------|------------|
| Regime | POST-CRASH (UNCERTAIN) |
| Strategy Signals | 0/6 active |
| Fundamental | Unreliable (data anomalies) |
| Technical | Deeply oversold (-31% vs MA20, at D20 low) |
| Volume | Extreme (VR 1.33x, 1.17B on gap-down) |
| Flow | BEARISH (local selling, foreign buying — divergence) |
| Next Support | 332 (today's low) — if broken, no support until ~250 |
| Next Resistance | 360 (gap-down level), then 484 (pre-suspension) |

**Entry trigger:** Wait for 3 consecutive days ABOVE the gap-down level (360) with declining volume. This confirms the selling climax is over. Then enter Vol-Weighted on the first VR > 1.3x + delta-positive day.

**If forced to trade:** Vol-Weighted with DEWA parameters (TP=3.5%, SL=3.0%, size=15%). Single-entry only. Do NOT add to position.

**Better use of capital:** Let DEWA stabilize for 1-2 weeks. The post-crash recovery trade on DEWA could be massive — the stock went from 109 to 765 in 9 months. A bounce from 336 to 450 (+34%) is entirely possible. But catching the falling knife will destroy capital. **Patience.**

---

## 10. Comparison: DEWA vs BRPT

| Dimension | BRPT | DEWA |
|-----------|------|------|
| Stock Type | Mid-cap petrochemical | Mid-cap mining services |
| Avg Daily Volume | 420M | **649M** (highest in IDX) |
| Quarterly Range | 41-81% | **92-202%** (extreme) |
| Daily ATR | ~4% | **11.14%** (3x BRPT) |
| Best Strategy | Conservative (+3.54%) | Vol-Weighted (+1.17%) |
| Strategies Profitable | 6/10 | 4/10 |
| Best Consistency | 75% | 75% |
| VR Profile | 0.76-1.10x | 0.55-1.63x |
| Strategy Fit | ✅ Multiple work | ✅ Vol-Weighted + Conservative work |
| Commission Impact | Moderate | Negligible (3.6% of daily range) |
| Current State | Post-crash (-35%) | Post-crash (-42%) |
| Suspension | 11 days | 11 days |
| Recommended | TRADE (when stabilized) | WAIT → TRADE (when stabilized) |

**DEWA is BRPT on steroids.** More volume, more range, more volatility. The strategy returns are lower (+1.17% vs +3.54%) because the strategies can't fully capture the extreme moves. DEWA is the higher-risk, higher-reward cousin.

---

*Report generated from idx-walkforward-5001 engine backtest data and live database analysis.*
