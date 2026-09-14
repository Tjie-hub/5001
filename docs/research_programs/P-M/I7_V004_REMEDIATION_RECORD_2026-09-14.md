# I7 v004 — CONTROLLED REMEDIATION RECORD — 2026-09-14

**Authority:** generated point-in-time record. **Scope:** closes the audit/process reservations raised in
`I7_V004_FORENSIC_AUDIT` (delivered in session; reservations R1–R9). **Documentary and mechanical only.**

> **The v004 admitted cohort is EXACTLY UNCHANGED.** 61,335 ticker-days · 76 sessions · 868 tickers ·
> 19,793,865 bar rows. The frozen store `I7_V004_ADMISSIBLE_v1.sqlite`
> (`e1375264…fba`) was **not rebuilt**. v003 (`a4a9f7f9…0e0`), v002, Dataset B, the registries and the
> production database are untouched. **I7 remains NOT registered and NOT executed.**

This document is issued as a **new dated record** rather than an edit to an existing one — which is also
the resolution of **R9**.

---

## R1 — X3 interpretation (documented; cohort unchanged)

### Operative interpretation

> **X3 operates as a session-level admission gate: a candidate session is admissible only if it is present
> in the effective session calendar with admitted status (`is_admitted = 1`). Sessions that the calendar
> evaluated and rejected, and sessions the calendar does not cover at all, are both excluded under X3.**

**Effective session calendar** = `DATASET_B_SESSION_CALENDAR_v2` (sha `5012be23…`, 386 sessions through
2026-08-27) **∪** `I7_SESSION_CALENDAR_EXTENSION_v1` (sha `a7a4eedf…`, 11 sessions 2026-08-28 → 2026-09-11).

### Why the effective-calendar formulation is the intended implementation of X3

The specification (`BRANCH_A_NEW_MECHANISM_AUDIT_2026-09-14.md` §8) words X3 as *"Non-admitted sessions per
`session_calendar.is_admitted = 0`"*. Three facts make membership the faithful implementation:

1. **The authoritative calendar artifact has no `is_admitted` column.** `DATASET_B_SESSION_CALENDAR_v2.json`
   carries a `sessions` list (admitted) and an `excluded` list. The `is_admitted` flag exists only in the
   derived convenience view `research_data/views_v1.sqlite::session_calendar`. The spec's phrasing names the
   *flag* in the view; the *artifact* expresses the same fact as list membership. `is_admitted = 1` and
   "present in `sessions`" are the same predicate over the same underlying decision.
2. **X3's purpose is admission, not enumeration.** Its role in §8 is to keep non-admitted sessions out of
   the cohort. A session the calendar never evaluated has, likewise, never been admitted — so admitting it
   would defeat the gate while formally satisfying its literal text.
3. **The stricter reading is the conservative one.** Where the two readings differ, membership excludes
   *more*. It cannot admit anything the literal reading would exclude.

### The two kinds, distinguished — as required

| Kind | Sessions | Evidence |
|---|---|---|
| **`is_admitted = 0`** — calendar evaluated and **rejected** | **2026-07-09**, **2026-07-24** | base artifact `excluded[]`, reason *"member price coverage below threshold"*; independently confirmed: only 137 and 134 tickers have `ohlcv` rows on those dates |
| **Absent from the effective calendar** — never evaluated | **2026-05-01, 05-14, 05-15, 05-28, 06-16** (non-trading days: **0** `ohlcv` tickers, absent from `trading_calendar`; the vendor nonetheless returned daily rows) and **2026-09-14** (beyond the frozen extension horizon — see R8) | independently verified against `ohlcv` and `trading_calendar` |

**Cohort effect: none beyond the single session the readiness review identified.** Verified by set
difference on the two frozen ledgers: in v003-admitted and not v004-admitted = `['2026-07-09']`; in
v004-admitted and not v003-admitted = `[]`. 62,162 − 827 = 61,335. The broader reading **relabelled** 6,211
already-excluded cells from E-PIT-2/3/4 to X3 and **admitted nothing new**.

