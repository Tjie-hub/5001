# HYP-PM-0023 — {FQ} E/P value premium (REGISTERED)

> **Status: REGISTERED** 2026-10-28 per DECISION_LOG **D-115** (Owner: "Approved recomend — delegate to zcode",
> 2026-10-28). Family **{FQ}** (P-M · Fundamental-Value, opened D-112), **one arm**. Census **613 → 614**; bar
> **3.300069** = `e_max_abs_z(614)` (`deflation_audit/bar_v2.py`). This record is frozen at registration; its
> sha256 is pinned in `g1_fq_ep.py::REG_SHA256`. The G1 may run **once**. Amendment only by a superseding
> D-entry.

## 1. Hypothesis (sign fixed)
Within the liquid IDX universe, a higher trailing earnings yield (E/P) earns a **positive** premium: the
value-weighted top-tercile minus bottom-tercile monthly return (long–short per freeze §4) has mean > 0 over
2009-05…2026-08 formation dates.

## 2. Universe, formation, signal (frozen: `G0_FREEZE_FQ_EP_2026-10-26.md` §2–§3, sha `e14ab4d9…`; D-111/D-112)
- Formation dates D = KSEI month-ends, **2009-05 … 2026-08 (208 dates)**; universe = 4-letter KSEI codes with
  price > 0, top-200 by `sec_num × price` at D, after the stale-price filter (identical price at D, D−1, D−2
  excludes formation).
- Signal: **E/P = TTM owners' net income (IDR) ÷ market cap at D**, PIT per the frozen D-111 v3 rule
  (deadlines, COVID shifts, FY exceptions, late-filer withholding; USD reporters converted at Yahoo month-end,
  0 of 4,908 vendor rates beyond 3%). Negative TTM → excluded from the rank, not the universe.
- G0 verdict on this exact panel: **203/208 qualifying months, T_eff 16.92 y, power 41.5% ≥ 20% — stop rule
  not fired** (D-114). The 50% post-publication haircut row of D-112 applies to a null G1: weak evidence.

## 3. Test (G1, computed once: freeze §4)
- Terciles of valid E/P at D, **value-weighted**; long top − short bottom; hold one month.
- Return D→D+1: KSEI price ratio with the frozen split rule (whole-ratio + ±25% checks); price-only
  (no dividends); delisting exits at last KSEI print; −100% and below-−95% rows reported beside the result.
- **Statistic: mean monthly long–short return, Newey–West SE (6 lags), one-sided (premium > 0), against bar
  3.300069.** Net line at 0.60% round trip × measured turnover beside the gross.
- **Kill rule: t < 3.300069 → FAILED (F2)**, one run, no rescue; sensitivities are reported, never
  substituted for the primary. A pass advances per HYPOTHESIS_LIFECYCLE (never VALIDATED without a
  forward-test receipt; the `set_status()` gateway governs any status write).

## 4. Pre-declared sensitivities (G1, report-only — freeze §6)
B/M · ROE · equal-weight · the −100% delisting row · era split at 2021-07 · without the D-111 covered
late-filer formation months (Dec 2024–Aug 2026) · USD reporters excluded · top-100 universe. Report-only
lines: FX cross-check, 92-code coverage, per-month missing reasons, USD counts.

## 5. Family scope — owner's no-widening clause (verbatim, D-115 / approval item 1, 2026-10-28)
"**No later widening of {FQ} with a valuation or profitability arm** (B/M, ROE, gross profitability, RNOA,
CF/P): their G1 sensitivities will have been read, so a post-G1 arm would be outcome-conditioned." B/M and ROE
are **G1 sensitivities only**. This clause supersedes `FQ_FAMILY_WIDENING_MEMO_2026-10-28.md` §4
("widen after G1").

## 6. Pins
- Freeze: `G0_FREEZE_FQ_EP_2026-10-26.md` sha256 `e14ab4d96d58947f7d1a475c46f754d39ad258e0215db9f1e6b0aba747358549`
- G0 script: `g0_fq_ep_breadth.py` sha256 `d741e9b5…` (unchanged since `d1e9497`)
- Inputs: `SHA256SUMS_2026-10-26.txt` sha `debbda26…` (fin.db `caefb1a2…`), KSEI csv `38c8a90b…`, Yahoo
  `a0937cde…`, late-filer list `b549358b…`, FY exceptions `013af724…` — verified by the G0 run (D-114).
- G1 script: `g1_fq_ep.py` (sha recorded in D-115 at pin time).
- Census: 614. Bar: 3.300069.
