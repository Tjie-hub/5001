# VERDICT: HYP-PM-0021 daily OIB continuation. G1 single run (2026-10-09)

**Result:** `RESULT_20261009T134014Z.json` · N = 612, bar 3.2991 · registered D-090 · run once, hashes verified first.
**Verdict: FAIL** (computed booleans): strength ✗, both halves ✗, incremental ✗, next-open ✓, tradeable ✗.

| Condition | Value | Pass |
|---|---|---|
| 1. S_cc (Q5−Q1, close t → close t+1) | **−0.171%/day, NW t −3.29**, n 383 | ✗ (wrong sign) |
| 2. Halves | H1 −0.135% (t −2.02, 230) · H2 −0.227% (t −2.69, 153) | ✗ |
| 3. FM OIB coefficient (controls: same-day return, log ADV, Parkinson-60) | **−0.135%, NW t −6.46** | ✗ |
| 4. S_oc (open t+1 → close t+1) | +0.075%, t 1.70 | ✓ |
| 5. 5-day block, next-open entry, net | **−2.93%** (t −13.99, 75 blocks); gross +0.02% (t 0.10) | ✗ |

Report only: mean block cost 1.69% (entry leg) / 1.26% (exit leg).

## Reading

- The predicted continuation is absent. High-OIB names **underperform** the next day, consistently in
  both halves and incrementally to the same-day return (FM t −6.5).
- The reversal sits **overnight** (close t → open t+1): from the next open the spread is mildly
  positive (+0.075%, t 1.7, below any bar). This is the signature of closing-price pressure — buyer-
  aggressor days close high and give it back at the open — not of a tradeable signal: a next-open
  entry has no gross edge over 5 days (+0.02%) and loses its turnover cost.
- Classified **F2** (registered prediction failed at its own gate). The reversal is an observation, not
  a rescue: it was not the registered sign, |t| 3.29 is below the bar anyway, and it lives in the
  untradeable close→open gap. Any reversal claim is a NEW registration.
- This is the first correctly measured trade-book order-flow test (MAX of the cumulative counters,
  D-089), so unlike HYP-PM-0001/-0009 it is evidence about the mechanism: on IDX, daily aggressor
  imbalance does not predict next-day continuation.
