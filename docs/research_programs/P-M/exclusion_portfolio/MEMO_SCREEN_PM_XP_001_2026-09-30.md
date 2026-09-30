# SCREEN-PM-XP-001 — long-only exclusion portfolio · RESULT MEMO · 2026-09-30

**Status:** screen run once, frozen spec (planner instruction 2026-09-30). Screen authority only —
no registration, no family slot, no forward test, no ledger writes. Script:
`run_screen.py` (this directory) · Output: `results.json` (this directory).

## Verdict line

**FAIL — combined variant (A∪B∪C) vs the PRIMARY benchmark (equal-weight same universe, no
exclusions), D-059 modeled cost: mean monthly excess −0.043%/mo, Newey-West t (lag 3) = −0.19
(bar: ≥ 2.8575 for PASS, ≥ 2.0 for SUGGESTIVE); positive-excess years 2/6 (bar: ≥ 2/3).**
The exclusion portfolio's gross tilt (+0.691%/mo, NW t +3.11) is fully consumed by cost at the
realized turnover of 0.86/month.

## The 4-variant × 2-benchmark table (D-059 modeled cost, net of cost, %/month)

| variant | vs EW universe (PRIMARY) | NW t | vs IHSG | NW t | turnover/mo |
|---|---|---|---|---|---|
| **A∪B∪C (combined)** | **−0.043** | **−0.18** | −0.842 | −1.88 | 0.858 |
| A only (young listing) | +0.201 | +1.98 | −0.598 | −1.56 | 0.158 |
| B only (VOLEX high-vol) | **+0.364** | **+3.41** | −0.435 | −1.13 | 0.188 |
| C only (failed breakdown) | −0.596 | −3.39 | −1.395 | −3.09 | 0.878 |

Gross (uncosted) excess, same order: combined +0.691 (t +3.11), A +0.172 (+1.73), B +0.364
(+3.42), C +0.224 (+1.42) vs PRIMARY; frozen-cost lens sits between gross and modeled in every
cell (full table in results.json). n = 54 months (2021-08 → 2026-06 entry months).

## Combined variant — by-year table (vs PRIMARY, %/month)

| year | months | gross | net (modeled) |
|---|---|---|---|
| 2021 | 5 | +0.000 | −0.479 |
| 2022 | 9 | +1.509 | **+0.846** |
| 2023 | 10 | +0.529 | −0.196 |
| 2024 | 12 | +0.485 | −0.115 |
| 2025 | 12 | +0.433 | −0.360 |
| 2026 | 6 | +1.236 | +0.018 |

**Era concentration ({LC}-screen style):** 97.9% of the positive cumulative net excess sits in
one calendar year (2022); the largest single month is +5.27% (2026-06-02 entry) — the combined
portfolio's entire case is one 2022 cohort plus one late month, not a broad-standing effect.
51.9% of months positive; max relative drawdown of the compounded net-excess curve −15.2%.

## What each rule contributed

- **B (VOLEX-001 high-vol) is the only leg that survives modeled cost alone**: +0.364%/mo
  (t +3.41) at 0.19 turnover, era concentration 0.291, max relative DD −2.0%. This is the
  low-volatility anomaly replication the program already knows — and **it already has its own
  forward test (FWD-PM-VOLEX-001)**; the screen adds no independent information for it beyond
  confirming the backtest magnitude (+0.394%/mo, t 3.74) translates to a monthly-rebalanced,
  next-open-filled book. Reported as descriptive only; the pre-declared verdict was on the
  combined variant and is not re-assigned post hoc.
- **C (failed breakdown) is the combined verdict's killer**: it excludes ~20 of 200 names every
  month (turnover 0.88 alone), its gross edge (+0.224%/mo, t +1.42) is smaller than the modeled
  cost of carrying that churn, and net of modeled cost the exclusion actively harms the book
  (−0.596%/mo, t −3.39). The FADE-001 anti-edge does not survive as a monthly-rebalance
  portfolio exclusion; its registered form (entry-suppression/exit overlay on another system)
  remains the only cost-sane application, exactly as its protocol §0 scoped.
- **A (young listing)** is marginal either way (+0.201%/mo net modeled, t +1.98) — below the
  screen bar, directionally consistent with SCREEN-PM-LC-001's young-name underperformance.

## Spec citations (frozen texts, implemented literally)

- Universe + B: `forward_exclusion/PROTOCOL.md` §2 (constants mirrored from its frozen
  `run_forward.py`, incl. the 95% session-completeness guard and ±20-session suspension pad).
- A: `broad_search/PREDECLARATION_S2_LC_LISTINGS.md` (YOUNG flag row = first own session with
  n_prior ≥ 25; onboarding-artifact exclusion; listing window [2015-01-01, 2026-09-16]; young
  state held for the primary hold of 252 own sessions).
