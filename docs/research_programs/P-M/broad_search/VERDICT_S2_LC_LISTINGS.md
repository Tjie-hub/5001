# VERDICT — SCREEN-PM-LC-001 (`{LC}` young-listing avoidance) · **PASS (screen level) — STOP RULE ENGAGED**

**Run:** one shot, 2026-09-29 (`RESULT_S2_*.json`; run_id recorded in
`research.db::research_runs`, kind `broad_search_screen_s2_lc_listings`, git `0029123`+
predeclaration `e282f313…`). Panel: snapshot `walkforward-20260928-213012` (sha `10f9c97f…`),
2,500,859 rows through 2026-09-16; FORU excluded from 2026-09-14 (8 rows dropped).
Listings: 441 tickers with first bar in [2015-01-01, cutoff] after the pre-declared
coverage-start exclusions (181 first bars on corpus start dates, 337 before 2015); 226 passed
the adv20 ≥ Rp 5bn flag-row gate (215 below-gate exclusions counted — the fingerprint lens).

## Primary cell (pre-declared): YOUNG · hold 252 · confirmation half · corrected · gross

- **−2.448 %/mo, t = −3.66, 62 valid months.** All four frozen PASS conditions met:
  1. ≥ 48 valid months ✓ (62);
  2. two-sided |t| ≥ 2.857 (recomputed full-census bar at N = 266) ✓ (3.66);
  3. point estimate negative ✓;
  4. discovery-as-replication half same sign (87 valid months ≥ 12 ⇒ gate applies):
     YOUNG · h252 · pre2021 = **−1.256 %/mo, t −1.29 — negative** ✓.
- **⇒ SCREEN PASS. Per the frozen stop rule (brief rule 11): no variants, no refinement, no
  further looks at any window of this data. The verdict is handed to the Owner.**

## Corroboration inside the frozen grid (all reported, none tuned)

| arm | events | valid mo | mean %/mo | t |
|---|---|---|---|---|
| YOUNG · h126 · pre2021 | 63 | 73 | −0.066 | −0.06 |
| YOUNG · h126 · post2021 | 142 | 61 | **−3.833** | **−3.92** |
| YOUNG · h252 · pre2021 (discovery) | 63 | 87 | −1.256 | −1.29 |
| **YOUNG · h252 · post2021 (PRIMARY)** | 142 | 62 | **−2.448** | **−3.66** |

- **Second benchmark (frozen, observability only):** vs IHSG over the same 62 months:
  **−2.435 %/mo, t −3.21** — independently clears the bar.
- **Per-date headline (brief rule 7):** mean daily excess on position-days **−0.122 %/day**
  (34.4–48.1% of months positive across cells — broad-based, not a two-month spike; the 2021-08
  sleeve month was −14.3% but the monthly series is in the RESULT).
- **Placebo (triggered by the pass, D-061 precedent):** same-count random-date flags on the same
  panel: t = **−0.41** ⇒ the listing dates carry the information, the machinery does not.
- Checks: FILL-1 PASS (141/141), ID-1 PASS (share 1.6e-4).
- **{V}-overlap cells (frozen mitigation):** realized-vol-conditioned splits of YOUNG · h252 —
  high-vol band −1.24 %/mo (t −1.83), low-vol band −1.35 %/mo (t −1.73): the effect is **flat
  across volatility bands**, i.e. not a re-derivation of the volatility exclusion.
  **Disclosed execution deviation:** these two descriptive cells ran on the pooled window
  instead of the confirmation half (the flag frame was not entry-split before conditioning).
  They gate nothing; the pooled result is reported as-run and not re-run, because the primary
  passed and the stop rule forbids further looks. Net observability: mirror-overlay net
  +0.15 %/mo at the 0.60% RT — the D-057 avoidance-family scale of economics.

## What this is — and is not

- **It is a screen PASS**: a pre-declared, census-priced look whose primary cleared the
  recomputed full-census bar with the pre-declared sign, in both halves, on both benchmarks,
  with a null placebo and a mechanism-consistent fingerprint. Survivorship direction is
  conservative for an avoid-side arm (54/929 names delisted-covered; the worst IPOs are missing,
  biasing against the effect).
- **It is not a registration, a family slot, or a strategy.** Family `{LC}` is unopened; slots,
  Rule Cards and any forward test are Owner decisions. The D-062 standing directive applies to
  any next step: **the proposed family is NOT correlated with FADE-001 (breakdowns), REGIME-002
  (trend onset) or VOLEX-001 (volatility exclusion)** — the event is a listing date, the effect
  is flat across vol bands, and the vol-conditioned cells exist precisely to make that claim
  checkable. The proposed DECISION_LOG text (handoff) asks the Owner to decide: open `{LC}` and
  draft the Rule Card (RC-0003), or shelve.

**Arms added to the census by this screen: 6** (see CENSUS_UPDATE.md).
