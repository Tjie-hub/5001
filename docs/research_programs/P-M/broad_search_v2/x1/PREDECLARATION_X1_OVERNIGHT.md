# PREDECLARATION — X1 overnight transmission screen (6 arms) · rev 4, 2026-10-05

**Status:** FROZEN DRAFT for REVIEW_R2-ter (committed with its `.sha256`, the re-frozen driver
`screen_x1_overnight.py` and the PIT tests `pit_tests_x1.py`; **no driver runs until a
REVIEW_R2*.md contains the exact hash-bound GO line on some line of some file — enforced
mechanically, see Guard**).
Detailed spec: `ZCODE_BRIEF_CROSS_ASSET_TRANSMISSION_2026-10-05.md`; timing rules `TIMING.md`
(rev 2); counts/σ/MDE `PHASE0_COUNTS.md` (rev 2); priors `PRIORS_X.md`; A-OPEN audit
`../A_OPEN_AUDIT_2026-10-05.md` + the reviewer's minute-bar receipt
`../A_OPEN_MINUTE_LEG_2026-10-05.{py,json}` (on this branch, cherry-picked from
`origin/research/new-order-2026-09-30`).

## Pre-run amendments (rev 3 → rev 4; authority: REVIEW_R2bis_2026-10-05.md)

All made **before any outcome read**; the census stays 555 + 6 (bar unchanged, §Estimator).

- **N1 — gap_tlkm built.** `books()` now returns `gap_tlkm` (tick-eligible TLKM,
  `open(D)/close(d) − 1`, same construction as `oc_tlkm`); the absorption loop no longer crashes
  after the arms print.
- **N2 — SPY arm aligned to the spec.** SPY is now the **raw compounded US-window return,
  standardized by the trailing σ of the y series over sessions strictly before j** (250 / min
  120) — no β, no hedge leg. The rev-3 driver wrongly residualized SPY against JKSE-USD. The
  spec text is unchanged; this aligns the code to it. **T1-SPY** added: perturbing JKSE_D/FX_D/
  TLKM open(D)/close(D) leaves SPY's R_std bit-identical (50/50) and moves **zero** later SPY
  sessions — proving the arm is raw.
- **N3 — guard scans all lines of all files.** `check_guard` no longer stops at the first
  candidate line (the REVIEW_R2 §2-B3 format template, which sorts before REVIEW_R2bis and
  carries no hashes); it scans every line of every `REVIEW_R2*.md`, ignores candidates without
  both 64-hex shas, accepts only a full match against the files on disk, and otherwise refuses
  listing every candidate and why it failed (fail-closed). **T4** added: four guard cases
  (template-only → refuse; wrong-sha → refuse with candidate listing; template + valid line in a
  later file → accept; no file → refuse).
- **BEYOND the review's list — disclosed prominently: a signal-construction bug found and fixed
  during the N2 rewrite.** The rev-3 `build_signal` set the regression target `ys_all =
  y_map[p][1]` — that is the session count k, **not the US return** `y_map[p][0]`. The β̂
  regression therefore fit a near-constant target (garbage slope) for EIDO/TLK; T1–T3 could not
  catch it (T1 is invariance, not correctness). Rev 4 sets `ys_all = y_map[p][0]`, which is what
  the spec has always said ("OLS of the US leg on the hedge leg"). This changes the EIDO/TLK
  signal materially and is the honest reason this rev-4 diff exceeds N1–N3.
- **Non-blocking cleanups (REVIEW_R2bis):** dead `beta_cache` deleted; `empty_a` computed (both
  empty-book counts disclosed); the driver's E4 disclosure now carries the confirmation-half
  boundary count (81,816; discovery 116,119) alongside the test output.
- Review files (`REVIEW_R2_2026-10-05.md`, `REVIEW_R2bis_2026-10-05.md`, minute-bar receipts,
  the EOD-plan input) are cherry-picked onto this branch so the GO file exists next to the driver
  at run time.

## Pre-run amendments (rev 2 → rev 3; authority: REVIEW_R2_2026-10-05.md)

All fixes below were made **before any outcome read** and are disclosed pre-run amendments, not
new arms; the census stays 555 + 6 (bar unchanged, §Estimator).

- **B1/B1b — hedge-leg look-ahead and misalignment (blocking).** The rev-2 driver's JKSE/FX legs
  were stamped `cal[j]` = D (part of the outcome window; mechanical negative slope) and, as
  written, crashed on the raw ^JKSE series. Rev 3 builds the hedge leg explicitly by date: for
  D = cal[j], values stamped **d = cal[j−1] and d₋₁ = cal[j−2]** only.
