# WP-D · Coverage Report

**As of:** 2026-07-17 (updated — parallel-execution Track A pass) · **Dataset:** `reconstitution_events.csv` · **Consistency audit:** **PASS** (0 collisions, all provenance present, 0 rows outside the OHLCV window, `announcement < effective` on every row).

## 1. Headline coverage

| Metric | Value (this pass) | Prior pass |
|---|---|---|
| Reviews covered | **11** | 9 |
| Window | **2022-08-01 → 2026-05-04** (~3.75 yr) | 2023-02 → 2026-02 |
| Total ticker-events | **188** (94 ADD / 94 DELETE) | 154 |
| Distinct `(ticker, effective_date, direction)` events | **172** | 143 |
| Cross-corroborated reviews | 6 of 11 | 5 of 9 |
| Primary-verified events | **0** (idx.co.id Cloudflare-blocked — §5) | 0 |

### Events by index

| Index | ADD | DELETE | Total |
|---|---|---|---|
| LQ45 | 34 | 34 | 68 |
| IDX30 | 22 | 22 | 44 |
| IDX80 | 38 | 38 | 76 |

## 2. Review-by-review coverage grid

Cadence rule ([[SOURCE_REGISTRY]]): semiannual (Feb/Aug) before Apr 2024, quarterly (Feb/May/Aug/Nov) after. Window = OHLCV start (2021-07-05) → present.

| Review (effective) | Cadence | Status | Note |
|---|---|---|---|
| 2021-H2 (Aug 2021) | semiannual | ❌ **MISSING** | earliest usable review; not retrieved |
| 2022-H1 (Feb 2022) | semiannual | ❌ **MISSING** | only commentary sources found — no clean per-index list |
| 2022-H2 (Aug 2022) | semiannual | ⚠️ **PARTIAL** ✅*new* | LQ45 + IDX30 verified; **IDX80 not covered by source** |
| 2023-H1 (Feb 2023) | semiannual | ⚠️ **PARTIAL** | LQ45 + IDX30; **IDX80 not covered** |
| 2023-H2 (Aug 2023) | semiannual | ✅ covered | effective day month-precision |
| 2024-H1 (Feb 2024) | semiannual | ✅ covered | last semiannual review |
| 2024-Q2 (May 2024) | quarterly | ❌ **MISSING** | first quarterly minor-eval; not retrieved |
| 2024-Q3 (Aug 2024) | quarterly | ✅ covered | IDX30 no constituent change |
| 2024-Q4 (Nov 2024) | quarterly | ✅ covered | |
| 2025-Q1 (Feb 2025) | quarterly | ✅ covered | |
| 2025-Q2 (May 2025) | quarterly | ❌ **MISSING** | no clean per-index source surfaced |
| 2025-Q3 (Aug 2025) | quarterly | ✅ covered | |
| 2025-Q4 (Nov 2025) | quarterly | ✅ covered | effective day month-precision |
| 2026-Q1 (Feb 2026) | quarterly | ✅ covered | |
| 2026-Q2 (May 2026) | quarterly | ✅ covered ✅*new* | first eval under new HSC/free-float criteria |

**Coverage:** 11 of ~15 expected reviews (~73%), 2 of them partial (IDX80 gaps). The window now spans the **2022 bear regime through 2026**, adding regime diversity vs the prior pass.

## 3. Confidence

| Segment | Confidence | Why |
|---|---|---|
| 2024-Q3 → 2026-Q2 | **High** | mostly cross-corroborated; clean per-index sources |
| 2022-H2 → 2024-H1 | **Medium** | single-source; IDX80 gaps in 2022-H2 & 2023-H1 |
| Pre-2022-H2, May-2024, May-2025 | **Absent** | not retrieved |
| All segments vs primary | **Secondary-only** | idx.co.id automated access blocked (§5) |

## 4. Gap analysis (explicit — no imputation)

| ID | Gap | Status this pass | Path to close |
|---|---|---|---|
| **G-WPD-1** | Early history 2021-H2, 2022-H1, 2022-H2 | **Partially closed** — 2022-H2 added; **2021-H2 & 2022-H1 remain** | 2022-H1: only commentary sources found (inconsistent counts) — needs a clean per-index source. 2021-H2: not yet located |
| **G-WPD-2** | May minor-evals 2024-Q2, 2025-Q2, 2026-Q2 | **Partially closed** — 2026-Q2 added; **2024-Q2 & 2025-Q2 remain** | Retrieve + verify; record "no change" explicitly if confirmed |
| **G-WPD-3** | IDX80 constituents for **2023-H1 and 2022-H2** | Open | Find an IDX80-inclusive source for both |
| **G-WPD-4** | 0 `PRIMARY_VERIFIED` — all events secondary | **Attempted, blocked** — see §5 | Manual/human download of IDX PDFs past Cloudflare |
| **G-WPD-5** | month-precision effective dates (2023-H2, 2025-Q4) | Open | Confirm exact first-trading-day from primary or `ohlcv` |

## 5. Retrieval status & primary-verification progress

**Secondary retrieval (this pass):** added 2022-H2 (kompas.com) and 2026-Q2 (bisnis.com), both verify-fetched first-hand. Method: targeted search → fetch of dedicated per-index "daftar lengkap / keluar-masuk" articles; recorded only what the article states.

**Primary retrieval attempt (idx.co.id):**
- **Method 1 — WebFetch** of the official announcement PDF (`Peng-00067/BEI.POP/04-2026`) → **HTTP 403**.
- **Method 2 — headless browser (Playwright)** of the same PDF URL → **HTTP 403, "Attention Required! | Cloudflare"**.
- **Method 3 — headless browser** of the HTML announcements listing (`/en/news/announcement/`) → **HTTP 403, Cloudflare**.
- **Conclusion:** idx.co.id enforces domain-wide Cloudflare bot protection; **automated primary retrieval is not possible in this environment.** Upgrading any event to `PRIMARY_VERIFIED` requires a **manual/human step** — a person opening the IDX announcement in a normal browser and saving the PDF (e.g. via the `! ` in-session command, or an owner-supplied download).

> **Remaining uncertainty from secondary-only sourcing:** transcription and reporting risk. It is mitigated by (a) using bisnis/kompas "daftar lengkap" articles that reproduce the official per-index lists, and (b) cross-corroboration on 6 of 11 reviews. It is **not eliminated**; before any capital-relevant claim, primary verification should be obtained.

## 6. Impact on statistical power (qualitative — no power computed)

Per instruction, no power analysis is run. Qualitatively, this pass **improves** the inputs: N rose 154 → 188 events (172 distinct), and the window now includes the 2022 bear regime, improving regime diversity for a regime-aware event study. The residual gaps (2021-H2, 2022-H1, two May evals) would add further events and earlier-regime coverage; their absence **caps achievable N and early-regime power** but does not prevent an event study on the covered 2022-2026 window. Whether the current N suffices at a plausible MDE is the (deferred) power analysis, reserved to the CRO.
