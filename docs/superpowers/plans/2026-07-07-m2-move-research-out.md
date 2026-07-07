# M2 — Move Research Out + CI Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Research modules move to `research/`, `STRATEGY_FUNCS` moves to the shared floor (`engine/strategies.py`), and a CI boundary test makes the separation enforceable — production behavior unchanged (import paths only).

**Architecture:** Spec §10-M2 (docs/superpowers/specs/2026-07-07-research-production-separation-design.md). Grounded reality is messier than the spec's assumption: dashboard routes and `scheduler/jobs.py` import research modules. Resolution: (a) `STRATEGY_FUNCS` is shared-floor material (a dict over `engine/strategies.py` functions) → relocate it there, converting `routes/portfolio.py` + `routes/screener.py` STRATEGY_FUNCS imports into *shared* imports (no boundary exception needed); (b) the remaining research imports (backtest dashboard pages = research UI; `jobs.py` research jobs = M3 scope) go on a **documented allowlist** in the boundary test that shrinks in M3. The trade path (scanner, monitor, paper_trade, forward_testing, engine core) is boundary-clean immediately.

**Tech Stack:** `git mv`, mechanical import rewrites, pytest. No behavior change anywhere.

---

## Move map

| From | To |
|---|---|
| `engine/walkforward_multi.py` | `research/walkforward_multi.py` |
| `engine/nr7_study.py` | `research/nr7_study.py` |
| `engine/optimizer.py` | `research/optimizer.py` |
| `engine/backtest_roller.py` | `research/backtest_roller.py` |
| `engine/portfolio_backtest.py` | `research/portfolio_backtest.py` |
| `engine/fastmover_study.py` | `research/fastmover_study.py` |
| `scripts/regime_edge_scan.py` | `research/studies/regime_edge_scan.py` |
| `scripts/nr7_generalization_study.py` | `research/studies/nr7_generalization_study.py` |

## Import rewrite table (mechanical; apply exactly)

| File | Old | New |
|---|---|---|
| `routes/portfolio.py:8` | `from engine.walkforward_multi import STRATEGY_FUNCS` | `from engine.strategies import STRATEGY_FUNCS` |
| `routes/screener.py:181,466,484` | same | same |
| `routes_backtest_multi.py:13` | `from engine.walkforward_multi import run_all_strategies, run_walk_forward` | `from research.walkforward_multi import …` (allowlisted) |
| `routes/backtest.py` (5 lazy sites) | `from engine.walkforward_multi import run_all_strategies` | `from research.walkforward_multi import run_all_strategies` (allowlisted) |
| `routes/backtest.py` optimizer import | `from engine.optimizer import …` | `from research.optimizer import …` (allowlisted) |
| `routes/backtest.py` roller import | `from engine.backtest_roller import …` | `from research.backtest_roller import …` (allowlisted) |
| `routes/portfolio.py:9` | `from engine.portfolio_backtest import run_portfolio_backtest` | `from research.portfolio_backtest import …` (allowlisted) |
| `routes/screener.py:154,161` | `from engine.fastmover_study import …` | `from research.fastmover_study import …` (allowlisted) |
| `scheduler/jobs.py:92,519` | `from engine.walkforward_multi import …` | `from research.walkforward_multi import …` (allowlisted until M3) |
| `scheduler/jobs.py:670` | `from engine.backtest_roller import …` | `from research.backtest_roller import …` (allowlisted until M3) |
| tests (7 files) + `scripts/tfb_trail_wf.py`, `scripts/wf_panic_rebound.py` | `engine.walkforward_multi` / `engine.nr7_study` / `engine.optimizer` / `engine.backtest_roller` / `engine.portfolio_backtest` / `scripts.regime_edge_scan` / `scripts.nr7_generalization_study` | `research.…` / `research.studies.…` |
| moved modules internally | `from .strategies import …` / `from engine.walkforward_multi import …` / `from engine.nr7_study import …` | `from engine.strategies import …` / `from research.walkforward_multi import …` / `from research.nr7_study import …` |

---

### Task 1: Relocate STRATEGY_FUNCS to the shared floor

