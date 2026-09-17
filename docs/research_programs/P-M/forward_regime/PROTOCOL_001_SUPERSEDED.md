# FWD-PM-REGIME-001 — forward test of the trend-regime entry + 3xATR exit rule

**Status:** **SUPERSEDED by FWD-PM-REGIME-002 on 2026-09-17T06:53:11+00:00** — closed with **zero recorded trades**.
> Superseded because the universe filter admitted zero-volume carry-forward bars (IDX suspensions
> appear as repeated OHLC on consecutive dates, not as calendar gaps). Limitation 1 below states
> "trading gaps > 30 days: zero, so suspension contamination is absent" — **that statement is wrong**
> and is corrected in 002. Discovered via LIFE (8 consecutive zero-volume sessions at 12725 scoring
> efficiency ratio 0.95). No forward evidence was observed before superseding; the ledger was empty.
> Body below is preserved unedited.

**Status (original):** OPEN · **Hypothesis:** HYP-PM-0010 · **Family:** P-M · Price-Trend {T1} (member 1)
**Drafted:** 2026-09-17 · **Opened:** 2026-09-17T06:35:57+00:00 · **First eligible entry:** 2026-09-18
**Spec frozen.** The specification in section 2 and the decision rule in section 3 are now closed.
Any change requires a new, dated, superseding protocol entry and a new spec id.
**Amended 2026-09-17** (pre-opening, therefore permitted): added section 2.1 (operator cost,
sensitivity, breakeven), section 4.1 (three tested-and-rejected policy overlays) and
limitation 8 (the unexploited tightening). No change to the section 2 frozen specification or
the section 3 decision rule.

## 1. What is being tested

Whether a per-stock trend-regime classifier, entered on regime onset and exited on a 3xATR
trailing stop, produces positive per-trade excess return over IHSG prospectively, as it did in
backtest.

This is **replication of a discovered effect**, not a novel alpha claim. The effect is trend /
time-series momentum, documented globally. The backtest is in-sample discovery on the same data the
rule was calibrated against and carries no confirmatory weight. The classifier was NOT derived from
the TUGU/SMMT case that opened the session; that hypothesis was separately refuted (section 8).

## 2. Frozen specification

| | |
|---|---|
| universe | `adv20 >= Rp 1e9` (20-session mean of close x volume, shifted 1); `close >= Rp 50`; >= 25 prior sessions; `is_final = 1` bars only |
| regime state | evaluated on data through `t-1` only (no look-ahead) |
| — slope | `ema20(t-1) / ema20(t-11) - 1 > +0.02` |
| — efficiency | Kaufman ER(20) `= abs(close(t-1) - close(t-21)) / sum(abs(daily close changes), 20) >= 0.30` |
| — participation | fraction of last 20 closes above EMA20 `>= 0.70` |
| entry | first session on which regime state turns True after being False (episode onset); fill at that session's **close** |
| exit | `close < (highest high since entry) - 3 x ATR14`, evaluated on the close; hard cap **60 sessions** |
| position cap | equal weight, **minimum 50 concurrent slots**; if signals exceed slots, select at random with a recorded seed |
| costs | buy leg 0.25%, sell leg 0.35% (`engine/exits/costs.py`: commission + slippage) |
| benchmark | IHSG close-to-close over the **identical** holding window, per trade |
| primary endpoint | `excess = (net trade return) - (IHSG return over same window)`, aggregated as a mean with **one-way date-clustered** standard errors, clustered on entry date |
| cadence | continuous; every episode onset in the universe is taken |
| contamination guard | exclude any trade whose window contains a split or a single-session move beyond +/-35% |

## 2.1 Cost model, operator cost, and breakeven

The endpoint in section 2 is measured at the repo cost authority (`engine/exits/costs.py`:
0.25% buy leg, 0.35% sell leg = **0.60% round trip**) so the result stays comparable with every
other study in this repo. That figure is **not** changed by this amendment.

Recorded separately: the operator's stated all-in round trip is **0.50%** (2026-09-17). Portfolio
economics across the plausible range, ex-2025 basis, ~12.6 round trips per slot per year:

| round trip | excess CAGR ex-2025 | Sharpe ex-2025 | absolute CAGR ex-2025 |
|---|---|---|---|
| 0.00% (gross) | +15.92% | 1.07 | +13.74% |
| 0.40% | +11.53% | 0.81 | +9.43% |
| **0.50% — operator stated** | **+10.46%** | **0.75** | **+8.38%** |
| 0.60% — repo authority, endpoint basis | +9.40% | 0.68 | +7.33% |
| 0.70% — fees + spread if liquidity is taken | +8.35% | 0.61 | +6.30% |
| 1.00% | +5.26% | 0.42 | +3.26% |
| 1.20% | +3.25% | 0.29 | +1.28% |

- **Breakeven round trip = 1.47%.** At the stated 0.50% there is ~3x headroom.
- Sensitivity: **1.09%/yr of excess per 0.10% of round trip.** Execution quality is the single
  largest controllable lever in this strategy.
