# Exploratory pattern scan — 2026-09-17

**Status:** EXPLORATORY · **NOT REGISTERED** · consumes **no multiplicity family slot**
**Universe:** liquid IDX (`adv20 >= Rp 1e9`, `close >= Rp 50`, >= 25 prior sessions, `volume > 0`,
>= 18 of trailing 20 sessions traded), 2021-07-05 to 2026-09-16, `is_final = 1` bars only
**Endpoint:** forward return net of 0.60% round trip, minus IHSG over the identical window,
aggregated with one-way **entry-date-clustered** standard errors
**Guards:** splits excluded; any single session beyond +/-35% excluded

## Why this is not a FAILURE_REGISTRY entry

None of these arms was ever registered. `FAILURE_REGISTRY.md` records the outcome of **registered**
hypotheses, and its counts feed the family denominators; filing unregistered exploratory arms there
would corrupt the institution's own failure-mode self-diagnostic. This file is the record instead.

**Multiplicity disclosure.** Roughly **twelve independent arms** plus six wedge-strictness variants
were measured on one corpus in one session. Any future registration drawn from this scan inherits
that count. Nothing here may be promoted on the strength of a single cell.

## 1. Results

| # | pattern | N | exc5% | t | exc20% | t | **exc20 ex-2025** | t |
|---|---|---|---|---|---|---|---|---|
| 1 | **Liquidity sweep** (production `engine/smc.py`) | 36,739 | **-0.83** | **-9.73** | -0.76 | -4.03 | **-1.33** | **-7.16** |
| 1a | — by type: PDL | 24,915 | -0.74 | -9.19 | -0.63 | -3.50 | -1.21 | -6.87 |
| 1b | — by type: PWL | 11,824 | -1.03 | -9.16 | -1.04 | -4.12 | **-1.60** | -6.44 |
| 2 | **Failed breakdown** (sweep 20d low, close back in) | 12,254 | **-1.20** | **-9.90** | -1.51 | -5.96 | **-1.94** | **-7.15** |
| 3 | Failed breakout (bull trap) | 13,120 | -0.30 | -2.71 | +0.36 | 1.49 | -0.60 | -2.55 |
| 4 | Resistance breakout (close > 20d high) | 15,340 | +0.66 | 4.98 | **+2.10** | **7.30** | +0.40 | 1.56 |
| 5 | Falling wedge + upside break | 13,892 | -0.66 | -5.32 | -0.88 | -3.33 | -1.42 | -4.78 |
| 6 | Falling wedge (no break required) | 82,629 | -0.79 | -12.31 | -0.85 | -5.53 | -1.32 | -7.41 |
| 7 | **Wedge Pop** (Kell, faithful) | 3,310 | **-1.23** | **-5.34** | -1.37 | -3.05 | **-1.89** | **-4.01** |
| 8 | Episodic Pivot (Qullamaggie, **daily proxy — see 3**) | 1,444 | -1.48 | -2.62 | +0.75 | 0.63 | -4.81 | -4.26 |

Sideways support/resistance mean reversion (five parameterisations, all significantly negative,
t = -4.76 to -7.32) is recorded separately in `P-M/forward_regime/PROTOCOL.md` section 4.1.

**The unifying result: every mean-reversion-flavoured pattern is significantly NEGATIVE.** These are
not null results — buying weakness on IDX is a reliable anti-edge, with t-stats reaching -9.7 on
36,739 observations. Only continuation (#4) is positive, and it collapses outside 2025 (+2.10% ->
+0.40%, t 7.30 -> 1.56).

## 2. Flow confirmation does not rescue the sweep

Restricted to 2025-01 onward, where `stockbit_flow` exists (13,307 sweeps with same-day flow):

| filter | N | exc5% | t | exc20% | t |
|---|---|---|---|---|---|
| no flow filter | 13,307 | -0.61 | -3.18 | +0.99 | 2.40 |
| net buying | 4,403 | -0.63 | -2.06 | +1.28 | 1.81 |
| net buying, top quartile | 3,327 | -0.84 | -2.41 | +1.14 | 1.48 |
| `smart_money = ACCUMULATION` | 1,903 | -0.11 | -0.28 | +1.23 | 1.30 |
| `smart_money = MORNING_TRAP` | 1,441 | -0.54 | -1.66 | -0.68 | -0.99 |

The only positive cells are 20-day at t ~ 1.3-1.8, inside the 2025 window that inflated every result
this session; the full-history 20-day figure is **-0.76%**. **Data defect found:** the
`stockbit_flow.composite_score` column is unpopulated — a `>= 70` filter returns **zero rows**, so
the engine's own composite flow score has never been testable.

