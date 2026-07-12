# R-10 Registry Lifecycle Enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make an `APPROVED`/`SHADOW` registry status require a verifiable evidence receipt (Phase C PROMOTE + Phase 5 forward GO), enforced hard in CI and softly (WARN, non-breaking) at runtime, with `NR7_BULL` grandfathered under a dated remediation deadline.

**Architecture:** A pure `validate_evidence(entry, manifest, bar)` helper in `engine/registry_loader.py` returns violation reasons; `load_registry` loads each entry's manifest, classifies non-compliant entries as `debt` (grandfathered) or `violations` (fail CI), and still loads them (non-breaking). A CI-static test (`tests/test_registry_lifecycle.py`) fails the build on any non-allowlisted violation and on a grandfathered entry past its deadline. `engine/` must not import `research/`, so the forward bar is a local constant pinned to `phase5_tracker.RULE` by a consistency test.

**Tech Stack:** Python, pytest, PyYAML, sqlite (not needed — evidence is snapshotted in manifests).

**Reference spec:** `docs/superpowers/specs/2026-07-12-r10-registry-lifecycle-enforcement-design.md`

---

## File Structure

- Modify: `engine/registry_loader.py` — `_FORWARD_BAR`, `_LIFECYCLE_DEBT`, `validate_evidence()`, `load_registry` wiring, `startup_summary` counts
- Modify: `registry/SCHEMA.md` — document the `evidence:` block
- Create: `tests/test_registry_lifecycle.py` — CI-static enforcement + loader-behavior + deadline + bar-consistency tests

`registry/manifests/NR7_BULL_v1.yaml` is **not** modified — NR7_BULL is grandfathered (it has no compliant receipt to add; its Phase C verdict is REJECT).

---

## Task 1: `validate_evidence` pure helper

**Files:**
- Modify: `engine/registry_loader.py`
- Test: `tests/test_registry_lifecycle.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_registry_lifecycle.py`:

```python
from engine.registry_loader import validate_evidence, _FORWARD_BAR

BAR = _FORWARD_BAR  # {'min_n': 15, 'go_exp': 0.50}
_PROMOTE = {"gate_decision": {"final_state": "PROMOTE_TO_FORWARD_TEST"}}


def test_non_loadable_status_needs_no_evidence():
    assert validate_evidence({"status": "CANDIDATE"}, {}, BAR) == []


def test_shadow_requires_promote_gate_decision():
    assert validate_evidence({"status": "SHADOW"}, {"evidence": {}}, BAR)          # missing -> reasons
    assert validate_evidence({"status": "SHADOW"}, {"evidence": _PROMOTE}, BAR) == []


def test_approved_requires_promote_and_forward_go():
    ev = {"evidence": dict(_PROMOTE,
          forward={"verdict": "GO", "n": 17, "exp_pct": 0.63})}
    assert validate_evidence({"status": "APPROVED"}, ev, BAR) == []


def test_approved_with_promote_but_no_forward_fails():
    reasons = validate_evidence({"status": "APPROVED"}, {"evidence": _PROMOTE}, BAR)
    assert reasons and any("forward" in r for r in reasons)


def test_approved_forward_below_bar_fails():
    ev = {"evidence": dict(_PROMOTE,
          forward={"verdict": "GO", "n": 10, "exp_pct": 0.63})}   # n < 15
    reasons = validate_evidence({"status": "APPROVED"}, ev, BAR)
    assert reasons and any("below bar" in r for r in reasons)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/test_registry_lifecycle.py -v`
Expected: FAIL — `ImportError: cannot import name 'validate_evidence'`

- [ ] **Step 3: Implement the helper**

In `engine/registry_loader.py`, after the existing module constants (near `_LOADABLE`/`_LIFECYCLE`), add:

