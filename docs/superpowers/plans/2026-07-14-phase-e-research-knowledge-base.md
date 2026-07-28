# Phase E — Research Knowledge Base Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `research/knowledge/` package that preserves every research experiment — a Hypothesis Library spine + Failure Registry + trace/orphan layer — unifying the existing `research_runs`/`gate_decisions`/`regime_profiles` tables without altering them.

**Architecture:** Mirrors `research/gatekeeper/` and `research/regime/`: idempotent DDL in `storage.py`, a pre-registered `knowledge_config.yaml` + typed `config.py`, append-only evidence tables, CI write-fence. A separate `hypothesis_links` mapping table ties scattered evidence to one `hypothesis_id`; the only mutable field is a hypothesis's `status`/`notes`. Read-only w.r.t. production; only `research/` writes these tables.

**Tech Stack:** Python 3, sqlite via `data.db.connect`, `dataclasses`, `pyyaml`, `pytest`.

**Spec:** `docs/superpowers/specs/2026-07-14-phase-e-research-knowledge-base-design.md`

**Baseline:** full suite 1464 passed (Phase D). Branch `ops/hardening-2026-07-10`. No production change; commit per task.

> **Amendment A1 (2026-07-14):** Task 11 added per Research Master Plan v3 DRAFT
> §3.4a (adversarial finding V3-4 — receipt-bound status transitions). Tasks 1–10
> are unchanged. Task 11 runs **after** Task 10. See
> `docs/RESEARCH_MASTER_PLAN_V3_DRAFT.md`.

---

## File Structure

- Create `research/knowledge/__init__.py` — package marker.
- Create `research/knowledge/knowledge_config.yaml` — pre-registered: version, status vocabulary, orphan-scope tables.
- Create `research/knowledge/config.py` — `KnowledgeConfig` dataclass + `load_config`.
- Create `research/knowledge/models.py` — `Status` enum, `Hypothesis`, `FailureRecord` dataclasses.
- Create `research/knowledge/storage.py` — DDL + `ensure_knowledge_tables`, hypothesis writes, link writer, failure insert, low-level readers.
- Create `research/knowledge/ingest.py` — `ingest_gate_rejects`, `record_failure`.
- Create `research/knowledge/trace.py` — `trace`, `orphan_report`, `check_status_consistency`.
- Create `research/knowledge/registries.py` — `experiment_registry`, `validation_archive`, `evidence_archive`.
- Create `research/knowledge/backfill.py` — `seed_known_hypotheses`.
- Create `research/knowledge/cli.py` — argparse subcommands.
- Create `tests/knowledge/__init__.py` and one test module per source module.
- Modify `tests/test_research_data_fence.py:22-24` — add the three new tables to `RESEARCH_TABLES`.

---

## Task 1: Knowledge config (yaml + typed loader)

**Files:**
- Create: `research/knowledge/__init__.py` (empty)
- Create: `research/knowledge/knowledge_config.yaml`
- Create: `research/knowledge/config.py`
- Create: `tests/knowledge/__init__.py` (empty)
- Test: `tests/knowledge/test_config.py`

- [ ] **Step 1: Create the package markers and config yaml**

`research/knowledge/__init__.py`: empty file.
`tests/knowledge/__init__.py`: empty file.
`research/knowledge/knowledge_config.yaml`:

```yaml
# Pre-registered knowledge-base configuration (Phase E).
# version bumps whenever the status vocabulary or orphan scope changes.
version: 1
statuses:
  - PROPOSED
  - UNDER_TEST
  - WATCHLIST
  - FORWARD_TESTING
  - REJECTED
  - VALIDATED
# Tables an experiment must be linked into to avoid being an "orphan".
orphan_scope:
  - research_runs
  - gate_decisions
```

- [ ] **Step 2: Write the failing test**

`tests/knowledge/test_config.py`:

```python
"""Phase E knowledge config: typed load of knowledge_config.yaml."""
from research.knowledge import config as cfg


def test_load_config_defaults():
    c = cfg.load_config()
    assert c.version == 1
    assert c.statuses == ["PROPOSED", "UNDER_TEST", "WATCHLIST",
                          "FORWARD_TESTING", "REJECTED", "VALIDATED"]
    assert c.orphan_scope == ["research_runs", "gate_decisions"]
    assert c.source_path.endswith("knowledge_config.yaml")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/knowledge/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: research.knowledge.config`

- [ ] **Step 4: Write `research/knowledge/config.py`**

```python
"""Knowledge-base configuration (Phase E, spec §7): typed load of
knowledge_config.yaml. Pre-registered — the status vocabulary and orphan scope
are fixed before use; changing them bumps `version`."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import yaml

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "knowledge_config.yaml")


@dataclass
class KnowledgeConfig:
    version: int
    statuses: list
    orphan_scope: list
    source_path: str = field(default="", compare=False)


def load_config(path: str = None) -> KnowledgeConfig:
    """Load knowledge_config.yaml into a KnowledgeConfig. Defaults to the shipped file."""
    path = path or DEFAULT_CONFIG_PATH
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return KnowledgeConfig(
        version=int(raw["version"]),
        statuses=list(raw["statuses"]),
        orphan_scope=list(raw["orphan_scope"]),
        source_path=path)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/knowledge/test_config.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add research/knowledge/__init__.py research/knowledge/knowledge_config.yaml \
        research/knowledge/config.py tests/knowledge/__init__.py tests/knowledge/test_config.py
git commit -m "feat(knowledge): Phase E config — status vocabulary + orphan scope"
```

---

## Task 2: Models (Status enum + dataclasses)

**Files:**
- Create: `research/knowledge/models.py`
- Test: `tests/knowledge/test_models.py`

- [ ] **Step 1: Write the failing test**

`tests/knowledge/test_models.py`:

```python
"""Phase E models: Status vocabulary + Hypothesis / FailureRecord dataclasses."""
from research.knowledge.models import FailureRecord, Hypothesis, Status


def test_status_values_match_config_vocabulary():
    assert Status.PROPOSED == "PROPOSED"
    assert {s.value for s in Status} == {
        "PROPOSED", "UNDER_TEST", "WATCHLIST",
        "FORWARD_TESTING", "REJECTED", "VALIDATED"}


def test_hypothesis_defaults():
    h = Hypothesis(hypothesis_id="NR7_BULL_v1", title="NR7 BULL breakout edge")
    assert h.status == Status.PROPOSED
    assert h.origin == "manual"
    assert h.rationale == ""


def test_failure_record_requires_source():
    f = FailureRecord(hypothesis_id="H1", reject_reason="no edge", source="manual")
    assert f.failing_stage is None
    assert f.source == "manual"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/knowledge/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: research.knowledge.models`

- [ ] **Step 3: Write `research/knowledge/models.py`**

