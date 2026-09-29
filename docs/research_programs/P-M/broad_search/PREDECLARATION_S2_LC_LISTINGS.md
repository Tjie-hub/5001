# PREDECLARATION — S2 `{LC}` young-listing avoidance screen (SCREEN-PM-LC-001)

**Status:** frozen before any outcome is computed · **Date:** 2026-09-29 ·
**Authority:** brief `ZCODE_BRIEF_BROAD_EDGE_SEARCH_2026-09-29.md` (screens only; no registration,
no family slot, no DECISION_LOG/registry edits). One run. Every cell of the pre-declared grid is
reported; the verdict is the pre-declared primary cell only. **This file and
`screen_s2_listings.py` are committed (with this file's sha256) before the run.**

## Rule (pre-declared)

Avoidance screen: do names within their first post-listing year underperform the equal-weight
liquid book? Single pre-declared event definition:

- **YOUNG:** for every ticker whose first panel bar (the listing-date proxy from the merged
  backfill + DB corpus) falls in [2015-01-01, 2026-09-16], flag the ticker's first own session
  with `n_prior ≥ 25` (the first row the engine can treat as eligible; entry follows at the next
  own session's open).

Defects dropped and counted: first bars exactly on a corpus-coverage start date (the backfill
start **or 2021-07-05, the DB corpus start**) are **onboarding artifacts of old names, not
listings** — excluded; tickers with no eligible row, rows below the adv gate; **FORU excluded
entirely from 2026-09-14 onward** (D-063). Listing-proxy limitation, accepted: yfinance
full-history makes the first bar ≈ the true listing for post-2000 listings; cohort shapes
2015–2020 (13/13/28/45/44/43) match known IDX IPO activity, the 2021 count (229) mixes ~90 real
IPOs with onboarding.

**Pre-run amendment (2026-09-29, before the frozen run — disclosed):** the vol-conditioned
descriptive cells below originally read "trailing `ret63`"; at the flag row (own session 26)
`ret63` is NaN by construction, so the frozen text is replaced by: trailing realized volatility =
std of daily returns over the name's own sessions since listing (expanding, min 10), above/below
the cross-sectional median of the flag date. No outcome data was read before this amendment.

## Universe (pre-declared)

Flag row must satisfy the engine's ex-ante liquid gate (`liquid_idx_v1`) **and** trailing adv20 at
the flag row ≥ **Rp 5bn** (brief rule 5). Benchmark = the engine's EW liquid book (adv20 ≥ Rp 1bn),
never IHSG (BM-1). Non-liquid young names are excluded and counted (fingerprint, not arm).

## PIT (pre-declared)

The first bar is known at its own close; the flag row (n_prior = 25) is ~5 weeks later; entry is
the next own session's open. No forward information can enter. No announcement fields exist to
mis-stamp.

## Price handling (brief rule 4)

Young listings span no issuance ex-dates by construction (the correction machinery of S1 is not
needed; a young name's OWN later rights issue can only fall inside the hold window if announced
post-listing — those events are corrected for with the same gap-verified wealth correction as S1,
using the event's own terms, so the hold window is never mechanically distorted).

## Estimand, benchmarks, horizons, split (pre-declared)

- Engine: `research/rulecard/events.py` (D-060) via `run_event_months` — same conventions as S1;
  monthly mean/SE of the valid months' `primary`; per-date mean daily excess reported beside it.
- **Benchmarks: EW liquid book (all cells) and IHSG (confirmation half only — no pre-2021 IHSG
  series in the corpus; declared)**, observability only (R4b).
- Horizons: **hold_sessions ∈ {126, 252}** own sessions (≈ lock-up horizon ≈ 6m; the Ritter
  3-year underperformance window truncated to the capturable first year).
- **Split (pre-declared by the brief): entries < 2021-07-05 = discovery-as-replication half;
  entries ≥ 2021-07-05 = confirmation half.**

## Grid (every cell run and reported; each cell = one arm; 6 arms)

- 1 def (YOUNG) × 2 holds (126, 252) × 2 halves = **4 primary-grid cells**, gross, corrected panel.
- **2 volatility-conditioned descriptive cells** (declared {V}-overlap mitigation, brief rule 10):
  YOUNG · hold 252 · confirmation half, restricted to flag rows whose trailing realized volatility
  since listing (see the pre-run amendment above) is above / below the cross-sectional median of
  their date. These report whether any young-listing effect survives *within* volatility bands;
  they gate nothing.
- Net-of-cost observability at 0.60% RT + D-059-modeled-cost qualitative reading via adv terciles
  ride inside the same arms. Engine checks FILL-1/ID-1 per cell. Placebo/random instrumentation
  only if the primary cell is read positive.

- **PRIMARY CELL: YOUNG · hold 252 · confirmation half (entries ≥ 2021-07-05) · gross.**
- Pre-declared sign: **negative** (young names underperform).

## Verdict rule (pre-declared)

- Primary cell readable only at ≥ **48 valid months** — otherwise **NOT TESTED — UNDERPOWERED**,
  no slot consumed (RC-0002 precedent).
- If readable: **screen PASS** requires two-sided |t| ≥ **2.86** (recomputed full-census bar:
  N = 252 + 14 arms = 266; E[max|Z|] = 2.857) AND the point estimate negative AND the
  discovery-as-replication half (YOUNG · hold 252 · pre-2021) carries the same sign if it has
  ≥ 12 valid months; below that, the maximum verdict is **EFFECT_CONFIRMATION_ONLY**. t < bar ⇒
  **screen FAIL (null)**; the `{LC}` young-listing lead closes at screen level.
- **Stop rule (brief rule 11):** a pass stops everything; no variants, no refinement.
- **Registration caveat (frozen):** even on a PASS, `{LC}` correlates with {V} (VOLEX-001 in
  flight) — the vol-conditioned cells decide whether any proposal to the Owner carries an
  incremental-effect claim; without one, the D-062 directive bars registration regardless.

## Survivorship statement (brief rule 8, before any long-side claim)

The corpus holds only names still listed in 2026-09 (54/929 `ohlcv_long` names end before 2026).
For an AVOID-side arm this biases against the effect (the worst IPOs delisted and are missing) —
conservative; stated here and on any future card.

## Power statement (before the run, from event counts alone — R5 honesty)

158 liquid young listings 2015+ (33–40 of them in each of 2021–2023). With the D-056 sleeve σ
range 4.6–6.5%/mo, the MDE at the bar is ≈ 1.6–2.0%/mo on ~120–145 valid months (hold 252 fills
months densely). The US-calibrated haircut effect (≈ −2…−4%/yr over 3 years ⇒ ≈ −0.1%/mo × 0.5) is
far below the MDE; the IDX 2021-cohort collapse is folk-magnitude but unverified. Same rationale
and same honesty as S1: expected verdict on a true US-sized effect is NULL; the screen is a cheap,
census-priced look whose null closes the family.

## Falsification note

Rank-2 family: strongest event density after S1, cleanest PIT, one declared correlation ({V}). A
null closes listing-lifecycle avoidance for this program.
