# W3 · SCREEN SKETCHES — drafts only; the Owner picks at R1 · 2026-10-05

Sketches, not frozen predeclarations. Each becomes a PREDECLARATION + `.sha256` + driver freeze
commit only after the Owner picks it (R1) and reviews the frozen plan (R2). Bar for every sketch:
**|t| ≥ 3.25** (recomputed at freeze from the ratified census + own arms). Tradeability rule
(D-065 §2), long-only, costs gross+net (0.60% RT floor + D-059 modeled cost), era-by-year table
mandatory, stop rule — all apply verbatim (broad-search brief §4).

## SKETCH-1 · X1 overnight transmission (US session → next IDX session)

**Full detail:** `P-M/cross_asset/DRAFT_PREDECLARATION_X1_OVERNIGHT.md` + `TIMING.md` +
`PHASE0_COUNTS.md` + `PRIORS_X.md`. Six arms (EIDO/TLK/SPY × confirmation/discovery), outcome =
valid-open LW book / TLKM open→close, NW(5) slope on the standardized residualized signal,
terciles + year-by-year, absorption-share capturability split, timing-overlay economics.
Counts: 1,166 / 2,169 / 839 / 1,326 / 1,166 / 2,174 usable days; MDE 14–22bp/day per 1σ.
**Verdict: runnable as-is at R2** (two disclosed spec deviations: valid-open restriction; local
stale DB until the snapshot arrives).

## SKETCH-2 · TS1 suspension/UMA resumption

- **Rule / PIT:** event = first session with a quote after a real `suspension`-classified gap
  (`suspension_events`, resume_date + classification; announcement-quality audit of 20 random
  events vs IDX disclosures before any run). Entry at the resumption-day **close** (the resumption
  open is the price-discovery shock itself — predeclare entry at close to avoid buying the
  printing line) or next open; horizons 5 and 20 sessions (2, per rule).
- **Universe:** names with adv20 ≥ Rp 5bn pre-suspension; tradeability rule at exit.
- **Estimand / benchmarks:** per-event excess vs EW liquid book and vs IHSG over the same window;
  date-clustered t (events cluster on resume dates); headline per-event-date mean.
- **Split:** 2022-04→2026-07 only (the archive's real coverage; pre-2022 does not exist) —
  **no discovery/confirmation halves available; say so in the predeclaration.**
- **Power:** N = 359 events, MDE ≈ 0.7–1.0%/20d at the bar — **expected underpowered; run only
  if the Owner accepts a likely-null**; the null is still the first read of this archive.
- **Kill rule:** |t| < bar ⇒ FAIL (null); no sub-classification fishing (classify only the
  pre-declared split vs the pre-registered memo-02 classes).

## SKETCH-3 · CAL1 turn-of-month execution timing

- **Rule:** day-of-month buckets from the IDX calendar (last 2 sessions + first 3 sessions of the
  month vs the rest). Two arms: (a) book open→close on ToM days vs other days (differences in the
  *capturable* leg); (b) the X1-overlay question on ToM days: buy-at-open vs buy-at-close cost.
  Outcome = valid-open LW book (same restriction as X1).
- **PIT:** trivially calendar. **Split:** confirmation 2021-07→2026-07 primary; discovery 2010-05
  →2021-06 replication.
- **Power:** N_ToM ≈ 250 confirmation days / 500 discovery (brief split) → MDE ≈ 60–100bp/day at
  the bar — the ToM effect in the literature is ~5–15bp/day. **Honest verdict: underpowered at
  the bar; run only as an observability lens, not as a family test.** (If the Owner wants it
  anyway, pool confirmation+discovery and predeclare it as ONE arm, N≈2,400, MDE ≈ 21bp.)
- **Kill rule:** |t| < bar ⇒ null; no bucket tuning.

## SKETCH-4 · C3 52-week high (George–Hwang)

- **Rule:** NEAR52 = close / 52-week high (trailing 250 sessions, PIT). Arms: (a) monthly-ish
  low-turnover tilt: bottom-quintile NEAR52 exclusion tilt vs the LW book (avoidance side,
  long-only); (b) decile-spread observability (long low-NEAR52 vs high-NEAR52, per-date excess).
  ONE horizon (formation monthly), turnover ≤ 0.25/mo per D-065 §5.
- **Gate:** **NOT RUN before FADE-001's first maturity (~2026-10-19)** — D-062 standing
  directive (52w-high is {T1}-correlated). Sketch now, freeze+run only after the read and R2.
- **Power:** cross-section ≈ 3,300 valid-open days → tilt-vs-book MDE ≈ 15–25bp/day per 1σ
  NEAR52-rank unit; the published effect is economically small but broad — plausible power.
- **Kill rule:** tilt |t| < bar ⇒ null; era-concentration rule as X1.

## SKETCH-5 · IX1 forward recorder (not a screen)

FTSE Russell notices API (no auth) → nightly pull of `ASEAN`/`GEISAC`-tagged review notices with
AnnouncedDate/EffectiveDate → an append-only recorder table (proposed, Owner to site it) with
per-name announced/effective dates. No family slot, no hypothesis; it starts the PIT clock for an
index-addition effect that cannot be judged for ≥48 months. MSCI excluded (registration-gated).

## Explicitly not sketched (underpowered or blocked — W1/W2)

CAL2 (pre-holiday, N≈250 → MDE ≥ 40–50bp, underpowered alone), BI1 (no free surprise proxy,
N≈65), N1 (Wikipedia breadth unproven for IDX small caps; Trends ToS-blocked), LC2 (lock-up dates
blocked), X2 (coal/CPO — the IDX-relevant legs — have no free source; gold/oil subset kept as a
W1 note, sketched only if the Owner wants a partial-coverage family).