```python
"""Phase E data models (spec §4, §7). str-valued enum so DB rows and comparisons
stay plain text; dataclasses carry the row shape for the writers in storage.py."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    PROPOSED = "PROPOSED"
    UNDER_TEST = "UNDER_TEST"
    WATCHLIST = "WATCHLIST"
    FORWARD_TESTING = "FORWARD_TESTING"
    REJECTED = "REJECTED"
    VALIDATED = "VALIDATED"


@dataclass
class Hypothesis:
    hypothesis_id: str
    title: str
    status: str = Status.PROPOSED
    rationale: str = ""
    origin: str = "manual"
    dataset_fingerprint: str = None
    config_hash: str = None
    git_commit: str = None
    prereg_ref: str = None
    proposed_at: str = None
    notes: dict = None


@dataclass
class FailureRecord:
    hypothesis_id: str          # may be None for a pre-hypothesis failure
    reject_reason: str
    source: str                 # 'gate' | 'manual'
    failing_stage: str = None
    evidence_ref: str = None    # decision_id (gate) or free ref (manual)
    fingerprint: str = None     # dedupe key
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/knowledge/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add research/knowledge/models.py tests/knowledge/test_models.py
git commit -m "feat(knowledge): Status enum + Hypothesis/FailureRecord models"
```

---

## Task 3: Storage — schema + hypothesis writes

**Files:**
- Create: `research/knowledge/storage.py`
- Test: `tests/knowledge/test_storage_hypotheses.py`

- [ ] **Step 1: Write the failing test**

`tests/knowledge/test_storage_hypotheses.py`:

```python
"""Phase E storage — schema idempotency + hypotheses writes (spec §4.1)."""
import pytest

from data.db import connect
from research.knowledge import storage
from research.knowledge.models import Hypothesis, Status


def test_ensure_knowledge_tables_is_idempotent(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    storage.ensure_knowledge_tables(conn)          # must not raise
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"hypotheses", "hypothesis_links", "failure_registry"} <= tables
    conn.close()


def test_record_and_get_hypothesis(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    storage.record_hypothesis(conn, Hypothesis(
        hypothesis_id="NR7_BULL_v1", title="NR7 BULL edge", rationale="liq-conditional"))
    row = storage.get_hypothesis(conn, "NR7_BULL_v1")
    assert row["hypothesis_id"] == "NR7_BULL_v1"
    assert row["status"] == "PROPOSED"
    assert row["rationale"] == "liq-conditional"
    assert row["proposed_at"]                       # auto-stamped
    conn.close()


def test_record_duplicate_hypothesis_id_raises(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    storage.record_hypothesis(conn, Hypothesis(hypothesis_id="H1", title="a"))
    with pytest.raises(Exception):
        storage.record_hypothesis(conn, Hypothesis(hypothesis_id="H1", title="b"))
    conn.close()


def test_set_status_updates_valid_value(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    storage.record_hypothesis(conn, Hypothesis(hypothesis_id="H1", title="a"))
    storage.set_status(conn, "H1", Status.REJECTED)
    assert storage.get_hypothesis(conn, "H1")["status"] == "REJECTED"
    conn.close()


def test_set_status_rejects_out_of_vocabulary(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    storage.record_hypothesis(conn, Hypothesis(hypothesis_id="H1", title="a"))
    with pytest.raises(ValueError):
        storage.set_status(conn, "H1", "BOGUS")
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/knowledge/test_storage_hypotheses.py -v`
Expected: FAIL with `ModuleNotFoundError: research.knowledge.storage`

- [ ] **Step 3: Write `research/knowledge/storage.py` (schema + hypotheses portion)**

```python
"""Phase E persistence (spec §4). Three tables in walkforward.db, created
idempotently. Evidence tables (hypothesis_links, failure_registry) are strictly
append-only: no UPDATE, no DELETE. `hypotheses` is append-only EXCEPT its
status/notes_json label columns (spec §4.1, §7). Production may READ; only
research/ WRITES (CI-fenced by tests/test_research_data_fence.py)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime

from research.knowledge.models import Status

HYPOTHESES_DDL = """
CREATE TABLE IF NOT EXISTS hypotheses (
    hypothesis_id       TEXT PRIMARY KEY,
    title               TEXT NOT NULL,
    rationale           TEXT,
    origin              TEXT,
    status              TEXT NOT NULL,
    dataset_fingerprint TEXT,
    config_hash         TEXT,
    git_commit          TEXT,
    prereg_ref          TEXT,
    proposed_at         TEXT NOT NULL,
    notes_json          TEXT
)
"""

HYPOTHESIS_LINKS_DDL = """
CREATE TABLE IF NOT EXISTS hypothesis_links (
    link_id            TEXT PRIMARY KEY,
    hypothesis_id      TEXT NOT NULL,
    source_table       TEXT NOT NULL,
    source_id          TEXT NOT NULL,
    source_fingerprint TEXT,
    linked_at          TEXT NOT NULL
)
"""

FAILURE_REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS failure_registry (
    failure_id     TEXT PRIMARY KEY,
    hypothesis_id  TEXT,
    reject_reason  TEXT NOT NULL,
    failing_stage  TEXT,
    source         TEXT NOT NULL,
    evidence_ref   TEXT,
    fingerprint    TEXT,
    recorded_at    TEXT NOT NULL
)
"""

_VALID_STATUSES = {s.value for s in Status}


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_knowledge_tables(conn) -> None:
    conn.execute(HYPOTHESES_DDL)
    conn.execute(HYPOTHESIS_LINKS_DDL)
    conn.execute(FAILURE_REGISTRY_DDL)
    conn.commit()


def record_hypothesis(conn, hyp) -> str:
    """Insert one hypotheses row. Raises if the hypothesis_id already exists
    (append-only identity — no silent overwrite). Returns the hypothesis_id."""
    status = hyp.status.value if isinstance(hyp.status, Status) else str(hyp.status)
    if status not in _VALID_STATUSES:
        raise ValueError(f"invalid status {status!r}; allowed {_VALID_STATUSES}")
    conn.execute(
        "INSERT INTO hypotheses (hypothesis_id, title, rationale, origin, status, "
        "dataset_fingerprint, config_hash, git_commit, prereg_ref, proposed_at, "
        "notes_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (hyp.hypothesis_id, hyp.title, hyp.rationale, hyp.origin, status,
         hyp.dataset_fingerprint, hyp.config_hash, hyp.git_commit, hyp.prereg_ref,
         hyp.proposed_at or _now(),
         json.dumps(hyp.notes) if hyp.notes else None))
    conn.commit()
    return hyp.hypothesis_id


def get_hypothesis(conn, hypothesis_id):
    """Return the hypotheses row as a dict, or None."""
    cur = conn.execute("SELECT * FROM hypotheses WHERE hypothesis_id=?",
                       (hypothesis_id,))
    row = cur.fetchone()
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def set_status(conn, hypothesis_id, status) -> None:
    """The one sanctioned mutation (spec §4.1/§7): update a hypothesis's label."""
    value = status.value if isinstance(status, Status) else str(status)
    if value not in _VALID_STATUSES:
        raise ValueError(f"invalid status {value!r}; allowed {_VALID_STATUSES}")
    conn.execute("UPDATE hypotheses SET status=? WHERE hypothesis_id=?",
                 (value, hypothesis_id))
    conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/knowledge/test_storage_hypotheses.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add research/knowledge/storage.py tests/knowledge/test_storage_hypotheses.py
git commit -m "feat(knowledge): storage schema + hypotheses writes (status-mutable, evidence append-only)"
```

---

## Task 4: Storage — links + failures

**Files:**
- Modify: `research/knowledge/storage.py` (append functions)
- Test: `tests/knowledge/test_storage_links_failures.py`

- [ ] **Step 1: Write the failing test**

`tests/knowledge/test_storage_links_failures.py`:

