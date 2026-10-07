# REGISTRATION DRAFT — HYP-PM-0015 · Price-Learning {L1} (DRAFT ONLY — not filed)

**Drafted at G0, 2026-10-06, per `ZCODE_BRIEF_ML_PRICE_RANK_2026-10-06.md`.** This file is a
draft for the owner to file at G0 approval. `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md` and
`DECISION_LOG.md` are **not edited** by this task. Families widen only by formal amendment and
are never narrowed (D-028).

---

## 1. Hypothesis-registry entry (draft text)

| field | draft value |
|---|---|
| id | **HYP-PM-0015** |
| family | **Price-Learning {L1}** — new family (proposal; no existing family covers a learned combination of price/volume features) |
| name | Price-learning cross-sectional ranking model (ML rank) |
| registered | 2026-10-06 (at G0 approval), brief `ZCODE_BRIEF_ML_PRICE_RANK_2026-10-06.md` |
| mechanism | A small frozen model family (ridge / shallow gradient boosting) trained on 14 cross-sectional price/volume feature ranks predicts the cross-sectional rank of next month's open-to-open return, monthly, long-only top quintile, top-150 ADV60 liquid universe, net of 0.60% RT |
| test | HYP-PM-0015-G1: single walk-forward run (train 2001→, validation 2016-01..2021-09 config selection on mean monthly rank IC, test 2021-10..latest-complete-month read once); PREDECLARATION.sha256-frozen |
| endpoint (pass bar, test period) | (1) net top-quintile excess vs the equal-weight base book > 0 with Newey-West t (lag 3) ≥ 3.06 (exact E[max\|Z\|] @ N=266 = 3.0558; brief/D-064 bar 3.06 applied); (2) beats M0 (low Parkinson-60 + 12-1 momentum rank average) paired t ≥ 2; (3) PBO (CSCV-16 over the 6-config grid's validation returns) < 0.5; (4) leave-one-year-out mean excess > 0; (5) vs IHSG reported, not gating |
| null handling | If only M0 passes: valid finding — the simple rule is the edge; the learned models register as NULL and the family question closes at G1. If nothing passes: NULL, family closes |
| multiplicity | 6 grid arms + this registration; deflation bar 3.06 @ N=266 frozen in PREDECLARATION §10.1; the grid enters the program census at the owner's filing act (raises the next gate's bar) |
| correlations | Expected overlap with {V} (volatility exclusion, FWD-PM-VOLEX-001 in flight): the honest prior is that the learned rank is close to low-vol + momentum. Any registration claim of incremental value over M0 must clear condition (2); a pass WITHOUT condition (2) leaves only M0's rule as the finding |
| data epoch + feature space | OHLCV + volume only (no fundamentals, no flow, no events) — invariant-12 scope statement for the family |
| status | G0 FROZEN, awaiting owner approval to run G1 |

## 2. Family proposal (draft text for the registry's family table)

| **P-M · Price-Learning** | {L1} | **1** — HYP-PM-0015 (G1 pending) | family opened at this registration (D-028, PG-3), owner approval at G0. Scope: learned combinations of price/volume features (returns, volatility, liquidity, market-risk structure) ranking the cross-section monthly on OHLCV-only data; liquid IDX top-150 ADV60. Separately denominated from {V} (vol exclusion), {R1,R2} (price reversal), the C-family, and {T1}: those are fixed rules; {L1} is a fitted model family. Widening permitted (e.g. {L2} for new feature spaces or horizons by formal amendment); narrowing or splitting not. |

## 3. DECISION_LOG entry (draft text — placeholder D-0xx, owner assigns)

```
### D-0xx · P-M Price-Learning {L1} family opened; HYP-PM-0015 registered (price-learning
cross-sectional ranking model); G0 predeclaration frozen; G1 gated on approval
**Status:** RECORDED · **Date:** 2026-10-06 · **Type:** New family + registration + G0 freeze ·
**Approval authority:** Owner, 2026-10-06, on `P-M/ml_rank/HANDOFF_G0.md` (branch
`research/ml-rank-2026-10`, frozen sha256 in PREDECLARATION.sha256).

- **Family.** Price-Learning opened as {L1} (new mechanism: learned combination of price/volume
  features; no existing family covers it). Registered count 0 -> 1. Data epoch + feature space:
  OHLCV+volume only, monthly cross-section, top-150 ADV60 liquid universe — separately
  denominated from {V}/{R1,R2}/C/{T1} (fixed rules vs fitted models).
- **HYP-PM-0015.** Ridge/shallow-GBDT on 14 feature ranks vs the pre-declared M0 rule
  (low Parkinson-60 + 12-1 momentum). One G1 run, test 2021-10.. read once, bar: NW t >= 3.06
  (exact E[max|Z|] @ N=266 = 3.0558, brief/D-064 3.06 frozen), beats-M0 t >= 2, PBO < 0.5,
  leave-one-year-out > 0; IHSG reported. If only M0 passes, M0 is the finding.
- **G0 freeze.** PREDECLARATION.md + driver + PIT tests + REGISTRATION_DRAFT committed with
  sha256; PIT verified on synthetic (17 tests) AND on the real corpus (10 cutoffs 2003-2025
  bit-identical under truncation, embargo clean 27 refits, universe identity). Deviations D-1..
  D-5 declared in PREDECLARATION §13 — **D-1 (market proxy for beta/idio in place of
  unavailable pre-2021 IHSG) requires explicit owner acknowledgment**.
- **Multiplicity.** Census N=266 (252 D-062 + 14 CENSUS_UPDATE); +4 XP-001 arms recorded
  2026-09-30 -> 270; bar 3.06 correct at both depths. This registration's 6 grid arms enter the
  census at filing and raise the next gate's bar.
- **Boundaries.** Research-side only; production untouched; ~/jurnal26 and
  research/broad-search-v2-zcode untouched; no registry edits by the executing agent; G1
  machine-gated on ML_RANK_G1_APPROVED=1.
```

## 4. FAILURE_REGISTRY note (draft — only if G1 verdicts NULL)

If M1/M2 (or everything incl. M0) NULLs at G1, the draft failure row is: *HYP-PM-0015
(Price-Learning {L1}) — learned rank of 14 price/volume features, monthly top-150 ADV60,
2016-2021 validation selection, 2021-10+ test read once — NULL (or: only M0 passes → learned
models add nothing over low-vol+momentum rule); multiplicity 6 grid arms carried; family closes
per the predeclared null handling.*
