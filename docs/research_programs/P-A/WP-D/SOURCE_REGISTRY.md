# WP-D · Source Registry

Every event in `reconstitution_events.csv` traces to a source below. **Primary sources always override secondary sources.**

## Source hierarchy & trust ranking

| Rank | Tier | Source | Fetchable? | Role in this dataset |
|---|---|---|---|---|
| **1** | **Primary** | **IDX official** — `idx.co.id` "Pengumuman Evaluasi Indeks" announcements + the index methodology PDF (`Panduan dan Metodologi Indeks IDX80, LQ45 dan IDX30`) | ❌ **HTTP 403** to the retrieval tool | The authoritative record. **Not directly retrievable in this pass** — referenced, not used as row source. Example known primary doc: `Peng-00067/BEI.POP/04-2026` (Evaluasi Indeks 24 Apr 2026). |
| **2** | **Secondary (of record)** | **market.bisnis.com** — dedicated "Daftar Lengkap / Daftar Saham Keluar-Masuk" articles | ✅ | **The source of record for all 9 reviews** — the only secondary that reliably publishes clean *per-index* add/remove lists. One article per review (URLs in the CSV `source_url`). |
| **3** | **Secondary (corroborating)** | kontan.co.id · RRI.co.id · kalderanews.com · blog.rivankurniawan.com · theeconopost.com · investortrust.id · ugems.id (bisnis syndication) | ✅ (mostly) | Used only to **cross-check** bisnis lists and raise a review to `SECONDARY_CROSSCHECKED`. Never the sole source for an event. |

### Methodology provenance (cadence field)

The `cadence` field and the semiannual→quarterly transition are sourced from `market.bisnis.com 20240328/1753500` ("Mulai April, BEI Rombak LQ45, IDX30, dan IDX80 per Tiga Bulan"), retrieved 2026-07-17: **before April 2024** IDX evaluated these indices twice yearly (announced Jan/Jul, effective Feb/Aug); **from April 2024** four times yearly (announced Jan/Apr/Jul/Oct, effective Feb/May/Aug/Nov).

## Per-review source map

| Review | Source of record (Rank 2) | Corroboration (Rank 3) | Status |
|---|---|---|---|
| 2023-H1 | bisnis 20230126/1621746 | — | `SECONDARY_SINGLE` (IDX80 not covered) |
| 2023-H2 | bisnis 20230726/1678262 | — | `SECONDARY_SINGLE` |
| 2024-H1 | bisnis 20240126/1735652 | — | `SECONDARY_SINGLE` |
| 2024-Q3 | bisnis 20240725/1785558 | kalderanews (LQ45) | `SECONDARY_CROSSCHECKED` |
| 2024-Q4 | bisnis 20241027/1810909 | — | `SECONDARY_SINGLE` |
| 2025-Q1 | bisnis 20250123/1834176 | theeconopost | `SECONDARY_CROSSCHECKED` |
| 2025-Q3 | bisnis 20250728/1896891 | kontan, rivankurniawan | `SECONDARY_CROSSCHECKED` |
| 2025-Q4 | bisnis 20251028/1923846 | search-corroborated list | `SECONDARY_CROSSCHECKED` |
| 2026-Q1 | bisnis 20260126/1947363 | RRI, ugems, investortrust | `SECONDARY_CROSSCHECKED` |

## Conflict-resolution policy

1. **Primary overrides secondary, always.** When an IDX official announcement becomes retrievable, it supersedes the secondary record; any discrepancy is corrected toward the primary and the row is upgraded to `PRIMARY_VERIFIED`.
2. **Among secondary sources**, a per-index "daftar lengkap" article (bisnis of record) outranks a narrative/commentary article. Commentary pieces that report only selected names are **not** used to add or remove events.
3. **Cross-corroboration is required, not assumed.** A review reaches `SECONDARY_CROSSCHECKED` only when a second *independent* source states the identical per-index lists. Otherwise it stays `SECONDARY_SINGLE` and is flagged for a future verification pass.
4. **Disagreement between secondary sources** is resolved in favour of the bisnis-of-record article and logged in `notes`; if unresolved, the event is quarantined (excluded) and recorded as a gap — never guessed.

## Outstanding source work (to reach `PRIMARY_VERIFIED`)

- The IDX announcement PDFs are the gold standard but are 403-blocked to the current tool. Retrieving them (authenticated/browser path, or an alternate mirror) would upgrade every row from secondary to primary. This is the single largest quality upgrade available and is recorded as a blocker in [[READINESS_ASSESSMENT]].