```python
"""Phase E storage — idempotent link writer + failure insert (spec §4.2, §4.3)."""
from data.db import connect
from research.knowledge import storage
from research.knowledge.models import FailureRecord


def _conn(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    return conn


def test_add_link_inserts_once_and_is_idempotent(tmp_path):
    conn = _conn(tmp_path)
    lid = storage.add_link(conn, "H1", "gate_decisions", "dec1", "fp1")
    assert lid is not None
    again = storage.add_link(conn, "H1", "gate_decisions", "dec1", "fp1")
    assert again is None                                # dedup: no second row
    n = conn.execute("SELECT COUNT(*) FROM hypothesis_links").fetchone()[0]
    assert n == 1
    conn.close()


def test_add_link_distinguishes_source_rows(tmp_path):
    conn = _conn(tmp_path)
    storage.add_link(conn, "H1", "gate_decisions", "dec1")
    storage.add_link(conn, "H1", "research_runs", "run1")
    n = conn.execute("SELECT COUNT(*) FROM hypothesis_links").fetchone()[0]
    assert n == 2
    conn.close()


def test_insert_failure_and_dedupe_by_fingerprint_stage(tmp_path):
    conn = _conn(tmp_path)
    f = FailureRecord(hypothesis_id="H1", reject_reason="gate REJECT at walk_forward",
                      source="gate", failing_stage="walk_forward",
                      evidence_ref="dec1", fingerprint="dec1")
    fid = storage.insert_failure(conn, f)
    assert fid is not None
    dup = storage.insert_failure(conn, f)               # same fingerprint+stage
    assert dup is None
    n = conn.execute("SELECT COUNT(*) FROM failure_registry").fetchone()[0]
    assert n == 1
    conn.close()


def test_insert_manual_failure_dedupe_by_reason(tmp_path):
    conn = _conn(tmp_path)
    f = FailureRecord(hypothesis_id="FLOW", reject_reason="no edge (mega+mid caps)",
                      source="manual")
    assert storage.insert_failure(conn, f) is not None
    assert storage.insert_failure(conn, f) is None      # same (hypothesis, reason)
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/knowledge/test_storage_links_failures.py -v`
Expected: FAIL with `AttributeError: module ... has no attribute 'add_link'`

- [ ] **Step 3: Append to `research/knowledge/storage.py`**

```python
def _link_exists(conn, hypothesis_id, source_table, source_id) -> bool:
    return conn.execute(
        "SELECT 1 FROM hypothesis_links WHERE hypothesis_id=? AND source_table=? "
        "AND source_id=? LIMIT 1",
        (hypothesis_id, source_table, source_id)).fetchone() is not None


def add_link(conn, hypothesis_id, source_table, source_id, source_fingerprint=None):
    """Append one hypothesis_links row unless (hypothesis_id, source_table,
    source_id) already exists. Returns the new link_id, or None if it was a dedup
    no-op — keeps the table append-only while making re-linking safe to re-run."""
    if _link_exists(conn, hypothesis_id, source_table, source_id):
        return None
    link_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO hypothesis_links (link_id, hypothesis_id, source_table, "
        "source_id, source_fingerprint, linked_at) VALUES (?,?,?,?,?,?)",
        (link_id, hypothesis_id, source_table, source_id, source_fingerprint, _now()))
    conn.commit()
    return link_id


def _failure_exists(conn, f) -> bool:
    if f.source == "gate":
        return conn.execute(
            "SELECT 1 FROM failure_registry WHERE source='gate' AND fingerprint=? "
            "AND IFNULL(failing_stage,'')=IFNULL(?,'') LIMIT 1",
            (f.fingerprint, f.failing_stage)).fetchone() is not None
    # manual: dedupe on (hypothesis_id, reject_reason) unless a fingerprint is given
    if f.fingerprint:
        return conn.execute(
            "SELECT 1 FROM failure_registry WHERE fingerprint=? LIMIT 1",
            (f.fingerprint,)).fetchone() is not None
    return conn.execute(
        "SELECT 1 FROM failure_registry WHERE IFNULL(hypothesis_id,'')=IFNULL(?,'') "
        "AND reject_reason=? LIMIT 1",
        (f.hypothesis_id, f.reject_reason)).fetchone() is not None


def insert_failure(conn, f):
    """Append one failure_registry row unless a matching one exists (dedup rule in
    _failure_exists). Returns the new failure_id, or None on a dedup no-op."""
    if _failure_exists(conn, f):
        return None
    failure_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO failure_registry (failure_id, hypothesis_id, reject_reason, "
        "failing_stage, source, evidence_ref, fingerprint, recorded_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (failure_id, f.hypothesis_id, f.reject_reason, f.failing_stage, f.source,
         f.evidence_ref, f.fingerprint, _now()))
    conn.commit()
    return failure_id
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/knowledge/test_storage_links_failures.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add research/knowledge/storage.py tests/knowledge/test_storage_links_failures.py
git commit -m "feat(knowledge): idempotent link writer + deduped failure insert"
```

---

## Task 5: Ingest — gate REJECTs + manual failures

**Files:**
- Create: `research/knowledge/ingest.py`
- Test: `tests/knowledge/test_ingest.py`

- [ ] **Step 1: Write the failing test**

`tests/knowledge/test_ingest.py`:

```python
"""Phase E ingest — auto-derive failures from gate REJECTs (idempotent) + manual
channel (spec §5). Uses the real gatekeeper storage to build a gate_decisions row."""
from data.db import connect
from research.gatekeeper import storage as gk
from research.gatekeeper.models import (FinalState, GateDecision, StageResult,
                                        Verdict)
from research.knowledge import ingest, storage


def _reject_decision(conn):
    gk.ensure_gate_tables(conn)
    results = [StageResult("walk_forward", Verdict.FAIL, {"consistency_pct": 46.8},
                           {"min_consistency_pct": 50})]
    d = GateDecision(final_state=FinalState.REJECT, failing_stage="walk_forward",
                     stage_results=results, candidate_hash="c", config_hash="cfg",
                     dataset_fingerprint="fp", git_commit="g", seed=1,
                     forward_test_rule=None, run_id="run1", strategy_fn="NR7 Breakout")
    return gk.persist_decision(conn, d)


def test_ingest_gate_rejects_creates_failure_and_is_idempotent(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    _reject_decision(conn)
    n1 = ingest.ingest_gate_rejects(conn)
    assert n1 == 1
    n2 = ingest.ingest_gate_rejects(conn)               # re-run: nothing new
    assert n2 == 0
    row = conn.execute("SELECT source, failing_stage FROM failure_registry").fetchone()
    assert row == ("gate", "walk_forward")
    conn.close()


def test_ingest_links_failure_when_resolver_maps_hypothesis(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    dec_id = _reject_decision(conn)
    ingest.ingest_gate_rejects(conn, resolve=lambda row: "NR7_BULL_v1")
    # both the failure row and the gate decision are linked to the hypothesis
    tables = {r[0] for r in conn.execute(
        "SELECT source_table FROM hypothesis_links WHERE hypothesis_id='NR7_BULL_v1'")}
    assert tables == {"failure_registry", "gate_decisions"}
    fr = conn.execute("SELECT hypothesis_id, evidence_ref FROM failure_registry"
                      ).fetchone()
    assert fr == ("NR7_BULL_v1", dec_id)
    conn.close()


def test_record_failure_manual(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    fid = ingest.record_failure(conn, "FLOW", "no edge (mega+mid caps)")
    assert fid is not None
    row = conn.execute("SELECT source FROM failure_registry WHERE failure_id=?",
                       (fid,)).fetchone()
    assert row[0] == "manual"
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/knowledge/test_ingest.py -v`
Expected: FAIL with `ModuleNotFoundError: research.knowledge.ingest`