**No minimum-session or minimum-cell rule was introduced.** Asserted by
`test_no_minimum_cell_rule_in_source` and `test_frozen_2026_09_08_retains_single_admitted_cell`.

---

## R2 — calendar predicate (fixed at source + proven)

**The defect.** `extend_session_calendar.py`'s docstring claimed the base rule was applied *"verbatim …
nothing added"*. **False.** `build_calendar_and_roster.py::build_calendar` has **four** gates; the extension
implemented **three** — `NAMED_EXCLUSIONS` was omitted.

**The fix, structural rather than textual.** New module
`i7_accrual/session_calendar_predicate.py` implements the rule once and **imports** `NAMED_EXCLUSIONS` and
`COVERAGE_THRESHOLD` from the base builder instead of copying them, so the predicate **cannot drift**.
`extend_session_calendar.py` now delegates to it (`evaluate_extension` → `SCP.admit`), the false claim is
removed from both the docstring and the artifact's `admission_rule.source` metadata, and the gate order is
recorded explicitly.

**The proof — the frozen artifact satisfies the FULL four-gate rule.**
`session_calendar_predicate.verify_extension_artifact()` re-evaluates 2026-08-28 → 2026-09-11 under all four
gates and compares against the frozen artifact:

| Check | Result |
|---|---|
| Admitted set | **identical — 11/11** |
| Excluded count | **identical — 0** |
| Every per-session coverage figure | **identical — all 1.0000** |
| `NAMED_EXCLUSIONS` members inside the window | **none** (its only member, 2026-08-25, is outside) |

Post-delegation dry run of `extend_session_calendar.py`: **11 admitted, 0 excluded** — unchanged.

**On byte-for-byte reproducibility, stated precisely.** The frozen artifact is **unchanged on disk**
(`a7a4eedf…`, verified). It is **not** byte-reproducible by re-running, because the builder stamps
`built_utc` and `git_commit` — that is true of the original code too and is not introduced here. What is
established is **decision-identity**: the artifact's admitted set, exclusions and coverages are exactly what
the corrected full-rule predicate produces. The artifact was deliberately **not** rebuilt.

---

## R5 — X3 tests (added)

`grep -c X3 test_i7_admissibility.py` returned **0** before this pass. New file `test_i7_x3.py`, **9 tests**,
all passing. Existing test semantics untouched.

| Test | Establishes |
|---|---|
| `test_is_admitted_zero_session_is_x3` | calendar-rejected session → X3 |
| `test_absent_from_calendar_session_is_x3` | absent session → X3 |
| `test_x3_precedes_epit_predicates` | **precedence** — cells that would be E-PIT-3/E-PIT-4 are labelled X3 when the session fails X3, and revert to their E-PIT labels once the session is admitted |
| `test_x3_session_cannot_be_admitted` | a perfectly-formed cell is still excluded if its session fails X3 |
| `test_frozen_2026_07_09_is_x3_excluded` | frozen cohort: 958 cells, 958 X3, 0 admitted, 0 bars |
| `test_frozen_2026_09_08_retains_single_admitted_cell` | single-cell session retained |
| `test_no_minimum_cell_rule_in_source` | no cells/sessions threshold in the accrual path |
| `test_x5_x6_not_applied_at_accrual` | AST: no `ohlcv`/`corporate_actions` in executable SQL; no dynamic SQL |
| `test_accrual_reads_only_provenance_and_bar_columns` | read surface whitelist |

Tests 1–4 and 7–9 run against **in-memory fixtures**, so they assert the *gate's* behaviour rather than one
dataset's contents — the distinction the audit drew between compliance tests and internal-consistency tests.

---

## R4 — executable validation (added)

`i7_accrual/validate_v004_freeze.py` — read-only, deterministic, non-zero on any discrepancy, emitting both
human-readable and machine-readable summaries. The seven documentation-only checks are now **eight
executable gates**:

