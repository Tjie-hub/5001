# WP-D · Readiness Assessment

**Question (per the WP-D brief):** Does WP-D now provide sufficient information to (a) count event sample size N, (b) estimate event variance σ, (c) compute MDE, (d) perform a ≥80% power analysis, and (e) finalize [[HYP-PA-0001_DRAFT|HYP-PA-0001]] registration? **No power analysis is computed here — this states only whether the required inputs are now available.**

## Input-availability verdict

| Input | Available now? | Basis |
|---|---|---|
| **(a) Count N** | ✅ **Yes, for the covered window** | 210 ticker-events (105 ADD / 105 DELETE); 192 distinct economic events; **13 review-date clusters**; window 2022-08 → 2026-05; sub-counts in [[COVERAGE_REPORT]]. Directly countable from `reconstitution_events.csv`. |
| **(b) Estimate σ** | ✅ **Inputs available** (not computed) | σ = event-window abnormal-return dispersion. Requires joining each `effective_date` to `ohlcv` (present, 2021-07→now, split-adjusted) and computing market-model abnormal returns on a pre-event estimation window. All inputs exist; computation is the experiment's, not WP-D's. |
| **(c) Compute MDE** | ✅ **Inputs available** (not computed) | MDE = (z₁₋α/₂ + z_power)·σ/√N is deterministic once N and σ are fixed. Both inputs now obtainable. |
| **(d) ≥80% power analysis** | ✅ **Inputs available** (not computed) | Follows directly from N and σ. Per instruction, **not run here.** |
| **(e) Finalize registration** | ⚠️ **Data precondition substantially met; two non-data items remain** | See below. |

## On (e) — what still stands between WP-D and registration

WP-D's job was the **data** precondition to G1 for HYP-PA-0001. For the covered window that precondition is **met**: N is countable and σ is computable. Registration additionally requires two things WP-D does not and should not supply:

1. **A CRO ex-ante decision (R5).** The reversal window `k`, the registered `MDE`, and the DSR bar must be fixed *before* any test. WP-D provides the N and σ that make a *defensible* MDE computable, but fixing it is the owner's ex-ante act ([[HYP-PA-0001_DRAFT]] §5, step 3).
2. **A coverage-sufficiency judgment.** The verified window is **~3.75 years / 210 events / 13 clusters (2022-08 → 2026-05)**, not the full ~5 years. This is enough to *compute* N/σ/MDE/power, but whether it is enough to *register on* — versus first closing the two residual review gaps (2021-H2, 2022-H1) for more clusters — is a CRO call. **Current owner status: HOLD** ([[HYP-PA-0001_POWER]] §4a).

## Remaining blockers (carried from [[COVERAGE_REPORT]] §4)

| Blocker | Blocks full-5yr readiness? | Blocks registration on covered window? |
|---|---|---|
| G-WPD-1 — 2021-2022 reviews not retrieved | **Yes** | No (event study can run on 2023-2026) |
| G-WPD-2 — May minor-evals not retrieved | Partially (undercounts N) | No |
| G-WPD-3 — IDX80 2023-H1 gap | Minor | No |
| G-WPD-4 — no primary verification (IDX 403) | Quality ceiling, not a count blocker | No — but raises transcription-risk; PRIMARY upgrade recommended before capital-relevant claims |
| G-WPD-5 — month-precision effective dates (2 reviews) | No | Resolve at experiment time from `ohlcv` |

## Bottom line

> **The required inputs to compute N, σ, MDE, and a ≥80% power analysis are available for the window 2022-08-01 → 2026-05-04 (210 events, 13 clusters).** The power analysis has been run ([[HYP-PA-0001_POWER]]): pooled MDE ≈1.2%/event but cluster-limited to ~5% — **HYP-PA-0001 is owner-HELD pending more clusters.** Full 5-year coverage is not reached; only **2021-H2 and 2022-H1** remain (documented gaps, closable only by further retrieval — **not** imputation). Primary (IDX) verification remains **0** (Cloudflare-blocked, §5); a manual download step is required before any capital-relevant use.
>
> **Recommendation (decision reserved to CRO):** proceed to compute N/σ and a power analysis on the covered window to see whether it clears ≥80% at a plausible MDE. If it does, register HYP-PA-0001 scoped to 2023-2026 with the gap explicitly declared. If more power or regime diversity is needed, authorize a bounded continuation pass to close G-WPD-1…G-WPD-3 first. **No registration, power computation, or inference is performed in WP-D.**
