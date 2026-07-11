# NR7 Edge-Generalization Study — Re-run on Split-Adjusted Corpus (2026-07-11)

**This is a NEW dated study. It does NOT replace the manifest-pinned evidence**
`docs/superpowers/results/2026-07-07-nr7-generalization-study.md`, which remains
the frozen approval artifact for `NR7_BULL v1`. This re-run re-verifies that
evidence against the Phase-A recomputed dataset (audit findings R-1/R-4).

---

## Provenance & reproducibility

| Field | Value |
|---|---|
| Study run_id | `f4f611f733474c279bd1a437b1da9a01` (`research_runs`, kind `nr7-generalization-study`, status DONE, 118.0 s) |
| Producing recompute run_ids | wf-refresh `cac9176966df4c178f6aedd9a82e85ce`; backtest-cache `ac1e8f9b8d92417a8c78b1b0aa013dd5` |
| Dataset fingerprint | `0d0175095fe72a32982eb9935b5bddecc1bf4d328f18fdf78112d32c96342f11` (identical to the recompute run — same corpus) |
| Git commit | `92936412175484b66f7cc27cb096146665253494` (`9293641`, branch `ops/hardening-2026-07-10`) |
| Config hash (`strategy_nr7_breakout` source, sha256) | `8845c57b918a67ed513e67357d89f5f60388ce61105c20d8d496e303eab87a08` — **matches `NR7_BULL_v1.yaml`; no code drift** |
| Corpus as-of | 2026-07-10 (settled `is_final=1`) |
| Corpus statistics | 1,044,387 settled rows; max_date 2026-07-10; corporate_actions applied via gap-verified layer → **0 factors apply** (adjusted == raw on this corpus) |
| Liquid universe | 187 tickers (ADV ≥ `VALUE_LIQ_MIN_IDR` at as-of 2026-07-10) |

**Reproduction:** `research/studies/nr7_generalization_study.py` reads via
`load_ohlcv_df` (settled + gap-verified split-adjusted). The re-run used a
harness that overrides the module's `RESULTS` path so the pinned file is never
touched, and wraps execution in `research.tracking.track_run` (hence the study
run_id above). Deterministic pipeline (no RNG) — identical inputs reproduce these
numbers exactly.

---

## Methodology (unchanged from the pinned study)

- **Universe:** liquid names only (30-day average traded value ≥ liquidity floor),
  re-selected at the current as-of date.
- **Signal:** `strategy_nr7_breakout` (narrowest-range-in-7 breakout), frozen
  source (config hash above).
- **Walk-forward:** 12-month train / 3-month test, non-overlapping OOS windows,
  60-bar warmup tail prepended per window; trades entered before `test_start`
  dropped — trade set mirrors what `wf_edge` sees.
- **Costs:** full round-trip re-derived from raw prices by `research.nr7_study`
  (single cost authority: 0.15% buy / 0.25% sell commission + 0.10% slippage/leg).
- **Regime label:** `detect_regime` on trailing ≤250 bars at entry (no look-ahead).
- **Tests / pre-registered bars:**
  - **T1** universe-pooled: PASS if exp ≥ +0.50% **and** N ≥ 300.
  - **T2** chronological CV (median-date split): PASS if late-window exp ≥ +0.50%,
    late N ≥ 150, retention ≥ 0.50.
  - **T3** regime strata: per-regime PASS if exp ≥ +0.50% **and** N ≥ 100.

---

## Results (OOS, net of round-trip costs)

### T1 — universe pooled
- exp **−0.085%/trade** | N **1108** | win 38.7% | **FAIL** (bar ≥ +0.50%, N ≥ 300)

### T2 — selection / chronological CV (boundary 2024-12-11)
- early-selected tickers: late exp **+1.674%** | late N **128** | early exp +2.610%
  | retention **0.64** | **FAIL** (late N 128 < 150 floor)

### T3 — regime strata
| Regime | exp/trade | N | win | Result |
|---|---|---|---|---|
| SIDEWAYS | −0.905% | 619 | 31.2% | **FAIL** |
| BEAR | +0.432% | 156 | 36.5% | **FAIL** |
| BULL | **+1.197%** | **333** | **53.8%** | **PASS** |