- **B2 — FX direction (blocking).** USDIDR=X is **IDR per USD**; `r_JKSE,USD =
  (JKSE_d/JKSE_{d−1}) · (FX_{d−1}/FX_d) − 1`. TIMING.md §3 amended to rev 2. The **TLK arm now
  uses its proper TLKM-USD hedge leg** (corpus TLKM closes at the same stamps; the rev-2 driver
  wrongly reused the JKSE leg there). JISDOR is auxiliary and computes no returns.
- **B3 — run guard (blocking).** The rev-2 substring guard would have unlocked on the NO-run
  review itself. Rev 3 runs only if a `REVIEW_R2*.md` contains the exact line
  `R2-DECISION: X1 GO driver_sha256=<sha> predeclaration_sha256=<sha>` **and both shas equal the
  files on disk**.
- **B4 — empty book ≠ zero return (blocking).** Days with no eligible member are NaN, never 0.0;
  the count is disclosed per run.
- **B5 — k ≥ 4 exclusion implemented (blocking).** Sessions whose signal window spans more than
  3 US sessions are excluded; the excluded count is printed per signal in the RESULT.
- **E1–E3 — D-059 cost block.** AR terms now come from the committed `cost_by_adv.ar_terms` /
  `ar_spread_from_terms` (correct `(c_t−η_t)(c_t−η_{t+1})` form), the 21-term mean is **shifted
  2 sessions** so a day-D cost uses terms ending ≤ d−1; the spread is floored at the tick
  **fraction** (not the Rupiah tick); the TLKM standalone line is inside the guarded block and
  indexes arrays correctly; a cost-block failure can no longer crash after the arms print.
- **E4 — tick schedule disclosed.** The current IDX schedule is assumed for all dates
  (historical schedules not verifiable from this host); the run reports the count of liquid
  name-days with tick_frac in [0.004, 0.0065] (boundary sensitivity), split by half.
- **E5 — recorder correlations.** Ledger schemas are checked (`trades[].entry_date` must exist
  in all three); low overlap is reported as an error, never a silent zero.
- **Minor fixes.** β̂ and σ use the **latest window strictly before j** (no silent drops when the
  previous session lacked a pair) and exactly **250**-point windows (was 251).
- **PIT tests T1–T3** (`pit_tests_x1.py`, output `PIT_TESTS_X1.json`, committed): T1 invariance
  (perturbing open(D), close(D), JKSE_D, FX_D by ±5% on 50 fixed-seed sessions leaves every
  R_std[D] bit-identical), T2 timestamp assertions (hedge stamps < D; every US close ≤ 08:45 WIB
  of D under the DST-aware mapping), T3 sign check (IDR depreciation with a flat index gives a
  **negative** USD return, appreciation positive, both leg variants). All were **run and pass**.

## Signal

`R_D = r_EIDO[US close(d−1) → US close(d)] − β̂_d · r_JKSE,USD`, with (rev 2 TIMING.md §3):

- US session window for day D: US closes inside (close(d), 08:45 WIB day D]; k≥2 gaps compound
  the US leg over all k sessions and keep the single last completed hedge leg; **k ≥ 4 excluded
  (implemented, B5)**; a k=1-only regression prints in the same run as a disclosed sensitivity
  line (not an arm, not gating).
- **Hedge leg**: `(JKSE_d/JKSE_{d−1}) · (FX_{d−1}/FX_d) − 1` — stamps d, d₋₁ only; FX is IDR per
  USD so the ratio is inverted (B2).
- **TLK arm hedge**: TLKM-USD built identically from corpus TLKM closes at stamps d, d₋₁.
- **β̂_d**: latest 250-pair window with session ≤ d (expanding to min 120); **σ_d**: latest 250
  values of the PIT R series (expanding to min 120). SPY arm: raw r_SPY standardized identically.
- **Predeclared sign: positive in every arm.**

## Outcome

- **PRIMARY: open(D) → close(D) of the LW book over tick-eligible members** — adv20 ≥ Rp 5bn as
  of close(d), `volume > 0` at D (D-065 §2, no carry-forward), `tick(close_d)/close_d ≤ 0.5%`
  (IDX schedule, assumed current for all dates — E4 disclosure in the run). Weights: LW =
  trailing-60-session median traded value, normalized within the day's book.
- **Co-equal lens (REVIEW_R1 §2.3): the all-rows book.** Both series print in the same run; the
  pass rule reads the primary; material disagreement is disclosed.
- Lens (not an arm): the overnight gap close(d) → open(D) of the same book; **absorption share**
  = gap slope ÷ (gap slope + open→close slope).
- TLKM arms use TLKM's own open→close. Benchmarks: the book itself and IHSG open→close (corpus
  2021-07→2026-07-29; discovery half from ^JKSE Yahoo, disclosed).

## Arms (6; census +6)