- [ ] **Step 3: Write `research/knowledge/ingest.py`**

```python
"""Phase E ingestion (spec §5). Hybrid failure feed: auto-derive one failure per
gate REJECT decision (idempotent, deduped on the decision's fingerprint), plus a
manual channel for pre-gate / non-gate deaths."""
from __future__ import annotations

from research.knowledge import storage
from research.knowledge.models import FailureRecord


def ingest_gate_rejects(conn, resolve=None) -> int:
    """Scan gate_decisions for final_state='REJECT'. For each not already in the
    failure_registry, append a failure row (source='gate', fingerprint=decision_id
    so re-ingest is a no-op) and, when `resolve(row)->hypothesis_id` returns an id,
    link both the failure and the gate decision to it. Returns the count of new
    failures. `resolve` defaults to None (unlinked failure, hypothesis_id NULL)."""
    rows = conn.execute(
        "SELECT decision_id, failing_stage, strategy_fn FROM gate_decisions "
        "WHERE final_state='REJECT'").fetchall()
    created = 0
    for decision_id, failing_stage, strategy_fn in rows:
        hyp = resolve({"decision_id": decision_id, "strategy_fn": strategy_fn,
                       "failing_stage": failing_stage}) if resolve else None
        f = FailureRecord(
            hypothesis_id=hyp,
            reject_reason=f"gate REJECT at {failing_stage}" if failing_stage
            else "gate REJECT",
            source="gate", failing_stage=failing_stage,
            evidence_ref=decision_id, fingerprint=decision_id)
        fid = storage.insert_failure(conn, f)
        if fid is not None:
            created += 1
            if hyp:
                storage.add_link(conn, hyp, "failure_registry", fid, decision_id)
        if hyp:
            storage.add_link(conn, hyp, "gate_decisions", decision_id)
    return created


def record_failure(conn, hypothesis_id, reject_reason, failing_stage=None,
                   evidence_ref=None, fingerprint=None):
    """Manual failure channel (source='manual'). Returns the failure_id, or None on
    a dedup no-op. Links to the hypothesis when one is supplied."""
    f = FailureRecord(hypothesis_id=hypothesis_id, reject_reason=reject_reason,
                      source="manual", failing_stage=failing_stage,
                      evidence_ref=evidence_ref, fingerprint=fingerprint)
    fid = storage.insert_failure(conn, f)
    if fid is not None and hypothesis_id:
        storage.add_link(conn, hypothesis_id, "failure_registry", fid, fingerprint)
    return fid
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/knowledge/test_ingest.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add research/knowledge/ingest.py tests/knowledge/test_ingest.py
git commit -m "feat(knowledge): hybrid failure ingest — gate REJECTs + manual channel"
```

---

## Task 6: Trace + orphan report + status consistency

**Files:**
- Create: `research/knowledge/trace.py`
- Test: `tests/knowledge/test_trace.py`

- [ ] **Step 1: Write the failing test**

`tests/knowledge/test_trace.py`:

```python
"""Phase E trace bundle + orphan report + status-consistency flag (spec §6, §7)."""
from data.db import connect
from research.gatekeeper import storage as gk
from research.gatekeeper.models import (FinalState, GateDecision, StageResult,
                                        Verdict)
from research.knowledge import ingest, storage, trace
from research.knowledge.models import Hypothesis, Status


def _reject_decision(conn, run_id="run1"):
    gk.ensure_gate_tables(conn)
    d = GateDecision(final_state=FinalState.REJECT, failing_stage="walk_forward",
                     stage_results=[StageResult("walk_forward", Verdict.FAIL, {}, {})],
                     candidate_hash="c", config_hash="cfg", dataset_fingerprint="fp",
                     git_commit="g", seed=1, forward_test_rule=None, run_id=run_id,
                     strategy_fn="NR7 Breakout")
    return gk.persist_decision(conn, d)


def test_trace_assembles_full_bundle(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    storage.record_hypothesis(conn, Hypothesis(hypothesis_id="NR7_BULL_v1",
                                               title="NR7 BULL", status=Status.REJECTED))
    dec_id = _reject_decision(conn)
    ingest.ingest_gate_rejects(conn, resolve=lambda row: "NR7_BULL_v1")
    bundle = trace.trace(conn, "NR7_BULL_v1")
    assert bundle["hypothesis"]["hypothesis_id"] == "NR7_BULL_v1"
    assert [d["decision_id"] for d in bundle["decisions"]] == [dec_id]
    assert bundle["decisions"][0]["evidence"]                # gate_evidence attached
    assert len(bundle["failures"]) == 1
    conn.close()


def test_orphan_report_flags_unlinked_then_clears(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    dec_id = _reject_decision(conn)
    orphans = trace.orphan_report(conn)
    assert dec_id in orphans["gate_decisions"]
    storage.add_link(conn, "NR7_BULL_v1", "gate_decisions", dec_id)
    assert trace.orphan_report(conn)["gate_decisions"] == []
    conn.close()


def test_check_status_consistency_flags_validated_over_reject(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    storage.record_hypothesis(conn, Hypothesis(hypothesis_id="H1", title="a",
                                               status=Status.VALIDATED))
    dec_id = _reject_decision(conn)
    storage.add_link(conn, "H1", "gate_decisions", dec_id)
    warnings = trace.check_status_consistency(conn, "H1")
    assert any("VALIDATED" in w and "REJECT" in w for w in warnings)
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/knowledge/test_trace.py -v`
Expected: FAIL with `ModuleNotFoundError: research.knowledge.trace`

- [ ] **Step 3: Write `research/knowledge/trace.py`**