**Files:**
- Modify: `engine/strategies.py` (append at bottom), `engine/walkforward_multi.py:223-243`
- Test: `tests/test_strategy_funcs_home.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_strategy_funcs_home.py
"""M2: STRATEGY_FUNCS lives on the shared floor (engine.strategies), so the
dashboard and research both import it without crossing the boundary."""


def test_strategy_funcs_importable_from_strategies():
    from engine.strategies import STRATEGY_FUNCS
    assert len(STRATEGY_FUNCS) == 14
    assert "NR7 Breakout" in STRATEGY_FUNCS
    assert callable(STRATEGY_FUNCS["NR7 Breakout"])
```

- [ ] **Step 2: Run to verify failure**

Run: `./venv/bin/python -m pytest tests/test_strategy_funcs_home.py -q`
Expected: FAIL — `ImportError: cannot import name 'STRATEGY_FUNCS' from 'engine.strategies'`

- [ ] **Step 3: Move the dict** — append to the very bottom of `engine/strategies.py`
(verbatim from walkforward_multi.py:223-243, functions are all local names there):

```python
# ── Strategy registry dict (moved from walkforward_multi in M2) ──────────────
# Shared floor: research backtests and the production dashboard both import
# this; the definitions live in this module so there is no boundary crossing.
STRATEGY_FUNCS = {
    'vol_weighted':              strategy_vol_weighted,
    'momentum':                  strategy_momentum,
    'vwap_reversion':            strategy_vwap_reversion,
    'conservative':              strategy_conservative,
    'Volume Profile POC':        strategy_volume_profile_poc,
    'Inside Bar Breakout':       strategy_inside_bar_breakout,
    'NR7 Breakout':              strategy_nr7_breakout,
    'ORB':                       strategy_orb,
    'VWMA Breakout Pullback':    strategy_vwma_breakout_pullback,
    'Swing Trend':               strategy_swing_trend,
    'Trend Following Breakout':  strategy_trend_following_breakout,
    'Crash Recovery':            strategy_crash_recovery,
    'Panic Rebound':             strategy_panic_rebound,
    'Liquidity Sweep':           strategy_liquidity_sweep_flow,
    # 'Regime Adaptive' deregistered 2026-07-02 (audit C-7): whole-window
    # look-ahead. Re-register only after a per-bar reimplementation.
}
```

In `engine/walkforward_multi.py`, delete the dict definition and replace with:

```python
from engine.strategies import STRATEGY_FUNCS  # noqa: F401  (moved in M2 — shared floor)
```

(Keep the re-export so every existing importer works unchanged until Task 3 rewrites paths.)

- [ ] **Step 4: Run tests**

Run: `./venv/bin/python -m pytest tests/test_strategy_funcs_home.py tests/test_walkforward_registry.py tests/test_strategy_specs.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/strategies.py engine/walkforward_multi.py tests/test_strategy_funcs_home.py
git commit -m "refactor(arch): STRATEGY_FUNCS to shared floor engine.strategies (M2)"
```

---

### Task 2: git mv the research modules

**Files:** the move map above + `research/__init__.py`, `research/studies/__init__.py`

- [ ] **Step 1: Move with history**

```bash
mkdir -p research/studies
touch research/__init__.py research/studies/__init__.py
git mv engine/walkforward_multi.py research/walkforward_multi.py
git mv engine/nr7_study.py research/nr7_study.py
git mv engine/optimizer.py research/optimizer.py
git mv engine/backtest_roller.py research/backtest_roller.py
git mv engine/portfolio_backtest.py research/portfolio_backtest.py
git mv engine/fastmover_study.py research/fastmover_study.py
git mv scripts/regime_edge_scan.py research/studies/regime_edge_scan.py
git mv scripts/nr7_generalization_study.py research/studies/nr7_generalization_study.py
git add research/__init__.py research/studies/__init__.py
```

- [ ] **Step 2: Fix the moved modules' internal imports**

In `research/walkforward_multi.py`: `from .strategies import (` → `from engine.strategies import (`.
In `research/optimizer.py`, `research/backtest_roller.py`, `research/portfolio_backtest.py`:
`engine.walkforward_multi` → `research.walkforward_multi`.
In `research/studies/regime_edge_scan.py` and `research/studies/nr7_generalization_study.py`:
`engine.nr7_study` → `research.nr7_study`, `engine.walkforward_multi` → `research.walkforward_multi`
(their `sys.path.insert(0, dirname(dirname(...)))` headers need one more `dirname` since they
are now one level deeper — change to `dirname(dirname(dirname(abspath(__file__))))`).

- [ ] **Step 3: Verify the research package imports standalone**

