# CLOSE-TO-CLOSE REVERSAL AFTER A LARGE PRIOR-DAY MOVE — DISCOVERY RESULT

**Doc:** S1-PM-0006 · **Date:** 2026-08-25 · **Owner:** Claude · **DISCOVERY ONLY**
**Cohort frozen in:** `S1-PM-0005_C2C_COHORT_PREDECLARATION.md`, sha256
`c6dfd438486e24ebe5c7e45a2eef652abca51af6653686565dd35a110680e5e1`, written **before** any
`r_{t+1}` was computed.
**`open` not used anywhere.** No registry modified · `HYP-PM-0002` untouched · no registration.

---

# DECISION: **3 — REJECTED. No credible edge.**

**The proposed direction is not merely absent — it is backwards.** After a ≥10% single-day fall, the
next close-to-close move is **down**, not up: mean **−0.587%**, next day up only **36.1%** of the
time (S2, n = 7,191, 787 tickers). Buying the crash loses money before costs.

A real reversal does exist — **after large UP days** — and it is **unexecutable and sub-cost.**

---

## Step 1 · Close-field integrity — **SUITABLE**, with two named caveats

The close field is in materially better shape than `open`. It survives.

| Check | Result |
|---|---|
| Rows / tickers / dates | 1,054,382 · 958 · 1,216 (2021-07-05 → 2026-07-29) |
| Close null / zero / negative | **0 / 0 / 0** |
| Duplicate (ticker, date) | **0** |
| `high < low` | **0** |
| Close outside `[low, high]` | **37** (0.0035%) |
| Non-integer closes | 37,029 (3.5%) — back-adjustment, expected |
| Zero-volume rows | 109,436 |

**Carry-forward.** `close == prev_close`: **32.01%** overall, **20.35%** in the liquid stratum.
Longest identical-close run **1,197** sessions (a dead ticker); in the liquid stratum the longest run
is **289** and 610 runs reach ≥10. **Compare `open`, which was 51.94% sticky in the same liquid
stratum — the close is roughly 2.5× less sticky, and its stickiness falls with liquidity as it
should.** This is why the close passes where the open failed.

**Are close-to-close returns dominated by adjustment artifacts? No.**
ARA/ARB make a move beyond the widest band (35% up / 35% down) mechanically impossible in the
regular market, so any such move must be an artifact, a corporate action, a PPK stock, or an error.

- **138 band-impossible moves in 1,051,742 rows = 0.013%**, across 27 tickers.
- Of those 138, **only 2 (1.4%) fall on a known corporate-action date** — the other 136 are
  unexplained by `corporate_actions`, consistent with the missing rights/bonus/reverse-split
  coverage (B-3) or PPK membership.

**Caveat 1 — this is a lower bound.** The test only catches moves beyond the *widest* band. A rights
issue producing a 25% apparent drop sits *inside* 35% and is invisible. Catching tier-specific
violations would require the stock's price tier, which depends on the price **level** — corrupted by
back-adjustment (B-0). **The refinement is unavailable, so 0.013% understates contamination.**

**Corporate-action days are more extreme but too few to matter:** median `|r|` **2.76%** on CA days
vs **0.94%** off; `P(|r| ≥ 0.10)` **6.87%** vs **2.67%**. But CA days are 2,155 of 1,051,742 (0.2%),
so they contribute well under 1% of the extreme cohort. F-c below confirms this empirically.

**Caveat 2 — `P(r_t == 0)` is 14.6%–22.6% in the liquid stratum**, and the median daily return is
exactly 0.00000 in every regime. Roughly one liquid trading day in five produces no price change at
all. This is real (tick granularity plus genuine no-trade closes), not a defect — but it makes any
two-way "reversal frequency" misleading, which is why zero is reported as its own category
throughout.

## Step 2 · Cohort — one cutoff, declared in advance

Liquid stratum `volume ≥ 100,000` (carried over unchanged from the frozen G-1 pre-registration,
not re-chosen); `t-1, t, t+1` consecutive sessions; **EXTREME := `|r_t| ≥ 0.10`**, DOWN and UP
reported separately; `0.15` shown **only** as the declared monotonicity check. **No threshold search
was run and none was selected on results.**

Base rows with a full `t-1, t, t+1` triple: 1,049,194 · liquid: **710,314**.

## Step 3 · Minimal edge check — `|r_t| ≥ 0.10`, liquid

**REV = P(next move opposite in sign). P(0) = share with `r_{t+1}` exactly zero.**

### DOWN cohort (`r_t ≤ −0.10`) — the only long-only-executable side

