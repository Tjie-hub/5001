# M4-lite — Research-Data Write Fence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CI-enforce that only `research/` writes `wf_scores`/`wf_edge`/`backtest_cache` (DAO exception: `engine/wf_edge.py`), completing the separation of authority without touching any reader.

**Architecture:** Spec: `docs/superpowers/specs/2026-07-08-m4-lite-write-fence-design.md`. One source-scan test (the proven boundary/db-centralization pattern) + two doc edits. Zero production `.py` changes → **no app restart needed**.

**Tech Stack:** pytest, regex source scan. Baseline suite 1111 passed / 3 skipped.

---

### Task 1: The fence test

**Files:**
- Create: `tests/test_research_data_fence.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_research_data_fence.py
"""M4-lite (spec 2026-07-08): wf_scores / wf_edge / backtest_cache are research
data products — ONLY research/ may write them. Production reads are unchanged
and allowed; this fence covers the WRITE side. DAO exception: engine/wf_edge.py
holds the table's write SQL, but its data-write fn is only callable from
research/ (rule W2)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Same scope convention as tests/test_architecture_boundary.py.
PRODUCTION_SCOPES = ["scheduler", "engine", "forward_testing", "data", "screener"]
PRODUCTION_FILES = ["monitor.py", "paper_trade.py", "app.py",
                    "news_filter.py", "flow_filter.py", "stockbit_fetcher.py"]

RESEARCH_TABLES = ("wf_scores", "wf_edge", "backtest_cache")
# Data-writes only. CREATE TABLE IF NOT EXISTS (ensure-schema by readers) is
# deliberately allowed — schema-safety, not a data write.
WRITE_SQL = re.compile(
    r"(INSERT(?:\s+OR\s+\w+)?\s+INTO|UPDATE|REPLACE\s+INTO|DELETE\s+FROM|DROP\s+TABLE)"
    r"\s+(?:%s)\b" % "|".join(RESEARCH_TABLES), re.I | re.S)

# DAO exception — shrink-only, never grow silently.
DAO_ALLOWLIST = {"engine/wf_edge.py"}


def _py_files():
    for scope in PRODUCTION_SCOPES:
        yield from (ROOT / scope).rglob("*.py")
    for f in PRODUCTION_FILES:
        p = ROOT / f
        if p.exists():
            yield p


def test_w1_no_research_table_writes_in_production():
    offenders = []
    for p in _py_files():
        rel = str(p.relative_to(ROOT))
        if rel in DAO_ALLOWLIST:
            continue
        if WRITE_SQL.search(p.read_text(encoding="utf-8")):
            offenders.append(rel)
    assert not offenders, (
        "production writes research tables (only research/ may): %s" % offenders)


def test_w2_save_wf_edge_only_called_from_research():
    offenders = []
    for p in _py_files():
        rel = str(p.relative_to(ROOT))
        if rel in DAO_ALLOWLIST:          # the definition itself
            continue
        src = p.read_text(encoding="utf-8")
        if re.search(r"\bsave_wf_edge\s*\(", src):
            offenders.append(rel)
    assert not offenders, f"production calls save_wf_edge (research-only): {offenders}"


def test_dao_allowlist_shrinks_only():
    assert len(DAO_ALLOWLIST) == 1
```

- [ ] **Step 2: Run — must PASS on the current tree** (grounded: only wf_edge.py has write SQL)

Run: `./venv/bin/python -m pytest tests/test_research_data_fence.py -q`
Expected: PASS (3 passed)

- [ ] **Step 3: Teeth check**

Seed `_ = "INSERT INTO wf_scores VALUES (1)"  # TEETH-TEST` at the top of `monitor.py`,
rerun → W1 must FAIL listing `monitor.py`; revert the line; rerun → PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_research_data_fence.py
git commit -m "test(arch): research-data write fence — only research/ writes wf tables (M4-lite)"
```

---

### Task 2: Documentation amendments

**Files:**
- Modify: `docs/superpowers/specs/2026-07-07-research-production-separation-design.md` (§10 M4 row)
- Modify: `registry/SCHEMA.md` (append section)

- [ ] **Step 1: Amend the original spec's M4 row** — replace the `**M4 — DB split**` row's
content cell with:

```
**AMENDED 2026-07-08 → M4-lite** (see specs/2026-07-08-m4-lite-write-fence-design.md):
grounding found ~10 production readers, so the physical move would rewrite the trade
path. Implemented instead: write-fence CI test (only research/ writes wf_scores/
wf_edge/backtest_cache; DAO exception engine/wf_edge.py). Physical split deferred
until each reader is individually retired.
```

- [ ] **Step 2: Append to `registry/SCHEMA.md`**

```markdown

## Research data products (M4-lite, 2026-07-08)

`wf_scores`, `wf_edge`, `backtest_cache` live in `walkforward.db` but are research
data products: **only `research/` writes them** (CI-enforced by
`tests/test_research_data_fence.py`; DAO exception `engine/wf_edge.py`, whose
`save_wf_edge` is research-only by rule W2). Production may read them (legacy gates,
dashboards); each such reader's retirement toward registry-artifact evidence is a
future, separate decision. `ensure_wf_edge_table` (idempotent CREATE) stays usable by
readers — schema-safety, not a data write.
```

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-07-07-research-production-separation-design.md registry/SCHEMA.md
git commit -m "docs(arch): record M4-lite amendment + research-data-product contract"
```

---

### Task 3: Regression + finish (no restart)

- [ ] **Step 1: Full suite** — `./venv/bin/python -m pytest -q`
Expected: 1111 baseline + 3 new = 1114 passed, 3 skipped.

- [ ] **Step 2: PR to master** — body: the amendment rationale (10-reader grounding),
the two rules, teeth-verification, "no production .py touched → no restart". CI, manual
merge, merge into prod branch `feat/tfb-context-filter` (clear untracked doc copies).
**No app restart** — verify `git diff --stat` shows only tests/ + docs/ + registry/SCHEMA.md.

- [ ] **Step 3: Memory** — separation memory: M4-lite done ⇒ **separation M1–M4 COMPLETE**
(M5 repo split deferred indefinitely); note the deferred-retirement list.

---

## Self-Review Notes
- Spec coverage: W1+W2+shrink guard (T1), spec amendment + SCHEMA.md contract (T2) — all
  DoD items mapped. CREATE excluded from W1 per spec (schema-safety).
- No placeholders; regex shown in full; teeth check explicit.
- Consistency: scope lists mirror the boundary test verbatim; DAO path identical across
  W1/W2/docs.
