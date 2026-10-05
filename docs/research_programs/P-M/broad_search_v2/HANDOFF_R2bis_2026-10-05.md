# HANDOFF_R2bis — re-freeze complete · 2026-10-05 (ZCode)

**Branch:** `research/broad-search-v2-zcode`, one re-freeze commit on top of the R2 package.
**No driver ran.** The screen awaits the reviewer's exact GO line (B3).

## Frozen package (rev 3)

| artifact | sha256 |
|---|---|
| `x1/PREDECLARATION_X1_OVERNIGHT.md` (rev 3) | `bbd449f63c2f32624a0cab07f019aa16ea9fcfa85634dc5b0a2835536db6c014` |
| `x1/screen_x1_overnight.py` (rev 3 driver) | `b5a55cc1a6eb027963b95f825417b38f7cb155f66b2324025a27e1c8a0d97394` |
| `x1/pit_tests_x1.py` (+ `PIT_TESTS_X1.json` output) | `1bee1565f511f1c10442fb994555a4487db1a3a92c4c28cb9583a29120341033` |

All three hashes are pinned in `x1/PREDECLARATION_X1_OVERNIGHT.sha256`. The GO line for R2-bis,
when the reviewer issues it, must read:

```
R2-DECISION: X1 GO driver_sha256=b5a55cc1a6eb027963b95f825417b38f7cb155f66b2324025a27e1c8a0d97394 predeclaration_sha256=bbd449f63c2f32624a0cab07f019aa16ea9fcfa85634dc5b0a2835536db6c014
```

(the B3 guard verifies both shas against the files on disk and refuses otherwise).

## Fix-by-fix confirmation (REVIEW_R2 §2–§3)

- **B1/B1b** — hedge legs rebuilt explicitly by date stamp: for D = cal[j], only values stamped
  d = cal[j−1] and d₋₁ = cal[j−2] (`fx_idr_usd_leg`); no stamped-D value enters; no raw-series
  misalignment (T2 asserts it).
- **B2** — FX direction corrected everywhere: `r_USD = (idx_d/idx_{d−1}) · (FX_{d−1}/FX_d) − 1`.
  TIMING.md amended to **rev 2** (§3 rewritten). The **TLK arm now has its TLKM-USD hedge leg**
  (corpus TLKM closes at the same stamps) — the rev-2 driver had wrongly reused the JKSE leg
  there, which the review's B2 instruction implied and this re-freeze fixes beyond the letter.
  JISDOR is auxiliary and computes no returns (checked).
- **B3** — guard replaced: exact `R2-DECISION: X1 GO driver_sha256=… predeclaration_sha256=…`
  line, both shas checked against disk. The old substring guard is gone.
- **B4** — empty-book days are NaN (weight-sum-0 guard), count disclosed in the RESULT
  (`empty_book_days`).
- **B5** — k ≥ 4 exclusion implemented; excluded count printed per signal
  (`excluded_k_gt_max_per_signal`).
- **E1** — AR terms via the committed `cost_by_adv.ar_terms`/`ar_spread_from_terms` (correct
  `(c_t−η_t)(c_t−η_{t+1})`), 21-term rolling mean **shifted 2 sessions** (a day-D cost uses terms
  ending ≤ d−1).
- **E2** — spread floored at the tick **fraction** (`tick_frac`), not the Rupiah tick.
- **E3** — TLKM standalone inside the guarded block; array indexing `cost_rt[j, tl]`; a cost-block
  failure can no longer crash after the arms print (whole block guarded, error recorded).
- **E4** — tick schedule disclosed as current-schedule-for-all-dates (historical schedules not
  verifiable from this host); boundary sensitivity counted and committed: **116,119 discovery /
  81,816 confirmation liquid name-days** with tick_frac in [0.004, 0.0065] — a dense zone, so the
  reviewer can see the cut's leverage.
- **E5** — ledger schemas checked (`trades[]` present, `entry_date` on every trade); low overlap
  recorded as `{"error": "insufficient overlap"}`, never a silent zero.
- **Minors** — β̂/σ use the latest window **strictly before j** (bisect, no silent drops) and
  exactly **250**-point windows.

## PIT tests T1–T3 — RUN AND PASS (`PIT_TESTS_X1.json` committed)

- **T1 invariance**: 50 fixed-seed (42) sessions, open(D)/close(D) (corpus TLKM leg), JKSE_D and
  FX_D perturbed ±5% → **R_std bit-identical at every perturbed session for all three signals
  (50/50 each)**. Sanity: 4,576–5,920 later sessions per signal DID move — the perturbation
  propagated only through the legitimate channel (D's stamps enter later pairs/β̂).
- **T2 timestamps**: 14,401 sessions checked; every hedge value stamped d or d₋₁ (< D, re-derived
  by explicit-stamp recomputation, max |diff| < 1e-15); every used US close lands ≤ 08:45 WIB of
  D under the DST-aware mapping.
- **T3 sign check**: IDR depreciation with a flat index gives a **negative** USD return
  (appreciation positive) for both the ^JKSE leg and the corpus-TLKM leg. (First run caught a
  test-construction error — depreciation placed outside the compared stamps — fixed in the test,
  not the driver.)
- One extra robustness fix surfaced while running: `pd.Series.get` returns `None` for a stamp
  missing from ^JKSE; the leg builder now skips such sessions (counted as absent legs) instead of
  crashing — same class as B1b hardening, disclosed here.

## Other R2 items (no action needed, recorded)

- PRIORS_X §3 now carries the explicit not-supported list for Gagnon–Karolyi; the predeclaration
  cites only the supported part (deviations exist; ~one-day mean reversion).
- The reviewer-delivered `x1/econ_input/eod_plan_2026-09.csv` (Sept 2026, inside the holdout) is
  acknowledged: the timing illustration runs **only at R3, inside the single holdout read**.
- Syncthing on tjiejet: re-checked before this commit — no `exec(open(...))` file reappeared (the
  resurrected dir contains only the Dell's two 2026-10-01 .md files).

## Stop

ZCode stops here. The reviewer checks the diff against REVIEW_R2's list and, if clean, issues
the exact GO line in `REVIEW_R2bis_<date>.md`; the driver then runs once.