### DECISION: **DO-NOT-WIDEN**

The only regime clearing the pre-registered bar is **BULL** — the exact slice
already promoted as `NR7_BULL v1`. Universe-wide (T1) and selection-CV (T2)
generalization both fail, as before.

---

## Do the conclusions differ from the previous study?

**No — the decision and the promoted edge are unchanged.**

| Metric | 2026-07-07 (pinned) | 2026-07-11 (adjusted) | Δ |
|---|---|---|---|
| Corpus as-of | 2026-07-07 | 2026-07-10 | +3 sessions |
| Liquid universe | 189 | 187 | −2 |
| CV boundary | 2024-12-23 | 2024-12-11 | earlier |
| T1 exp / N | −0.001% / 1129 | −0.085% / 1108 | still **FAIL** |
| T2 retention / late N | 0.62 / 129 | 0.64 / 128 | still **FAIL** |
| T3 SIDEWAYS | −0.821% (FAIL) | −0.905% (FAIL) | unchanged verdict |
| T3 BEAR | +0.653% / 158 (**PASS**) | +0.432% / 156 (**FAIL**) | **verdict flipped** |
| T3 BULL | +1.181% / 346 / 54.0% (**PASS**) | +1.197% / 333 / 53.8% (**PASS**) | unchanged, ~identical |
| **Decision** | **DO-NOT-WIDEN** | **DO-NOT-WIDEN** | **unchanged** |

**One material sub-change: BEAR flipped PASS → FAIL** (+0.653% → +0.432%, now
below the +0.50% bar).
- **Immaterial to the promotion:** `NR7_BULL v1` was approved for **BULL only**;
  BEAR was never promoted. The flip changes no live decision.
- **It reveals the 07-07 BEAR PASS was fragile:** it cleared the bar by only
  +0.15pp at N=158. A 3-session corpus extension and universe re-selection was
  enough to drop it below +0.50%. This is a robustness caveat, not a regression —
  and it argues *against* ever widening to BEAR on that thin margin.

**Why the numbers moved at all (they moved little):** the differences are driven
by (a) **+3 trading sessions** of new data (as-of 07-07 → 07-10), which shifts the
median CV boundary and adds/drops a few tail trades, and (b) **universe
re-selection** (189 → 187 liquid names at the new as-of). They are **not** driven
by split adjustment — the gap-verified layer applies **zero** factors to this
corpus, so adjusted prices equal raw prices. The flagship BULL edge is essentially
identical (+1.197% vs +1.181%; N 333 vs 346; win 53.8% vs 54.0%) — marginally
*stronger* on expectancy.

---

## Confidence notes

- **BULL edge is stable across the recompute:** same sign, same magnitude, same
  N-band, same PASS. Re-verification on the adjusted corpus did not weaken it.
- **Negative conclusions reproduce cleanly:** T1 fail, T2 fail, SIDEWAYS fail —
  all consistent with 07-07, mostly slightly more negative (conservative direction).
- **Split-contamination concern (audit R-1) is empirically retired for NR7:** the
  frozen NR7 universe overlaps zero split-gapped tickers, and the corpus carries no
  split gaps (see the Audit Correction — R-1 section of the Phase A report). The
  +1.18%/+1.20% BULL result was never split-contaminated.

## Limitations (carried forward, unchanged by this re-run)

- **One regime cycle:** ~5y of IDX data contains roughly one episode of each
  regime; BULL-conditional expectancy is estimated from clustered, overlapping
  conditions. The pre-registered forward-test timebox is the compensating control.
- **No uncertainty quantification:** expectancy carries no bootstrap CI / standard
  error; no multiple-testing correction across the 3 regime cells (audit R-6, OPEN).
- **Liquidity/fills:** flat 0.10% slippage with full fill at open; no
  volume-participation cap on thin IDX names (optimistic for illiquid tickers).
- **Selection sensitivity:** the T2 selection step and liquid-universe membership
  shift with as-of date; the BEAR flip demonstrates borderline cells are not robust
  to small corpus changes.

---

*Re-study performed 2026-07-11 on the Phase-A recomputed corpus. The manifest-pinned
2026-07-07 evidence was not modified (verified: file mtime unchanged). No production
behavior was altered.*
