# Phase E — Research Knowledge Base — Design Spec

**Date:** 2026-07-14
**Branch:** `ops/hardening-2026-07-10`
**Roadmap:** Research Master Plan v2 (FROZEN), Phase E. Prereqs A✅ B✅ C✅ D✅, R-10 enforcement✅.
**Status:** design only — no code until the implementation plan is approved.

---

## 1. Objective

Preserve every research experiment so nothing is orphaned and no failure is lost.
Negative results are first-class evidence. This pass builds the **missing spine** and
the **Failure Registry**, and unifies the already-existing research tables into a
traceable, queryable knowledge base — it does **not** re-materialize data that
`research_runs`, `gate_decisions`/`gate_evidence`, and `regime_profiles` already hold.

Serves master-plan completion criteria: *every experiment traceable end-to-end; every
rejection documented and preserved; the Failure Registry queryable by Phase F; no orphan
experiments.* Advances invariants 7 (traceable) and 8 (rejected hypotheses preserved).

## 2. Scope (locked in brainstorming)

**Build:** Hypothesis Library (the `hypothesis_id` spine) + Failure Registry + a
trace/query layer that unifies existing tables. The other three named outputs
(Experiment Registry, Validation Archive, Evidence Archive) are delivered as **query
views over existing tables**, not new storage.

**Do not build this pass:** all five registries as duplicated first-class tables; Phase F's
generator; any production change.

## 3. Architecture

New package **`research/knowledge/`**, mirroring `research/gatekeeper/` and
`research/regime/`. Read-only w.r.t. production: production may READ these tables
(dashboards), only `research/` WRITES them — enforced by the existing CI fence
(`tests/test_research_data_fence.py`). `engine/` must not import `research/` (existing
boundary guard). The two **evidence** tables (`hypothesis_links`, `failure_registry`) are
strictly **append-only**: no UPDATE, no DELETE; a superseding record is a new row. The
`hypotheses` table is append-only except for its `status`/`notes_json` label columns (§4.1).

```
research/knowledge/
  __init__.py
  models.py             Hypothesis, HypothesisLink, FailureRecord dataclasses + Status enum
  storage.py            idempotent DDL + append-only insert fns for the 3 new tables
  ingest.py             ingest_gate_rejects(); link-writing helpers
  trace.py              trace(hypothesis_id) evidence bundle; orphan_report()
  registries.py         Experiment / Validation / Evidence registries as query views
  backfill.py           seed known hypotheses + back-link existing rows by fingerprint
  cli.py                record-hypothesis | record-failure | trace | orphans | backfill | list-failures
  knowledge_config.yaml pre-registered: status vocabulary + orphan-scope table list + version
tests/knowledge/        mirrors tests/gatekeeper/
```

Connection handling mirrors gatekeeper `storage.py`: `ensure_*_table(conn)` creates
schema idempotently (schema-safety `CREATE TABLE IF NOT EXISTS` is allowed in any scope by
the fence); insert helpers mint a fresh `uuid4().hex` id per call.

## 4. Data model — three new append-only tables

### 4.1 `hypotheses` (Hypothesis Library)

```sql
CREATE TABLE IF NOT EXISTS hypotheses (
    hypothesis_id       TEXT PRIMARY KEY,   -- caller-supplied stable id (e.g. NR7_BULL_v1)
    title               TEXT NOT NULL,
    rationale           TEXT,               -- why this hypothesis is worth testing
    origin              TEXT,               -- manual | mutation | regime_scan | ...
    status              TEXT NOT NULL,      -- see §7 vocabulary
    dataset_fingerprint TEXT,
    config_hash         TEXT,
    git_commit          TEXT,
    prereg_ref          TEXT,               -- path/hash of a pre-registration doc, if any
    proposed_at         TEXT NOT NULL,
    notes_json          TEXT
)
```

`hypothesis_id` is the **caller-supplied stable identifier** (not a random uuid) so it can
be referenced across phases and pre-registration docs. Re-recording an existing id raises
(the PK already exists); a second `record_hypothesis` with the same id is an error, not a
silent overwrite.