| arm | signal → outcome | split | role |
|---|---|---|---|
| X1-A | EIDO residual → LW book (tick-eligible) | 2021-07-05 → **2026-07-29** | **PRIMARY** |
| X1-B | same | 2010-05-01 → 2021-06-30 | replication (sign must match) |
| X1-C | TLK residual → TLKM | 2021-07-05 → 2026-07-29 | single-name, Tier 2 |
| X1-D | same | 2010-05-01 → 2021-06-30 | replication |
| X1-E | SPY → LW book (tick-eligible) | 2021-07-05 → 2026-07-29 | broad-risk comparator |
| X1-F | same | 2010-05-01 → 2021-06-30 | replication |

Counts (tick-eligible primary, rev 2 of PHASE0_COUNTS): 1,168 / 2,612 / 1,165 / 2,604 / 1,168 /
2,618 usable days. MDE at the 3.2745 bar: 11.3 / 8.8 / 17.1 / 9.4 / 11.3 / 8.7 bp per day per 1σ
of signal. (The rev-3 driver's re-built signal may shift usable-day counts at the margin — e.g.
the k≥4 exclusion now actually fires and empty-book days are NaN; the RESULT discloses both
counts and any material shift is reviewer-visible before the run reads outcomes.)

## Estimator and pass rule (primary)

Time-series OLS slope of the outcome on standardized R_D, Newey-West t (5 lags), headline
per-day. Terciles by fixed normal-quantile cutoffs on the standardized signal (bottom ≤ −0.4307,
top ≥ +0.4307 — PIT by construction), with **year-by-year breakdown mandatory**.

**Pass rule for X1-A:** slope > 0, |t| ≥ **3.2745** (exact `bar_v2` integral at census
N = 555 + 6 = 561), X1-B same sign, and absorption share < 0.8.

**Kill rules.** X1-A below the bar ⇒ FAIL (null). X1-B opposite sign ⇒ FAIL. Absorption ≥ 0.8
with an insignificant open→close slope ⇒ **"real but not capturable"** (counts as FAIL for
trading; recorded as an information finding). Any single calendar year carrying > half of X1-A's
t ⇒ verdict at most "era-concentrated, not opened" (D-064 S2 precedent). **Stop rule: a pass ⇒
stop — no refinement, no variants.**

## Economics (reported, not gating)

1. **Timing-overlay value**: on bottom-tercile days deferring a planned buy from open to close
   saves −E[open→close | bottom]; on top-tercile days deferring a planned sell saves
   E[open→close | top]; expressed in bp per affected trade and the share of days affected.
   Close-fill mechanism: the IDX pre-closing/closing call auction; fill assumption:
   market-on-close at the official close, fees + ½-tick floor, no spread cost inside the
   auction, slippage risk acknowledged for imbalanced auctions. The September 2026 EOD-trade-plan
   input (`x1/econ_input/eod_plan_2026-09.csv`, reviewer-delivered) lies **inside the frozen
   holdout**, so that illustration runs **only at R3, inside the single holdout read**.
2. **Standalone observability**: top-tercile open→close long, net of (a) the frozen 0.60% RT
   floor and (b) the D-059 modeled cost as co-equal column (0.50% fees + Abdi–Ranaldo spread
   floored at one tick via the committed `cost_by_adv.py` functions, terms ending ≤ d−1, +
   2·σ_d·√(Q/adv20), Q = Rp 100m per position). Expected to fail; reported honestly if it does.

## Correlation (D-062)

Report corr(R_D) with the daily entry counts of FADE-001, REGIME-002 and VOLEX-001 (ledger
dates, schema-checked per E5), declared, not assumed.

## Prior citation for X1-C/D (REVIEW_R2 §4)

X1-C/D cite **only the supported part** of Gagnon–Karolyi (2010): ADR–home-market price
deviations exist and mostly mean-revert within a day (θ = −0.55; significant for essentially all
pairs). **Not relied on and not supported as claimed:** "sizeable" deviations (the published
average is an "economically small" 4.9 bp), the "arbitrage energy" phrase (not in the paper), and
any long-persistence reading (the paper also documents persistence up to five days tied to
holding costs — carried as a caveat). PRIORS_X.md §3 states this explicitly.

## Reproducibility

This predeclaration + `.sha256` + `screen_x1_overnight.py` + `pit_tests_x1.py` (+ its output)
are committed in **one re-freeze commit** before any outcome read; the driver refuses to run
without the exact hash-bound REVIEW_R2 GO line (B3). One run through `research/tracking.py`
(run_id, git sha, dataset fingerprint) → `RESULT_X1_<utc>.json` next to the driver. A crash
before outcomes print may be re-run with disclosure; anything after that is a new arm needing a
new R2 GO. Local corpus disclosed in every RESULT (fingerprint + max date 2026-07-29).
