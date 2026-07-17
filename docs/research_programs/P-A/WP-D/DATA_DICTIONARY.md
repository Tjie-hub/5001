# WP-D · Data Dictionary — `reconstitution_events.csv`

**Format:** long / tidy — **one row per (index, review, ticker, direction) event.** A wide "added/removed lists per review" view is a pivot of this table; the long form is canonical because it attaches provenance to *every* event ([[README]] integrity guarantees).

## Fields

| # | Field | Type | Definition | Allowed values / format | Missing-value policy |
|---|---|---|---|---|---|
| 1 | `event_id` | string | Stable unique key for the event | `PA-RC-NNNN` (zero-padded) | Never missing (generated) |
| 2 | `index` | enum | The index the event belongs to | `LQ45` · `IDX30` · `IDX80` | Never missing |
| 3 | `review_period` | string | The evaluation the event came from | `YYYY-H1/H2` (semiannual) or `YYYY-Qn` (quarterly) | Never missing |
| 4 | `cadence` | enum | Review cadence in force at the time | `semiannual` (pre-Apr 2024) · `quarterly` (Apr 2024→) | Never missing |
| 5 | `announcement_date` | date | Date IDX announced the evaluation result | ISO `YYYY-MM-DD` | Never missing; from source |
| 6 | `effective_date` | date | Date the change takes effect | ISO `YYYY-MM-DD` | Never missing; see `date_precision` |
| 7 | `date_precision` | enum | Precision of `effective_date` | `day` (exact date stated by source) · `month` (only month stated; nominal first-trading-day used) | Never missing |
| 8 | `event_type` | enum | Direction of the membership change | `ADD` (masuk) · `DELETE` (keluar) | Never missing |
| 9 | `ticker` | string | IDX ticker code | 3–4 uppercase letters (`^[A-Z]{3,4}$`) | Never missing |
| 10 | `source_name` | string | Human-readable source label | e.g. `bisnis.com 20250728/1896891` | Never missing |
| 11 | `source_url` | url | The exact retrieved document | https URL | Never missing |
| 12 | `retrieval_date` | date | When the source was fetched | ISO `YYYY-MM-DD` (`2026-07-17`) | Never missing |
| 13 | `verification_status` | enum | Corroboration level | `PRIMARY_VERIFIED` · `SECONDARY_CROSSCHECKED` · `SECONDARY_SINGLE` | Never missing |
| 14 | `notes` | string | Caveats (precision, corroboration, gaps) | free text | May be empty `""` |

### `verification_status` values

| Value | Meaning | Present in this dataset? |
|---|---|---|
| `PRIMARY_VERIFIED` | Confirmed against the official IDX announcement document | **No** — idx.co.id is Cloudflare-blocked to WebFetch **and** headless browser ([[SOURCE_REGISTRY]], [[COVERAGE_REPORT]] §5) |
| `SECONDARY_CROSSCHECKED` | Stated identically by ≥2 independent secondary sources | 6 of 11 reviews |
| `SECONDARY_SINGLE` | Stated by one fetched secondary source, not yet cross-corroborated | 5 of 11 reviews |

## Validation rules (enforced by the builder; audit result in [[COVERAGE_REPORT]])

1. **No self-collision** — a ticker may not be both `ADD` and `DELETE` within the same `(index, review_period)`.
2. **Ticker format** — matches `^[A-Z]{3,4}$`.
3. **Provenance completeness** — `source_url`, `retrieval_date`, `verification_status` all non-empty on every row.
4. **Temporal order** — `announcement_date < effective_date`.
5. **Usability window** — `effective_date ≥ 2021-07-05` (start of the `ohlcv` history the event study will use); rows outside are flagged.

## What is deliberately absent

- **No membership-state series.** This table records *changes*, not point-in-time constituent lists. Reconstructing a running membership state requires complete coverage from a known baseline and is a downstream validation, not a WP-D deliverable.
- **No returns / prices.** Abnormal-return estimation is the experiment's job; it joins this calendar to `ohlcv` at run time.
- **No imputed events.** Absence of a row for a period/index means *not found in a source*, not *no change occurred* — see [[COVERAGE_REPORT]] gaps.