- **Open ambiguity, carried:** typical IDX retail fee structures (~0.15-0.19% buy, ~0.25-0.29% sell
  including the 0.1% final tax) sum to roughly the stated 0.50%, which suggests the figure is
  **commissions and tax only**. The repo model's 0.10%/leg is *slippage* — spread crossing and
  impact — which is additive to fees. If liquidity is taken on names at the Rp 1e9 ADV floor, the
  true all-in is nearer 0.70%. Both clear breakeven; the difference is ~2%/yr of excess. This must
  be resolved from actual fills, not estimated, and the realised figure recorded here.
- IHSG returned **-2.80%/yr** over the same ex-2025 window.

## 3. Pre-declared decision rule

Backtest reference, 2021-07-05 to 2026-09-16, 7,422 trades over 1,162 entry-date clusters:

| basis | mean excess / trade | clustered SE | t |
|---|---|---|---|
| full sample | +2.260% | 0.350% | 6.45 |
| **ex-2025 (planning basis)** | **+1.106%** | **0.330%** | **3.35** |

The ex-2025 figure is the planning basis because calendar 2025 contributed +85.5% of a +147% total
and inflates every full-sample statistic in this study.

Power on the ex-2025 effect, one-sided alpha 0.05, 80% power, ~5.9 trades/day:

| elapsed | entry-date clusters | SE | detectable effect | status |
|---|---|---|---|---|
| 12 months | ~250 | 0.637% | +1.58% / trade | **underpowered** — interim read only, no decision |
| **24 months** | **~514** | **0.444%** | **+1.10% / trade** | powered for the planning effect — **decision point** |

- **At 12 months:** report only. No decision, no spec change, no stopping.
- **At 24 months (~514 trading days):**
  - **PASS** — mean excess `>= +0.55%` / trade **and** one-sided clustered `t > 1.65`.
  - **FAIL** — mean excess `<= 0`, **or** mean `< +0.30%` / trade (under a third of the planning estimate).
  - **INCONCLUSIVE** — anything else. Not a pass; the candidate stays parked.
- Early stopping is permitted in one direction only: if after 12 months the mean is below
  `-0.50%` / trade, the rule is abandoned.

## 4. Forbidden once formations are visible

Changing the slope / ER / participation thresholds, the ATR multiple, the 60-session cap, the entry
or exit convention, the liquidity floor, the position cap, the cost model or the benchmark; adding
or removing candidate rules; re-running the primary under any variation; back-filling trades;
selective sub-period reporting; silent edits to the ledger.

## 4.1 Tested and rejected — do not re-propose

Each variant below was measured on the same corpus on 2026-09-17 and **failed**. They are recorded
so they cannot be re-introduced mid-test as an "improvement", which section 4 forbids. Re-opening
any of them requires a new spec id and a new protocol entry.

**(a) Widen the trailing stop to cut turnover.** Turnover falls as predicted; the edge falls faster.

| exit | turns/yr | excess CAGR ex-2025 | Sharpe |
|---|---|---|---|
| 3xATR (frozen) | 12.29 | **+9.20%** | **1.07** |
| 4xATR | 8.19 | +2.98% | 0.79 |
| 5xATR | 6.44 | -0.22% | 0.54 |
| 6xATR | 5.41 | -2.36% | 0.31 |

**(b) Mean-reversion at support/resistance during SIDEWAYS regime.** Long-only, buy lower band of
the trailing-20 range, exit at an upper-band target. Median sideways range is 11.7% of price, so
range width is not the constraint. Five parameterisations, all significantly **negative**:

| spec | N | net | excess | t | win% |
|---|---|---|---|---|---|
| buy<0.25, tgt 0.75, 10d | 4,030 | -0.62% | -0.57% | -4.87 | 35.0 |
| buy<0.25, tgt 0.60, 10d | 4,030 | -0.64% | -0.58% | -5.28 | 36.5 |
| buy<0.20, tgt 0.80, 15d | 3,212 | -0.86% | -0.78% | -5.11 | 36.2 |
| buy<0.30, tgt 0.70, 10d | 4,551 | -0.63% | -0.56% | -4.76 | 39.6 |
| buy<0.25, tgt 0.50, 5d | 4,679 | -0.69% | -0.60% | -7.32 | 38.6 |

Support does not hold in IDX sideways names; weakness persists. Consistent with the EMA20 reclaim
rate in SIDEWAYS measuring 49.3% — a coin flip — and this being worse than one.

**(c) Suspend entries during an IHSG downtrend.** Filter: IHSG above its own EMA20 and 10-session
EMA slope > -0.5%, lagged one session.

| | excess CAGR ex-2025 | Sharpe | MaxDD |
|---|---|---|---|
| no market filter (frozen) | **+9.20%** | **1.07** | **-29.2%** |
| + IHSG downtrend filter | +0.19% | 0.82 | -43.6% |

Actively harmful: it removes the counter-market names that carry the alpha and concentrates the
remainder into market-up periods where the book is mostly beta. In 2026 IHSG returned -23.8% while
the unfiltered strategy returned -0.3%. One filter definition tested; the effect size makes a
definitional artifact unlikely but it is not excluded.

## 5. Why the ledger starts empty

