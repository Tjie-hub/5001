# REGISTRATION DRAFT — HYP-PM-0016, sniper setup filter (meta-label, {L1})

**Status:** DRAFT (G0). Not filed. The D-number is **D-0xx**; the next free number at the time of
writing is **D-071** (D-070 = the price-pattern closure, filed 2026-10-07 at `a28ec7e`). The owner
assigns the number at filing.

---

### D-0xx · Sniper setup filter admitted as HYP-PM-0016 (meta-label on the owner's entry); G0 frozen — the last price-feature study under D-070
**Status:** RECORDED · **Date:** 2026-10-0x · **Type:** Registration + G0 freeze ·
**Approval authority:** Owner, 2026-10-07, "yes, do both", on
`ZCODE_BRIEF_SNIPER_FILTER_2026-10-07.md` (04d412b) as overridden by
`ZCODE_NEXT_TASKS_2026-10-07.md` (7ccb15d); G0 frozen at `research/sniper-filter-2026-10`
(PREDECLARATION.sha256 at the freeze commit).

- **Why admitted.** **D-070** (§Decision 2) closes daily-OHLCV-shape research and names
  HYP-PM-0016 as the **last admitted price-feature study**: it filters an existing owner entry
  rule (meta-labelling — the entry stays) and its pre-registered baseline is a risk measure
  (low volatility), not a price pattern.
- **Family.** Price-Learning **{L1}** (D-067) — "learned combination of price/volume features";
  the family stays as it is and HYP-PM-0016 inherits its multiplicity. **Census: 276 + 4
  configurations = 280** (D-070 adds no trials); the deflation bar at N=280 is **3.07** (exact
  E[max|Z|] = 3.0713; the D-067 M0-uncounted convention would give N=279 → 3.0702 — same bar at
  2 dp).
- **Study.** One G1 walk-forward on the exit study's E-SN fills (outcome = the frozen X1 net R):
  10 setup-day features (zone structure, planned R:R, MA distances/slope, Parkinson-60, 126-session
  return, IHSG-vs-MA200), each cross-sectionally ranked over the trailing 250 sessions of setups;
  M0 = the pre-registered low-vol+momentum rank mean; M1 = L2 logistic ("R > 0", C ∈ {0.1, 10},
  chosen on validation); M2 = one shallow HistGradientBoosting; selection = top 40% of scores
  among the trailing 250 sessions' setups. Train 2001–2015-12, validation 2016-01..2021-09, test
  2021-10.. read once; yearly expanding refits with a 20-session label embargo.
- **Pass bar (TEST).** (1) selected − all filled monthly mean R difference > 0 with Newey-West t
  (lag 3) ≥ 3.07; (2) selected mean net R > 0; (3) difference > 0 in both halves (to 2023-12 /
  from 2024-01); (4) M1/M2 beat M0 with paired monthly t ≥ 2, else M0 is the finding; (5)
  PBO < 0.5 (`research/statistics.py::pbo_cscv`, n_splits 16) over the 4-configuration grid.
- **Honest prior.** A NULL, or "skip the volatile names", is the likely answer (HYP-PM-0015:
  price-only learning converges to low volatility plus momentum; D-068: FAILED). Both outcomes
  are useful; neither is an edge claim.
- **Boundaries.** Research-side only; read-only data (PKLs + mode=ro DB for the fingerprint and
  the IHSG series); the exit study's frozen files are called, never modified; ~/jurnal26,
  production, `ops/hardening` and the other branches untouched; G1 machine-gated on
  `SNIPER_FILTER_G1_APPROVED=1`.
- **Forward test (record only, nothing built).** If a model passes at G1, its frozen score
  becomes a forward test on the owner's live setups via jurnal26's `setup_outcomes` table (same
  X1/P0 rules, 0.60% RT, outcomes in R). **Subset caveat:** jurnal26 candidates come from 5001's
  feeds, not a full-market sniper scan — only the `watchlist`-sourced rows match E-SN's
  selection; the forward test should use that subset.