```python
"""Phase E trace + orphan detection (spec §6, §7). All joins go through
hypothesis_links so the source tables are never altered."""
from __future__ import annotations

from research.knowledge.config import load_config
from research.knowledge.storage import get_hypothesis

# PK column for each linkable source table.
_PK = {"research_runs": "run_id", "gate_decisions": "decision_id",
       "regime_profiles": "profile_id", "failure_registry": "failure_id"}


def _rows(conn, table, ids):
    """Fetch rows of `table` whose PK is in `ids`, as dicts."""
    if not ids:
        return []
    pk = _PK[table]
    marks = ",".join("?" * len(ids))
    cur = conn.execute(f"SELECT * FROM {table} WHERE {pk} IN ({marks})", tuple(ids))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _linked_ids(conn, hypothesis_id, source_table):
    return [r[0] for r in conn.execute(
        "SELECT source_id FROM hypothesis_links WHERE hypothesis_id=? AND "
        "source_table=?", (hypothesis_id, source_table)).fetchall()]


def trace(conn, hypothesis_id) -> dict:
    """Assemble the full evidence bundle for one hypothesis."""
    decisions = _rows(conn, "gate_decisions",
                      _linked_ids(conn, hypothesis_id, "gate_decisions"))
    for d in decisions:
        ev = conn.execute("SELECT stage, verdict, statistic_json, threshold_json "
                          "FROM gate_evidence WHERE decision_id=?",
                          (d["decision_id"],)).fetchall()
        d["evidence"] = [{"stage": s, "verdict": v, "statistic_json": sj,
                          "threshold_json": tj} for s, v, sj, tj in ev]
    return {
        "hypothesis": get_hypothesis(conn, hypothesis_id),
        "experiments": _rows(conn, "research_runs",
                             _linked_ids(conn, hypothesis_id, "research_runs")),
        "decisions": decisions,
        "regime_profiles": _rows(conn, "regime_profiles",
                                 _linked_ids(conn, hypothesis_id, "regime_profiles")),
        "failures": _rows(conn, "failure_registry",
                          _linked_ids(conn, hypothesis_id, "failure_registry")),
    }


def _table_exists(conn, table) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                        (table,)).fetchone() is not None


def orphan_report(conn, scope=None) -> dict:
    """Every row in the orphan-scope tables with no hypothesis_links entry. Advisory
    — this operationalizes 'no orphan experiments' (spec §6). Missing tables yield []."""
    scope = scope or load_config().orphan_scope
    out = {}
    for table in scope:
        if not _table_exists(conn, table):
            out[table] = []
            continue
        pk = _PK[table]
        ids = [r[0] for r in conn.execute(
            f"SELECT {pk} FROM {table} WHERE {pk} NOT IN "
            f"(SELECT source_id FROM hypothesis_links WHERE source_table=?)",
            (table,)).fetchall()]
        out[table] = ids
    return out


def check_status_consistency(conn, hypothesis_id) -> list:
    """Advisory contradictions between declared status and linked evidence (spec §7)."""
    hyp = get_hypothesis(conn, hypothesis_id)
    if hyp is None:
        return [f"unknown hypothesis {hypothesis_id!r}"]
    warnings = []
    linked_dec_ids = _linked_ids(conn, hypothesis_id, "gate_decisions")
    states = [r[0] for r in _rows_states(conn, linked_dec_ids)]
    if hyp["status"] == "VALIDATED" and "REJECT" in states:
        warnings.append("status=VALIDATED but a linked gate_decision=REJECT")
    if hyp["status"] == "REJECTED" and not _linked_ids(
            conn, hypothesis_id, "failure_registry"):
        warnings.append("status=REJECTED but no linked failure row")
    return warnings


def _rows_states(conn, decision_ids):
    if not decision_ids:
        return []
    marks = ",".join("?" * len(decision_ids))
    return conn.execute(
        f"SELECT final_state FROM gate_decisions WHERE decision_id IN ({marks})",
        tuple(decision_ids)).fetchall()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/knowledge/test_trace.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add research/knowledge/trace.py tests/knowledge/test_trace.py
git commit -m "feat(knowledge): trace bundle + advisory orphan report + status-consistency flag"
```

---

## Task 7: Registries — query views over existing tables

**Files:**
- Create: `research/knowledge/registries.py`
- Test: `tests/knowledge/test_registries.py`

- [ ] **Step 1: Write the failing test**

`tests/knowledge/test_registries.py`:

```python
"""Phase E registries as query views (spec §9): no new storage, stable read API."""
from data.db import connect
from research.gatekeeper import storage as gk
from research.gatekeeper.models import (FinalState, GateDecision, StageResult,
                                        Verdict)
from research.knowledge import registries
from research.tracking import ensure_research_runs_table


def test_experiment_registry_reads_research_runs(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    ensure_research_runs_table(conn)
    conn.execute("INSERT INTO research_runs (run_id, kind, started_at, status) "
                 "VALUES ('run1','nr7','2026-07-14','ok')")
    conn.commit()
    rows = registries.experiment_registry(conn)
    assert [r["run_id"] for r in rows] == ["run1"]
    conn.close()


def test_validation_archive_and_evidence_archive(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    gk.ensure_gate_tables(conn)
    d = GateDecision(final_state=FinalState.WATCHLIST, failing_stage=None,
                     stage_results=[StageResult("min_sample", Verdict.PASS, {}, {})],
                     candidate_hash="c", config_hash="cfg", dataset_fingerprint="fp",
                     git_commit="g", seed=1, forward_test_rule=None, run_id="run1",
                     strategy_fn="NR7 Breakout")
    dec_id = gk.persist_decision(conn, d)
    assert [r["decision_id"] for r in registries.validation_archive(conn)] == [dec_id]
    ev = registries.evidence_archive(conn, decision_id=dec_id)
    assert ev and ev[0]["stage"] == "min_sample"
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/knowledge/test_registries.py -v`
Expected: FAIL with `ModuleNotFoundError: research.knowledge.registries`

- [ ] **Step 3: Write `research/knowledge/registries.py`**

```python
"""Phase E registries (spec §9): the Experiment Registry, Validation Archive and
Evidence Archive are query VIEWS over existing research tables — no duplicated
storage. Stable read API for Phase F/G."""
from __future__ import annotations


def _dicts(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def experiment_registry(conn, kind=None) -> list:
    """Every research run (optionally filtered by kind)."""
    if kind:
        return _dicts(conn.execute(
            "SELECT * FROM research_runs WHERE kind=? ORDER BY started_at", (kind,)))
    return _dicts(conn.execute("SELECT * FROM research_runs ORDER BY started_at"))


def validation_archive(conn, final_state=None) -> list:
    """Every gate decision (optionally filtered by final_state)."""
    if final_state:
        return _dicts(conn.execute(
            "SELECT * FROM gate_decisions WHERE final_state=? ORDER BY decided_at",
            (final_state,)))
    return _dicts(conn.execute("SELECT * FROM gate_decisions ORDER BY decided_at"))


def evidence_archive(conn, decision_id=None) -> list:
    """Gate evidence rows, optionally scoped to one decision."""
    if decision_id:
        return _dicts(conn.execute(
            "SELECT * FROM gate_evidence WHERE decision_id=?", (decision_id,)))
    return _dicts(conn.execute("SELECT * FROM gate_evidence"))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/knowledge/test_registries.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add research/knowledge/registries.py tests/knowledge/test_registries.py
git commit -m "feat(knowledge): Experiment/Validation/Evidence registries as query views"
```

---

## Task 8: Backfill — seed the two live hypotheses, zero orphans

**Files:**
- Create: `research/knowledge/backfill.py`
- Test: `tests/knowledge/test_backfill.py`

- [ ] **Step 1: Write the failing test**

`tests/knowledge/test_backfill.py`:

