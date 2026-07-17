# WP-D · Coverage Report

**As of:** 2026-07-17 (updated — parallel-execution Track A pass) · **Dataset:** `reconstitution_events.csv` · **Consistency audit:** **PASS** (0 collisions, all provenance present, 0 rows outside the OHLCV window, `announcement < effective` on every row).

## 1. Headline coverage

| Metric | Value (this pass) | Prior pass |
|---|---|---|
| Reviews covered (**= P-A clusters**) | **12** | 11 |
| Window | **2022-08-01 → 2026-05-04** (~3.75 yr) | 2022-08 → 2026-05 |
| Total ticker-events | **194** (97 ADD / 97 DELETE) | 188 |
| Distinct `(ticker, effective_date, direction)` events | **178** | 172 |
| Cross-corroborated reviews | 6 of 12 | 6 of 11 |
| Primary-verified events | **0** (idx.co.id Cloudflare-blocked — §5) | 0 |

### Events by index

| Index | ADD | DELETE | Total |
|---|---|---|---|
| LQ45 | 34 | 34 | 68 |
| IDX30 | 23 | 23 | 46 |
| IDX80 | 40 | 40 | 80 |

*New this pass:* 2025-Q2 (May 2025) added — IDX30 (BBTN/ARTO), IDX80 (BUKA,DSNG/BMTR,MIDI); **LQ45 verified NO CHANGE** (recorded as a fact, distinct from "not retrieved").

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
| 2025-Q2 (May 2025) | quarterly | ✅ covered ✅*new* | kompas; **LQ45 verified no-change**, IDX30/IDX80 changed |
| 2025-Q3 (Aug 2025) | quarterly | ✅ covered | |
| 2025-Q4 (Nov 2025) | quarterly | ✅ covered | effective day month-precision |
| 2026-Q1 (Feb 2026) | quarterly | ✅ covered | |
| 2026-Q2 (May 2026) | quarterly | ✅ covered ✅*new* | first eval under new HSC/free-float criteria |

**Coverage:** 12 of ~15 expected reviews (~80%), 2 of them partial (IDX80 gaps). The window spans the **2022 bear regime through 2026**. Crucially for P-A power, **12 review-date clusters** are now covered (up from 11).

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
| **G-WPD-2** | May minor-evals 2024-Q2, 2025-Q2, 2026-Q2 | **Mostly closed** — 2026-Q2 and 2025-Q2 added; **only 2024-Q2 (May 2024) remains** | Retrieve + verify a clean per-index source for May 2024 |
| **G-WPD-3** | IDX80 constituents for **2023-H1 and 2022-H2** | Open | Find an IDX80-inclusive source for both |
| **G-WPD-4** | 0 `PRIMARY_VERIFIED` — all events secondary | **Attempted, blocked** — see §5 | Manual/human download of IDX PDFs past Cloudflare |
| **G-WPD-5** | month-precision effective dates (2023-H2, 2025-Q4) | Open | Confirm exact first-trading-day from primary or `ohlcv` |

## 5. Retrieval status & primary-verification progress

**Secondary retrieval (cumulative):** 2022-H2 (kompas), 2026-Q2 (bisnis), and **2025-Q2 (kompas — this pass)** verify-fetched first-hand. Method: targeted search → fetch of dedicated per-index "daftar" articles; recorded only what the article states (incl. verified *no-change* for LQ45 2025-Q2). May 2024 (2024-Q2) attempted again — no clean per-index source surfaced; remains a gap.

**Primary retrieval attempt (idx.co.id):**
- **Method 1 — WebFetch** of the official announcement PDF (`Peng-00067/BEI.POP/04-2026`) → **HTTP 403**.
- **Method 2 — headless browser (Playwright)** of the same PDF URL → **HTTP 403, "Attention Required! | Cloudflare"**.
- **Method 3 — headless browser** of the HTML announcements listing (`/en/news/announcement/`) → **HTTP 403, Cloudflare**.
- **Conclusion:** idx.co.id enforces domain-wide Cloudflare bot protection; **automated primary retrieval is not possible in this environment.** Upgrading any event to `PRIMARY_VERIFIED` requires a **manual/human step** — a person opening the IDX announcement in a normal browser and saving the PDF (e.g. via the `! ` in-session command, or an owner-supplied download).

> **Remaining uncertainty from secondary-only sourcing:** transcription and reporting risk. It is mitigated by (a) using bisnis/kompas "daftar lengkap" articles that reproduce the official per-index lists, and (b) cross-corroboration on 6 of 11 reviews. It is **not eliminated**; before any capital-relevant claim, primary verification should be obtained.

## 6. Impact on statistical power (qualitative — no power computed)

Per instruction, no power analysis is run. Qualitatively, coverage now stands at **194 events (178 distinct) across 12 review-date clusters** (from 154/9 originally). Because P-A power is **cluster-limited** ([[HYP-PA-0001_POWER]] §3), the clusters count is the binding quantity: 12 vs 11 modestly lifts the cluster-robust floor. The residual gaps (2021-H2, 2022-H1, May-2024) would each add **one more cluster**; closing them is the highest-value power lever. Whether 12 clusters suffice is the CRO's call — HYP-PA-0001 remains **owner-held**.