| Stratum | n | tickers | mean `r_{t+1}` | median | **REV (=P up)** | P(0) |
|---|---:|---:|---:|---:|---:|---:|
| **All regimes** | 10,787 | 828 | **−0.857%** | 0.000% | **0.380** | 0.128 |
| session S0 | 44 | 13 | −4.802% | −9.420% | 0.273 | 0.000 |
| session S1 | 159 | 33 | −4.305% | −5.488% | 0.195 | 0.057 |
| **session S2 (primary)** | **7,191** | **787** | **−0.587%** | **0.000%** | **0.361** | 0.165 |
| session S3 | 3,393 | 632 | −1.215% | −0.797% | 0.431 | 0.054 |
| ARB R1 (band −7%) | 250 | 40 | −4.637% | −7.912% | 0.204 | 0.044 |
| ARB R2 (−15%) | 486 | 205 | −2.982% | −2.128% | 0.282 | 0.115 |
| **ARB R3 (symmetric)** | 4,465 | 663 | **−0.049%** | 0.000% | 0.367 | 0.201 |
| ARB R4 (−15%) | 5,586 | 749 | −1.148% | −0.820% | 0.407 | 0.074 |

**Every single stratum is negative.** The next day is up only 36–43% of the time. **This is
continuation, not reversal, and the candidate hypothesis is refuted in direction on its executable
side.**

### UP cohort (`r_t ≥ +0.10`) — reversal is real here, and unreachable

| Stratum | n | tickers | mean `r_{t+1}` | median | **REV (=P down)** | P(0) |
|---|---:|---:|---:|---:|---:|---:|
| **All regimes** | 14,848 | 837 | −0.064% | **−1.460%** | **0.546** | 0.115 |
| session S0 | 1,294 | 379 | **+1.804%** | −1.635% | 0.561 | 0.047 |
| session S1 | 2,921 | 520 | +0.486% | −2.454% | 0.599 | 0.046 |
| **session S2 (primary)** | **8,183** | **746** | **−0.354%** | −0.707% | **0.511** | 0.164 |
| session S3 | 2,450 | 569 | −0.735% | −2.247% | 0.590 | 0.066 |
| ARB R1 (band −7%) | 4,449 | 597 | **+0.822%** | −2.288% | 0.590 | 0.047 |
| ARB R3 (symmetric) | 4,528 | 612 | −0.855% | 0.000% | 0.491 | 0.201 |
| ARB R4 (−15%) | 5,414 | 683 | −0.128% | −1.681% | 0.553 | 0.101 |

**Note the mean/median divergence** — median −1.46% against a mean of −0.064% all-regimes. The
distribution is strongly right-skewed: many small declines, a few very large gains. **A strategy
earns the mean, not the median.** Anyone reading the median as the payoff would be reading the one
number that flatters the trade.

### Monotonicity check at `|r_t| ≥ 0.15` (declared, not substituted)
DOWN: all-regimes mean −0.832%, REV 0.357 — **same sign, same magnitude, no inversion.**
UP: all-regimes mean +0.691%, REV 0.519 — **the mean flips positive** while the median stays
negative (−0.943%), which is the right-skew above becoming more pronounced. The UP effect is *not*
stable in the quantity that matters.

## Step 4 · Falsification — all five run

**F-a · Regime dependence — FAILS, and diagnostically.**
DOWN-side continuation is **−4.64% in R1, −2.98% in R2, −0.05% in R3, −1.15% in R4.** In the
**symmetric-band regime R3 the effect is essentially zero.** UP-side mean flips sign across ARB
regimes: **+0.822% in R1 vs −0.855% in R3.**

> **And the cohort itself is not the same object across regimes.** In R1 the ARB band was **−7%**, so
> a ≥10% down day was **mechanically impossible** in the regular market — yet 250 appear. Those are
> PPK stocks, unrecorded corporate actions, or errors. At the 0.15 cutoff R1 has **n = 6**.
> **Selecting on large down moves is partly selecting on proximity to the auto-rejection band, so
> the cohort's composition is set by the rule, not by the market.** That is the same
> event-definition failure that invalidated M6/I1's first design, and it puts this candidate back
> inside the blocked M6/I1 territory.

**F-b · Ticker concentration — PASSES (the effect is broad, not narrow).**
DOWN S2: top 10 tickers = **9.9%** of observations across 787 tickers; per-ticker mean `r_{t+1}`
median **−1.03%**, and only **37.9%** of tickers have a positive mean.
UP S2: top 10 = **8.1%** across 746 tickers; per-ticker median **−0.85%**, **38.9%** positive.
**Roughly 62% of tickers point the same way in both cohorts.** The finding is genuinely broad —
which is precisely why the negative sign on the DOWN side has to be taken seriously rather than
dismissed as noise.

