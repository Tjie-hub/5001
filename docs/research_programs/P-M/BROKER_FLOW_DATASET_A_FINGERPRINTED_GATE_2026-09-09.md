# Dataset A — FINGERPRINTED Gate (F-1, F-2)

**Status:** **PREPARATORY — mechanism defined, fingerprint computed, coverage receipt produced. Dataset A is
NOT marked FINGERPRINTED by this document.** Per [[CUSTODY_MODEL]] and this session's own DECLARED-transition
precedent (D-040), a lifecycle transition requires an explicit Owner/CRO act, not an automatic promotion once
its prerequisites are satisfied.
**Date:** 2026-09-09 · **Program:** P-M · **Object:** `DS-broker_flow-idx80-nonpit-2025_2026v1` (Dataset A, O4,
DECLARED per D-040)
**Builds on:** `BROKER_FLOW_DATASET_A_DECLARED_READINESS_2026-09-09.md`, `..._TRANSITION_REQUEST_2026-09-09.md` —
neither modified. No production data, schema, or code was modified to produce this document; all computation
below is read-only against `data/walkforward.db`.

---

## 1. Governing fingerprint requirements (inspected before defining anything)

- **[[CUSTODY_MODEL]] §5.5, Rule CU-15:** *"Every fingerprint declares its scope, and the declaration is part of
  the fingerprint's meaning. A fingerprint that pins less than its name implies is worse than none."* Current
  `research/tracking.py:119-152` `dataset_fingerprint()` hashes **`ohlcv` (is_final=1) + `corporate_actions`
  only** — scoped to the settled research corpus, not `broker_flow`. CU-15's amendment: *"`dataset_fingerprint`
  is renamed in concept to a corpus fingerprint and each asset declares its own."*
- **[[RESEARCH_OBJECT_SCHEMA]] §3.4, O4 Provenance facet:** `provenance_hash` · vendor + retrieval time ·
  transformation lineage · `point_in_time` construction argument.
- **[[CUSTODY_MODEL]] §4.2, T-C2 guard:** `CREATED → REGISTERED` requires *"Identity + fingerprint + lineage."*
  Under D-036 (orthogonal-axes ruling), this asset-state guard is a separate axis from DECLARED and is **not**
  itself required to reach DECLARED — but the fingerprint it requires is the same artifact this document
  produces, so this work is not wasted regardless of which axis eventually consumes it.

**Convention reused, not invented** (per instruction — no conflicting custody mechanism introduced): the exact
method `dataset_fingerprint()` already uses — an order-independent-in-content, per-ticker aggregate
(`COUNT(*)`, `MIN(date)`, `MAX(date)`, integer sums), rows iterated in `ORDER BY ticker`, joined `"|"`-delimited
per row with a trailing `\n`, SHA-256 over the concatenated bytes. Applied here to `broker_flow` instead of
`ohlcv`, with `lot`/`lot_value` in place of `close`/`volume`.

## 2. F-1 — `broker_flow` fingerprint, Dataset A exact scope

**Scope declaration (CU-15 — states what this pins, and explicitly what it does not):**

- **Population:** `broker_flow` rows where `ticker` ∈ the 79-ticker roster (R-3 receipt, SHA-256
  `7d4eb1004e7d1e83153eede9a5d4e458ab5298ac1a4a4d7fa301f095f665eee0`) **and** `trade_date` ∈
  `[2025-01-02, 2026-08-27]` **and** `trade_date ≠ 2026-08-25`.
- **Pins:** per-ticker row count, min/max `trade_date`, `SUM(lot)`, `SUM(lot_value)` — deterministic and stable
  regardless of query plan or row-insertion order within a ticker.
- **Does NOT pin** (explicitly, per CU-15): `broker_code`/`side` granularity (aggregated away), `freq`,
  `avg_price`, `investor_type`, `value`/`value_total` columns, or row-insertion order. A future consumer needing
  broker-level or side-level granularity guaranteed must define a separate, more granular fingerprint — this one
  does not imply that coverage.

**Mechanism (executed read-only, `data/walkforward.db`, 2026-09-09):**
```sql
SELECT ticker, COUNT(*), MIN(trade_date), MAX(trade_date),
       SUM(CAST(lot AS INTEGER)), SUM(CAST(lot_value AS INTEGER))
FROM broker_flow
WHERE ticker IN (<79-ticker roster, R-3>)
  AND trade_date BETWEEN '2025-01-02' AND '2026-08-27'
  AND trade_date != '2026-08-25'
GROUP BY ticker ORDER BY ticker;
```
SHA-256 over the 79 resulting rows, `"|".join(str(x) for x in row) + "\n"` per row, matching
`research/tracking.py`'s exact byte-level convention.

**Result:**
```
per_ticker_rows:    79
total_rows_hashed:  1,222,713   (cross-checks exactly against the R-4 receipt's independently-counted row total)
fingerprint_sha256: 329b22e49f0ef882b6da031f437e9d87084d2863837ebf8c830de362b7942558
```

**Reproducibility receipt:** any read-only session against an unchanged `data/walkforward.db` running the exact
query above, in ticker-sorted order, with the exact hash construction, will reproduce this value bit-for-bit.
No code was added to the repository to compute this — the mechanism is fully specified above (query +
algorithm) rather than embedded in a new function, consistent with not modifying `research/tracking.py` or
inventing a parallel custody mechanism.