```python
"""Phase E backfill (spec §8): seed NR7_BULL_v1 + NR7_BULL_LOWLIQ_v1, link their
existing gate_decisions/regime_profiles, and leave the seeded corpus orphan-free."""
from data.db import connect
from research.gatekeeper import storage as gk
from research.gatekeeper.models import (FinalState, GateDecision, StageResult,
                                        Verdict)
from research.knowledge import backfill, storage, trace
from research.regime import storage as rg


def _seeded_corpus(conn):
    # a NR7 REJECT gate decision + a NR7 regime profile (the real evidence shapes)
    gk.ensure_gate_tables(conn)
    d = GateDecision(final_state=FinalState.REJECT, failing_stage="walk_forward",
                     stage_results=[StageResult("walk_forward", Verdict.FAIL, {}, {})],
                     candidate_hash="c", config_hash="cfg", dataset_fingerprint="fp",
                     git_commit="g", seed=1, forward_test_rule=None, run_id="run1",
                     strategy_fn="NR7 Breakout")
    gk.persist_decision(conn, d)
    rg.ensure_profile_tables(conn)
    conn.execute("INSERT INTO regime_profiles (profile_id, strategy_fn, created_at) "
                 "VALUES ('prof1','NR7 Breakout','2026-07-10')")
    conn.commit()


def test_backfill_seeds_and_leaves_no_orphans(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    _seeded_corpus(conn)
    summary = backfill.seed_known_hypotheses(conn)
    assert summary["hypotheses"] >= 2
    # NR7_BULL_v1 traces to its gate decision + regime profile + failure
    bundle = trace.trace(conn, "NR7_BULL_v1")
    assert bundle["decisions"] and bundle["regime_profiles"] and bundle["failures"]
    # the seeded corpus has no orphan gate_decisions
    assert trace.orphan_report(conn)["gate_decisions"] == []
    conn.close()


def test_backfill_is_idempotent(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    _seeded_corpus(conn)
    backfill.seed_known_hypotheses(conn)
    backfill.seed_known_hypotheses(conn)                # must not raise / duplicate
    n = conn.execute("SELECT COUNT(*) FROM hypotheses").fetchone()[0]
    assert n == 2
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/knowledge/test_backfill.py -v`
Expected: FAIL with `ModuleNotFoundError: research.knowledge.backfill`

- [ ] **Step 3: Write `research/knowledge/backfill.py`**

```python
"""Phase E backfill (spec §8). Seed the two live hypotheses and back-link their
existing evidence by strategy_fn. Idempotent: safe to re-run (record_hypothesis is
guarded, links + failures dedupe). Broader historical backfill is deferred."""
from __future__ import annotations

from research.knowledge import ingest, storage
from research.knowledge.models import Hypothesis, Status

# strategy_fn (as written in gate_decisions/regime_profiles) -> hypothesis_id
_STRATEGY_TO_HYPOTHESIS = {"NR7 Breakout": "NR7_BULL_v1"}

_SEED_HYPOTHESES = [
    Hypothesis(hypothesis_id="NR7_BULL_v1", title="NR7 BULL breakout edge",
               rationale="BULL-regime NR7 breakout; liquidity-conditional (Phase D).",
               origin="manual", status=Status.REJECTED),
    Hypothesis(hypothesis_id="NR7_BULL_LOWLIQ_v1",
               title="NR7 BULL edge conditioned on LOW liquidity",
               rationale="BULL AND LOW_LIQ sub-cell (+2.29% vs -0.47% HIGH_LIQ).",
               origin="regime_scan", status=Status.FORWARD_TESTING,
               prereg_ref="docs/superpowers/specs/2026-07-12-prereg-nr7-bull-lowliq-v1.md"),
]


def _record_if_absent(conn, hyp):
    if storage.get_hypothesis(conn, hyp.hypothesis_id) is None:
        storage.record_hypothesis(conn, hyp)


def _link_by_strategy(conn, table, source_pk):
    """Link every row of `table` to the hypothesis its strategy_fn maps to."""
    for source_id, strategy_fn in conn.execute(
            f"SELECT {source_pk}, strategy_fn FROM {table}").fetchall():
        hyp = _STRATEGY_TO_HYPOTHESIS.get(strategy_fn)
        if hyp:
            storage.add_link(conn, hyp, table, source_id)


def seed_known_hypotheses(conn) -> dict:
    """Seed the live hypotheses, link their gate_decisions/regime_profiles, ingest
    their gate REJECTs as failures, and add one manual failure seed. Returns a
    small summary. Idempotent."""
    for hyp in _SEED_HYPOTHESES:
        _record_if_absent(conn, hyp)
    _link_by_strategy(conn, "gate_decisions", "decision_id")
    _link_by_strategy(conn, "regime_profiles", "profile_id")
    ingest.ingest_gate_rejects(
        conn, resolve=lambda row: _STRATEGY_TO_HYPOTHESIS.get(row["strategy_fn"]))
    # one manual failure seed (flow-edge study — predates the gate)
    ingest.record_failure(conn, None, "flow edge: no edge (mega+mid caps)",
                          fingerprint="flow_edge_study_2026-07-07")
    return {"hypotheses": conn.execute(
        "SELECT COUNT(*) FROM hypotheses").fetchone()[0]}
```

Note: `_link_by_strategy` runs before `ingest_gate_rejects`; both are idempotent, so re-running `seed_known_hypotheses` adds no duplicate links, failures, or hypotheses.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/knowledge/test_backfill.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add research/knowledge/backfill.py tests/knowledge/test_backfill.py
git commit -m "feat(knowledge): backfill seeds NR7 hypotheses + zero-orphan corpus"
```

---

## Task 9: CLI

**Files:**
- Create: `research/knowledge/cli.py`
- Test: `tests/knowledge/test_cli.py`

- [ ] **Step 1: Write the failing test**

`tests/knowledge/test_cli.py`:

```python
"""Phase E CLI: record-hypothesis, record-failure, orphans, trace, backfill."""
from data.db import connect
from research.knowledge import cli, storage


