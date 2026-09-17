# FWD-PM-REGIME-002 — forward test of the trend-regime entry + 3xATR exit rule

**Status:** **OPEN** · **Hypothesis:** HYP-PM-0010 (retained) · **Family:** P-M · Price-Trend {T1} (member 1)
**Supersedes:** FWD-PM-REGIME-001 (opened and closed 2026-09-17, **zero recorded trades**)
**Opened:** 2026-09-17T06:53:11+00:00 · **First eligible entry:** 2026-09-18
**Spec frozen.** Section 2 and the section 3 decision rule are closed. Any change requires a new,
dated, superseding protocol entry and a new spec id.

## 0. Why 002 exists

001's universe filter admitted **zero-volume carry-forward bars**. On IDX a suspended or untraded
name is not a calendar gap — the session still appears, with OHLC repeated from the prior close and
volume 0. 001's survivorship audit checked only date gaps, found none, and recorded "suspension
contamination is absent". That conclusion was **wrong**.

The failure is not cosmetic. The Kaufman efficiency ratio divides net move by the sum of absolute
daily moves, so a frozen price **stops growing the denominator** and drives ER toward 1.0. A
non-trading stock therefore scores as a maximally clean trend. Measured: zero-volume bars are
**0.951%** of liquid ticker-days but **4.778%** of regime-UP liquid ticker-days — a 5x
over-representation. At entry level the onset rule absorbs most of it (1.04% of entries on a
zero-volume bar, 1.93% within 5 sessions of one), but the contamination is real and directional.

Found via **LIFE** (insurance): ran 5675 -> 12725 (+124% in 7 sessions) then printed **8 consecutive
zero-volume sessions** at 12725, scoring ER 0.86 -> 0.95. 001's liquidity floor excluded it only by
accident of size — peak ADV20 Rp 976m against the Rp 1e9 floor, **97.6% of the threshold**.

Removing the contamination **lowers** the measured effect (ex-2025 +1.106% -> +0.928%/trade), which
is the expected direction: the artifact was inflating it. Section 3 is re-powered accordingly.

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
| **traded-days guard (NEW in 002)** | entry bar must have **`volume > 0`**, and **at least 18 of the trailing 20 sessions** must have `volume > 0`. The regime state is computed over a 20-session window, so the guard must cover that window; allowing 2 stale sessions tolerates ordinary illiquidity without admitting a frozen quote. Chosen on data-hygiene grounds **before** looking at which variant performed best — across no-guard / vol>0 / >=18-of-20 / 20-of-20 the ex-2025 excess moved 0.78 / 0.85 / 0.83 / 0.80 (%), i.e. within noise, confirming the guard is hygiene and not a performance lever. |
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

Backtest reference under the 002 universe, 2021-07-05 to 2026-09-16:

| basis | trades | entry-date clusters | mean excess / trade | clustered SE | t |
|---|---|---|---|---|---|
| full sample | 7,194 | 1,154 | +2.171% | 0.345% | 6.29 |
| **ex-2025 (planning basis)** | **5,391** | **925** | **+0.928%** | **0.328%** | **2.83** |

Calendar 2025 contributed +85.5% of a +147% total in the 001 study and inflates every full-sample
statistic; ex-2025 is the planning basis. Under 001 these were +2.260% / +1.106% (t 3.35) — the
reduction is the removed zero-volume artifact, not a change of mechanism.

Power on the ex-2025 effect, one-sided alpha 0.05, 80% power, ~5.8 trades/day:

| elapsed | entry-date clusters | SE | detectable effect |
|---|---|---|---|
| 12 months | ~250 | 0.631% | +1.569% / trade |
| 24 months | ~500 | 0.446% | +1.110% / trade |
| **36 months** | ~756 | 0.363% | +0.902% / trade |

The planning effect of **+0.928%** is detectable only at ~34 months, so the decision point moves to
**36 months** (001 placed it at 24 — that is now underpowered and 24 becomes a second interim).

- **At 12 months:** report only. No decision, no spec change, no stopping.
- **At 24 months:** report only. Explicitly **not** a decision point in 002.
- **At 36 months (~756 trading days):**
  - **PASS** — mean excess `>= +0.46%` / trade **and** one-sided clustered `t > 1.65`.
  - **FAIL** — mean excess `<= 0`, **or** mean `< +0.30%` / trade.
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