**F-c · Corporate actions — PASSES (not the driver).**
Excluding known CA dates at both `t` and `t+1` removes **82 of 7,191** DOWN rows and **22 of 8,183**
UP rows, and moves the means by under 1 basis point (−0.587% → −0.584%; −0.354% → −0.346%).

**F-d · Outlier influence — PASSES (not driven by a handful of observations).**
DOWN S2: winsorised 0.5/99.5 → −0.690%; drop the single largest `|r_{t+1}|` → −0.597%; trimmed 1/99
→ −0.788%. UP S2: −0.236% / −0.334% / −0.267%. **Baseline −0.587% and −0.354% are stable.**

**F-e · Transaction costs — DESTROYS BOTH SIDES.**
The floor is **0.60% round-trip** and a one-day hold pays it in full.
- **DOWN, long:** mean **−0.587%**. Negative before costs; **−1.19%** after.
- **DOWN, short** (would earn +0.587%): **below the 0.60% floor**, and shorting is not practically
  available on IDX.
- **UP, short** (the direction with a real reversal): S2 mean **−0.354%** → gross **+0.354%**,
  **below the floor** — and again requires shorting.
- Only the all-regimes UP **median** (−1.46%) clears 0.60%, and the median is not what a strategy
  earns.

**Additional structural finding — liquidity sign-flip.** UP cohort, S2, by volume:
**100k–1M: mean +1.321%, REV 0.395** · 1M–10M: −0.286%, REV 0.436 · **>10M: −0.780%, REV 0.569**.
**The reversal exists only in the most heavily traded names and inverts to continuation in the
least.** One signal, two opposite behaviours in the same cohort. A single-threshold strategy would be
netting these against each other.

## Step 5 · Decision

# 3 — REJECTED. No credible edge.

**Three independent reasons, any one sufficient:**

1. **The stated direction is backwards.** Reversal after a large *down* move does not exist on IDX.
   Continuation does — mean −0.587% in the primary window, negative in all four session regimes and
   all four ARB regimes, robust to outliers, corporate actions, and liquidity bucket.
2. **The real effect is on the side that cannot be traded.** Reversal after a large *up* move is
   present (REV 0.546, median −1.46%), and harvesting it requires **shorting**, which IDX does not
   practically permit. **This is the fourth time this programme has found the effect on the forbidden
   side** — HYP-PA-0001's ADD leg, LC-PM-0007's ARA leg, LC-PM-0013's open-reversal leg, now this.
   That is no longer coincidence; it is a property of a long-only market with a truncated downside.
3. **Costs kill what remains.** Every executable variant sits below the 0.60% round-trip floor at a
   one-day holding period.

**And a fourth reason to stop rather than iterate:** the DOWN cohort's composition is determined by
the ARB band, so any attempt to rescue this candidate walks straight back into M6/I1 — which is
**data-blocked and explicitly out of scope**.

**No hypothesis statement and no test design are offered**, because the decision is not "promising".
Manufacturing one here would be exactly what this task was meant to prevent.

### The one usable by-product — a filter, not an edge

`P(r_{t+1} < 0) = 0.546` after a ≥10% up day, with a median of −1.46%, is a **negative screen**:
*do not initiate a long immediately after a ≥10% single-day gain.* That is risk management with no
transaction cost of its own, and it is worth carrying into any future long-only strategy. **It is not
an edge and must not be written up as one.**

### The residual worth a separate look — and what would make it valid

The **liquidity sign-flip** (+1.32% in 100k–1M vs −0.78% in >10M, same cohort, same window) is the
only genuinely unexplained structure this pass turned up. It is a *different* question from the one
asked — about who is on the other side of a large move in thin versus deep names — and it would need
its own S1 with a mechanism before any data work. **It is recorded, not pursued.**

## Sample burned

Per §7 of the pre-declaration: **this run computed the outcome variable on S2 and on every other
regime. The corpus is now burned for confirmatory use of this formation.** Any future test of a
close-to-close extreme-move signal must use **out-of-sample forward data** or a pre-registered
replication on a different universe. Recorded here so it cannot later be presented as fresh.

## Confirmations

No hypothesis registered · no registry modified · `HYP-PM-0002` untouched · **`open` not used for
formation, entry, or outcome** · `stockbit_flow_bars` not queried · no OFI, no `cont_k` · no Sharpe,
no equity curve, no portfolio construction · **no threshold optimisation, no parameter sweep, no
ranking of alternative signals** — one cutoff was declared in advance and one monotonicity check was
declared alongside it, and neither was substituted for the other · database opened `mode=ro` and
unmodified.

**Files created:** `S1-PM-0005_C2C_COHORT_PREDECLARATION.md`, `S1-PM-0006_C2C_REVERSAL_DISCOVERY.md`.