def test_cli_record_hypothesis_then_trace(tmp_path, capsys):
    db = str(tmp_path / "t.db")
    conn = connect(db)
    storage.ensure_knowledge_tables(conn)
    conn.close()
    rc = cli.main(["--db", db, "record-hypothesis", "--id", "H1", "--title", "a hyp"])
    assert rc == 0
    rc = cli.main(["--db", db, "trace", "--id", "H1"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "H1" in out


def test_cli_orphans_runs(tmp_path):
    db = str(tmp_path / "t.db")
    conn = connect(db)
    storage.ensure_knowledge_tables(conn)
    conn.close()
    assert cli.main(["--db", db, "orphans"]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/knowledge/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: research.knowledge.cli`

- [ ] **Step 3: Write `research/knowledge/cli.py`**

```python
"""Phase E CLI (spec §3): record hypotheses/failures, run backfill, inspect the
knowledge base. Mirrors research/gatekeeper/cli.py argparse style."""
from __future__ import annotations

import argparse
import json
import sys

from data.db import connect
from research.knowledge import backfill, ingest, storage, trace
from research.knowledge.models import Hypothesis


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    p = argparse.ArgumentParser(prog="knowledge",
                                description="Phase E research knowledge base")
    p.add_argument("--db", default="walkforward.db", help="sqlite path")
    sub = p.add_subparsers(dest="cmd", required=True)

    rh = sub.add_parser("record-hypothesis")
    rh.add_argument("--id", required=True)
    rh.add_argument("--title", required=True)
    rh.add_argument("--rationale", default="")

    rf = sub.add_parser("record-failure")
    rf.add_argument("--id", default=None, help="hypothesis_id (optional)")
    rf.add_argument("--reason", required=True)

    tr = sub.add_parser("trace")
    tr.add_argument("--id", required=True)

    sub.add_parser("orphans")
    sub.add_parser("backfill")

    args = p.parse_args(argv)
    conn = connect(args.db)
    storage.ensure_knowledge_tables(conn)

    if args.cmd == "record-hypothesis":
        storage.record_hypothesis(conn, Hypothesis(hypothesis_id=args.id,
                                                   title=args.title,
                                                   rationale=args.rationale))
        print(f"recorded {args.id}")
    elif args.cmd == "record-failure":
        fid = ingest.record_failure(conn, args.id, args.reason)
        print(f"failure {fid}" if fid else "duplicate failure (no-op)")
    elif args.cmd == "trace":
        print(json.dumps(trace.trace(conn, args.id), indent=2, default=str))
    elif args.cmd == "orphans":
        print(json.dumps(trace.orphan_report(conn), indent=2))
    elif args.cmd == "backfill":
        print(json.dumps(backfill.seed_known_hypotheses(conn), indent=2))

    conn.close()
    return 0


if __name__ == "__main__":                              # pragma: no cover
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/knowledge/test_cli.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add research/knowledge/cli.py tests/knowledge/test_cli.py
git commit -m "feat(knowledge): CLI — record/trace/orphans/backfill"
```

---

## Task 10: Write-fence extension + full-suite guard

**Files:**
- Modify: `tests/test_research_data_fence.py:22-24`
- Test: same file (assert the three new tables are fenced)

- [ ] **Step 1: Add the three tables to `RESEARCH_TABLES`**

In `tests/test_research_data_fence.py`, replace the `RESEARCH_TABLES` tuple (currently at lines 22-24):

```python
# Phase C gate_decisions / gate_evidence and Phase D regime profiles are research
# products too — only research/ writes them; production may read (dashboards) but
# not write. Phase E knowledge base extends this.
RESEARCH_TABLES = ("wf_scores", "wf_edge", "backtest_cache",
                   "gate_decisions", "gate_evidence",
                   "regime_profiles", "regime_profile_cells",
                   "hypotheses", "hypothesis_links", "failure_registry")
```

- [ ] **Step 2: Add a guard test to `tests/test_research_data_fence.py`**

Append:

```python
def test_phase_e_tables_are_fenced():
    """Guard the guard: the Phase E knowledge tables must be in RESEARCH_TABLES so
    a stray production write to them fails CI."""
    assert {"hypotheses", "hypothesis_links", "failure_registry"} <= set(RESEARCH_TABLES)
```

- [ ] **Step 3: Run the fence tests**

Run: `pytest tests/test_research_data_fence.py -v`
Expected: PASS (existing tests + `test_phase_e_tables_are_fenced`). No production file writes the new tables, so `test_w1_no_research_table_writes_in_production` stays green.

- [ ] **Step 4: Run the full knowledge suite + boundary/architecture guards**

Run: `pytest tests/knowledge/ tests/test_research_data_fence.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the FULL suite to confirm no regression**

Run: `pytest -q`
Expected: previous baseline (1464) + new knowledge tests, all passing, zero failures. If any pre-existing unrelated failure appears, note it but do not fix out of scope.

- [ ] **Step 6: Commit**

```bash
git add tests/test_research_data_fence.py
git commit -m "test(knowledge): fence hypotheses/hypothesis_links/failure_registry (research-write-only)"
```

---

## Task 11 (Amendment A1): Receipt-bound status transitions

> Added 2026-07-14 per Master Plan v3 DRAFT §3.4a. Runs after Task 10. Closes the
> `set_status("MY_PET_PROJECT", "VALIDATED")` executive-override hole: promotion-track
> labels must carry a gate receipt, structurally verified — not just vocabulary-checked.

**Design:**
- Gated statuses: `FORWARD_TESTING` and `VALIDATED`.
- `set_status(conn, hid, FORWARD_TESTING, evidence_decision_id=...)` — requires an
  existing `gate_decisions` row with `final_state = FinalState.PROMOTE`
  (`"PROMOTE_TO_FORWARD_TEST"`); raises `ValueError` otherwise.
- `set_status(conn, hid, VALIDATED, evidence_decision_id=..., forward_receipt=...)` —
  requires the PROMOTE receipt **plus** a non-empty forward-test receipt ref.
- On success the receipt is bound: `add_link(hid, "gate_decisions", decision_id)` +
  receipt merged into `notes_json`.
- `record_hypothesis` rejects gated **initial** statuses (no back door via insert),
  except a shrink-only `_STATUS_DEBT = {"NR7_BULL_LOWLIQ_v1"}` grandfather list
  (seeded FORWARD_TESTING by Task 8 backfill under its 2026-07-12 pre-registration;
  mirrors the R-10 `_LIFECYCLE_DEBT` pattern; FORWARD_TESTING only — VALIDATED is
  never seedable).
- `check_status_consistency` (trace.py) stays advisory for legacy rows; the hard
  gate lives at the mutation gateway.

**Files:**
- Modify: `research/knowledge/storage.py` (`set_status` signature + guards; `record_hypothesis` initial-status guard; `_STATUS_DEBT`)
- Modify: `tests/knowledge/test_trace.py` (one test — see step 2)
- Test: `tests/knowledge/test_status_receipts.py`

- [ ] **Step 1: Write the failing test**

`tests/knowledge/test_status_receipts.py`:

```python
"""Phase E Task 11 (v3 amendment V3-4): receipt-bound status transitions.
Promotion-track labels are structurally gated on gate_decisions receipts."""
import pytest

from data.db import connect
from research.gatekeeper import storage as gk
from research.gatekeeper.models import (FinalState, GateDecision, StageResult,
                                        Verdict)
from research.knowledge import storage
from research.knowledge.models import Hypothesis, Status


def _decision(conn, final_state, run_id="run1"):
    gk.ensure_gate_tables(conn)
    d = GateDecision(final_state=final_state, failing_stage=None,
                     stage_results=[StageResult("min_sample", Verdict.PASS, {}, {})],
                     candidate_hash="c", config_hash="cfg", dataset_fingerprint="fp",
                     git_commit="g", seed=1, forward_test_rule=None, run_id=run_id,
                     strategy_fn="NR7 Breakout")
    return gk.persist_decision(conn, d)


def _seed(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    storage.record_hypothesis(conn, Hypothesis(hypothesis_id="H1", title="a"))
    return conn


def test_forward_testing_requires_receipt(tmp_path):
    conn = _seed(tmp_path)
    with pytest.raises(ValueError):
        storage.set_status(conn, "H1", Status.FORWARD_TESTING)
    conn.close()


def test_forward_testing_accepts_promote_receipt_and_links_it(tmp_path):
    conn = _seed(tmp_path)
    dec_id = _decision(conn, FinalState.PROMOTE)
    storage.set_status(conn, "H1", Status.FORWARD_TESTING,
                       evidence_decision_id=dec_id)
    assert storage.get_hypothesis(conn, "H1")["status"] == "FORWARD_TESTING"
    row = conn.execute(
        "SELECT 1 FROM hypothesis_links WHERE hypothesis_id='H1' AND "
        "source_table='gate_decisions' AND source_id=?", (dec_id,)).fetchone()
    assert row is not None
    conn.close()


def test_forward_testing_rejects_non_promote_receipt(tmp_path):
    conn = _seed(tmp_path)
    dec_id = _decision(conn, FinalState.WATCHLIST)
    with pytest.raises(ValueError):
        storage.set_status(conn, "H1", Status.FORWARD_TESTING,
                           evidence_decision_id=dec_id)
    conn.close()


def test_validated_requires_promote_receipt_plus_forward_receipt(tmp_path):
    conn = _seed(tmp_path)
    dec_id = _decision(conn, FinalState.PROMOTE)
    with pytest.raises(ValueError):                     # no forward receipt
        storage.set_status(conn, "H1", Status.VALIDATED,
                           evidence_decision_id=dec_id)
    storage.set_status(conn, "H1", Status.VALIDATED, evidence_decision_id=dec_id,
                       forward_receipt="ft_go_2026-07-14")
    assert storage.get_hypothesis(conn, "H1")["status"] == "VALIDATED"
    conn.close()


def test_gated_status_rejects_unknown_decision_id(tmp_path):
    conn = _seed(tmp_path)
    with pytest.raises(ValueError):
        storage.set_status(conn, "H1", Status.VALIDATED,
                           evidence_decision_id="nope", forward_receipt="ft")
    conn.close()


def test_record_hypothesis_rejects_gated_initial_status(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    with pytest.raises(ValueError):
        storage.record_hypothesis(conn, Hypothesis(
            hypothesis_id="X", title="x", status=Status.VALIDATED))
    with pytest.raises(ValueError):
        storage.record_hypothesis(conn, Hypothesis(
            hypothesis_id="Y", title="y", status=Status.FORWARD_TESTING))
    conn.close()


def test_status_debt_grandfather_allows_seeded_forward_testing(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    storage.record_hypothesis(conn, Hypothesis(
        hypothesis_id="NR7_BULL_LOWLIQ_v1", title="grandfathered",
        status=Status.FORWARD_TESTING))                 # in _STATUS_DEBT
    assert (storage.get_hypothesis(conn, "NR7_BULL_LOWLIQ_v1")["status"]
            == "FORWARD_TESTING")
    conn.close()
```

- [ ] **Step 2: Adjust the one now-invalid trace test**

`tests/knowledge/test_trace.py::test_check_status_consistency_flags_validated_over_reject`
seeds a hypothesis directly at `Status.VALIDATED`, which Task 11 forbids. The test's
*intent* is to exercise the advisory checker on an inconsistent (legacy/corrupt)
state — so simulate that state honestly with a raw UPDATE instead:

```python
    storage.record_hypothesis(conn, Hypothesis(hypothesis_id="H1", title="a"))
    conn.execute("UPDATE hypotheses SET status='VALIDATED' WHERE hypothesis_id='H1'")
    conn.commit()
```

(replacing the `record_hypothesis(... status=Status.VALIDATED)` call; the rest of
the test is unchanged.)

- [ ] **Step 3: Run tests to verify red**

Run: `pytest tests/knowledge/test_status_receipts.py -v`
Expected: FAIL — `set_status` takes no `evidence_decision_id` kwarg; the two
`record_hypothesis` guard tests fail because no ValueError is raised.

- [ ] **Step 4: Implement in `research/knowledge/storage.py`**

Add near `_VALID_STATUSES`:

```python
# Task 11 (v3 §3.4a): promotion-track labels are receipt-bound.
_GATED_STATUSES = {"FORWARD_TESTING", "VALIDATED"}
# Shrink-only grandfather list — hypotheses that may be *seeded* directly at
# FORWARD_TESTING under a pre-registration that predates Task 11 (mirrors the
# R-10 _LIFECYCLE_DEBT pattern). Never add entries; VALIDATED is never seedable.
_STATUS_DEBT = {"NR7_BULL_LOWLIQ_v1"}
```

In `record_hypothesis`, after the vocabulary check:

```python
    if status in _GATED_STATUSES and not (
            status == "FORWARD_TESTING" and hyp.hypothesis_id in _STATUS_DEBT):
        raise ValueError(
            f"initial status {status!r} requires a gate receipt — record as "
            f"PROPOSED and transition via set_status(evidence_decision_id=...)")
```

Replace `set_status` with:

```python
def set_status(conn, hypothesis_id, status, evidence_decision_id=None,
               forward_receipt=None) -> None:
    """The one sanctioned mutation (spec §4.1/§7): update a hypothesis's label.
    Task 11 (v3 §3.4a): FORWARD_TESTING requires a linked gate PROMOTE receipt;
    VALIDATED additionally requires a forward-test receipt ref. The binding is
    recorded as a hypothesis_links row + notes_json entry."""
    from research.gatekeeper.models import FinalState

    value = status.value if isinstance(status, Status) else str(status)
    if value not in _VALID_STATUSES:
        raise ValueError(f"invalid status {value!r}; allowed {_VALID_STATUSES}")
    if value in _GATED_STATUSES:
        if not evidence_decision_id:
            raise ValueError(f"status {value!r} requires evidence_decision_id "
                             f"(gate PROMOTE receipt)")
        row = conn.execute(
            "SELECT final_state FROM gate_decisions WHERE decision_id=?",
            (evidence_decision_id,)).fetchone()
        if row is None:
            raise ValueError(f"unknown gate decision {evidence_decision_id!r}")
        if row[0] != FinalState.PROMOTE:
            raise ValueError(f"status {value!r} requires final_state="
                             f"{FinalState.PROMOTE!r}, got {row[0]!r}")
        if value == "VALIDATED" and not forward_receipt:
            raise ValueError("status 'VALIDATED' additionally requires "
                             "forward_receipt (forward-test evidence ref)")
        add_link(conn, hypothesis_id, "gate_decisions", evidence_decision_id)
        hyp = get_hypothesis(conn, hypothesis_id)
        notes = json.loads(hyp["notes_json"]) if hyp and hyp["notes_json"] else {}
        notes[f"receipt_{value.lower()}"] = {
            "decision_id": evidence_decision_id, "forward_receipt": forward_receipt,
            "bound_at": _now()}
        conn.execute("UPDATE hypotheses SET notes_json=? WHERE hypothesis_id=?",
                     (json.dumps(notes), hypothesis_id))
    conn.execute("UPDATE hypotheses SET status=? WHERE hypothesis_id=?",
                 (value, hypothesis_id))
    conn.commit()
```

(The `FinalState` import is local to keep module import cost flat; gatekeeper is a
sibling research package, so no boundary is crossed.)

- [ ] **Step 5: Run tests to verify green**

Run: `pytest tests/knowledge/test_status_receipts.py tests/knowledge/test_trace.py tests/knowledge/test_storage_hypotheses.py tests/knowledge/test_backfill.py -v`
Expected: all PASS (7 new + adjusted trace test + existing hypotheses/backfill tests
— backfill's `NR7_BULL_LOWLIQ_v1` FORWARD_TESTING seed passes via `_STATUS_DEBT`).

- [ ] **Step 6: Run the full knowledge suite + fence**

Run: `pytest tests/knowledge/ tests/test_research_data_fence.py -q`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add research/knowledge/storage.py tests/knowledge/test_status_receipts.py tests/knowledge/test_trace.py
git commit -m "feat(knowledge): receipt-bound status transitions — gate PROMOTE receipt required for FORWARD_TESTING/VALIDATED (v3 A1)"
```

---

## Done criteria

- `research/knowledge/` package complete: config, models, storage, ingest, trace, registries, backfill, cli.
- Three tables live; evidence append-only, `hypotheses.status`/`notes` the only mutable surface.
- **(A1)** Promotion-track statuses receipt-bound: no FORWARD_TESTING/VALIDATED without a verifiable gate PROMOTE receipt; `_STATUS_DEBT` shrink-only.
- Gate REJECTs auto-ingest (idempotent) + manual failure channel; hybrid feed working.
- `trace(hypothesis_id)` assembles the full bundle; `orphan_report` operational (advisory); backfilled corpus orphan-free.
- The three query-view registries expose a stable read API for Phase F/G.
- Write-fence extended; full suite green; no production change.
- Commit the plan itself and the memory update; do NOT push (per the phase pattern — user pushes deliberately).
