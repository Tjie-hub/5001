# VERDICT: HYP-PM-0020 retail ownership (KSEI) {OC}. G1 NULL, both arms FAIL

**Run:** `RESULT_20261009T075700Z.json`, single G1 run 2026-10-09.
- Sidecar verified; snapshots and KSEI hashes re-verified before any outcome.
- N = 611, bar 3.2987.
- 209 formations for A1, 208 for A2 (A2 needs a previous file).

## Computed pass conditions (frozen; nothing else decides)

| Arm | Net mean / month | NW t | H1 | H2 | FM coef (t) | strength | halves | incremental | **pass** |
|---|---|---|---|---|---|---|---|---|---|
| A1 level | −1.14% | −2.61 | −1.19% | −1.10% | −0.0009 (−0.61) | ✗ | ✗ | ✗ | **FALSE** |
| A2 flow | −2.61% | −7.35 | −1.89% | −3.32% | −0.0001 (−0.08) | ✗ | ✗ | ✗ | **FALSE** |

## Reading (report-only; it cannot rescue or rescore)

**No effect before costs:**

| Arm | Gross Q1−Q5 | t | Q1 | Q5 |
|---|---|---|---|---|
| A1 | −0.30% | −0.71 | +1.24% | +1.54% |
| A2 | −0.05% | −0.13 | +1.34% | +1.39% |

- **The negative net t-values are trading cost only.**
  - A1 legs cost 0.26% and 0.58% a month.
  - A2 legs turn over almost fully each month and cost 1.26% and 1.30%.
  - So the net spread is the cost line, not a reversed effect.
- **Fama-MacBeth after size, Parkinson-60, momentum and VOLEX:** both coefficients are about zero. The
  individual share carries no information beyond those controls.
- **Avoidance book** (universe without Q5 minus the universe): +0.00% (t 0.08) for A1 and +0.01% for A2.
  Dropping the most retail-held names changes nothing.
- **Listed-shares denominator (A1):** gross −0.24% (t −0.48), FM t −0.41. Same NULL.
- **Era:** no year shows a consistent sign. The two halves agree on "nothing".
- **Counts:** 87 and 86 bad-print name-months dropped; 3 stale; 0 σ fallbacks.

## Verdict

**FAILED (F2, prediction failure): a determinate NULL.**
- The MDE was 1.68% a month. The gross spreads are an order of magnitude smaller, with t-values near 0.
- This is not F4 (cost destruction): there is no gross edge for costs to destroy.
- Retail ownership, as KSEI's monthly holdings measure it, does not predict IDX returns at a monthly
  horizon over 2009–2026, either as a level or as a flow.
- Both {OC} slots are consumed (X8); the census stays at **611**.

**Not tested here:** weekly or daily retail flow (path 1, broker imbalance) and other horizons. Any
follow-up needs its own mechanism D-entry. This result is not a licence to re-run variants.
