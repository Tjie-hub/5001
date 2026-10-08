# REGISTRATION DRAFT — HYP-PM-0019, market-stress reversal S1 (G0-frozen; DO NOT FILE)

> Draft only. This branch does not edit `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md` or
> `DECISION_LOG.md`. Filed by the owner at G0 approval, under the next free D-number
> (expected **D-077**; D-076 is reserved by HYP-PM-0017's draft). The family-widening amendment
> below is part of the filing.

## Proposed registry row

| field | value |
|---|---|
| id | HYP-PM-0019 |
| family | Price-Reversal **widened {R1, R2} → {R1, R2, R3}** at this registration (formal amendment, D-028, PG-3/PG-6); R3 = market-stress liquidity provision; closest relative HYP-PM-0014 |
| statement | On a market-wide stress day (EW liquid return ≤ −2.5× its trailing-250σ), selling is balance-sheet-driven rather than informative; liquidity supplied at the close of t earns a premium: the bottom-quintile basket of the day's liquid names outperforms over 5 sessions, beta-adjusted and net of the D-059 cost |
| arms | S1 (exactly one; S2/horizons/later-in-episode days are report-only) |
| panels | E1 history_long (2007-01..2021-06-30), E2 walkforward (2021-07→); E1/E2 flag agreement gated ≤ 20% at G0 |
| primary statistic | pooled mean R over episodes, t = mean/sd·√n (episodes independent) |
| bar | **3.2954 at N = 604** (expected; `bar_v2.e_max_abs_z`), 3.2959 at N = 605 if HYP-PM-0018 registers first; N re-verified at submission and at G1 |
| halves | E1 2007-01..2020-12 and E2 2021-07→ means both > 0; 2021-01..06 events pooled but in neither half |
| data | walkforward snapshot `a2d7e675…` + history_long snapshot `7d298068…` (2026-10-08, `CENSUS_G0.json`) |
| G0 | branch `research/market-stress-reversal-2026-10`, PREDECLARATION.sha256 sidecar, counts-only census + E1/E2 agreement + 15:49 pre-close check |
| falsification | D-075: mean ≤ 0 / below bar / half sign-flip / positive only at close-t entry / explained by the Parkinson-matched control |

## Proposed family amendment (filed with the registration)

> **Amendment (D-028, PG-3/PG-6):** the Price-Reversal family widens from **{R1, R2}** to
> **{R1, R2, R3}**, where R3 = market-stress liquidity provision (D-075). The feature space
> remains a price reversal conditioned on market stress; HYP-PM-0014 (big-4 bank 2-ATR climax
> low) is R1/R2's surviving member and is carried as an explicit control (ex-big-4-banks), not
> a third slot. The widening is disclosed at the G0 registration, before any outcome is read;
> the family count grows by the one arm this registration adds.

## Proposed D-entry text (draft)

### D-077 (expected) · HYP-PM-0019 (market-stress reversal) registered in {R3}, G0 frozen

**Status:** (to be RECORDED at owner approval) · **Type:** Registration + G0 freeze + family
amendment · **Approval authority:** owner approval of the 2026-10-08 G0 (this branch), after
HYP-PM-0017's registration (D-075 ordering).

- **Why admitted.** D-075 accepts market-stress reversal as liquidity provision to forced
  sellers (D-070 §1); this is the direct test the D-entry admits.
- **Study (frozen).** PREDECLARATION.md (this branch, sha256 sidecar): events = first days of
  −2.5σ EW-liquid stress episodes (≥ 30 liquid names; σ over 250 defined r_m, ≥ 120); S1 =
  bottom-quintile basket, close t → close t+5, β per member (250-day OLS on r_m), net of the
  D-059 cost at the true-rupiah ADV; total-return legs by dividend add-back (vendor-basis-
  consistent, verified); pass = strength (t ≥ frozen bar) + both halves + next-day entry > 0 +
  Parkinson-60-decile control > 0; ex-big-4 and ex-ex-date controls reported.
- **Freeze.** G0 = this branch's PREDECLARATION + drivers + 9 PIT tests + `CENSUS_G0.json`
  (counts only: episodes/events per year and half, basket sizes, ARB exclusions, the E1/E2
  agreement rate, the 15:49 pre-close agreement, provenance and power; no return after any
  stress day's close was computed, printed or stored).
- **Provenance disclosed at G0** (D-075 requirements): history_long built by
  `atr_plan/build_long_db.py` (yfinance-derived, split-adjusted, `adj_close` ≡ `close`); CA
  coverage starts 2009 (2007–08 events price-only, counted); split-corrected ADV convention;
  54/929 tickers stale pre-2026 (delisted names present); the panel's earlier VOLEX
  out-of-sample use asked a different question.
- **G1.** One run, `STRESS_G1_APPROVED=1`, both snapshots re-hashed pre-outcome; RESULT /
  VERDICT / HANDOFF, then STOP. Null is the honest prior (D-075).
- **Forward test.** Only if S1 passes: every new first-day stress episode after the G1 date,
  recorded at t and t+5 (~3–6 episodes/year; a verdict takes years).
