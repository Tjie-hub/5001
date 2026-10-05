# PREDECLARATION — X1 overnight transmission screen (6 arms) · rev 2, 2026-10-05

**Status:** FROZEN DRAFT for REVIEW_R2 (committed with its `.sha256` and the driver
`screen_x1_overnight.py`; **the driver does not run until a REVIEW_R2 file containing GO for X1
exists** — the driver enforces this mechanically). Detailed spec:
`ZCODE_BRIEF_CROSS_ASSET_TRANSMISSION_2026-10-05.md` (on `origin/research/new-order-2026-09-30`);
timing rules `TIMING.md`; counts/σ/MDE `PHASE0_COUNTS.md` (rev 2); priors `PRIORS_X.md`;
A-OPEN audit `../A_OPEN_AUDIT_2026-10-05.md`.

## Revisions since the R1 draft (per REVIEW_R1)

1. **The valid-open restriction is withdrawn** (reviewer rejected it: `open == prev_close` is
   IDX price discreteness + the pre-opening auction clearing at the previous close, not
   corruption). Replaced by the §2.3 ex-ante tick-eligibility rule below. The A-OPEN audit's
   local legs confirm the discreteness gradient; the decisive minute-bar leg is **blocked on
   this host** (store absent) and is handed to the reviewer — if it disagrees, everything stops
   and escalates per §2.2.
2. **Bar updated for the W0 additions** (REVIEW_R1 §1): census 515 + 20 (double-top, counted
   from notes) + 20 (gap-battery placeholder) = 555; + this screen's 6 arms = **561 → bar
   |t| ≥ 3.2745** (exact two-sided `bar_v2` integral; recomputed and frozen).
3. **Gagnon–Karolyi verified with quotes** (PRIORS_X.md §3, partially as claimed) → **X1-C/D
   stay in** per REVIEW_R1 §3.
4. **Confirmation end frozen at 2026-07-29** (local corpus max). **2026-07-30 → latest is a
   pre-declared untouched holdout**, to be read once at R3 from the XPS snapshot.
5. CAL1 was **not admitted** (MDE gate failed; see `../HANDOFF_R2.md`) → the census carries only
   X1's 6 arms from this brief.

## Signal (unchanged from the brief)

`R_D = r_EIDO[US close(d−1) → US close(d)] − β̂_d · r_JKSE,USD[close(d−1) → close(d)]`.

- US session window for day D: US closes inside (close(d), 08:45 WIB day D]; k≥2 gaps compound
  the EIDO leg over all k sessions and keep the single last completed IDX-day USD leg
  (`TIMING.md` §4); **k ≥ 4 excluded**; a k=1-only regression prints in the same run as a
  disclosed sensitivity line (not an arm, not gating).
- `r_JKSE,USD` uses ^JKSE closes and USDIDR=X bars stamped d−1, d (both known ≤ 08:45 WIB D;
  the declared daily-FX stagger applies identically to every historical pair).
- **β̂_d**: OLS slope of the EIDO leg on the JKSE-USD leg over pairs with session ≤ d, rolling
  250 pairs, expanding before that with a minimum of 120 pairs.
- **Standardization**: R_D / σ_d, σ = trailing 250-day std of the (PIT) R series, expanding
  before that with a minimum of 120.
- TLK arm: same construction with TLK and TLKM-USD. SPY arm: raw r_SPY standardized identically.
- **Predeclared sign: positive in every arm.**

## Outcome

- **PRIMARY: open(D) → close(D) of the LW book over tick-eligible members** — adv20 ≥ Rp 5bn as
  of close(d), `volume > 0` at D (D-065 §2, no carry-forward), `tick(close_d)/close_d ≤ 0.5%`
  (IDX schedule; computed ex-ante from close(d) only). Weights: LW = trailing-60-session median
  traded value, normalized within the day's book.
- **Co-equal lens (REVIEW_R1 §2.3): the all-rows book** — same construction without the tick
  rule. Both series print in the same run; the pass rule reads the primary; material
  disagreement is disclosed.
- Lens (not an arm): the overnight gap close(d) → open(D) of the same book; **absorption share**
  = gap slope ÷ (gap slope + open→close slope).
- TLKM arms use TLKM's own open→close (tick-eligible TLKM; TLKM is eligible on essentially all
  days). Benchmarks: the book itself and IHSG open→close (corpus 2021-07→2026-07-29;
  discovery half from ^JKSE Yahoo, disclosed).

## Arms (6; census +6)

| arm | signal → outcome | split | role |
|---|---|---|---|
| X1-A | EIDO residual → LW book (tick-eligible) | 2021-07-05 → **2026-07-29** | **PRIMARY** |
| X1-B | same | 2010-05-01 → 2021-06-30 | replication (sign must match) |
| X1-C | TLK residual → TLKM | 2021-07-05 → 2026-07-29 | single-name, Tier 2 |
| X1-D | same | 2010-05-01 → 2021-06-30 | replication |
| X1-E | SPY → LW book (tick-eligible) | 2021-07-05 → 2026-07-29 | broad-risk comparator |
| X1-F | same | 2010-05-01 → 2021-06-30 | replication |

Counts (tick-eligible primary): 1,168 / 2,612 / 1,165 / 2,604 / 1,168 / 2,618 usable days.
MDE at the 3.2745 bar: 11.3 / 8.8 / 17.1 / 9.4 / 11.3 / 8.7 bp per day per 1σ of signal
(PHASE0_COUNTS.md rev 2).

## Estimator and pass rule (primary)

Time-series OLS slope of the outcome on standardized R_D, Newey-West t (5 lags), headline
per-day. Terciles by fixed normal-quantile cutoffs on the standardized signal (bottom ≤ −0.4307,
top ≥ +0.4307 — PIT by construction), with **year-by-year breakdown mandatory**.

**Pass rule for X1-A:** slope > 0, |t| ≥ **3.2745**, X1-B same sign, and absorption share < 0.8.

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
   auction, slippage risk acknowledged for imbalanced auctions. (The September EOD-trade-plan
   list lives on XPS-13; the reviewer attaches it at R2 and the illustration runs there or at
   R3 — disclosed, not gating.)
2. **Standalone observability**: top-tercile open→close long, net of (a) the frozen 0.60% RT
   floor and (b) the D-059 modeled cost as co-equal column (0.50% fees + Abdi–Ranaldo spread
   floored at one tick, trailing 21 sessions, via the committed `cost_by_adv.py` functions +
   2·σ_d·√(Q/adv20), Q = Rp 100m per position). Expected to fail; reported honestly if it does.

## Correlation (D-062)

Report corr(R_D) with the daily entry counts of FADE-001, REGIME-002 and VOLEX-001 (ledger
dates), declared, not assumed.

## Reproducibility

This predeclaration + `.sha256` + `screen_x1_overnight.py` are committed frozen (one commit)
**before any outcome read by the driver**; the driver refuses to run without a REVIEW_R2 GO
marker. One run through `research/tracking.py` (run_id, git sha, dataset fingerprint) →
`RESULT_X1_<utc>.json` next to the driver. A crash before outcomes print may be re-run with
disclosure; anything after that is a new arm needing a new R2 GO. Local corpus disclosed in
every RESULT (fingerprint + max date 2026-07-29).
