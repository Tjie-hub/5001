# DRAFT PREDECLARATION — X1 overnight transmission screen (6 arms) · 2026-10-05

**Status: DRAFT — not frozen, not sha256-stamped, not run.** Under the broad-search-v2 gates this
predeclaration is submitted to the Owner at R2 (~2026-10-19) and runs only after the Owner's
frozen-plan review. The detailed spec is `ZCODE_BRIEF_X1_OVERNIGHT_2026-10-05.md`; timing rules in
`TIMING.md`; counts/sigma/MDE in `PHASE0_COUNTS.md`; priors in `PRIORS_X.md`.

## Spec deviations from the brief (disclosed up front, Owner must approve at R2)

1. **Outcome restriction (valid-open).** The brief's outcome is the LW book open→close. The
   P0-D open-quality table shows `open == prev_close` on 21–34% of MEGA-CAP name-days (BBCA/TLKM/
   BBRI 2022+, direct DB check) and 47–56% of liquid-panel name-days 2023–2025: a stale open print
   makes "open→close" partly an overnight return — not the capturable leg. **PRIMARY outcome = LW
   book over valid-open members only** (`open > 0`, `open != close`, `open != prev_close`,
   `volume > 0`, adv20 ≥ Rp 5bn as of the prior session, no carry-forward). The unrestricted book
   is reported as a secondary line in the same run. This restriction applies to every arm.
2. **Bar moved by the W0 recount.** The brief said |t| ≥ ≈3.07 at N = 276. The Owner's 2026-10-05
   recount (245 countable pattern-study trials added) gives census N = 515 + 6 arms = **521 → bar
   |t| ≥ 3.2534** (exact two-sided integral, `deflation_audit/bar_v2.py`). If the Owner's ratified
   census differs, the bar is recomputed from the final N and written here before the freeze.
3. **TLK arm discovery window.** The brief fixes the discovery split as 2010-05 → 2021-06
   (EIDO-anchored). For the TLK arm this leaves usable TLK data before 2010-05 unused; the screen
   follows the brief's split exactly (X1-D = 2010-05 → 2021-06); the longer 2001-05 → 2010-04 TLK
   segment is NOT tested (no extra arms).
4. **Local corpus, not snapshot.** The snapshot `walkforward-20261004-213000.db.zst` never
   reached this host; the screen reads the local `D:\IDX\data\walkforward.db`
   (fingerprint + `max(date) = 2026-07-29` recorded by `research.tracking` and disclosed in the
   RESULT). Confirmation window = 2021-07-05 → 2026-07-29.

## Signal (unchanged from the brief)

`R_D = r_EIDO[US close(d−1) → US close(d)] − β̂_d · r_JKSE,USD[close(d−1) → close(d)]`, β̂_d =
rolling 250-pair OLS (expanding, min 120 pairs), standardized by trailing-250-pair σ of R
(expanding, min 120). TLK arm: TLK vs TLKM-USD, same construction. SPY arm: raw r_SPY,
standardized the same way. **Predeclared sign: positive in every arm.** Gap aggregation per
`TIMING.md` §4 (k≥2 US sessions: compounded EIDO leg minus the single last completed IDX-day USD
leg; k≥4 excluded; k=1-only regression printed in the same run as a disclosed sensitivity line).

## Outcome

Primary = open(D) → close(D) of the valid-open LW book (X1-A/B/E/F) or TLKM (X1-C/D) per the
restriction above. Lens (not an arm): the gap close(d) → open(D); absorption share = gap slope ÷
(gap slope + open→close slope).

## Arms (6; census +6)

| arm | signal → outcome | split | role |
|---|---|---|---|
| X1-A | EIDO residual → LW book (valid-open) | 2021-07-05 → 2026-07-29 | **PRIMARY** |
| X1-B | same | 2010-05-01 → 2021-06-30 | replication (sign must match) |
| X1-C | TLK residual → TLKM (valid-open) | 2021-07-05 → 2026-07-29 | single-name, Tier 2 |
| X1-D | same | 2010-05-01 → 2021-06-30 | replication |
| X1-E | SPY → LW book (valid-open) | 2021-07-05 → 2026-07-29 | broad-risk comparator |
| X1-F | same | 2010-05-01 → 2021-06-30 | replication |

Universe/weights: LW = trailing-60-session median traded value weights, formed with information
≤ d, normalized within the day's valid-open members; `issuance=True` recorded in params; prices
through `research.rulecard.data.load_extended_ohlcv(issuance=True)` (no hand-rolled SQL).

## Estimator and pass rule (primary)

Time-series OLS slope of the outcome on standardized R_D, Newey-West t (5 lags), headline per-day.
Also: tercile means (bottom/middle/top; terciles = standardized-signal ≤ −0.4307 / ≥ +0.4307,
PIT by construction) with year-by-year breakdown (mandatory — era concentration is what
downgraded S2).

**Pass rule for X1-A:** slope > 0, |t| ≥ **3.2534** (bar above), X1-B same sign, and absorption
share < 0.8.

**Kill rules.** X1-A below the bar ⇒ FAIL (null). X1-B opposite sign ⇒ FAIL. Absorption ≥ 0.8
with an insignificant open→close slope ⇒ **"real but not capturable"** (counts as FAIL for
trading; recorded as an information finding). Any single calendar year carrying > half of X1-A's
t ⇒ verdict at most "era-concentrated, not opened" (D-064 S2 precedent). **Stop rule: a pass ⇒
stop — no refinement, no variants.**

## Economics (reported, not gating)

1. **Timing-overlay value**: on bottom-tercile days deferring a planned buy from open to close
   saves −E[open→close | bottom]; on top-tercile days deferring a planned sell saves
   E[open→close | top]; expressed in bp per affected trade and share of days affected. Close-fill
   mechanism: the IDX pre-closing/closing call auction; fill assumption: market-on-close at the
   official close, fees + ½-tick floor, no spread cost inside the auction, slippage risk
   acknowledged. Same calculation on last month's EOD-trade-plan entry list (illustration only,
   read-only) — pending locating that list on this host.
2. **Standalone observability**: top-tercile open→close long, net of the 0.60% RT floor and the
   D-059 modeled cost. Expected to fail; reported honestly if it does.

## Correlation (D-062)

Report corr(R_D) with the daily entry counts of FADE-001, REGIME-002 and VOLEX-001 (ledger
dates), declared, not assumed. Expected small (US-session information is exogenous to IDX paths).

## Reproducibility

Predeclaration + `.sha256` + `screen_x1_overnight.py` committed in one freeze commit BEFORE any
outcome read; one run through `research/tracking.py` (run_id, git sha, dataset fingerprint);
RESULT_X1_<utc>.json next to the driver. A crash before outcomes print may be re-run and
disclosed; a re-run after outcomes print is a new arm needing the Owner's approval.