```python
# Forward-test bar for APPROVED. Mirrors research.studies.phase5_tracker.RULE;
# engine/ must not import research/, so it is pinned here and asserted equal by
# tests/test_registry_lifecycle.py::test_forward_bar_matches_phase5_rule.
_FORWARD_BAR = {'min_n': 15, 'go_exp': 0.50}


def validate_evidence(entry, manifest, bar):
    """Return a list of reasons a SHADOW/APPROVED entry fails its evidence receipt.

    Pure. Empty list == compliant (or a non-loadable status that needs no receipt).
    SHADOW needs a Phase C PROMOTE gate_decision; APPROVED also needs a Phase 5
    forward GO clearing `bar`."""
    status = entry.get('status')
    if status not in ('SHADOW', 'APPROVED'):
        return []
    ev = (manifest or {}).get('evidence') or {}
    reasons = []
    gd = ev.get('gate_decision') or {}
    if gd.get('final_state') != 'PROMOTE_TO_FORWARD_TEST':
        reasons.append('no PROMOTE gate_decision')
    if status == 'APPROVED':
        fw = ev.get('forward') or {}
        if fw.get('verdict') != 'GO':
            reasons.append('forward verdict != GO')
        elif fw.get('n', 0) < bar['min_n'] or fw.get('exp_pct', -1.0) < bar['go_exp']:
            reasons.append(
                f"forward below bar (n={fw.get('n')}, exp={fw.get('exp_pct')})")
    return reasons
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/pytest tests/test_registry_lifecycle.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add engine/registry_loader.py tests/test_registry_lifecycle.py
git commit -m "feat(registry): validate_evidence — bind SHADOW/APPROVED to an evidence receipt"
```

Append to every commit body in this plan:

```

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XEskq7Bqug89JtRNXuPNxW
```

---

## Task 2: Forward-bar consistency test (no drift from phase5_tracker)

**Files:**
- Test: `tests/test_registry_lifecycle.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_registry_lifecycle.py`:

```python
def test_forward_bar_matches_phase5_rule():
    # Tests may import research/; engine/ may not. Lock the mirrored bar so it can
    # never drift from the canonical Phase 5 rule.
    from research.studies.phase5_tracker import RULE
    assert _FORWARD_BAR['min_n'] == RULE['min_n']
    assert _FORWARD_BAR['go_exp'] == RULE['go_exp']
```

- [ ] **Step 2: Run test to verify it passes immediately**

Run: `./venv/bin/pytest tests/test_registry_lifecycle.py::test_forward_bar_matches_phase5_rule -v`
Expected: PASS (values already equal — this is a regression lock, not a red/green)

- [ ] **Step 3: Commit**

```bash
git add tests/test_registry_lifecycle.py
git commit -m "test(registry): lock registry forward bar to phase5_tracker.RULE"
```

---

## Task 3: Grandfather allowlist + `load_registry` wiring

**Files:**
- Modify: `engine/registry_loader.py`
- Test: `tests/test_registry_lifecycle.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_registry_lifecycle.py`:

```python
from engine.registry_loader import load_registry, _LIFECYCLE_DEBT


def test_real_registry_loads_with_nr7_as_debt_not_violation():
    r = load_registry()
    # governance unchanged: NR7_BULL still loads
    assert any(e['id'] == 'NR7_BULL' for e in r['entries'])
    # it is classified as known debt, NOT a live violation
    debt_ids = {d[0] for d in r['debt']}
    viol_ids = {v[0] for v in r['violations']}
    assert 'NR7_BULL_v1' in debt_ids
    assert 'NR7_BULL_v1' not in viol_ids
    assert r['violations'] == []          # no un-grandfathered violations today


def test_nr7_bull_is_the_only_grandfathered_entry():
    assert set(_LIFECYCLE_DEBT) == {("NR7_BULL", 1)}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/test_registry_lifecycle.py -k "real_registry or grandfathered_entry" -v`
Expected: FAIL — `ImportError: cannot import name '_LIFECYCLE_DEBT'` / `KeyError: 'debt'`

- [ ] **Step 3: Add the allowlist and wire the loader**

In `engine/registry_loader.py`, add the debt allowlist near `_FORWARD_BAR`:

