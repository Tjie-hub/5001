# WP-D · Coverage Report

**As of:** 2026-07-17 · **Dataset:** `reconstitution_events.csv` · **Consistency audit:** **PASS** (0 collisions, all provenance present, 0 rows outside the OHLCV window, `announcement < effective` on every row).

## 1. Headline coverage

| Metric | Value |
|---|---|
| Reviews covered | **9** |
| Window | **2023-02-01 → 2026-02-02** (~3.0 years) |
| Total ticker-events | **154** (77 ADD / 77 DELETE) |
| Distinct `(ticker, effective_date, direction)` economic events | **143** |
| Reviews cross-corroborated (`SECONDARY_CROSSCHECKED`) | 5 of 9 |
| Reviews single-source (`SECONDARY_SINGLE`) | 4 of 9 |
| Primary-verified events | **0** (IDX PDFs 403-blocked) |

### Events by index

| Index | ADD | DELETE | Total |
|---|---|---|---|
| LQ45 | 26 | 26 | 52 |
| IDX30 | 18 | 18 | 36 |
| IDX80 | 33 | 33 | 66 |

## 2. Review-by-review coverage grid

Expected reviews are derived from the cadence rule ([[SOURCE_REGISTRY]]): semiannual (Feb/Aug) before Apr 2024, quarterly (Feb/May/Aug/Nov) after. Window = the `ohlcv` history start (2021-07-05) → present.

| Review (effective) | Cadence | Status | Note |
|---|---|---|---|
| 2021-H2 (Aug 2021) | semiannual | ❌ **MISSING** | earliest usable review; not retrieved |
| 2022-H1 (Feb 2022) | semiannual | ❌ **MISSING** | candidate sources found, none clean per-index |
| 2022-H2 (Aug 2022) | semiannual | ❌ **MISSING** | candidate sources found, none clean per-index |
| 2023-H1 (Feb 2023) | semiannual | ⚠️ **PARTIAL** | LQ45 + IDX30 only — **IDX80 not covered by source** |
| 2023-H2 (Aug 2023) | semiannual | ✅ covered | effective day month-precision |
| 2024-H1 (Feb 2024) | semiannual | ✅ covered | last semiannual review |
| 2024-Q2 (May 2024) | quarterly | ❌ **MISSING** | first quarterly minor-eval; not retrieved |
| 2024-Q3 (Aug 2024) | quarterly | ✅ covered | IDX30 no constituent change |
| 2024-Q4 (Nov 2024) | quarterly | ✅ covered | |
| 2025-Q1 (Feb 2025) | quarterly | ✅ covered | |
| 2025-Q2 (May 2025) | quarterly | ❌ **MISSING** | minor-eval; not retrieved |
| 2025-Q3 (Aug 2025) | quarterly | ✅ covered | |
| 2025-Q4 (Nov 2025) | quarterly | ✅ covered | effective day month-precision |
| 2026-Q1 (Feb 2026) | quarterly | ✅ covered | |
| 2026-Q2 (May 2026) | quarterly | ❌ **MISSING** | primary doc known (Peng-00067, 24 Apr 2026) but 403 |

**Coverage:** 9 of ~15 expected reviews (≈60%). The **recent quarterly window (2024-Q3 → 2026-Q1) is complete except 2025-Q2 (May 2025)** — 6 of 7 reviews, fully cross-corroborated in the last year.

## 3. Confidence

| Segment | Confidence | Why |
|---|---|---|
| 2024-Q3 → 2026-Q1 | **High** | 5 of 6 cross-corroborated; clean per-index sources |
| 2023-H1 → 2024-H1 | **Medium** | single-source (bisnis of record), not yet cross-checked; IDX80 gap in 2023-H1 |
| Pre-2023 & May-evals | **Absent** | not retrieved |
| All segments vs primary | **Secondary-only** | no IDX official confirmation yet (403) |

## 4. Gap analysis (explicit — no imputation)

| ID | Gap | Impact | Path to close |
|---|---|---|---|
| **G-WPD-1** | 2021-H2, 2022-H1, 2022-H2 (three semiannual reviews) not retrieved | Shrinks history from ~5 yr to ~3 yr; removes the 2022 bear regime from the sample | Targeted retrieval of clean per-index sources for these dates + verification |
| **G-WPD-2** | May minor-evals 2024-Q2, 2025-Q2, 2026-Q2 not retrieved | Undercounts events; May evals may be small/empty but must be **verified**, not assumed | Retrieve + verify (record "no change" explicitly if confirmed) |
| **G-WPD-3** | IDX80 constituents for 2023-H1 not covered by its source | Missing IDX80 events for one review | Find an IDX80-inclusive source for Feb 2023 |
| **G-WPD-4** | Zero `PRIMARY_VERIFIED` — all events secondary | Quality ceiling; secondary transcription risk | Retrieve IDX official PDFs (currently 403); upgrade rows |
| **G-WPD-5** | `effective_date` month-precision for 2023-H2 and 2025-Q4 | Event-window alignment needs exact day | Confirm exact first-trading-day from primary or `ohlcv` |

> **No gap has been filled by estimation.** A missing review means *not found in a retrieved source*, not *no change occurred*. Filling G-WPD-1…G-WPD-3 requires additional retrieval, which is a bounded continuation of this same work package.