## 3. A correction: the Episodic Pivot daily proxy was not the strategy

Arm 8 entered at the gap day's **close**. Qullamaggie's rule explicitly says *not* to buy the open —
wait for the 09:00-09:30 opening range and buy its break. Re-tested faithfully on 1-minute bars
(2025-01+, the intraday-data era), median entry 09:55:

| hold | N | net% | excess% | t | win% |
|---|---|---|---|---|---|
| 5d | 345 | +0.63 | +0.64 | 0.39 | 40.9 |
| 10d | 342 | +1.37 | +1.83 | 0.87 | 40.1 |
| 20d | 311 | +2.09 | +3.77 | 1.30 | 36.0 |

Positive, **not significant** — and the era split kills it: **2025 +12.24% (t 2.68), 2026 -5.81%
(t -1.89)**. Two IDX-specific blockers: **58%** of signals never break the opening range, and
**16.1%** of gap days close at/near limit-up (ARA), structurally unfillable next session — a
constraint absent from the US market these strategies were built for.

## 4. Detector validation — the results are not an artifact

1. **Bar-level inspection.** 2026-03-17 BRPT: low 1230 pierced the 20d low of 1240, closed 1355 —
   a textbook failed breakdown. 2026-04-07: highs -25.03/bar, lows -23.59/bar, range 415 -> 285,
   close reclaiming the 10 EMA — a genuine wedge pop.
2. **Independent implementation.** Arm 1 used the **production** `detect_liquidity_sweep`, not a
   re-implementation, and returned the same answer.
3. **Definition invariance.** The wedge criterion was found to be **too loose** (it fires on any
   downward channel where highs fall marginally faster than lows). Five stricter definitions were
   tested; the 5-day excess is stable at **-1.16% to -1.22% across all six**:

| wedge definition | N | exc5% | exc20% |
|---|---|---|---|
| loose (original) | 4,402 | -1.22 | -1.47 |
| highs fall >= 25% faster | 2,155 | -1.16 | -1.61 |
| highs fall >= 50% faster | 1,266 | -1.17 | -1.21 |
| range tightens >= 30% | 2,968 | -1.21 | -1.43 |
| range tightens >= 50% | 1,728 | -1.16 | -1.18 |
| strict (both) | 1,028 | -1.21 | -1.12 |

Invariance to the detector is the strongest available evidence that the effect is real: a detection
artifact would move when the detector is tightened. It does not.

## 5. The most valuable finding — single-ticker validation is worthless here

Every pattern above was re-run on **BRPT alone**, the ticker chosen for visual verification:

| pattern | BRPT exc20% | win20% | panel ex-2025 |
|---|---|---|---|
| Liquidity sweep | **+6.09** | 45.6 | **-1.33** |
| Failed breakdown | **+4.48** | 38.1 | **-1.94** |
| Failed breakout | **+5.99** | 37.0 | -0.60 |
| Resistance breakout | +4.72 | 43.2 | +0.40 |
| Wedge Pop | **+4.41** | 38.9 | **-1.89** |

**Every refuted pattern looks profitable on BRPT.** Two causes, measured:

1. **Ticker drift — about a third.** BRPT's unconditional 20-day excess is **+3.05%** (940 -> 1600,
   +70%, while IHSG fell 23.8%). Removing each ticker's own mean moves the failed-breakdown panel
   from -1.51% to **-1.02% (t -3.97)** — still significantly negative, so drift is not the whole
   story.
2. **BRPT is an outlier — the rest.** Across 454 tickers with >= 10 signals: only **35% are
   positive**, median **-1.59%**, 10th/90th percentile **-9.23% / +4.15%**. BRPT at +4.48% sits at
   the **91st percentile**.

A single ticker chosen at random therefore has a **~35% chance** of appearing to confirm a genuinely
negative effect, and it will do so convincingly — the chart really does show the signals working.
This is the same error that produced the refuted absorption hypothesis from two names on 2026-09-16.

**Operating rule:** with a per-ticker spread of -9.23% to +4.15%, no single chart can confirm or
refute a pattern. Roughly 30-50 names are needed before a visual impression carries information —
which is why `FWD-PM-REGIME-002` carries a >= 50 position floor.

The chart remains useful for **mechanism**, not validation: it showed *why* the 2026-04-28 regime
entry failed (entry landed on the first pullback after a near-vertical rally), which no summary
statistic made visible.

## 6. Status

Nothing here is registered, promoted, or wired into production. `FWD-PM-REGIME-002` is untouched.
The value of this scan is its negative results and the single-ticker finding in section 5.