No historical trade has been or may be inserted. The backtest exists in the session analysis and in
`scripts/`; replaying it into this ledger would convert in-sample discovery into an apparent forward
record. Every entry carries `generated_utc` and a content fingerprint.

## 6. Known limitations, carried

1. **Survivorship — unquantified, direction known.** Across all 959 tickers the maximum lag between
   a ticker's last bar and the panel end is **61 days**; no ticker's series terminates mid-sample.
   The corpus therefore contains only names still listed as of 2026-09, and any stock delisted
   during 2021-2026 is absent entirely. Bias is **optimistic**; magnitude is **not measured**.
   Trading gaps > 30 days: **zero**, so suspension contamination is absent.
2. **2025 dominance.** Full-sample Sharpe 1.13 / CAGR 20.0%; ex-2025 Sharpe 0.51 / CAGR 7.4%.
   Excess over IHSG ex-2025: +9.48%/yr at Sharpe 0.68. Underwrite the second set.
3. **Fill assumptions are optimistic.** Close-to-close fills, flat per-leg cost, no market impact,
   at ~6 entries and ~6 exits per session in Rp 1bn-ADV names.
4. **Effective breadth ~10.** Concurrent holdings correlate at rho = 0.089, giving N_eff ~= 10.4
   from ~131 nominal positions. Sharpe still improves with position count up to 131 (cap 30 -> 0.86,
   cap 50 -> 0.95, cap 100 -> 1.05), so the cap floor of 50 is binding, not cosmetic.
5. **Sector neutrality is untested and unenforceable.** No ticker->sector map exists for 77% of the
   universe; `engine/sector_rotation.py` maps 82 of 959 tickers and returns a permissive
   `"sector unknown"` for the remainder. Max single-sector share among concurrent positions measured
   36% (p90 55%) on the 23% mapped subset — **not trusted**, small-sector biased.
6. **Long-only, beta ~0.95.** Not market neutral. Alpha = +2.258% (t = 6.43) after beta adjustment,
   so the excess is not a beta artifact, but the book carries full market exposure.
7. **Distribution is lottery-shaped.** Median trade is negative under every exit rule tested;
   win rate 33% for 3xATR. Requires the breadth floor to be honoured.
8. **A better parameter set exists and is deliberately NOT used.** A 48-cell threshold grid
   (slope x ER x participation), split-sample tuned on 2021-2023 and evaluated on 2024-2026, gives
   an IS->OOS rank correlation of **0.779** with **all 48 cells positive** — a smooth surface, not
   an overfitting signature. Tightening to slope .10 / ER .40 / participation .90 roughly doubles
   the ex-2025 per-signal excess (+1.27% -> +2.35% per 20 sessions) and turns 2023, the one losing
   year, positive (-0.79% -> +1.90%).

   It is **not adopted**, for three reasons: it inverts in **2026**, the most recent and most
   live-relevant year (+0.25% -> **-3.09%**, and -6.26% at .10/.50/.90); it cuts signal count by
   **69%** (45,391 -> 13,967), which collides with the >= 50 position floor and N_eff ~ 10; and
   adopting a grid-selected point before any forward evidence is precisely the failure this whole
   session documented. The frozen spec keeps the wider thresholds: more breadth, higher t (7.15 vs
   5.53), and positive in 2026.

   Recorded here so the tightening cannot be introduced later as a fresh idea. Adopting it requires
   a new spec id, a new protocol entry, and it inherits the 48-cell multiplicity count.

## 7. Governance status

- **REGISTERED as HYP-PM-0010**, 2026-09-17T06:35:57+00:00, owner decision of 2026-09-17.
- **Family: P-M · Price-Trend {T1}** — a NEW family opened at this registration (D-028, PG-3).
  Scope, declared here and binding: **directional trend features derived from OHLCV**
  (moving-average slope, Kaufman efficiency ratio, participation above a moving average, ATR-based
  exits), liquid IDX universe, data epoch **2021-07-05 → 2026-09-16**. This candidate is **member 1**;
  multiplicity k = 1.
- **Why a new family and not a shared price family:** no price-feature family existed at the time of
  this registration — FWD-PM-VOLEX-001 (Parkinson-60 volatility exclusion) is an **unregistered**
  prospective record and holds no family slot, so nothing was split. Widening {T1} to absorb
  volatility/dispersion features later is **permitted**; narrowing or splitting it is **not**.
- The 48-cell threshold search recorded in limitation 8 was conducted **before** this registration
  and is disclosed there. Adopting any cell from it requires a new spec id and inherits that count.
- Per Research Master Plan invariants #4 and #5, a backtest cannot promote anything; promotion
  requires a gatekeeper PROMOTE plus forward-test evidence.

## 8. Provenance — what this is NOT

This protocol does **not** carry forward the "absorption consolidation" hypothesis from the
2026-09-17 session. That hypothesis was refuted three independent ways: it did not fire on either
name that generated it; its primary specification returned negative excess at all five horizons
(TREAT - CTRL = -4.06% at h=20, t = -2.50); and it produced a 1.04x lift (t = 0.31) on conditional
surge probability. It should be filed FAILED if it is ever registered. See `scripts/` for the
refutation code.