```python
# Shrink-only lifecycle debt (like tests/test_research_data_fence._ROUTES_WRITE_DEBT).
# Pre-existing APPROVED/SHADOW entries that predate R-10 enforcement. NEW violations are
# NOT added here — they fail CI. Entries are removed as they remediate, never added.
_LIFECYCLE_DEBT = {
    ("NR7_BULL", 1): {
        "reason": "APPROVED 2026-07-04 under the pre-Phase-C generalization bar; "
                  "Phase C gate=REJECT and shadow N=0. Governs on legacy grounds.",
        "remediation": "Phase 5 forward test (phase5_tracker); deadline 2027-01-08.",
        "deadline": "2027-01-08",
    },
}
```

In `load_registry`, initialise `violations, debt = [], []` alongside `entries, skipped`, and
immediately before the final `entries.append(e)` insert the evidence check (the entry has
already passed status/version/artifact checks here):

```python
        manifest = {}
        if e.get('manifest'):
            man_path = os.path.join(os.path.dirname(path), e['manifest'])
            try:
                with open(man_path, 'r') as f:
                    manifest = yaml.safe_load(f) or {}
            except Exception:
                manifest = {}
        # else: no manifest -> empty -> validate_evidence flags the missing receipt
        reasons = validate_evidence(e, manifest, _FORWARD_BAR)
        if reasons:
            key = (e['id'], e['version'])
            if key in _LIFECYCLE_DEBT:
                debt.append((ident, _LIFECYCLE_DEBT[key]['reason']))
                logger.info("edge_registry %s — known lifecycle debt (%s)",
                            ident, _LIFECYCLE_DEBT[key]['remediation'])
            else:
                violations.append((ident, "; ".join(reasons)))
                fail_open_alarm("edge_registry",
                                f"{ident} lifecycle-unverified — {'; '.join(reasons)}",
                                count=1, notify=False)
        entries.append(e)
```

Change the final return to include the new lists:

```python
    return {'entries': entries, 'skipped': skipped,
            'violations': violations, 'debt': debt, 'hash': _registry_hash(path)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/pytest tests/test_registry_lifecycle.py -v`
Expected: PASS (all tests; NR7_BULL classified as debt, zero violations)

- [ ] **Step 5: Commit**

```bash
git add engine/registry_loader.py tests/test_registry_lifecycle.py
git commit -m "feat(registry): load_registry classifies debt vs violations (non-breaking WARN)"
```

---

## Task 4: CI-static enforcement + deadline test

**Files:**
- Test: `tests/test_registry_lifecycle.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_registry_lifecycle.py`:

```python
import datetime as _dt


def test_no_ungrandfathered_lifecycle_violations_in_real_registry():
    """CI gate: any SHADOW/APPROVED entry lacking a valid receipt fails the build,
    unless explicitly grandfathered. New bad approvals cannot merge."""
    r = load_registry()
    assert r['violations'] == [], f"un-grandfathered lifecycle violations: {r['violations']}"


def test_a_new_noncompliant_approved_entry_would_fail():
    # Prove the door is shut: a fabricated APPROVED entry with no forward GO,
    # not in the allowlist, yields violation reasons.
    fabricated = {"status": "APPROVED", "id": "FAKE_EDGE", "version": 1}
    reasons = validate_evidence(fabricated, {"evidence":
        {"gate_decision": {"final_state": "PROMOTE_TO_FORWARD_TEST"}}}, _FORWARD_BAR)
    assert reasons and ("FAKE_EDGE", 1) not in _LIFECYCLE_DEBT


def test_grandfathered_debt_not_past_deadline():
    """Once a debt entry's remediation deadline passes, this fails until it is
    remediated (compliant receipt) or demoted + removed from the allowlist."""
    today = _dt.date.today()
    overdue = [k for k, v in _LIFECYCLE_DEBT.items()
               if _dt.date.fromisoformat(v['deadline']) < today]
    assert overdue == [], f"lifecycle debt past remediation deadline: {overdue}"
```

- [ ] **Step 2: Run test to verify current state**

Run: `./venv/bin/pytest tests/test_registry_lifecycle.py -v`
Expected: PASS — real registry has zero un-grandfathered violations; NR7_BULL deadline (2027-01-08) is in the future.