1. **Survivorship — unquantified; and the 001 suspension claim was WRONG.** Across all 959 tickers
   the maximum lag between a ticker's last bar and the panel end is 61 days; no series terminates
   mid-sample. The corpus therefore holds only names still listed as of 2026-09, and any stock
   delisted during 2021-2026 is absent. Bias **optimistic**, magnitude **not measured**.
   **Correction to 001:** 001 recorded "trading gaps > 30 days: zero, so suspension contamination is
   absent." Calendar gaps are indeed zero, but that is not the same claim — IDX suspensions appear as
   **zero-volume carry-forward bars on consecutive dates**, which the audit script (`delist.py`) never
   checked. Zero-volume bars are 0.951% of liquid ticker-days and 4.778% of regime-UP liquid
   ticker-days. 002's traded-days guard addresses the signal contamination; it does **not** address
   universe survivorship, which remains open and unmeasured.
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
9. **Return concentration is far more extreme than limitation 7 states.** *(appended 2026-09-17T07:28:36+00:00
   after a post-opening execution audit; section 2 specification and section 3 decision rule are
   UNCHANGED — this is disclosure, not a spec change.)*

   Splitting the 7,194 backtest trades by exit reason:

   | exit | N | share | mean days | net/trade | excess/trade |
   |---|---|---|---|---|---|
   | 3xATR trail | 6,957 | 96.7% | 18.5 | **+0.64%** | +0.74% (t 2.25) |
   | 60-session cap | 237 | **3.3%** | 59.4 | **+45.93%** | +44.17% (t 12.85) |

   - **The top 1% of trades (71) carry 85% of the total excess.**
   - **66.5% of trades have negative excess.** Positive excess sums to +58,209pp against -42,590pp
     negative, netting +15,620pp = +2.171%/trade.

   The mechanism is therefore not "a trailing stop that works": it is 96.7% of trades cut near
   break-even to fund 3.3% that run into the 60-session cap — and those cap-exits were **still
   trending** when force-closed. Limitation 7's "median trade negative, 33% win rate" understates
   this materially.

   **Consequence for the >= 50 position floor:** at N_eff ~ 10 independent bets, missing even a
   handful of those 71 trades destroys the result. The breadth floor is load-bearing for a far
   sharper reason than diversification.

10. **Execution audit — the frozen endpoint is conservative, not inflated.** *(appended 2026-09-17T07:28:36+00:00)*
    The section 2 entry convention fills at the signal session's close. Because the regime state is
    computed entirely from data through `t-1`, that signal is known before session `t` opens, so the
    fill is executable and carries no look-ahead; bar-level verification confirms the exit likewise
    uses only information available at its own close. Re-running under a stricter specification:

    | specification | ex-2025 excess/trade | t |
    |---|---|---|
    | **A — close entry vs IHSG (the frozen section 3 reference)** | **+0.93%** | **2.83** |
    | B — next-open entry vs IHSG | +0.85% | 2.60 |
    | C — close entry vs equal-weight book | +1.33% | 4.13 |
    | D — next-open entry vs equal-weight book | **+1.26%** | **3.90** |

    Execution realism costs **0.08%/trade**. The frozen reference (A) sets a **harder** bar than the
    most rigorous specification (D), so no reopening is warranted. Recorded because IHSG is a
    large-cap index the average liquid stock beats by +0.35%/20d — a bias that flatters any long
    signal, and which the section 3 endpoint carries.

    Known approximation, carried: the exit is **close-triggered**; a real intraday stop would fire
    earlier at a different price.

## 7. Governance status

**Recorded attribute added 2026-09-17T07:38:52+00:00 — observability, NOT a spec change.** The ledger now records
`ihsg_regime_at_entry` (BULL / BEAR / SIDEWAYS via the production
`engine.regime_filter.detect_regime`). It **never filters, gates or sizes anything**: every signal
the section 2 specification emits is recorded regardless of regime, and the section 3 endpoint is
computed over all of them. Sections 2 and 3 are unchanged.

Rationale, measured 2026-09-17. Regime is strongly informative *descriptively* — by IHSG regime at
entry the backtest shows BULL **+6.74%**/trade, SIDEWAYS +1.51%, BEAR **-2.03%** (absolute, net) —
but acting on it is not supportable and not attempted, for two reasons:

1. **No sample.** Effective N for a regime claim is *episodes*, not sessions: **BULL 9**, BEAR 13,
   SIDEWAYS 23 over five years. `regime_config.yaml` requires min_n = 100 per cell and the full
   taxonomy is 12 cells; BULL has **98 sessions in total**. A BULL-specific rule would be fitted to
   nine observations.
2. **It is redundant, and gating actively hurts.** The stock-level filter already tapers exposure
   without any market input — qualifying names per day run **66.0 (BULL) / 36.5 (SIDEWAYS) / 12.6
   (BEAR)**, a ~5x automatic cut. Explicitly skipping BEAR entries *worsens* ex-2025 CAGR
   (6.35% -> 5.31%) and max drawdown (-29.90% -> -34.98%), because it removes the counter-trend
   leaders that carry the alpha. Entering only in BULL is catastrophic (CAGR 0.86%, ex-2025 -9.98%).

The attribute exists so the 2029 decision can be informed by **forward** evidence on regime
conditioning instead of a backtest fitted to nine episodes.

- **Spec 002 supersedes 001**, which closed with **zero recorded trades**. HYP-PM-0010 and the
  Price-Trend {T1} family slot are **retained, not re-registered** — the mechanism, thresholds
  (.02/.30/.70), exit (3xATR14), horizon, benchmark and endpoint are unchanged; 002 adds a
  data-hygiene guard and re-powers the decision point. No forward observation existed when 002 was
  written (the 001 ledger was empty), so the re-spec cannot be outcome-driven. Registering a second
  hypothesis for one mechanism risked once would inflate the family count rather than protect it.
  **This is a governance judgement and is flagged for owner override:** if the owner prefers the
  conservative reading, 002 becomes HYP-PM-0011 and Price-Trend {T1} advances to 2 members.
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