## 3. F-2 — Formal IDX80-scoped coverage-audit receipt (`broker_cell_complete()`, direct)

Executed by calling `tools.broker_flow_idx80_gap.idx80_universe()`, `canonical_trading_dates()`, and
`broker_cell_complete()` **directly, unmodified, read-only** — reusing the canonical predicate rather than
re-deriving row counts (per the admission draft's own warning that raw counts must not substitute for this).

| Parameter | Value |
|---|---|
| Roster | `idx80_universe(conn)` → 79 tickers (identical set to R-3) |
| Date window | `canonical_trading_dates(conn, '2025-01-02', '2026-08-28')` — exclusive upper bound, giving inclusive coverage through `2026-08-27` |
| Confirmed trading dates | **388** (IHSG-bar-and-`trading_calendar`-confirmed) |
| `2026-08-25` disposition | **Not in the confirmed set at all** — `trading_calendar` carries a `scraper_eod`-sourced row for it, but **no IHSG `ohlcv` bar exists**, so the canonical predicate excludes it on its own; Dataset A's explicit exclusion rule is therefore a no-op against this predicate, not an override of it. Cause remains **[UNRESOLVED]** — not established, not invented. |
| Dataset A dates (post-exclusion) | 388 (unchanged — 2026-08-25 was never in the 388) |
| Expected grid | 79 × 388 = **30,652** — exact match to the figure already established in D-035's FULLY RECONCILED finding |
| Observed missing cells (`broker_cell_complete() == False`) | **0** |
| `2026-08-25` `broker_flow` row count | 0 (re-confirmed) |

**Relationship to the already-completed FULLY RECONCILED result (D-035):** D-035's reconciliation worked
forward from log evidence and manual accounting to the identity `30,652 = 24,109 + 144 + 6,399`. This receipt
arrives at the same `30,652`-cell expected grid and the same zero-missing-cells conclusion via the opposite
route — direct, live invocation of the canonical completeness predicate against the current database, with no
log evidence involved at all. The two independent methods agree exactly; neither superseded the other, and D-035
is not re-litigated.

## 4. F-1 / F-2 status

| Item | Status |
|---|---|
| **F-1 mechanism** | **Defined and executed.** Fingerprint scope declared per CU-15; value computed; reproducibility receipt recorded. |
| **F-2 coverage receipt** | **Produced**, using the canonical predicate directly, formally superseding the earlier ad-hoc accounting as the standalone artifact D-035 itself noted was still missing. |
| **F-3, F-4, F-5** | **Not performed.** Nothing encountered in F-1/F-2 surfaced any of them as a genuine FINGERPRINTED-gate prerequisite — `corporate_actions_applied` verification, the consumer-formula audit, and `regime_classification` remain exactly where the admission draft placed them: FROZEN-gate items (§J.2), not FINGERPRINTED-gate items. |

## 5. Is Dataset A legitimately FINGERPRINTED?

**No — not yet, and not by this document.** The technical prerequisites this session could locate for
FINGERPRINTED (a scope-declaring fingerprint mechanism + value, per CU-15 and RESEARCH_OBJECT_SCHEMA §3.4's
Provenance facet) are now satisfied. But — exactly as DECLARED required an explicit D-040 rather than an
automatic promotion once R-1…R-10 closed — marking FINGERPRINTED is a lifecycle transition and requires its own
explicit Owner/CRO act. **This document is the request package for that act, not the act itself.**

**Proposed DECISION_LOG wording, NOT applied:**

> ### D-041 · Dataset A `DS-broker_flow-idx80-nonpit-2025_2026v1` transitioned to FINGERPRINTED
> **Status:** [PENDING OWNER APPROVAL] · **Date:** [date] · **Type:** O4 Dataset lifecycle transition · **Approval authority:** Owner
>
> **Decision.** Dataset A enters `FINGERPRINTED` ([[RESEARCH_OBJECT_SCHEMA]] §3.4), with `provenance_hash =
> 329b22e49f0ef882b6da031f437e9d87084d2863837ebf8c830de362b7942558` (scope declared per
> `BROKER_FLOW_DATASET_A_FINGERPRINTED_GATE_2026-09-09.md` §2) and the formal coverage-audit receipt (§3 of the
> same document) both on record.
>
> **Not authorized by this transition:** FROZEN, hypothesis registration, or empirical testing — each remains
> gated on F-3/F-4/F-5 and [[HYPOTHESIS_LIFECYCLE]] G1 respectively.
>
> **Files changed:** this entry · `BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md` §G (FINGERPRINTED row) ·
> `BROKER_FLOW_DATASET_A_FINGERPRINTED_GATE_2026-09-09.md` (status annotation only).
>
> **Related:** D-040 · `BROKER_FLOW_DATASET_A_FINGERPRINTED_GATE_2026-09-09.md`.

## 6. Remaining FROZEN blockers (unchanged from the readiness audit, not re-investigated this pass)

F-3 (`corporate_actions_applied` verification), F-4 (consumer-formula audit, non-blocking per the admission
draft's own classification), F-5 (`regime_classification` assessment) — none performed, none required by
FINGERPRINTED specifically.

## 7. Worktree note

Files touched this turn: `docs/research_programs/P-M/BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md`
(header/status + §H wording only, per instruction) and this new artifact. No other file, no code, no DB write.