- [ ] **Step 3: No implementation needed**

These assert behavior already delivered by Tasks 1 and 3. If any fails, fix the wiring from Task 3 rather than weakening the test.

- [ ] **Step 4: Commit**

```bash
git add tests/test_registry_lifecycle.py
git commit -m "test(registry): CI gate on lifecycle violations + dated debt deadline"
```

---

## Task 5: `startup_summary` reports violations + debt

**Files:**
- Modify: `engine/registry_loader.py`
- Test: `tests/test_registry_lifecycle.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_registry_lifecycle.py`:

```python
from engine.registry_loader import startup_summary, _reset_cache


def test_startup_summary_reports_debt_and_violations():
    _reset_cache()
    s = startup_summary()
    assert "1 debt" in s          # NR7_BULL
    assert "0 unverified" in s     # no live violations
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/test_registry_lifecycle.py::test_startup_summary_reports_debt_and_violations -v`
Expected: FAIL — current summary has no debt/unverified counts

- [ ] **Step 3: Extend `startup_summary`**

In `engine/registry_loader.py`, update `startup_summary`:

```python
def startup_summary():
    r = get_registry()
    n_app = sum(1 for e in r['entries'] if e['status'] == 'APPROVED')
    n_sh = sum(1 for e in r['entries'] if e['status'] == 'SHADOW')
    return (f"registry @{r['hash']}: {n_app} approved, {n_sh} shadow, "
            f"{len(r['skipped'])} skipped, {len(r.get('debt', []))} debt, "
            f"{len(r.get('violations', []))} unverified")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/pytest tests/test_registry_lifecycle.py::test_startup_summary_reports_debt_and_violations -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/registry_loader.py tests/test_registry_lifecycle.py
git commit -m "feat(registry): startup_summary surfaces debt + unverified counts"
```

---

## Task 6: Document the `evidence:` block in SCHEMA.md

**Files:**
- Modify: `registry/SCHEMA.md`

- [ ] **Step 1: Add the schema section**

Append to `registry/SCHEMA.md` a section documenting the manifest `evidence:` block and the
lifecycle rule (copy the §3 table and §4 YAML from the design spec):

```markdown
## Lifecycle evidence (R-10 enforcement)

A `SHADOW`/`APPROVED` entry must carry a verifiable receipt in its manifest. `SHADOW` needs a
Phase C PROMOTE `gate_decision`; `APPROVED` also needs a Phase 5 forward `GO` clearing the
frozen bar (`min_n=15, go_exp=0.50`). Enforced by `tests/test_registry_lifecycle.py` (CI, hard)
and `engine/registry_loader.validate_evidence` (runtime WARN, non-breaking). Pre-R-10 entries
may be grandfathered in `registry_loader._LIFECYCLE_DEBT` (shrink-only, with a remediation
deadline).

    evidence:
      gate_decision: {decision_id, final_state: PROMOTE_TO_FORWARD_TEST, config_hash, dataset_fingerprint}
      forward:        # APPROVED only
        {verdict: GO, n, exp_pct, rule: {min_n: 15, go_exp: 0.50}, as_of}
```

- [ ] **Step 2: Verify nothing else references the old schema incorrectly**

Run: `./venv/bin/pytest tests/test_registry_lifecycle.py -q`
Expected: PASS (doc-only change; tests still green)

- [ ] **Step 3: Commit**

```bash
git add registry/SCHEMA.md
git commit -m "docs(registry): document the manifest evidence block (R-10)"
```

---

## Final Verification

- [ ] `./venv/bin/pytest tests/test_registry_lifecycle.py -v` — all R-10 tests pass
- [ ] `./venv/bin/pytest tests/ -k "registry or architecture or boundary" -q` — loader + boundary guards still green (no engine→research import introduced)
- [ ] `./venv/bin/pytest -q` — full suite green; real registry loads with `violations=[]`, `debt=[NR7_BULL_v1]`, governance unchanged
- [ ] `git log --oneline` — one commit per task on `ops/hardening-2026-07-10`