**Mutability exception:** `hypotheses` is the one table that is *not* strictly append-only —
`status` and `notes_json` may be UPDATEd in place (a hypothesis's lifecycle label is a
mutable rollup, not evidence). Every **evidence** store (`hypothesis_links`,
`failure_registry`, and the existing `research_runs`/`gate_decisions`) remains strictly
append-only: no UPDATE, no DELETE. This confines the mutable surface to a single label
column and keeps all evidence immutable. Status *transition history* (an audit of past
statuses) is a non-goal this pass — only the current status is kept (see §7, §12).

### 4.2 `hypothesis_links` (the spine)

```sql
CREATE TABLE IF NOT EXISTS hypothesis_links (
    link_id           TEXT PRIMARY KEY,     -- uuid4 per link
    hypothesis_id     TEXT NOT NULL,
    source_table      TEXT NOT NULL,        -- research_runs | gate_decisions | regime_profiles | failure_registry
    source_id         TEXT NOT NULL,        -- PK of the row in source_table (run_id / decision_id / ...)
    source_fingerprint TEXT,                -- fingerprint/config_hash for back-linking legacy rows
    linked_at         TEXT NOT NULL
)
```

Ties scattered evidence to one hypothesis **without altering the source tables**. New
experiments write a link row at record time; existing rows are back-linked by their known
`source_id`/fingerprint (§8). Uniqueness of `(hypothesis_id, source_table, source_id)` is
enforced by an idempotent guard in the writer (check-before-insert), keeping the table
append-only while making link-writing safe to re-run.

### 4.3 `failure_registry` (Failure Registry)

```sql
CREATE TABLE IF NOT EXISTS failure_registry (
    failure_id     TEXT PRIMARY KEY,        -- uuid4
    hypothesis_id  TEXT,                     -- nullable: a failure may precede a formal hypothesis id
    reject_reason  TEXT NOT NULL,
    failing_stage  TEXT,                     -- the gate stage that failed, if gate-sourced
    source         TEXT NOT NULL,            -- 'gate' | 'manual'
    evidence_ref   TEXT,                     -- decision_id (gate) or free ref (manual)
    fingerprint    TEXT,                     -- dedupe key
    recorded_at    TEXT NOT NULL
)
```

Dedupe key = `(fingerprint, failing_stage)` for gate-sourced rows; manual rows dedupe on
`(hypothesis_id, reject_reason)` unless a fingerprint is supplied.

## 5. Failure ingestion — hybrid (auto + manual)

