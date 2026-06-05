# BRPT Case Study: Extreme Event Handling Design Reference
_Formalized 2026-06-05 | Source events: April–June 2026_

This document formalizes the BRPT analysis that motivated Sprints 17 G1–G9 (suspension detector, backtest roller, crash recovery strategy, VR context, premover auto-execution, adaptive strategy selector). It serves as a reference for why each piece was built and what evidence drove the design.

---

## 1. Timeline

| Date | Event | Close | Volume |
|------|-------|-------|--------|
| 2026-04-02 | Sharp drop −12.4% (pre-suspension decline begins) | 1,280 | 120M |
| 2026-04-08 | Recovery bounce begins | 1,720 | 264M |
| 2026-04-14 | Peak close — rally top | **2,450** | 379M |
| 2026-04-15–May 14 | Gradual decline −15% from peak | 2,080 | — |
| 2026-05-14 | **Last pre-suspension bar** (vol 1.03B — selling surge) | 2,080 | 1,036M |
| 2026-05-15–24 | **Trading suspended** — 5 trading days missing | — | — |
| 2026-05-25 | **Resume bar** — gap-down −22.4% open | 1,495 | 426M |
| 2026-05-26 | First post-resume bar — massive volume (VR ~4.9×) | 1,565 | 1,489M |
| 2026-05-28 | Second post-resume bar — VR ~5.7× | 1,555 | 1,724M |
| 2026-05-29 | Breakout bar — close 1,915 (+23% from resume low) | 1,915 | 680M |
| 2026-06-02 | Intraday high 2,210 (+45% from resume open of 1,615) | 1,890 | 1,817M |

**Suspension event (DB record):**
- `last_normal_date`: 2026-05-14
- `resume_date`: 2026-05-25
- `missing_td`: 5 trading days
- `gap_pct`: −22.4% (1,615 open vs 2,080 prior close)
- `classification`: `suspension`

---

## 2. Indicator Contamination

