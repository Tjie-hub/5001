# VERDICT — SCREEN-PM-X1-001 · {X} overnight transmission · 2026-10-05

**Verdict: FAIL (null).** One run of the rev-4 driver (`screen_x1_overnight.py` sha
`ea7cf68c…77c05b`, predeclaration rev 4 sha `994f21a9…f47c5`, GO per REVIEW_R2ter 2026-10-05),
RESULT: `RESULT_X1_20261005T091312Z.json` (this directory), tracked via `research/tracking.py`
(kind `x1_screen`; run_id, git sha `2562b1d`, dataset fingerprint = local walkforward.db, max date
2026-07-29). Bar: |t| ≥ 3.2745 (census 555 + 6 arms). The frozen pass/kill order is followed
below. The stop rule applies to passes; there was no pass.

## 1 · X1-A bar (PRIMARY)

EIDO residual → tick-eligible LW book, 2021-07-05 → 2026-07-29: **n = 1,168, slope −1.11 bp per
1σ of signal, Newey-West(5) t = −0.296**. |t| is far below 3.2745 → **FAIL (null)**. The
predeclared sign was positive; the observed point estimate is negative but statistically
indistinguishable from zero.

## 2 · X1-B sign (replication half)

2010-05-01 → 2021-06-30: n = 2,314, slope **+0.62 bp/1σ, t = +0.889**. The sign matches the
predeclared positive direction, so the opposite-sign kill does not fire — but t is far below the
bar. The discovery half carries no effect either.

## 3 · Absorption share

X1-A absorption = gap slope ÷ (gap slope + open→close slope) = **1.05**. The kill rule's
"real but not capturable" verdict requires the information to be *real* first: neither the
open→close slope (t −0.296) nor the implied gap slope (≈ −23 bp, opposite sign to the outcome
slope) is significant, so the antecedent is unmet. On a null primary the absorption ratio is a
meaningless ratio of two noise slopes; **the honest reading is a plain null, not "real but not
capturable"**. This matches the reviewer's prior: Hamao–Masulis–Ng's t 7.7–13.9 is a *next-open*
result — exactly the uncapturable part — and nothing survived past the open here at all.

## 4 · Single-year concentration

X1-A year-by-year slopes (bp/1σ): 2021 +15.7, 2022 +1.5, 2023 +4.3, 2024 +5.3, 2025 −11.5,
2026 −10.0 — small fragments with sign changes and no dominant year. The era-concentration rule
has nothing to elevate: the verdict stays FAIL (null).

## 5 · All-rows lens (co-equal, REVIEW_R1 §2.3)

X1-C all-rows: slope +1.43 bp/1σ, t = +0.377 — same null conclusion as the primary. The sign
flips between primary (−1.11) and lens (+1.43) with both insignificant: pure noise, no material
disagreement in conclusion. Disclosed as required.

## 6 · k = 1 sensitivity

X1-A restricted to k=1 signal days: t = −0.391 (vs −0.296 pooled). Same null. The k≥2 gap
aggregation is not driving anything (16 EIDO sessions had k≥4 and were excluded; 409
tick-eligible empty-book days are NaN and disclosed).

## 7 · X1-C/D (TLK→TLKM) and X1-E/F (SPY→book)

- **X1-C** (confirmation): n = 1,161, slope **−11.09 bp/1σ, t = −1.933** — negative (opposite to
  the predeclared positive sign) and below the bar; the mild negative slope is a descriptive
  fragment, not a finding. **X1-D**: n = 3,644, slope +0.08, t = +0.871 — null. The Tier-2
  single-name arm adds nothing; consistent with the Gagnon–Karolyi prior as actually supported
  (deviations exist and mean-revert within a day — nothing left for the IDX session to capture).
- **X1-E** (SPY, confirmation): n = 1,170, slope +0.15, t = +0.045 — null. **X1-F**
  (discovery): n = 4,767, slope −4.98, t = −1.568 — below the bar. Broad US risk carries no
  capturable IDX-session information either.

## 8 · Economics (reported, not gating)

- **Timing overlay**: deferring a planned buy from open to close on bottom-tercile days
  "saves" +11.8 bp/trade (EIDO, 30.9% of days); deferring a planned sell on top-tercile days
  −14.5 bp (i.e. it costs). These numbers are the mechanical compensation of a book whose
  open→close drift is negative in this window (2025–26 crash era), conditioned on an
  insignificant signal — **they are not an executable edge**. The pre-closing/closing call
  auction remains the close-fill mechanism (fees + ½-tick floor; no spread cost assumed inside
  the auction).
- **Standalone**: top-tercile open→close long, net of the 0.60% RT floor: **−74.5 bp/trade**
  (EIDO), −77.5 (TLK), −74.9 (SPY). Net of the D-059 modeled cost (book cost ≈ 146 bp):
  **−160 bp/trade**. Dead, exactly as predeclared. The September 2026 EOD-plan illustration was
  NOT run (it lies inside the holdout; R3 only).

## 9 · Recorder correlations (D-062)

Declared, not assumed — and not computable: **FADE-001 and REGIME-002 entry dates have zero
overlap** with the signal window on this corpus (both recorders began after 2026-07-29, the
frozen end), and **VOLEX-001's ledger lacks `trades[].entry_date`** (reported as an error by the
E5 check, never a silent zero). No overlap ⇒ no correlation to declare. The concern that an X1
signal would be correlated with the in-flight recorders is moot for the same reason the verdict
is null.

## ERRATUM (REVIEW_R2ter §2 — restated as the correcting record)

The rev-4 predeclaration, the driver docstring ("EXTRA") and HANDOFF_R2ter stated that rev 3's
`build_signal` used the session count as the regression target and that rev 4 fixed it to the US
return. **That claim is false.** `git show 735721c:docs/research_programs/P-M/broad_search_v2/
x1/screen_x1_overnight.py` line 147 reads `ys_all = np.array([y_map[p][0] …])` — rev 3 was
already correct — and the rev-4 diff only deleted the adjacent, unused `ks_all` line, which was
misread. **No signal change occurred between rev 3 and rev 4**; the EIDO/TLK β regression was
correct throughout, and this verdict's numbers come from a signal identical to rev 3's. The
frozen rev-4 documents are not re-frozen for narrative (reviewer's ruling); this erratum is the
correcting record, and no "rev-3 regression-target bug" may be cited anywhere. Process note
adopted: claimed defects are verified against the committed object (`git show <rev>:<path>`)
before disclosure.

## Holdout (2026-07-30 → latest) — NOT read

This GO does not authorize the holdout and the local corpus ends at the frozen 2026-07-29. At
R3, the snapshot-based single holdout read (~45 sessions) can only **contradict** a pass (sign
flip / collapse) — it cannot confirm one. There is no pass to contradict; the R3 holdout read
remains available per the review's procedure but has nothing to reverse here.

## Disposition

**SCREEN-PM-X1-001 = FAIL (null).** The {X} family closes at screen level: US-session
information (EIDO residual, TLK ADR, SPY) carries no capturable open→close information for the
next IDX session at the deflation bar. The acquired series, manifests, timing contract and
JISDOR path remain the durable assets (recorder proposal stands in HANDOFF_R3). No refinements,
no variants, no further looks at this panel.