- **`ingest_gate_rejects(conn)`** — scans `gate_decisions WHERE final_state='REJECT'`.
  For each not already represented (dedupe on the decision's fingerprint + `failing_stage`),
  inserts one `failure_registry` row (`source='gate'`, `evidence_ref=decision_id`,
  `reject_reason` derived from `failing_stage`/`summary_json`) **and** a `hypothesis_links`
  row (`source_table='failure_registry'`) when the decision resolves to a known
  `hypothesis_id`. Idempotent: re-running inserts nothing new.
- **`record_failure(conn, hypothesis_id, reject_reason, ...)`** — manual channel for
  pre-gate / non-gate deaths (e.g. the flow-edge study, which predates the gate). `source='manual'`.

Nothing that goes through the gate can be silently lost; the registry is not limited to
gate output.

## 6. Trace layer + orphan guarantee

- **`trace(conn, hypothesis_id) -> dict`** — assembles the full bundle by joining through
  `hypothesis_links`: `{hypothesis, experiments:[research_runs], decisions:[gate_decisions
  + their gate_evidence], regime_profiles:[...], failures:[...]}`. This is the end-to-end
  traceability deliverable.
- **`orphan_report(conn) -> {gate_decisions:[...], research_runs:[...]}`** — every row in
  the orphan-scope tables (from `knowledge_config.yaml`) with **no** `hypothesis_links`
  entry. This operationalizes "no orphan experiments."
  **Posture: advisory.** Exposed as an API and asserted by a test that the current corpus
  **after backfill** has zero orphans; it is *not* a CI-hard block on future production
  builds (consistent with the research-package posture — the DSR gate is advisory, and
  R-10's hard gate was specifically registry lifecycle, not the research ledger).

## 7. Hypothesis status

Stored field on `hypotheses`, **researcher-declared** (not auto-derived), updated in place
via `set_status(conn, hypothesis_id, status)` — the sanctioned mutation of §4.1. Vocabulary
mirrors the existing gate/phase5 language:

```
PROPOSED -> UNDER_TEST -> { WATCHLIST | FORWARD_TESTING | REJECTED | VALIDATED }
```

`set_status` rejects any value outside the vocabulary. Defined in `knowledge_config.yaml`
(pre-registered, versioned). A helper
**`check_status_consistency(conn, hypothesis_id)`** flags contradictions between the
declared status and the linked evidence — e.g. `status=VALIDATED` while a linked
`gate_decision.final_state=REJECT`, or `status=REJECTED` with no failure row. Advisory
flag, not an enforced transition. A full status-history/audit table is a non-goal this pass.

## 8. Backfill

`backfill.py` seeds the two live hypotheses and back-links their existing evidence:

- **`NR7_BULL_v1`** — governs `approved_universe`; its Phase C gate verdict is REJECT at
  walk_forward. Back-link its `gate_decisions` rows (e.g. fingerprint `0d017509`) and its
  `regime_profiles`. Its REJECT decision also flows into `failure_registry` via
  `ingest_gate_rejects`.
- **`NR7_BULL_LOWLIQ_v1`** — the pre-registered (REGISTERED-UNCONFIRMED) BULL∧LOW_LIQ
  hypothesis; link its prereg doc (`prereg_ref`) and its `regime_profiles`.
- One **manual failure seed** (flow-edge study, "no edge, mega+mid caps") to exercise the
  manual channel.

Broader historical backfill of pre-gate studies is deferred. Completion check for the
backfill: `orphan_report` returns zero orphans over the seeded corpus.

## 9. The three registries as query views (no new storage)

`registries.py` exposes a stable, documented query API so Phase F/G consume a fixed
surface rather than raw SQL:

- **Experiment Registry** — query view over `research_runs`.
- **Validation Archive** — query view over `gate_decisions` (PROMOTE/WATCHLIST/validated outcomes).
- **Evidence Archive** — query view over `gate_evidence`.

## 10. Write-fence + boundaries

Add `hypotheses`, `hypothesis_links`, `failure_registry` to `RESEARCH_TABLES` in
`tests/test_research_data_fence.py` so production write attempts fail CI. No `engine/`→
`research/` import introduced (existing architecture guard stays green).

## 11. Testing (TDD, subagent-driven — mirrors C/D/R-10)

`tests/knowledge/`:

1. schema idempotency (`ensure_*` twice is safe).
2. append-only (evidence): `hypothesis_links`/`failure_registry` inserts mint new ids; no
   UPDATE/DELETE code paths touch them. `set_status`/`notes` UPDATE `hypotheses` only, and
   `set_status` rejects an out-of-vocabulary value.
3. `ingest_gate_rejects` derives a failure + link from a REJECT decision.
4. ingest idempotency: second run inserts nothing (dedupe by fingerprint+stage).
5. `record_failure` manual path (`source='manual'`).
6. `trace` assembles hypothesis + experiments + decisions(+evidence) + regime + failures.
7. `orphan_report` detects an unlinked `gate_decisions` row (positive) and returns empty
   after linking (negative).
8. backfill → `orphan_report` empty over the seeded corpus.
9. `check_status_consistency` flags `VALIDATED`-over-`REJECT`.
10. `knowledge_config.yaml` version assertion; status vocabulary present.
11. fence test lists the three new tables (guard the guard).

Full suite must stay green (Phase D baseline 1464 passed + new knowledge tests). No
production behavior change.

## 12. Non-goals

- Mutating or migrating existing tables (append-only; spine is a separate mapping table).
- Making promotion decisions — that is Phase C.
- Storing production execution data.
- Building Phase F's generator/mutation engine (only the failure store it will consume).
- A status-history/audit table or auto-derived status transitions.

## 13. Deliverables

- `research/knowledge/` package (9 modules + `knowledge_config.yaml`).
- Three new tables in `walkforward.db` (`hypothesis_links`/`failure_registry` append-only;
  `hypotheses` append-only except `status`/`notes_json`).
- `tests/knowledge/` suite; extended `RESEARCH_TABLES` fence.
- Backfill of the two live hypotheses + one manual failure seed; zero orphans over that corpus.
- No production change; committed on `ops/hardening-2026-07-10` (not pushed), per the phase pattern.
