# Book-level overlay policy — volatility exclusion

**Status:** ACTIVE · **Declared:** 2026-09-17 · **Scope:** allocation, not measurement
**Owner decision:** 2026-09-17 (option 3 of three — overlay outside both specs)

## 1. What this is, and what it is deliberately not

This declares a **portfolio-construction rule applied at allocation time**, sitting outside every
frozen forward-test specification. It is **not** a hypothesis, it makes **no new alpha claim**, and
it **consumes no multiplicity family slot**.

It exists because volatility exclusion measurably improves a book built from trend signals, but
welding it into the trend specification would permanently widen the `P-M · Price-Trend {T1}` family
to cover volatility/dispersion features — a one-way door (families widen, never narrow; D-028,
PG-3/PG-6/R7.5). Keeping it at book level preserves the separation between two effects that have
independent evidence.

## 2. The separation that makes this legitimate

| | measures | decides |
|---|---|---|
| `FWD-PM-REGIME-002` | the trend mechanism, on the **unfiltered** signal set | nothing |
| `FWD-PM-VOLEX-001` | the volatility-exclusion effect, on its own universe | nothing |
| **this overlay** | nothing | what the book actually holds |

**Binding rule.** The 002 primary endpoint is computed on **every** signal its frozen spec emits,
whether or not the overlay would have held the name. The overlay never filters the ledger, never
alters the endpoint, and never appears in a 002 decision. `run_formation.py` records the unfiltered
set by design — that is not an oversight and must not be "fixed".

**Equally binding.** Combined book performance is **not** evidence for either hypothesis. It is an
operating result. Neither forward test may cite it.

Declared **before** either test recorded a single trade (002's ledger was empty on 2026-09-17), so
the overlay cannot have been selected on forward evidence.

## 3. The rule

At allocation, exclude candidates in the **top volatility quintile** of the eligible set, measured
at entry. Estimator and cadence follow `FWD-PM-VOLEX-001` (`P-M/forward_exclusion/PROTOCOL.md`),
which is the evidential home of this effect; this document does not restate or re-derive it.

Measured effect on a book built from 002 signals (cuts fitted on 2021-23 only, never on the
evaluation window):

| | excess CAGR | ex-2025 | Sharpe ex-25 | MaxDD |
|---|---|---|---|---|
| no overlay | 16.60% | 8.21% | 0.60 | -29.90% |
| **volatility-quintile exclusion** | **19.62%** | **10.42%** | **0.76** | **-25.95%** |

Return, Sharpe and drawdown all improve together. This is a **sizing/allocation** measurement, not
a test result.

## 4. Why this effect and not the others tested

Six entry filters were measured on 2026-09-17. Five were rejected; the numbers are in section 5.
Volatility exclusion is treated differently for one reason only: it is **not a fresh in-sample
search result**. It has independent prior support — the high-volatility decile measured
-2.93%/month against +0.78%/month for the rest, and `FWD-PM-VOLEX-001` is already forward-testing
it under its own frozen spec. The other five have no prior and no forward test.

## 5. Tested and rejected — do not re-propose as entry filters

Endpoint: per-trade excess vs IHSG, entry-date-clustered, 002 universe, 7,194 trades. Cuts fitted
on 2021-23.

| filter | N | FULL excess | t | ex-2025 | t | win% |
|---|---|---|---|---|---|---|
| **F0 none (= spec 002)** | 7,194 | **2.17%** | 6.29 | 0.93% | 2.83 | **33.47** |
| F1 drop slope Q5 | 5,728 | 2.16% | 6.12 | 1.04% | 3.09 | 33.41 |
| F2 drop slope Q4+Q5 | 4,166 | 1.17% | 3.18 | 0.55% | 1.66 | 32.43 |
| F3 drop extension Q5 | 5,650 | 1.15% | 3.52 | 0.41% | 1.28 | 32.30 |
| F4 drop volatility Q5 | 5,639 | 2.04% | 6.03 | 1.12% | 3.36 | 33.76 |
| F5 F1 + F3 | 4,922 | 1.21% | 3.65 | 0.52% | 1.61 | 32.39 |

**The finding that matters: no filter changes the win rate.** All six sit between 32% and 34%. The
losses are the mechanism, not a removable subset — a trailing-stop trend system produces many small
losses and few large wins, and at entry the two are not separable. F2, F3 and F5 demonstrate the
cost of trying: each roughly halves the edge by cutting winners alongside losers.

F1 and F4 survive as entry filters only in the weak sense that they do not destroy the edge. F1 is
worth **+0.11%/trade** ex-2025 with no win-rate change — inside the noise across six trials. It is
**not** adopted anywhere.

**Correction on record:** earlier session advice to "size down or skip slope-Q5" was overstated. It
rested on BRPT showing 0 wins in 4 steep-slope entries, which is small-sample noise, not a
replication of the panel effect (panel: slope Q5 has the highest mean and the lowest win rate, but
excluding it moves a book's Sharpe only 0.60 -> 0.69).

## 6. Forbidden

Filtering the 002 ledger by this overlay; citing combined book performance as evidence for 002 or
VOLEX; introducing F1/F2/F3/F5 as entry filters without a new spec id; re-deriving the volatility
estimator here rather than inheriting VOLEX's; changing the overlay while either forward test is
open without a dated superseding entry in this file.

## 7. Review

Reviewed when `FWD-PM-VOLEX-001` reaches its own decision point. If VOLEX FAILS, this overlay is
withdrawn — its entire evidential basis is that test, not the section 3 table.

## 8. Early review — 2026-09-29 (dated superseding entry; §1–§7 above are as declared)

Owner ruling D-063 §6. **Evidence corrected; rule unchanged, status ACTIVE.**

- §4's prior ("high-vol decile −2.93%/month vs +0.78%/month") is **withdrawn as a citation**. It came
  from a measurement that used a look-ahead tradeability filter (D-053; AUDIT_2026-09-24 row 32:
  UNVERIFIED). The overlay's sole evidential basis is now `FWD-PM-VOLEX-001`'s audited pooled result,
  **+0.30%/month, t 2.6** (n = 24, power ≈ 55%), which survived its ±20 suspension look-ahead audit.
  D-062's deflation audit puts VOLEX at 2.59 against a 2.84 full-census bar, so this basis is
  **thin**: it is an operating rule on weak evidence, not an established effect.
- §3's book table is an **in-sample operating figure**. It is not evidence and is never cited as such
  (§2 already forbids it).
- §7 is unchanged: withdrawal is tied to VOLEX-001 failing at its own decision point. It has not
  failed, and withdrawing early on a weakened prior would be a decision taken on an interim look.
