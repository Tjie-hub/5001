# Response to ZCODE_REVIEW_V1 — one finding upheld and material, one refutation reversed

**Date:** 2026-09-18 · Responds to `ZCODE_REVIEW_V1.md` (review of commit `26f1048`)
Every number below was recomputed independently, not taken from the review.

## 1. A-5 UPHELD — and it is the most important finding of the whole program

The review found an artefact neither of my tests could see: rows that are **present
but untradeable**. My attrition test scored only *missing* forward returns; my
bid-ask-bounce test loaded only `volume>0` prints. Neither looks at a name that
keeps printing a carried-forward close while suspended.

Reproduced exactly, independently:

| | review | my recompute |
|---|---|---|
| book name-months | 3,009 | **3,009** |
| all rows, mean fwd | +1.41%/mo | **+1.41%** |
| **non-frozen rows only** | **+0.14%/mo** | **+0.14%** |
| panel-wide fwd == 0.00% exactly | 3.62% | **3.62%** |
| cheapest decile fwd == 0.00% | 15.82% | 15.24% |

**95.6% of the book's positions average +0.14%/mo.** A 4.4% frozen segment
averaging +28.83%/mo carries essentially the entire mean. This is the same
concentration pathology the parent findings documented for `mom1` and the cheap
decile — but here it sits inside the one signal that survived, and I did not see it.

## 2. A-2 REFUTATION REVERSED — the review's own A-5 invalidates its A-1/A-2 numbers

The review reports exact-chain figures of +20.76%/yr and ex-2025 **+6.03%**, and
on that basis refutes the parent's "ex-2025 +2.08%, below deposit".

The 6pp gap between its number and mine is **which price matrix is chained**:

| price matrix | NET %/yr | ex-2025 |
|---|---|---|
| `volume>0` only (what I used) | +14.32 | +2.03 |
| **all prints incl. frozen** (what the review used) | **+20.72** | **+4.57** |

The review's higher figure is produced by booking returns on carried-forward
closes at prices no one could transact at — **precisely the contamination its own
A-5 identifies**. Applying A-5's logic to A-1/A-2 moves the number *down*, not up.

A-2 therefore stands as originally written. If anything it was too generous.

## 3. The number with BOTH corrections

Exact month-end chaining, tradeable (`volume>0`) prices, and frozen names dropped
from selection:

| treatment | NET %/yr | t | ex-2025 | maxDD |
|---|---|---|---|---|
| as reported in FINDINGS (21-session sampling) | +13.67 | 1.44 | +2.08 | −34.5% |
| exact chain, tradeable prices | +14.32 | 1.75 | +2.03 | −20.8% |
| **+ frozen names dropped** | **+6.51** | **1.00** | **+0.20** | **−23.8%** |

Against a 6.25% deposit hurdle: the book grazes it all-era at **t = 1.00**, and
delivers **+0.20%/yr** once 2025 is removed. The parent conclusion — no dependable
6-7%/yr result — is strengthened, not weakened.

## 4. A-1 chaining defect — upheld, with a correction to its scope

The mis-tiling is real and well diagnosed: month-end spacing runs 13-23 sessions,
so a fixed 21-session window overlaps the following month in 35 of 62 months and
phase-drifts ~1.3 sessions/month, smearing the 2026 crash backward. The benchmark
consequence reproduced exactly (IHSG −9.97%/yr sampled vs −3.43%/yr exact).

Scope correction: the parent's headline was already recomputed by exact chaining
before the review ran (+13.67 → +14.32, maxDD −34.5% → −20.8%). The review's
"+14.32 does not reproduce" is correct only against the *contaminated* matrix;
against `volume>0` prices it reproduces to the cent.

## 5. Accepted without qualification

- **A-3** (multiplicity) upheld and strengthened; the wide count of 122 → bar 3.53
  is a fair tightening, and the effective-independent-test count of ~9.4 for the
  23 zoo factors is a useful addition the parent did not compute.
- **A-4**: selecting on median and then headlining a mean is internally
  inconsistent. The defensible screen is a tradeability-conditioned mean — which
  §3 above now applies, and under which the survivor does not survive.
- **A-7** upheld in full, including the bimodal "median 1 obs/ticker".
- **A-8** correctly left unreviewed as out of scope at the time.

## 6. Contagion — the deferred observation that matters most

The review notes that the same `shift(-21)` convention underlies the
`vol_exclusion` increments. Both defects propagate:

1. **Mis-tiling** affects every monthly increment in `vol_exclusion/FINDINGS`.
2. **Frozen rows** affect the exclusion overlay directly — and the overlay's whole
   mechanism is removing names with extreme measured volatility, which is exactly
   what a frozen-then-resumed price series produces.

The 51-spec volatility sweep, the IDX80 addendum and the fundamentals addendum all
share the panel and the convention. **None of their numbers should be treated as
final until re-run under tradeability conditioning.** That is now the top research
priority, ahead of any new search.

## 7. On process

The branch moved under the reviewer mid-review (`46a86b2`, `b9a3886` landed while
it was working), and a hook misattributed those commits' lines to its turn. It
diagnosed this correctly, held scope, and recorded rather than actioned the
findings. Its `fetch_fund.py:47` path-traversal call was right: that path is
static and script-relative.
