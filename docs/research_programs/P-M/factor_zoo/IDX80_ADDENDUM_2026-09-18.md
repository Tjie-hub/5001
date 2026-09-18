# Addendum — Restricting to IDX80: everything fails

**Date:** 2026-09-18 · **Script:** `scripts/idx80.py`
**Question:** had the work been tested on IDX80 only? **No.** Prior tests used
top-100 / top-200-by-ADV as proxies. This uses the real thing.

## 1. Membership is point-in-time and well sourced

`idx80_membership_history` carries 8 reconstitution periods (P0-P7), 80 members
each, joined by `effective_from`/`effective_to` so no name enters the book before
it was actually a constituent. Provenance is unusually good: 4 periods
PRIMARY_VERIFIED against BEI announcement documents, 2 CROSS_VALIDATED against
multiple contemporaneous sources, 2 BRACKETED_RECONSTRUCTED with the
reconstruction method recorded.

**Binding limitation: coverage starts 2025-01-02.** Only **19 of 59** panel months
overlap, and P0's `effective_from` is a left-censor to window start, not a real
reconstitution date. There is no pre-2025 IDX80 membership, so **no era test is
possible** — and the 19 available months contain both the 2025 boom and the 2026
crash.

## 2. Result — every strategy inverts inside IDX80

Same 19 periods, same specs, only the universe differs:

| universe | strategy | NET %/yr | t | universe %/yr |
|---|---|---|---|---|
| **IDX80** | hi52 top20 + volex | **−21.34** | −0.72 | −15.66 |
| broad liquid | hi52 top20 + volex | **+19.21** | 0.88 | +2.21 |
| **non-IDX80 liquid** | hi52 top20 + volex | **+25.27** | 1.03 | +7.98 |

Volatility exclusion, the most robust result in the whole program:

| universe | incremental | t | ann |
|---|---|---|---|
| **IDX80** | **−0.286%/mo** | **−0.98** | −3.44%/yr |
| broad liquid | +0.305%/mo | 1.88 | +3.66%/yr |
| **non-IDX80 liquid** | **+0.467%/mo** | **3.35** | **+5.61%/yr** |

## 3. It is the signal, not breadth

The obvious objection is that an IDX80 top-20% book holds only ~15 names, below
the breadth threshold established in the volatility work (IR 0.39 at N=10 vs 1.14
at N=200). Widening the book does not rescue it:

| book width | names | NET %/yr | t |
|---|---|---|---|
| top 20% | 15 | −21.34 | −0.72 |
| top 35% | 25 | −22.92 | −0.88 |
| top 50% | 36 | −24.27 | −0.97 |
| top 75% | 54 | −18.64 | −0.71 |

Negative at every width. The failure is not a sampling-error problem.

## 4. Why — and what it confirms

Over these 19 periods the IDX80 universe returned **−0.72%/mo** (median −1.84%)
against **+0.69%/mo** for the 315 non-IDX80 liquid names (median −2.11%). Large
caps underperformed on the mean; the small-cap mean advantage is the familiar
tail effect (better mean, worse median) documented in the parent findings.

This independently **confirms the prior record** — which stated that volatility
exclusion "fails entirely in the top-ADV tercile (~83 names): all 12 specs tested
era-fail" — now using actual index membership rather than an ADV proxy.

## 5. What it means practically

**If the mandate is IDX80, nothing found in this program applies.** Every edge
identified lives in the liquid names *outside* the index: the volatility overlay
earns +5.61%/yr there at t 3.35, its cleanest reading anywhere, and −3.44%/yr
inside IDX80.

That is a genuine tension with tradeability. IDX80 names are where capacity and
execution quality live (Roll spread 0.39-0.42% vs the thin band's 0.21%, and ADV
an order of magnitude higher); the edge is where capacity is not.

## 6. Caveats

- **19 periods.** All t-statistics here are weak except the non-IDX80 volatility
  overlay (3.35). This is directional evidence, not a settled result.
- **No era test.** Pre-2025 membership does not exist, so the single most
  informative check in this program cannot be run on IDX80.
- The window is dominated by two anomalous regimes (2025 boom, 2026 crash).
- Acquiring pre-2025 IDX80 membership would make this testable properly and is
  now the highest-value remaining data acquisition, ahead of the sector map.
