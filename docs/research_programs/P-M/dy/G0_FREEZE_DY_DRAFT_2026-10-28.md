# G0 FREEZE — C-003 dividend-yield level, family {PY} (FINAL, pinned 2026-10-28)

**Status: FROZEN** per the owner's choices of 2026-10-28 ("Approved recomend — delegate to zcode": dividends
only; floor 0.80%/mo; separate family **{PY}**; liquidity gate **(b)**). Its sha256 is pinned in
`g0_dy_breadth.py::FREEZE_SHA256`; the G0 runs once. Amendment only by a superseding D-entry. The in-repo
prior (alpha_search_v2 #6: mean t 2.46 / median t 4.11 on 2021–26) remains **disclosed multiplicity debt,
used for nothing**.

## 1. Inputs (pinned; verified by the G0 before anything else)
KSEI monthly holdings csv sha `38c8a90b…`; Yahoo USDIDR month-end `a0937cde…`; {FQ} late-filer list
`b549358b…`; fiscal-year exceptions `013af724…`; fin.db as pinned by `SHA256SUMS_2026-10-26.txt`
(`caefb1a2…`, sums sha `debbda26…`) — the same state the {FQ} G0 verified (D-114). Extraction
`extract_dividends.py` v1.1 (v1 `72d2f6d`; v1.1 2026-10-28 `106db63` replaced the f-string SQL predicate in
`_ticker_currency` with constant SQL + bound labels — currency output identical on all 998 tickers; 20
synthetic tests): parent dividends-paid label whitelist, NCI/subsidiary/received/tax/advance exclusions,
DISCRETE/CUMULATIVE layout classifier, USD-reporter conversion at period-end month rate, D-111 v3 deadlines,
late-filer withholding.

## 2. Universe and formation
- Monthly formation at KSEI month-ends 2009-04 → 2026-09 (209 formations; 2 warm-up months).
- Universe per month: top-200 by KSEI market cap (sec_num × price), stale-price filter (the D-112/E/P rule),
  **price ≥ Rp 50 — gate (b), owner 2026-10-28**: the same universe basis as the E/P arm (no ADV gate, no
  2021-07 era break), keeping the FM-over-E/P separator like-for-like.
- Numerator: TTM cash dividends paid = payouts whose period_end lies within 12m of the newest D-111-available
  period (disclosure-anchored), 15-month staleness cap, withheld periods excluded.
- Signal: TTM payout / KSEI market cap (total-payout yield; no per-share arithmetic). Non-payers are yield-0,
  not missing.
- Book: long-only top quintile of valid-yield names (≥ 30 valid names required to form), EW, monthly
  close-to-close, net D-082 cost_realised on turnover (computed at G1 only).

## 3. Coverage gates (the G0's first verdict)
- **Formability:** ≥ 80% of the 209 months must have ≥ 30 valid-yield names (measured: median ≈ 68 valid
  names/month; every year 26.5–41.1% name-month coverage — formability holds throughout).
- Name-month coverage is REPORTED, not gated (the original 60%-of-panel idea in SKEL-C-003 was mis-specified
  for a payer-only signal; non-payers have yield 0, not missing data).

## 4. Power (the G0's second verdict, prior-only)
- **SD source (pre-registered placebo, the {OC}/{RF} precedent):** seeded random quintile assignment of each
  panel month's universe (10 draws, seed 20261028); the monthly Q5−Q1 spread SD σ_m is computed from KSEI
  price returns D→D+1 of the RANDOM buckets. Random assignment carries no yield information, so no signal
  outcome is read (D-092 / HYP-PM-0020 precedent on the same panel).
- **Floor: 0.80%/mo net** (owner, 2026-10-28). Power = Φ(0.008 · √n_formable / σ_m − 3.300069), bar at
  census 614 (this G0 does not change the census — the arm counts only at registration). MDE80 =
  2.487 · σ_m / √n reported beside it. Pass: power ≥ 20%.
- **Honest scale, recorded at pin time (before the run):** the {OC} G0 measured MDE80 ≈ 1.68%/mo on the same
  panel construction (σ_m ≈ 9.8%/mo), implying **power at a 0.80%/mo floor in the single digits against the
  census-deflated bar**. The earlier "power at 0.80%/mo ≈ 33–45%" in the draft §4 (and "~80–95%" in
  `search/cand/C-003` §4) used a plain 5% test instead of the deflation bar — an arithmetic error, corrected
  here. The floor stands as the owner pinned it; the stop rule decides.

## 5. Stop rule
Fires (→ **WITHDRAWN before registration, uncounted**, precedents D-087, D-102, D-110) if: formable share <
0.80, or floor power < 20%, or any pinned-input mismatch. One run; crash-only re-run per the standing rule.

## 6. Family
Separate family **{PY} · Payout** (the draft's Option B — inference-equivalent to widening {FQ}, chosen so
the payout mechanism stands alone; the FM-over-E/P separator at G1 remains mandatory, distinctness being
empirical). Dividends only. **C-009 buyback: UNDERPOWERED standalone; not folded into C-003 (owner
2026-10-28).**

## 7. What the G0 script does NOT do
No return, spread, t-stat, IR or P/L of any dividend-yield sort; no sort of the panel by yield; no reading of
the alpha_search_v2 outcomes. If a step seems to need one, it stops and asks (brief rule).

## 8. Registration text (draft — filed only by the owner, only after a passing G0)

> **HYP-PM-00NN · {PY} · dividend-yield level (payout-commitment risk premium).** Long-only top-quintile
> total-payout-yield book (TTM dividends paid / KSEI market cap, D-111 v3 PIT, universe per the freeze) vs
> the EW liquid book, monthly 2009-04→, net D-082 cost. H₁: net monthly spread ≥ +0.80% with one-sided
> t ≥ 3.300069 (census bar at registration), both halves > 0, FM incremental over E/P, size, Parkinson-60,
> VOLEX (t ≥ 2). Kill: t < bar, either half ≤ 0, or FM incremental < 2 (re-labelled value). Declared debt:
> alpha_search_v2 exploratory trial #6 (2021–26); census 614 → 615 at registration.

## 9. D-entry proposal for the freeze itself (text only)

> ### D-11x · {PY} opened (payout-commitment); C-003 G0 freeze pinned — dividends only, floor 0.80%/mo,
> gate (b); census unchanged at 614
> **Status:** RECORDED · **Date:** 2026-10-28 · **Type:** mechanism + G0 freeze · **Approval authority:**
> Owner, 2026-10-28. Freeze sha `<pin>`; script `g0_dy_breadth.py` sha `<pin>`; inputs per §1. G0 once; stop
> rule per §5; registration only on a separate owner go after the G0.