| Gate | Validates |
|---|---|
| 1 `artifact_hashes` | store, manifest sidecar, extension + sidecar, and the two code hashes the manifest pins |
| 2 `v003_immutable` | v003 sha256 against the recorded anchor **and** `0o444` mode |
| 3 `ledger_reconciles` | MECE, duplicate-free, and every count equal to the manifest's |
| 4 `x3_exclusions` | no session both X3 and admitted; no X3 session is calendar-admitted; all 11 review sessions evaluable; 2026-07-09 fully excluded |
| 5 `no_pre_cutoff_admitted` | no same-day pre-16:15 admitted cell; every admitted lag ∈ {0,1} |
| 6 `result_blindness` | AST: no outcome token in executable SQL, no dynamic SQL |
| 7 `x1_to_x6_disposition` | all six spec exclusions carry a recorded disposition; X1/X2 subsumption is a date fact |
| 8 `calendar_from_source` *(opt-in `--with-source`)* | re-derives the calendar under the full four-gate rule |

Gates 1–7 depend only on frozen state. Only gate 8 touches production, and it is opt-in.

**Result: 8/8 PASS, exit 0.**

---

## R3 / R6 — documentation accuracy

### R3 — precise language on value vs presence

The v004 manifest states *"no close, return, or outcome column is read by the builder"*. True of the
builder; **incomplete** as an account of the pipeline. The precise statement, which supersedes it:

> **No value field participates in admission.** The accrual builder's entire executable read surface is
> `stockbit_flow(ticker, trade_date, updated_at)` and `stockbit_flow_bars(trade_date, COUNT(*))`. Bar value
> columns (`price`, `net_value`, `delta`) are read **only** when copying admitted cells, after admission is
> decided.
>
> **One presence check exists, in the calendar predicate, and it reads no value.** The base calendar's
> admission rule counts roster members having a **non-null** `ohlcv.close` for that session
> (`session_calendar_predicate.admit`). The close **value** is never read, compared, ranked or returned;
> only its existence is tested, and only for the session itself — no forward-dated row is touched. This is
> the base rule's own unchanged predicate, inherited, not introduced.

The frozen manifest string cannot be corrected without rebuilding v004, which is forbidden and unwarranted.
**This record supersedes it.**

### R6 — 2026-08-25 corrected

The v004 completion narrative listed 2026-08-25 among *"the three calendar-excluded dates"* removed by X3.
**That is wrong.** 2026-08-25 is `is_admitted = 0` in the base calendar, but it **produces no candidate cell
at all** — it has no bars and no qualifying daily row — so it appears **nowhere** in the v004 ledger and is
**not** an X3 exclusion. The X3 set is **eight** sessions, listed in R1, and 2026-08-25 is not among them.
Counts are unaffected; the narrative was.

---

## R7 — source-state provenance (recorded)

New artifact `store/I7_V004_SOURCE_PROVENANCE_v1.json` (+ `.sha256`, read-only). Every field is labelled
with its evidential strength, and **nothing is presented as a cryptographic content hash of the source**:

| Field | Strength | Value |
|---|---|---|
| Source size / mtime | **WEAK** — mutable, live | 13,722,992,640 bytes · 2026-09-14T12:00:42Z |
| Content hash | — | **deliberately not computed**: 13.7 GB, live, changes daily — stale before use |
| Schema fingerprint (sha256 over `sqlite_master` SQL for the two source tables) | **STRONG for schema, silent on content** | `cabe892cc70e87ab…` |
| Source extents (min/max `trade_date`, `stockbit_flow` row count) | **MODERATE** | pins the span, not the values |
| **Source-agreement spot check** | **STRONGEST AVAILABLE** | **200/200 sampled admitted cells agree** with the live source; 0 disagree |

The spot check is the load-bearing item: a deterministic, evenly-spaced sample of frozen admitted cells has
its bar count recomputed from production and compared to the frozen ledger.

