# Broker-Flow Dataset Population Specification — H-7C (Dataset A / Dataset B)

**Status:** SPECIFICATION / READ-ONLY GOVERNANCE ARTIFACT — NOT a Dataset Object lifecycle transition. Neither
candidate below is DECLARED, FINGERPRINTED, or FROZEN by this document.
**Date:** 2026-09-09 · **Program:** P-M · **Object type:** two candidate [[RESEARCH_OBJECT_MODEL]] O4 Dataset
instances, specified per [[RESEARCH_OBJECT_SCHEMA]] §3.4.
**Owner decision this artifact operationalizes:** **H-7C APPROVED (2026-09-09)** — treat the August 2026 non-PIT and
August/September PIT-aware IDX80 backfill executions as **separate dataset populations**; do not collapse them. This
directly resolves — by splitting rather than merging — the ambiguity left OPEN as **H-6** ("P1 provenance-boundary
treatment") in `BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md` §H. This artifact does not amend, supersede, or
grant DECLARED status to that admission draft, nor does it amend [[DECISION_LOG]] D-032 or D-033. H-2, H-3, H-4, H-5
from that draft remain independently OPEN and apply to whichever candidate(s) later proceed toward DECLARED.

**Evidence-classification legend (carried forward from the admission draft for consistency):**
- **[CANONICAL]** — verifiable in the Research Governance Corpus or repository at a cited `file:line`.
- **[DB-VERIFIED]** — this session directly queried `data/walkforward.db` read-only and observed the stated fact.
- **[LOG-DERIVED]** — sourced from `backfill_broker_flow_idx80.log`; **see §0 — this log is confirmed contaminated by
  test-suite output and must not be trusted without DB cross-verification.**
- **[INFERRED]** — a plausible reading of DB-VERIFIED evidence, not itself directly recorded (e.g. rowid/timestamp lag
  reasoning). Never upgraded to fact.
- **[UNRESOLVED]** — open question; no interpretation offered.
- **[OWNER]** — requires an explicit Owner decision.

---

## 0. Evidence-integrity finding (read before §1–§13 — governs how every number below must be weighted)

This finding was produced in this session, correcting an over-reliance on log evidence in the immediately prior H-6
investigation, and must be carried forward:

`backfill_broker_flow_idx80.log` (repo root) is **not a reliable production-write record on its own**.
`tools/backfill_broker_flow_idx80.py`'s `LOG_PATH` is a fixed relative path with no test-time monkeypatch
[DB-VERIFIED — `tests/test_backfill_broker_flow_idx80.py` monkeypatches `R.DB_PATH` (line 50) but never `LOG_PATH`],
so pytest runs of this tool's test suite append real-looking `Backfill start / [n/n] N missing cells / DONE:
populated=N` lines to this **same shared log file** while writing only to an ephemeral temp DB. Direct evidence of
contamination: the log's final entry (`2026-09-08 12:21:06`, `universe_mode=pit`, dates 2025-01-02/2025-01-03,
`DONE: populated=158 skipped=2`) **has no corresponding write anywhere in `bandar_detector`** — the only
`bandar_detector` row with `updated_at` on `2026-09-08` is `AADI` at `2026-09-08T18:30:04`, `trade_date=2026-09-08`
(same-day, i.e. that day's ordinary live job, unrelated) [DB-VERIFIED]. Likewise several PIT-mode log lines target
`trade_date=2025-02-02`, a Sunday, which the tool's real trading-calendar gate (`canonical_trading_dates`,
`tools/broker_flow_idx80_gap.py:52`) would never schedule — consistent with synthetic test fixtures, not a real run.

**Governing rule for this document:** every quantitative claim below is either **[DB-VERIFIED]** (queried directly
against `data/walkforward.db`, cross-checked for same-day-write contamination) or explicitly marked
**[LOG-DERIVED]** and flagged as unconfirmed. Where the two conflict or a log figure has no DB corroboration, this is
recorded as **[UNRESOLVED]**, not silently reconciled, per instruction.

---

## Dataset A — IDX80 NON-PIT

### A.1 Identity

| Field | Value |
|---|---|
| Candidate dataset ID | `DS-broker_flow-idx80-nonpit-2025_2026v1` — **interim/non-canonical**, per instruction; registry treatment remains H-5 (OPEN, admission draft) |
| Exact analytical window | `2025-01-02` → `2026-08-27` inclusive, excluding `2026-08-25` |
| Exact universe definition | The **current-at-backfill-time** `idx_tickers WHERE status='active' AND in_idx80=1` roster (79 tickers as of the backfill execution), applied retrospectively/uniformly to every date in the window — **the same 79-ticker set for every date**, regardless of true historical membership |
| PIT status | **NON-PIT** — explicitly, by construction (`tools/broker_flow_idx80_gap.py::idx80_universe()` queries today's flag, not a date-scoped membership table) |
| 2026-08-25 treatment | Excluded — confirmed `0` rows for that date [DB-VERIFIED: `SELECT COUNT(*) FROM broker_flow WHERE trade_date='2026-08-25'` → `0`]. Not repaired, not imputed by this artifact. |
| Intended research role | Candidate input to a per-ticker broker-flow/return mechanism study (P-M), **not** usable for any claim requiring historical index composition |

### A.2 Inclusion predicate

A `broker_flow` row is in Dataset A iff:
`ticker ∈ {today's idx80_universe()}` **AND** `trade_date ∈ [2025-01-02, 2026-08-27]` **AND** `trade_date ≠ 2026-08-25`
**AND** the row's cell `(ticker, trade_date)` was resolved (written or confirmed-empty) by the August 2026 non-PIT
backfill campaign or by the ordinary live collection path, whichever populated it first — the two are mutually
exclusive by construction (§4 below; `broker_cell_complete()` gap-check).

### A.3 Exclusion predicate

Explicitly excluded:
- `trade_date = 2026-08-25` (confirmed zero-row date; cause not established by this or the prior investigation).
- Any ticker not in the **current** IDX80 roster, even if it appears in `broker_flow` for a date inside the window
  (e.g. the 17 tickers per early-2025 date attributable to Dataset B — see §5 comparison).
- Any `trade_date` outside `[2025-01-02, 2026-08-27]`, even for an IDX80 ticker.

### A.4 Provenance status

| Claim | Class | Evidence |
|---|---|---|
| The non-PIT campaign executed and wrote real rows | **[DB-VERIFIED]** | `bandar_detector.updated_at` shows a concentrated write session `2026-08-28T08:32:17` → `2026-08-29T08:26:55`, 24,934 rows across 308 distinct `trade_date` values, all with `trade_date < updated_at` by 60+ days |
| Exact cell-level outcome breakdown (populated/skipped/empty_confirmed) | **[LOG-DERIVED, partially corroborated]** | Log aggregate across 307 "x 79 IDX80 ticker(s)" run blocks: `populated=24,004 skipped=223 empty_confirmed=26` (≈24,030 cells). DB-direct count for the same write-days is `24,934` rows — a **~904-row gap, [UNRESOLVED]**, not reconciled here. |
| 2025-01-02 specifically: 79/79 cells were missing before this run, all populated, zero pre-existing | **[DB-VERIFIED]** cross-check | Log line `2026-08-28 09:27:06 ... [1/1] 2025-01-02: 79 missing cells ... DONE: populated=79 skipped=0` matches `bandar_detector` rows for `AALI…` etc. on `2025-01-02` with `updated_at` in the exact `09:27:06–09:29:21` window, 79 rows total |
| No genuine P1 (real-time, 2025-era) write ever preceded this campaign for IDX80 tickers | **[INFERRED]**, strong but not certain | Table-wide: every `bandar_detector` row with `trade_date` before `2026-04-20` has `updated_at` in either `2026-08` (34,465 rows) or the 8–60-day bucket (5,122 rows, `trade_date` `2026-04-01`→`2026-07-27`); **zero** rows show a same-day (0–1 day lag) write for any `trade_date` before `2026-04-20`. Absence of same-day evidence is not proof no real-time collection ever ran, only that none of its writes survive in the current table state. |

### A.5 Coverage

**Do not use row count alone.** What is establishable from current evidence:
- 307 real (`79 IDX80 ticker`) log-recorded run invocations across `2025-01-02`…`2026-08-27`-range dates [LOG-DERIVED].
- 308 distinct `trade_date` values touched in the DB-verified `2026-08-28/29` write session [DB-VERIFIED] — close to but not proven identical to the log's 307-run figure (runs can revisit the same date on retry; not a 1:1 date count).
- Zero duplicate-key rows exist anywhere in `broker_flow` (`PRIMARY KEY(ticker, trade_date, broker_code, side)`; `GROUP BY … HAVING COUNT(*)>1` → `0`) [DB-VERIFIED], so no cell in Dataset A can be double-counted or silently overwritten.
- **Formal coverage audit still required:** a per-(ticker, trade_date) completeness sweep against the full 79-ticker × trading-calendar cross product for the exact window, using the same predicate `tools/broker_flow_idx80_gap.py::broker_cell_complete()` already canonical per D-032 — not yet run by this artifact (explicitly out of scope: no empirical test was run).

### A.6 Universe integrity

**Fixed-roster limitation (documented, not resolved):** the 79-ticker roster is today's IDX80 membership, applied
uniformly to every date back to 2025-01-02. IDX80 reconstitutes periodically; a ticker that was in IDX80 in, say,
mid-2025 but has since been removed is **absent from Dataset A for its entire IDX80-member history**, and a ticker
newly added since is **present for dates before it was ever actually a member**. This is a survivorship/look-ahead
risk on any claim of the form "ticker X was in IDX80 on date Y" — Dataset A cannot support such a claim. No claim of
historical membership accuracy is made anywhere in this artifact.

### A.7 Known gaps

- `2026-08-25` — zero rows, cause not established (§A.1). Applies to Dataset A by explicit exclusion.
- The ~904-row discrepancy between log-aggregate and DB-direct counts (§A.4) is an unresolved coverage-accounting gap, not a data gap per se.
- No formal per-cell audit against the full 79×trading-calendar grid has been run (§A.5).

### A.8 O4 field mapping (per [[RESEARCH_OBJECT_SCHEMA]] §3.4 — no fields invented)

| O4 field | Status | Value / note |
|---|---|---|
| `dataset_id` | derivable | `DS-broker_flow-idx80-nonpit-2025_2026v1` — proposed label, not registry-issued (H-5 open) |
| `asset_class` | evidenced | IDX equities, current-IDX80 (79-ticker) universe |
| `resolution` | evidenced | Daily, broker-level; one row per (ticker, trade_date, broker_code, side) [CANONICAL schema] |
| `regime_classification` | unresolved/not available | No regime analysis run |
| `provenance_hash` | unresolved/not available | No fingerprint function exists for `broker_flow` (`research/tracking.py:119` scopes only `ohlcv`+`corporate_actions`) |
| `capability_class` | pending verification | CRO decision, not made here (§9) |
| `fidelity_limit` | derivable | Cannot distinguish historical IDX80 membership as-known-then; cannot distinguish P1 (pre-backfill live) rows from this campaign's own writes at the schema level (no `source` column) |
| `proxy_for` | pending verification | Informed-flow/adverse-selection proxy tier per `DATA_FEASIBILITY_STUDY` §4.1 — not re-verified by this artifact |
| `point_in_time` | evidenced (negative) | **NO** for any index-composition-dependent claim (§A.6) |
| `corporate_actions_applied` | unresolved/not available | No evidence establishes this either way |
| `custody_partition` | unresolved/not available | Not assigned |

### A.9 Capability/fidelity

`capability_class` is **not chosen here** (explicit instruction). Evidence needed for that CRO decision: (a) the
formal coverage audit (§A.5), (b) resolution of the ~904-row log/DB discrepancy, (c) `corporate_actions_applied`
verification, (d) confirmation of whether the History-Maturity Gate (`DATA_FEASIBILITY_STUDY` §5.3, cited in the
admission draft §F.7) applies given the now-confirmed 2025-01-02 start date.

### A.10 Freeze prerequisites (outstanding receipts/audits — none satisfied here)

1. Persisted Owner authorization receipt for the non-PIT backfill scope specifically (distinguishing it from Dataset B) — extends admission-draft R-1/R-2.
2. Formal per-cell coverage audit (§A.5), against the 79-ticker roster and full trading calendar.
3. Reconciliation or explicit acceptance of the ~904-row log/DB discrepancy (§A.4).
4. `broker_flow` fingerprint scope/mechanism definition (does not exist today) — before any `FINGERPRINTED` step.
5. `corporate_actions_applied` verification.
6. CRO `capability_class` ruling (§A.9).
7. Dataset ID / registry ruling (shared gap with the admission draft's H-5).
8. Explicit Owner ruling that Dataset A, so scoped, is the intended narrowing under H-1 (already APPROVED at the single-dataset level via D-033; **not yet re-confirmed at the split-into-two level this artifact introduces**).

### A.11 Research eligibility

Not declared · Not fingerprinted · Not frozen · Empirical gate not passed · Hypothesis registration not authorized.
No status changes as a result of this artifact.

---

## Dataset B — IDX80 PIT-AWARE

### B.1 Identity

| Field | Value |
|---|---|
| Candidate dataset ID | `DS-broker_flow-idx80-pit-2025_2026-04v1` — **interim/non-canonical.** Named for the reliably-evidenced continuous window only (§B.7 documents the discontinuity that makes a single clean end-date claim unsafe) |
| Exact analytical window (evidenced) | **Continuous incremental campaign:** `2025-01-02` → `2026-04-22` (matches observed trading-day cadence, no unexplained internal gaps in this sub-range). **Isolated addendum:** a single further date, `2026-07-24`, written in the same session but disconnected from the continuous run by an unexplained ~3-month jump — treated as a **separate, unverified extension**, not folded into the named window. **Do NOT assume coverage through 2026-08-27** (Dataset A's window) — no evidence supports that for Dataset B. |
| Exact universe definition | **Date-varying** — a PIT-aware membership roster whose *observed incremental addition count* (new tickers per date, beyond whatever the non-PIT Dataset A campaign already wrote) is **not constant**: 17/date (2025-01-02 through ~2025-10-31), 19/date (~2025-11-03 through ~2026-01-30), 20/date (~2026-02-02 through ~2026-04-16, with two anomalous 18-count dates at 2026-04-17 and 2026-04-20), 20/date again (2026-04-21, 2026-04-22), then the isolated 22-count date 2026-07-24. **These are incremental-addition counts, not necessarily full roster sizes** — see §B.6. |
| PIT status | **PIT-aware**, explicitly named `universe_mode=pit` in the tool invocation and structurally distinct in its write pattern from Dataset A (§4) |
| 2026-08-25 treatment | **Out of the evidenced window entirely** — Dataset B's real writes stop (continuous run) at 2026-04-22 and (isolated) at 2026-07-24, neither of which is 2026-08-25. The question does not arise for Dataset B as currently evidenced. |
| Intended research role | Same candidate P-M mechanism-study role as Dataset A, but explicitly as a **separate, not-yet-comparable** population pending resolution of universe-definition differences (§5) |

### B.2 Inclusion predicate

A `broker_flow` row is in Dataset B iff its `(ticker, trade_date)` cell was written by the PIT-aware campaign
specifically — operationally: the cell's paired `bandar_detector.updated_at` falls in the verified write session
`2026-08-31T13:04:13` → `2026-08-31T16:40:34`, **excluding** any row whose `trade_date = 2026-08-31` itself (that
date's rows are the ordinary same-day live job, not the PIT campaign — see §0/§B.4). This is an **operational,
timestamp-based** inclusion rule in the absence of a real provenance column, not a schema-level guarantee.

### B.3 Exclusion predicate

Explicitly excluded:
- Rows also present in Dataset A for the same cell (mutually exclusive by the shared gap-check design — §4).
- `trade_date = 2026-08-31` rows written at `2026-08-31T18:30:xx` (824 rows, `AADI`-pattern same-day live job — confirmed unrelated to the PIT backfill by same-day-write timing).
- Any `trade_date` between 2026-04-23 and 2026-07-23 inclusive, and any date after 2026-07-24 — **no evidence of PIT-campaign writes exists for these**; do not interpolate.
- The `2026-09-08` PIT-mode log entries — **excluded as unconfirmed / likely test-suite artifacts** (§0).

### B.4 Provenance status

| Claim | Class | Evidence |
|---|---|---|
| A real, sustained PIT-mode write session occurred against production `data/walkforward.db` | **[DB-VERIFIED]** | `bandar_detector` rows with `updated_at` in `2026-08-31T13:04:13`–`16:40:34.405`, spanning trade dates `2025-01-02`→`2026-04-22` continuous, plus one at `2026-07-24`; 5,490 rows / 308 distinct trade_dates total (307 in the continuous run + the 1 isolated date) |
| Per-date incremental-addition counts (17/19/20/18/22) | **[DB-VERIFIED]** | Directly queried, grouped by `trade_date`, for the same write session |
| A second, later invocation (`2026-09-08 12:21:06`, `universe_mode=pit`) also wrote real production rows | **[UNRESOLVED — evidence points against it]** | No `bandar_detector` row anywhere has `updated_at` on `2026-09-08` except one unrelated same-day live row (`AADI`, `trade_date=2026-09-08`). Treated as **not corroborated**; do not cite the log's `populated=158` figure for this timestamp as a real write. |
| "PIT universe has 81 members; expected nominal IDX80 size is 80" (log WARNING, dates 2025-02-02/2025-02-03) | **[LOG-DERIVED, unconfirmed, likely contaminated]** | `2025-02-02` is a Sunday — outside `canonical_trading_dates()`'s real gate — inconsistent with a genuine scheduled run against the real trading calendar; most plausibly test-fixture noise sharing the log path (§0). **Not used as evidence of the real PIT roster size for any date in this artifact.** |
| The continuous run's growing increment (17→19→20) reflects real historical IDX80 reconstitution events | **[INFERRED]**, plausible, not verified | Consistent with periodic index rebalancing cadence, but this artifact does not independently verify against a historical reconstitution calendar |

### B.5 Coverage

**Do not use row count alone.** What is establishable:
- 5,490 rows, 308 distinct trade_dates, real DB-verified write session `2026-08-31T13:04:13`→`16:40:34` (continuous portion `2025-01-02`→`2026-04-22`) plus the isolated `2026-07-24` date (22 rows) [DB-VERIFIED].
- **No formal coverage audit exists** for what fraction of the *true* historical PIT-IDX80 roster this represents on any given date — these are *incremental-addition* counts on top of whatever Dataset A already covered, not a measure of total roster completeness per date.
- **The window is confirmed non-contiguous and confirmed shorter than Dataset A's** — do not assume Dataset B reaches 2026-08-27, or that its April–July gap will resolve to continuous coverage without a new, explicitly authorized run.

### B.6 Universe integrity

**Date-specific membership, not merged with Dataset A's fixed roster.** Unlike Dataset A, Dataset B's universe
genuinely varies by date (per §B.1's incremental-count pattern) — this is a meaningfully different construction, and
the two universe definitions **must not be merged or treated as interchangeable** per the H-7C instruction. The
anomalous roster-size log WARNING (81 members vs nominal 80) is recorded as an **observed data point in the log**,
explicitly **not normalized to 80 and not treated as DB-confirmed** (§B.4) — a genuine PIT roster occasionally
differing from the nominal 80-member count (index float, corporate actions, or reconstitution-transition effects) is
plausible in principle, but this artifact does not resolve which, if any, of the log's specific member-count claims
reflect real production behavior versus test noise.

### B.7 Known gaps

- **Confirmed internal discontinuity:** the continuous incremental run ends at `2026-04-22`; the next (and only
  further) evidenced date is `2026-07-24`, an unexplained ~3-month jump with no evidence of what happened to
  `2026-04-23`→`2026-07-23` in this campaign.
- **Confirmed absence of coverage** past `2026-07-24` through `2026-08-27` (Dataset A's window end) — Dataset B does
  **not** cover this range on current evidence.
- **The `2026-09-08` extension is unconfirmed** (§B.4) — if a real production run is later confirmed to have occurred
  then, this specification will need a superseding revision, not a silent edit.
- Two anomalous incremental-count dates (`2026-04-17`, `2026-04-20`: 18 instead of the surrounding 20) are recorded,
  not explained.

### B.8 O4 field mapping

| O4 field | Status | Value / note |
|---|---|---|
| `dataset_id` | derivable | `DS-broker_flow-idx80-pit-2025_2026-04v1` — proposed, non-canonical |
| `asset_class` | evidenced | IDX equities, date-varying PIT-aware IDX80-adjacent roster |
| `resolution` | evidenced | Same schema/resolution as Dataset A (shared table) |
| `regime_classification` | unresolved/not available | Not assessed |
| `provenance_hash` | unresolved/not available | No fingerprint mechanism exists (shared gap with Dataset A) |
| `capability_class` | pending verification | CRO decision, not made here |
| `fidelity_limit` | derivable | Cannot establish true historical roster completeness per date (§B.5); cannot separate a cell's provenance from Dataset A's at the schema level except via the timestamp-operational rule in §B.2, which is inference, not a guarantee |
| `proxy_for` | pending verification | Not independently re-verified for this narrower population |
| `point_in_time` | pending verification | **Better-positioned than Dataset A** (date-varying roster is the PIT design intent) but **not verified as PIT-correct** — no independent historical-membership source was cross-checked in this artifact |
| `corporate_actions_applied` | unresolved/not available | Not established |
| `custody_partition` | unresolved/not available | Not assigned |

### B.9 Capability/fidelity

Not chosen here. Evidence needed: (a) resolution of whether the `2026-09-08` extension is real (§B.4), (b) an
independent historical-IDX80-membership source to verify the PIT-roster claim rather than infer it from write
patterns, (c) explanation of the `2026-04-22`→`2026-07-24` gap and the 18-count anomaly dates, (d) a decision on
whether the incomplete/non-contiguous window is admissible for any research use at all before it reaches parity with
Dataset A's window.

### B.10 Freeze prerequisites

1. Resolve whether the `2026-09-08` PIT-mode invocation constitutes a real, separate write event or pure test noise — a positive determination either way, not left open.
2. Independent verification of the PIT-roster construction against a historical membership source (not just internal write-pattern inference).
3. Explicit decision on the `2026-04-22`→`2026-07-24` gap and post-`2026-07-24` absence — extend the campaign, or freeze only the continuous sub-window.
4. Same shared items as Dataset A: fingerprint mechanism, `corporate_actions_applied`, CRO `capability_class`, registry/ID ruling.
5. Owner ruling on whether a non-contiguous, partial-window dataset is eligible to proceed toward DECLARED at all, or must first reach full-window parity.

### B.11 Research eligibility

Not declared · Not fingerprinted · Not frozen · Empirical gate not passed · Hypothesis registration not authorized.

---

## 4. Structural note shared by both candidates (why cell-level collision is not a concern)

Both campaigns write through `INSERT OR REPLACE` gated by `broker_cell_complete()` (any existing `broker_flow` row,
or a confirmed-empty `bandar_detector` marker, for that `(ticker, trade_date)` ⇒ skip). `broker_flow`'s primary key
is exactly `(ticker, trade_date, broker_code, side)`, and a direct query confirms zero duplicate-key groups exist
anywhere in the table [DB-VERIFIED]. This means Dataset A and Dataset B's rows are **structurally disjoint at the
cell level by construction**, not merely disjoint as a matter of the observed data — reinforcing why H-7C's
instruction to keep them as separate populations is consistent with the actual write mechanics, not just a labeling
convenience.

---

## 5. Comparison — why A and B are separate populations and must not be combined

| Dimension | Dataset A (non-PIT) | Dataset B (PIT-aware) | Why they can't merge |
|---|---|---|---|
| Universe construction | Fixed: today's 79-ticker IDX80 list applied to every date | Date-varying: incremental roster additions per date (17→19→20, with anomalies) | Merging would silently convert a date-varying PIT construction into a fixed-roster one or vice versa — exactly the collapse H-7C forbids |
| Evidenced window | `2025-01-02`→`2026-08-27` (minus `2026-08-25`) | `2025-01-02`→`2026-04-22` continuous + isolated `2026-07-24`; **not** proven to `2026-08-27` | A's window is materially longer and more complete; treating B as co-extensive with A would overstate B's coverage |
| Write session | `2026-08-28T08:32`→`2026-08-29T08:27` | `2026-08-31T13:04`→`16:40` (separate day, separate session) | Distinct executions, distinct roster logic, distinct completeness — conflating write sessions loses the audit trail each needs independently |
| PIT correctness | Explicitly NOT PIT; survivorship/look-ahead risk documented (§A.6) | PIT-*aware* by design intent, but not independently verified (§B.9) | A cell's meaning ("was this ticker in IDX80 on this date") is opposite in kind between the two — a merged table could not honestly answer that question for any row |
| Known gaps | One excluded date (`2026-08-25`), one unresolved count discrepancy (~904 rows) | Confirmed internal discontinuity (`2026-04-22`→`2026-07-24`) and unconfirmed extension (`2026-09-08`) | Different gap *shapes* requiring different remediation — a merged gap ledger would obscure which population needs what |
| Log reliability | Log corroborated for 2025-01-02 spot-check; ~904-row aggregate gap unresolved | Log actively contradicted for the `2026-09-08` entries (§0) | B's log evidence is *more* suspect than A's — a merged confidence rating would either overstate B or understate A |

---

## 6. Governance recommendation

**Both should remain candidates; neither should proceed toward DECLARED yet, and additional evidence is required
first** — for materially different reasons per candidate:

- **Dataset A** is closer to admission-ready: it has a longer, DB-corroborated window, one already-flagged exclusion,
  and one unresolved-but-bounded (~904-row) accounting gap. Its prerequisites (§A.10) are largely audit/receipt work
  on data that already exists.
- **Dataset B** is materially earlier-stage: its evidenced window is shorter and non-contiguous, its most recent
  claimed extension (`2026-09-08`) does not survive DB cross-verification, and its core PIT-correctness claim has
  not been independently verified against any historical-membership source — it currently rests on internal
  write-pattern inference only. Recommend explicit Owner/CRO scoping of what additional evidence-gathering (not
  empirical testing) is authorized before Dataset B's prerequisites (§B.10) can even be attempted in the same order
  as Dataset A's.

Recommended immediate next governance action: an Owner ruling that (a) explicitly re-confirms H-1 (IDX80-scoped
admission path, previously approved at the single-dataset level via D-033) now applies, if at all, **separately** to
each of Dataset A and Dataset B under H-7C, and (b) authorizes or declines further evidence-gathering on the
`2026-09-08` extension and the historical-PIT-roster verification for Dataset B before its freeze-prerequisite work
begins.

---

## 7. Verification commands used (read-only; none mutate `data/walkforward.db`)

```sql
-- structural: zero duplicate-key rows anywhere
SELECT COUNT(*) FROM (SELECT ticker,trade_date,broker_code,side,COUNT(*) c
  FROM broker_flow GROUP BY 1,2,3,4 HAVING COUNT(*)>1);

-- Dataset A evidence: non-PIT write session bounds
SELECT COUNT(*), COUNT(DISTINCT trade_date), MIN(updated_at), MAX(updated_at)
FROM bandar_detector WHERE substr(updated_at,1,10) IN ('2026-08-28','2026-08-29');

-- Dataset B evidence: PIT-mode write session, excluding the same-day live spike
SELECT COUNT(*), COUNT(DISTINCT trade_date), MIN(trade_date),
       MAX(CASE WHEN trade_date != '2026-08-31' THEN trade_date END)
FROM bandar_detector
WHERE substr(updated_at,1,10)='2026-08-31' AND trade_date != '2026-08-31';

-- per-date incremental counts for Dataset B
SELECT trade_date, COUNT(*), MIN(updated_at), MAX(updated_at)
FROM bandar_detector WHERE substr(updated_at,1,10)='2026-08-31'
GROUP BY trade_date ORDER BY trade_date;

-- contamination check: does the 2026-09-08 log entry correspond to a real write?
SELECT * FROM bandar_detector WHERE substr(updated_at,1,10)='2026-09-08';
```
```bash
# log evidence used for A's aggregate figures and to identify the contaminated 2026-09-08 entry
grep -n "universe_mode=pit\|PIT roster\|PIT universe" backfill_broker_flow_idx80.log
grep -n "LOG_PATH\|monkeypatch" tests/test_backfill_broker_flow_idx80.py
```

---

## 8. Confirmation

- `git status` was checked before and after this session's work; the only change introduced is this file (new,
  untracked). No tracked file was modified. No `data/walkforward.db` write occurred (all queries `SELECT`-only,
  verified via `stat` timestamp on the DB file being older than the query session).
- No schema, index, trigger, or provenance column was added to `broker_flow` or `bandar_detector`.
- No Dataset Object was declared, fingerprinted, or frozen. No hypothesis was registered. No empirical test was run.
- The two populations were **not** silently reconciled — their ~904-row (A) and unconfirmed-extension (B)
  discrepancies are recorded as open, not resolved.