Run: `./venv/bin/python -c "import research.walkforward_multi, research.nr7_study, research.optimizer, research.backtest_roller, research.portfolio_backtest, research.fastmover_study; print('RESEARCH PKG OK')"`
Expected: `RESEARCH PKG OK`

- [ ] **Step 4: Commit**

```bash
git add -A research/ engine/ scripts/
git commit -m "refactor(arch): move research modules to research/ (M2, git mv preserves history)"
```

---

### Task 3: Rewrite external importers

**Files:** `routes_backtest_multi.py`, `routes/backtest.py`, `routes/portfolio.py`,
`routes/screener.py`, `scheduler/jobs.py`, `scripts/tfb_trail_wf.py`,
`scripts/wf_panic_rebound.py`, and tests: `test_panic_rebound.py`,
`test_walkforward_registry.py`, `test_strategy_specs.py`, `test_walkforward_metrics.py`,
`scheduler/test_wf_refresh_lock.py`, `engine/test_strategy_sweep_flow.py`,
`test_nr7_study.py`, `test_optimizer.py`, `test_backtest_roller.py`,
`test_portfolio_backtest.py`, `test_regime_edge_scan.py`, `test_nr7_study_script.py`

- [ ] **Step 1: Apply the rewrite table mechanically**

```bash
# STRATEGY_FUNCS-only imports become SHARED imports (not research):
sed -i 's/from engine.walkforward_multi import STRATEGY_FUNCS/from engine.strategies import STRATEGY_FUNCS/' \
  routes/portfolio.py routes/screener.py
# everything else engine.<research module> → research.<module>:
sed -i 's/engine\.walkforward_multi/research.walkforward_multi/g; s/engine\.nr7_study/research.nr7_study/g; s/engine\.optimizer/research.optimizer/g; s/engine\.backtest_roller/research.backtest_roller/g; s/engine\.portfolio_backtest/research.portfolio_backtest/g; s/engine\.fastmover_study/research.fastmover_study/g' \
  routes_backtest_multi.py routes/backtest.py routes/portfolio.py routes/screener.py \
  scheduler/jobs.py scripts/tfb_trail_wf.py scripts/wf_panic_rebound.py \
  tests/test_panic_rebound.py tests/test_walkforward_registry.py tests/test_strategy_specs.py \
  tests/test_walkforward_metrics.py tests/scheduler/test_wf_refresh_lock.py \
  tests/engine/test_strategy_sweep_flow.py tests/test_nr7_study.py tests/test_optimizer.py \
  tests/test_backtest_roller.py tests/test_portfolio_backtest.py
# moved study scripts' test imports:
sed -i 's/scripts\.regime_edge_scan/research.studies.regime_edge_scan/g' tests/test_regime_edge_scan.py
sed -i 's/scripts\.nr7_generalization_study/research.studies.nr7_generalization_study/g' tests/test_nr7_study_script.py
```

Then verify nothing still references the old paths:

```bash
grep -rn "engine\.walkforward_multi\|engine\.nr7_study\|engine\.optimizer\|engine\.backtest_roller\|engine\.portfolio_backtest\|engine\.fastmover_study\|scripts\.regime_edge_scan\|scripts\.nr7_generalization" \
  --include="*.py" . | grep -v venv | grep -v scratchpad | grep -v _archive
```
Expected: no output (mocks in tests patching e.g. `"scheduler.jobs.run_walk_forward"` style
strings are unaffected; if any `"engine.walkforward_multi…"` PATCH STRINGS surface in test
files, rewrite those strings identically).

- [ ] **Step 2: Import + targeted test sweep**