**Reproducibility statement (recorded in the artifact):** v004 **cannot** be reproduced byte-for-byte from
recorded inputs — the source is mutable and unhashed and the builder stamps `built_utc`. It **can** be
re-derived in content for any cell whose source rows are unchanged, which the spot check evidences.
**This is inherent to accruing from a live vendor-fed table, not a defect introduced by v004**, and it is
precisely the gap the prospective capture service closes for future sessions.

---

## R8 — current-day handling

**2026-09-14 is excluded because it lies outside the frozen extension horizon (2026-08-28 → 2026-09-11),
i.e. by the effective-calendar boundary — not by any current-day rule.**

**No current-day rule exists and none was introduced.** Two facts, for the record:

- Had the horizon covered it, 2026-09-14 would still have been excluded — by **E-PIT-3**, since its capture
  is same-day pre-cutoff. Its exclusion is therefore over-determined, but the **operative** gate in v004 is
  the calendar boundary.
- In v003 the same session was labelled **E-PIT-3**. The v004 relabelling to X3 follows from session-gate
  precedence and changes no admitted cell.

---

## Files changed

| File | Change |
|---|---|
| `i7_accrual/session_calendar_predicate.py` | **new** — shared four-gate predicate; imports base constants; R2 proof function |
| `i7_accrual/test_i7_x3.py` | **new** — 9 X3 tests |
| `i7_accrual/validate_v004_freeze.py` | **new** — 8 executable gates |
| `i7_accrual/source_provenance.py` | **new** — R7 fingerprint builder |
| `i7_accrual/store/I7_V004_SOURCE_PROVENANCE_v1.json` (+ `.sha256`) | **new** — R7 artifact |
| `i7_accrual/extend_session_calendar.py` | **edited** — false "verbatim" claim removed; delegates to the shared predicate; metadata corrected. **Logic equivalence proven; artifact not rebuilt.** Its hash is recorded in no manifest, so no provenance link is broken |
| `I7_V004_REMEDIATION_RECORD_2026-09-14.md` | **new** — this record |

**Deliberately NOT touched:** `build_v004_freeze.py` and `i7_admissibility.py` — their sha256 values
(`187e71c0…`, `5e58745e…`) are **recorded in the frozen v004 manifest**; editing either would break the
artifact's provenance link. The frozen stores, registries, Dataset B, v002, v003 and the production database
are untouched.

---

## Remaining reservations

| # | Status |
|---|---|
| R1 | **CLOSED** — interpretation documented; cohort unchanged |
| R2 | **CLOSED** — predicate single-sourced; false claim removed; decision-identity proven |
| R3 | **CLOSED** — precise value-vs-presence language recorded here (frozen manifest string superseded, not rewritten) |
| R4 | **CLOSED** — 8 executable gates, 8/8 PASS |
| R5 | **CLOSED** — 9 X3 tests added |
| R6 | **CLOSED** — 2026-08-25 corrected |
| R7 | **MITIGATED, not eliminable** — strongest available fingerprint recorded; byte-reproducibility remains impossible while accruing from a live table. Must be declared at registration |
| R8 | **CLOSED** — boundary explanation recorded; no current-day rule introduced |
| R9 | **CLOSED** — issued as a new dated record |

**R7 is mitigated rather than closed, and should not be reported as closed.**

---

## Registration status

**Unchanged — I7 is NOT registered and NOT executed.** The two Owner decisions identified by
`I7_REGISTRATION_READINESS_REVIEW_2026-09-14.md` §9 remain outstanding and are untouched by this pass:

1. **D-1** — accept the population substitution (v004's 76 sessions are disjoint from the ~277 the
   specification describes).
2. **D-2** — supply the missing ex-ante MDE / σ / feasibility gate required by spec §13 and §G.2.

This remediation closed **audit and process** gaps. It did not, and could not, resolve either decision.