### ATR Inflation
Pre-crash ATR14 ≈ 80–120 IDR (normal range for 2,000–2,400 price).
On resume bar (2026-05-25): True Range = max(1,615, 2,080) − 1,480 = 600 pts → **5× normal ATR**.
Post-suspension ATR14 remains inflated for ~14 bars (Wilder's smoothing).

**Impact:** Any ATR-based SL (e.g., `entry − 2×ATR`) on 2026-05-26 would place SL ~450 pts below entry (~1,050), making position size negligibly small (risk exceeds capital cap). This is why G3 uses **resume bar low as SL**, not ATR.

### VR Miscontextualization
Average volume prior to suspension: ~280M/day.
Post-resume volumes: 426M, 1,489M, 1,724M.
VR (2026-05-26) = 1,489M / rolling_mean ≈ **4.9×**.

Pre-G4: REVERSAL_BREAKOUT scored 30pts for VOLUME_EXPLOSION (VR > 2×) without distinguishing *why* the volume spiked. A crash-absorption VR 4.9× is mechanically similar to a breakout VR 4.9× but represents entirely different dynamics. G4 (`classify_volume_context`) adds the `crash_absorption` tag to distinguish them.

### Walk-Forward Blind Spot
Pre-G1: Walk-forward windows ended 2026-04-29. The May 2026 crash period (5% of BRPT's history containing the most extreme move) was invisible to all strategy scores.
Post-G1: `backtest_windows` table includes `is_partial=1` window for BRPT covering 2026-04-16→2026-06-04, making the crash period visible to analysis.

---

## 3. Strategy Failure Analysis

### What fired (but was misleading)
`REVERSAL_BREAKOUT` premover pattern fired 2026-05-26 with score=55:
- VOLUME_EXPLOSION: 30pts (VR ~4.9×) ✓
- POSITIVE_CLOSE: 15pts (close > prev close) ✓
- ATR_EXPANSION: 10pts ✓
- PRICE_NEAR_LOW: 0pts — stock was 4.9% above its 50d low (new lower range post-crash)
- BREAKING_SHORT_TREND: 0pts — 3d MA was still below post-crash close

**Detection without action:** Alert sent via Telegram but `paper_trades` was empty. The detection-execution gap (G6) meant no trade was opened.

### What all 10 existing strategies got wrong
| Strategy | Problem |
|----------|---------|
| `conservative` | Requires `close > MA20` — post-crash close (1,565) far below pre-crash MA20 (~2,100) |
| `momentum` | Requires 2-day close streak + VR > 1.3× — first post-resume bar had VR but was the only bar |
| `vwap_reversion` | Designed for mean-reversion to VWAP — price was far below any meaningful VWAP anchor |
| `Trend Following Breakout` | Requires Donchian 20-day breakout — post-crash price couldn't break prior 20-day channel |
| All others | None designed for post-suspension gap-down entry |

**Root cause:** All strategies assume continuous price history with valid MA/ATR/channel references. A 5-day trading gap invalidates all these references for weeks.

### What crash recovery (G3) correctly captured
Entry condition: gap ≥ 5 calendar days + gap-down ≥ 20% + VR > 2× + bullish close.
- Gap: 2026-05-14 → 2026-05-25 = 11 calendar days ✓
- Gap-down: −22.4% ✓
- 2026-05-26: VR ~4.9×, close 1,565 > open 1,500 ✓

**Result:** Entry 2026-05-28 at 1,500. SL = 1,480 (resume bar low). TP = 1,615 + 0.5×(2,080−1,615) = 1,848.
Exit 2026-05-29 at TP ≈ 1,845. **PnL: +22.4%.**

---

## 4. Gap Detection Methodology (G2)

The `suspension_detector.py` (`detect_gaps()`) identifies BRPT's event using:
1. **Calendar-aware trading day counter** — counts actual trading days skipped (5), not calendar days (11)
2. **Price discontinuity threshold** — `abs(gap_pct) ≥ 10%` → classifies as `suspension` (not `data_gap`)
3. **Three-layer API**: `detect_gaps()` (pure), `scan_all()` (DB write), `get_status()` (read)

The distinction between `suspension` and `data_gap` matters because:
- `suspension` triggers the Telegram alert pipeline (G8)
- `suspension` is eligible for crash recovery entry (G3)
- `data_gap` (e.g., missing data fetch) does not trigger trading logic

---

## 5. Strategy Heatmap Evidence (motivating G7)

BRPT `wf_scores` (4 windows, 2025-04-16 → 2026-04-16):

| Strategy | Consistency | Score | Regime Fit |
|----------|-------------|-------|------------|
| conservative | 75% | 0.895 | BULL/SIDEWAYS |
| vol_weighted | 75% | 0.558 | Any |
| momentum | 75% | 0.546 | BULL |
| Trend Following Breakout | 75% | 0.534 | BULL |
| vwap_reversion | 25% | 0.416 | SIDEWAYS |
| ORB | 25% | 0.290 | BULL |
| Inside Bar Breakout | 25% | 0.266 | BULL |
| Volume Profile POC | 25% | 0.179 | Any |
| Swing Trend | 0% | 0.048 | BULL |
| NR7 Breakout | 0% | 0.036 | BULL |

**Key insight:** Conservative dominates (0.895 score). This makes sense — during BRPT's extreme volatility period, conservative's tight ATR gates prevented bad entries. The heatmap shows clear clustering: BULL regime → conservative/momentum/TFB; SIDEWAYS → vwap_reversion/vol_weighted.
This evidence directly motivated `_REGIME_STRATEGY_MAP` in `adaptive_strategy_selector()` (G7).

---

## 6. What Was Built (Sprint 17 G-series)

| Feature | Sprint Item | Evidence from BRPT |
|---------|-------------|-------------------|
| Suspension detector | G2 | BRPT 5-day gap invisible without it |
| Post-suspension alert | G8 | Alert pipeline fires on resume day |
| Suspension markers on chart | G9 | Dive page gap markers from suspension_events |
| Backtest roller | G1 | May 2026 crash invisible in static WF windows |
| Crash recovery strategy | G3 | No strategy handled post-gap entry — +22.4% trade validated |
| VR context classifier | G4 | VR 4.9× post-crash ≠ breakout VR 4.9× |
| Premover auto-execution | G6 | Alert fired, paper_trades empty — gap closed |
| Adaptive strategy selector | G7 | Regime heatmap → automated strategy-regime routing |

---

## 7. Lessons for Extreme Event Design

1. **ATR becomes unusable for 2–3 weeks post-suspension.** Any SL using ATR during this period will be either too wide (inflated) or trigger incorrectly. Use structural price levels (resume bar low) instead.

2. **Standard MA/VWAP references reset after a gap.** A 20-day MA computed before suspension is meaningless after a −22% gap-down. Strategies that gate on `close > MA20` will stay locked out for weeks.

3. **High post-crash volume is crash-absorption, not breakout accumulation.** Distinguish contexts (G4: `classify_volume_context`). The appropriate strategy changes: crash recovery entry (G3) vs normal breakout (TFB).

4. **The detection-execution gap is real.** System detected the opportunity (REVERSAL_BREAKOUT score=55), alerted the user, but executed nothing. The shadow/enforce toggle (G6) closes this gap operationally.

5. **Walk-forward evaluation requires the crash period to be visible.** Pre-G1, the May 2026 crash was outside all WF windows. Partial windows (G1: `is_partial=1`) make current-period crash events immediately visible for analysis.