Run: `./venv/bin/python -c "import app" 2>&1 | tail -2 && ./venv/bin/python -m pytest tests/test_walkforward_registry.py tests/test_strategy_specs.py tests/test_nr7_study.py tests/test_regime_edge_scan.py tests/test_optimizer.py tests/test_backtest_roller.py tests/test_portfolio_backtest.py tests/scheduler/ -q`
Expected: app imports; PASS

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "refactor(arch): rewrite research import paths across routes/jobs/tests (M2)"
```

---

### Task 4: CI boundary test

**Files:**
- Create: `tests/test_architecture_boundary.py`

- [ ] **Step 1: Write the boundary test (it should PASS immediately — it encodes the new invariant; verify it FAILS if seeded with a violation, step 2)**

```python
# tests/test_architecture_boundary.py
"""Architecture boundary (spec §2): production may not import research/;
research may not import execution. Source-scan enforcement, same pattern as
tests/test_db_centralization.py (Phase 3C)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RESEARCH_IMPORT = re.compile(r"^\s*(from|import)\s+research[.\s]", re.M)
EXECUTION_IMPORT = re.compile(
    r"^\s*(from|import)\s+(scheduler|monitor|paper_trade|forward_testing|app)[.\s]", re.M)

# Trade-path + engine surface that must stay research-free.
PRODUCTION_SCOPES = ["scheduler", "engine", "forward_testing", "data", "screener"]
PRODUCTION_FILES = ["monitor.py", "paper_trade.py", "app.py",
                    "news_filter.py", "flow_filter.py", "stockbit_fetcher.py"]

# Documented exceptions — each must shrink over time, never grow silently.
ALLOWLIST = {
    "scheduler/jobs.py",        # research jobs (refresh_wf_scores, roller) — REMOVED IN M3
}


def _py_files(scopes, files):
    for scope in scopes:
        yield from (ROOT / scope).rglob("*.py")
    for f in files:
        p = ROOT / f
        if p.exists():
            yield p


def test_production_does_not_import_research():
    offenders = []
    for p in _py_files(PRODUCTION_SCOPES, PRODUCTION_FILES):
        rel = str(p.relative_to(ROOT))
        if rel in ALLOWLIST:
            continue
        if RESEARCH_IMPORT.search(p.read_text(encoding="utf-8")):
            offenders.append(rel)
    assert not offenders, f"production imports research/: {offenders}"


def test_research_does_not_import_execution():
    offenders = []
    for p in (ROOT / "research").rglob("*.py"):
        if EXECUTION_IMPORT.search(p.read_text(encoding="utf-8")):
            offenders.append(str(p.relative_to(ROOT)))
    assert not offenders, f"research/ imports execution modules: {offenders}"


def test_allowlist_shrinks_only():
    # If someone adds an exception, this number forces a conscious edit + review.
    assert len(ALLOWLIST) == 1
```

Note: dashboard route files (`routes/`, `routes_backtest_multi.py`) are research-UI and
deliberately outside `PRODUCTION_SCOPES` — documented here and in the spec; the trade
path itself is fully covered.

- [ ] **Step 2: Verify the test has teeth**

Temporarily add `import research.walkforward_multi  # test` to the top of `monitor.py`,
run `./venv/bin/python -m pytest tests/test_architecture_boundary.py -q` → must FAIL
listing `monitor.py`; then revert the line and re-run → PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_architecture_boundary.py
git commit -m "test(arch): CI boundary — production↛research, research↛execution (M2)"
```

---

### Task 5: Regression + finish + deploy

- [ ] **Step 1: Full suite**

Run: `./venv/bin/python -m pytest -q`
Expected: 1098+ passed (baseline 1098 + boundary/home tests), 3 skipped, no new failures.

- [ ] **Step 2: Finish branch**

Push, PR to `master` (body: move map, rewrite table summary, boundary rules + allowlist,
"no behavior change — import paths only"), CI, manual merge.

- [ ] **Step 3: Deploy**

Merge master → prod branch `feat/tfb-context-filter` (clear untracked doc copies first —
recurring), restart in a quiet slot (route/jobs import paths changed → restart required),
verify: HTTP 200, registry banner still prints, no import errors in `/tmp/app5001.log`,
and the Friday WF-refresh job is still registered (it now imports research.walkforward_multi
via the allowlisted jobs.py — unchanged behavior until M3).

---

## Self-Review Notes

- **Spec coverage (M2):** modules moved with history (T2), boundary test in CI (T4),
  production untouched behaviorally — only import paths (T1/T3). Deviation from spec's
  optimistic assumption (routes/jobs import research) resolved explicitly: STRATEGY_FUNCS
  → shared floor (T1) removes two false positives; the rest is a documented, shrink-only
  allowlist (T4) with jobs.py earmarked for M3.
- **Cycle safety:** engine/strategies.py imports only indicators + exits.costs → adding
  STRATEGY_FUNCS there creates no cycle (grounded).
- **Type consistency:** move map, rewrite table, and boundary scopes reference identical
  paths throughout.
- **No placeholders:** every sed/command is literal; the patch-string caveat in T3 has a
  concrete detection step (the grep) rather than a vague warning.