- C: `forward_fade/PROTOCOL.md` §2 (gates mirrored verbatim from
  `scripts/fade_failed_breakdown.py`: adv20 ≥ Rp 1e9 shifted-1, close ≥ 50, n ≥ 25, volume > 0,
  nz20 ≥ 18 of trailing 20; lo20 = rolling-20 low shifted 1; signal = sweep below + close back
  above). "Within the trailing 20 sessions" = the 20 own sessions ending at the formation day,
  inclusive (ambiguity C-1 below).
- Costs: frozen 0.60% RT (0.30%/side on turnover) and the D-059 model (0.50% fees + ½
  Abdi-Ranaldo spread per side floored at one tick + 2σ_d·√(Q/adv20) at entry; Q = Rp 100m,
  D-059's primary size; primitives copied verbatim from `cost_liquidity/cost_by_adv.py`).
- Benchmarks: PRIMARY = EW same universe under the identical convention; IHSG open-to-open over
  the same session pairs.
- Verdict rule: planner instruction 2026-09-30 (PASS = NW t ≥ 2.8575 [D-064 bar] AND ≥ 2/3 of
  calendar years positive; SUGGESTIVE = 2.0 ≤ t < 2.8575; else FAIL), evaluated on the combined
  variant vs PRIMARY under modeled cost only.

## Provenance

- Panel: prepared outside the repo by the committed frozen pipeline
  `research.rulecard.data.load_extended_ohlcv(issuance=True)` (backfill `hist_pre2021.pkl` +
  corpus merge with split repair, plus the D-064 issuance holder-wealth correction), then the
  broad-search conventions: FORU rows ≥ 2026-09-14 dropped (D-063), panel cut 2026-09-16.
  Artifact `~/xp_panel/panel.csv.gz`, sha256 `4fbc79db527ca2aa…` (full hash in results.json;
  verified by the script against its sidecar), 2,468,921 rows × 958 tickers, data through
  **2026-07-29**. The fingerprinted broad-search snapshot (data through 2026-09-16) lives on
  the other machine and was not reachable from this box (limitation L-1).
- Universe/suspension reads: local `data/walkforward.db` strictly read-only (`mode=ro` URI).
- Run: WSL, Python 3.12.13 venv, 2026-09-30; `results.json` generated_utc in file.

## Ambiguities (met with the frozen literal text; none invented)

- **A-1:** the LC rule flags ONE row per listing; as a portfolio state it is read as "young for
  the screen's tested primary hold (252 own sessions from the flag row)". Names younger than the
  flag (own sessions < 25) are NOT excluded by the literal rule but can enter the VOLEX universe
  (its trailing-60 median has min_periods 20). Measured exposure: 18 name-months across 60
  formations (~0.3 per formation) — immaterial to the verdict.
- **C-1:** "within the trailing 20 sessions" = the 20 own sessions ending at the formation day
  inclusive (the formation day's signal is known at formation; FADE's own fill convention makes
  it actionable at exactly the rebalance fill).
- **B-1:** B's top-decile cut is re-ranked among each month's universe members, per VOLEX's own
  frozen `generate()`.

## Limitations

- **L-1:** local corpus ends 2026-07-29, so the screen covers ~1.5 fewer months than the
  2026-09-29 screens' window (their CUT 2026-09-16 is unreachable from this box).
- **L-2:** the D-064 issuance correction ran inside the panel prep; its event source is the
  corpus's issuance table — the same coverage limits recorded in D-064 apply here.
- **L-3:** the corpus is a current-roster backfill (no pre-discovery delistings) — for an
  AVOID-side portfolio this biases against the exclusions (conservative), same statement as
  every spec in this program.
- **L-4:** names missing an entry/exit open (suspension at the rebalance session) are dropped
  from that month's basket mean (VOLEX's own `basket()` convention); 45 cost sides fell back to
  the frozen per-side rate for missing D-059 liquidity inputs (counted in results.json).
- **L-5:** the final month's book is never liquidated in the cost accounting (identical across
  variants and benchmarks; no effect on excess).

## What the Owner would need to decide to open this as a family

1. **Nothing about B** — it already has FWD-PM-VOLEX-001; a second forward test of the same
   rule in portfolio form would be a duplicate spend of a family slot, and D-062 bars
   registration without an incremental-effect claim.
2. **A cost-aware redesign decision for C** — the evidence says the failed-breakdown exclusion
   is real gross but is destroyed by monthly churn; if the Owner wants it in portfolio form at
   all, the only defensible next step is a NEW pre-registration with a low-turnover mechanism
   (e.g., event-triggered suppression rather than monthly re-ranking), specified before any
   look at its results — that is a new spec, not an amendment of this screen.
3. **Whether a combined "avoidance book" mandate is worth a slot at all** — the combined
   verdict is FAIL at modeled cost, the effect is era-concentrated (97.9% of positive excess in
   2022), and the only surviving leg is already forward-tested. The honest reading is that this
   screen closes the "exclusion portfolio as a standalone product" idea at screen level, the
   same way S1/S2 closed their families.
