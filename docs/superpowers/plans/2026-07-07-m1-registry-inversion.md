# M1 — Edge Registry Inversion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Production stops reading `wf_edge` live and instead reads a git-versioned Edge Registry (entry + frozen universe artifact + approval manifest + compatibility check) — behavior-identical by construction.

**Architecture:** Per spec §6/§10-M1 (docs/superpowers/specs/2026-07-07-research-production-separation-design.md). New `registry/` holds `edge_registry.yaml` (NR7_BULL v1, APPROVED), a frozen ticker artifact generated from today's `wf_edge>0` set, an approval manifest, and SCHEMA.md. New `engine/registry_loader.py` validates schema + `requires` vs `ENGINE_VERSIONS`, skips incompatible entries with a `fail_open_alarm`, and exposes `approved_universe(strategy_fn)`. `_edge_selectable` consults the registry for governed strategies (NR7 only today) and falls back to the legacy live `wf_edge` query for ungoverned ones — so the selector output is unchanged. M2–M4 are explicitly out of scope.

**Tech Stack:** Python 3, PyYAML 6.0.3 (verified in venv), stdlib `json`/`hashlib`/`subprocess`, existing `engine/fail_open_alarm.py`, pytest.

---

## Loader API (used consistently in every task)

```python
# engine/registry_loader.py
ENGINE_VERSIONS = {'data_schema': 1, 'exit_kernel': 1, 'regime_model': 1, 'engine_version': 1}
load_registry(path=None, engine_versions=None) -> dict
    # {'entries': [entry, ...], 'skipped': [(id_version, reason), ...], 'hash': '<sha or git>'}
    # entry = raw yaml dict + entry['universe'] = set(tickers) loaded from its artifact
get_registry() -> dict            # cached singleton of load_registry(); _reset_cache() for tests
approved_universe(strategy_fn) -> set | None   # None = strategy not registry-governed
startup_summary() -> str          # "registry @<hash>: N approved, M shadow, K skipped"
```

Statuses: only `APPROVED` and `SHADOW` entries load; `CANDIDATE/RETIRED/SUSPENDED/SUPERSEDED`
are ignored silently (they are lifecycle states, not errors). Invalid schema or `requires`
mismatch → entry goes to `skipped` + one `fail_open_alarm(..., notify=False)` per entry.
Loader failure anywhere → `approved_universe` returns None → selector falls back to legacy
behavior (safe migration fallback) + alarm.

---

### Task 1: Freeze script + registry files

**Files:**
- Create: `scripts/freeze_nr7_universe.py`
- Create: `registry/SCHEMA.md`
- Create: `registry/edge_registry.yaml`
- Create: `registry/manifests/NR7_BULL_v1.yaml`
- Generated: `registry/artifacts/NR7_BULL_v1_tickers.json`

- [ ] **Step 1: Write the freeze script**

```python
#!/usr/bin/env python3
"""One-off M1 freeze: snapshot today's live NR7 eligibility (wf_edge>0) into the
registry artifact, so production can stop querying wf_edge (spec §10-M1)."""
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.db import connect as db_connect

DB_PATH = os.getenv('DB_PATH', os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'data', 'walkforward.db'))
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'registry', 'artifacts', 'NR7_BULL_v1_tickers.json')

conn = db_connect(DB_PATH)
tickers = sorted(r[0] for r in conn.execute(
    "SELECT ticker FROM wf_edge WHERE strategy='NR7 Breakout' AND expectancy_pct>0"))
conn.close()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w') as f:
    json.dump({'strategy': 'NR7 Breakout', 'frozen_at': str(date.today()),
               'source': "wf_edge WHERE strategy='NR7 Breakout' AND expectancy_pct>0",
               'tickers': tickers}, f, indent=2)
print(f"froze {len(tickers)} tickers -> {OUT}")
```

- [ ] **Step 2: Run it against the prod DB**

Run: `DB_PATH="/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db" ./venv/bin/python scripts/freeze_nr7_universe.py`
Expected: `froze 35 tickers -> …/registry/artifacts/NR7_BULL_v1_tickers.json` (count ≈35, the current wf_edge>0 NR7 set).

- [ ] **Step 3: Write the registry entry**

```yaml
# registry/edge_registry.yaml — the ONLY research→production interface (spec §6).
# Entries are IMMUTABLE once status leaves CANDIDATE; changes = new version.
- id: NR7_BULL
  version: 1
  status: APPROVED
  strategy_fn: "NR7 Breakout"
  regimes: [BULL_MODERATE, BULL_STRONG]
  universe_artifact: artifacts/NR7_BULL_v1_tickers.json
  risk_category: breakout-long
  owner: tjie
  approved: "2026-07-04"
  manifest: manifests/NR7_BULL_v1.yaml
  requires:
    data_schema: 1
    exit_kernel: 1
    regime_model: 1
    engine_version: 1
  changelog: "v1 — M1 freeze of the live config approved after the Phase-2 recompute (PR #12) and generalization study (PR #18)."
```

- [ ] **Step 4: Write the approval manifest**

```yaml
# registry/manifests/NR7_BULL_v1.yaml — immutable approval evidence (spec §6).
approval:
  strategy: NR7_BULL
  version: 1
  approved_by: tjie
  approval_date: "2026-07-04"
  decision: "APPROVED for BULL regimes only; per-ticker universe frozen from wf_edge>0. SIDEWAYS explicitly rejected (-0.82%/trade, N=628)."
artifacts:
  walkforward: docs/superpowers/results/2026-07-07-nr7-generalization-study.md
  universe: artifacts/NR7_BULL_v1_tickers.json
  report: docs/superpowers/results/2026-07-07-regime-edge-scan.md
  config_hash: "sha256 of engine/strategies.py::strategy_nr7_breakout at code_commit (see below)"
  code_commit: "<filled at execution: git rev-parse HEAD of the freeze commit>"
  corpus_snapshot: {as_of: "2026-07-07", basis: "raw is_final (Phase 2A)", history: "5y"}
evidence_summary:
  oos: {exp_net_pct: 1.18, n_trades: 346, win_pct: 54.0, regime: BULL}
  pooled_44_ticker: {exp_net_pct: 1.75, n_trades: 1061}
  robustness: {universe_generalization: FAIL (T1 -0.001%), regime_stratification: BULL PASS, sideways: REJECTED}
  shadow: {from: "2026-07-04", trades: 0, verdict: pending}
```

At execution: replace `code_commit` with the real `git rev-parse HEAD` output and
`config_hash` with `sha256sum` of the `strategy_nr7_breakout` source block (one command
each; exact values pasted into the file before committing).

- [ ] **Step 5: Write `registry/SCHEMA.md`**

```markdown
# Edge Registry Schema (v1)

## edge_registry.yaml — list of entries
| field | type | req | notes |
|---|---|---|---|
| id | str | ✓ | `<FAMILY>_<REGIME-SCOPE>`, stable across versions |
| version | int | ✓ | immutable once status leaves CANDIDATE |
| status | enum | ✓ | CANDIDATE, SHADOW, APPROVED, SUSPENDED, RETIRED, SUPERSEDED |
| strategy_fn | str | ✓ | key into STRATEGY_FUNCS / checker dispatch |
| regimes | list | ✓ | regime-map bands the strategy may trade |
| universe_artifact | path | ✓ | frozen ticker JSON, relative to registry/ |
| risk_category | str | ✓ | descriptive |
| owner | str | ✓ | |
| approved | date | ✓ for APPROVED/SHADOW | |
| manifest | path | ✓ for APPROVED/SHADOW | approval manifest, relative to registry/ |
| requires | map | ✓ | data_schema, exit_kernel, regime_model, engine_version (ints) |
| changelog | str | ✓ | |

## Loading rules (engine/registry_loader.py)
- Only APPROVED and SHADOW load. Other statuses are ignored (lifecycle, not error).
- Missing required field, unreadable artifact, or any `requires` value ≠ the engine's
  ENGINE_VERSIONS ⇒ entry SKIPPED + fail-open alarm; engine continues with the rest.
- Production reads the registry ONCE at startup and logs its hash.

## Immutability & promotion
Promotion/suspension/rollback = git commit (PR + CI + manual merge). Never edit an
approved entry — supersede it with a new version.
```

- [ ] **Step 6: Commit**

```bash
git add scripts/freeze_nr7_universe.py registry/
git commit -m "feat(registry): M1 registry files — NR7_BULL v1 entry, frozen universe, manifest, schema"
```

---

### Task 2: Registry loader (TDD)

**Files:**
- Create: `engine/registry_loader.py`
- Test: `tests/test_registry_loader.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_registry_loader.py
"""Loader: schema validation, compatibility gate, universe loading, banner."""
import json
import yaml
import pytest

import engine.registry_loader as rl


def _mk_registry(tmp_path, entries, tickers=("AAAA", "BBBB")):
    reg = tmp_path / "registry"
    (reg / "artifacts").mkdir(parents=True)
    art = reg / "artifacts" / "u.json"
    art.write_text(json.dumps({"tickers": list(tickers)}))
    for e in entries:
        e.setdefault("universe_artifact", "artifacts/u.json")
    (reg / "edge_registry.yaml").write_text(yaml.safe_dump(entries))
    return str(reg / "edge_registry.yaml")


def _entry(**kw):
    base = dict(id="NR7_BULL", version=1, status="APPROVED",
                strategy_fn="NR7 Breakout", regimes=["BULL_MODERATE"],
                risk_category="breakout-long", owner="t", approved="2026-07-04",
                manifest="manifests/x.yaml",
                requires=dict(data_schema=1, exit_kernel=1,
                              regime_model=1, engine_version=1),
                changelog="v1")
    base.update(kw)
    return base


def test_valid_entry_loads_with_universe(tmp_path, monkeypatch):
    monkeypatch.setattr(rl, "fail_open_alarm", lambda *a, **k: "")
    path = _mk_registry(tmp_path, [_entry()])
    r = rl.load_registry(path=path)
    assert len(r["entries"]) == 1 and r["skipped"] == []
    assert r["entries"][0]["universe"] == {"AAAA", "BBBB"}
    assert r["hash"]


def test_candidate_status_ignored_silently(tmp_path, monkeypatch):
    alarms = []
    monkeypatch.setattr(rl, "fail_open_alarm", lambda *a, **k: alarms.append(a) or "")
    path = _mk_registry(tmp_path, [_entry(status="CANDIDATE")])
    r = rl.load_registry(path=path)
    assert r["entries"] == [] and r["skipped"] == [] and alarms == []


def test_requires_mismatch_skipped_with_alarm(tmp_path, monkeypatch):
    alarms = []
    monkeypatch.setattr(rl, "fail_open_alarm", lambda *a, **k: alarms.append(a) or "")
    bad = _entry(requires=dict(data_schema=1, exit_kernel=2,   # kernel bumped
                               regime_model=1, engine_version=1))
    path = _mk_registry(tmp_path, [bad])
    r = rl.load_registry(path=path)
    assert r["entries"] == []
    assert len(r["skipped"]) == 1 and "exit_kernel" in r["skipped"][0][1]
    assert len(alarms) == 1


def test_missing_field_skipped_with_alarm(tmp_path, monkeypatch):
    alarms = []
    monkeypatch.setattr(rl, "fail_open_alarm", lambda *a, **k: alarms.append(a) or "")
    e = _entry()
    del e["regimes"]
    path = _mk_registry(tmp_path, [e])
    r = rl.load_registry(path=path)
    assert r["entries"] == [] and len(r["skipped"]) == 1 and len(alarms) == 1


def test_approved_universe_and_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(rl, "fail_open_alarm", lambda *a, **k: "")
    path = _mk_registry(tmp_path, [_entry(), _entry(id="X_S", status="SHADOW",
                                                    strategy_fn="Xs")])
    monkeypatch.setattr(rl, "REGISTRY_PATH", path)
    rl._reset_cache()
    assert rl.approved_universe("NR7 Breakout") == {"AAAA", "BBBB"}
    assert rl.approved_universe("nonexistent") is None
    s = rl.startup_summary()
    assert "1 approved" in s and "1 shadow" in s and "0 skipped" in s
    rl._reset_cache()
```

- [ ] **Step 2: Run to verify failure**

Run: `./venv/bin/python -m pytest tests/test_registry_loader.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine.registry_loader'`

- [ ] **Step 3: Implement**

```python
# engine/registry_loader.py
"""Edge Registry loader — the production side of the research→production contract.

Spec: docs/superpowers/specs/2026-07-07-research-production-separation-design.md §6.
Production reads the registry ONCE (cached), validates schema + compatibility, and
exposes approved_universe() to the selector. Incompatible/invalid entries are skipped
with a visible alarm; loader failure degrades to None (selector falls back to legacy
behavior) — never crashes the engine.
"""
import hashlib
import json
import logging
import os
import subprocess

import yaml

from engine.fail_open_alarm import fail_open_alarm

logger = logging.getLogger(__name__)

ENGINE_VERSIONS = {'data_schema': 1, 'exit_kernel': 1,
                   'regime_model': 1, 'engine_version': 1}

REGISTRY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             'registry', 'edge_registry.yaml')

_REQUIRED = ('id', 'version', 'status', 'strategy_fn', 'regimes',
             'universe_artifact', 'requires', 'changelog')
_LOADABLE = ('APPROVED', 'SHADOW')
_LIFECYCLE = ('CANDIDATE', 'SUSPENDED', 'RETIRED', 'SUPERSEDED')

_cache = None


def _registry_hash(path):
    try:
        out = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'],
                             cwd=os.path.dirname(path), capture_output=True,
                             text=True, timeout=5)
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def load_registry(path=None, engine_versions=None):
    path = path or REGISTRY_PATH
    versions = engine_versions or ENGINE_VERSIONS
    with open(path, 'r') as f:
        raw = yaml.safe_load(f) or []
    entries, skipped = [], []
    for e in raw:
        ident = f"{e.get('id', '?')}_v{e.get('version', '?')}"
        status = e.get('status')
        if status in _LIFECYCLE:
            continue                       # lifecycle state, not an error
        missing = [k for k in _REQUIRED if k not in e]
        if status not in _LOADABLE or missing:
            reason = f"invalid: status={status}, missing={missing}"
            skipped.append((ident, reason))
            fail_open_alarm("edge_registry", f"{ident} skipped — {reason}",
                            count=1, notify=False)
            continue
        mismatch = {k: (v, versions.get(k)) for k, v in e['requires'].items()
                    if versions.get(k) != v}
        if mismatch:
            reason = "incompatible: " + ", ".join(
                f"{k} needs {a} engine has {b}" for k, (a, b) in mismatch.items())
            skipped.append((ident, reason))
            fail_open_alarm("edge_registry", f"{ident} skipped — {reason}",
                            count=1, notify=False)
            continue
        art = os.path.join(os.path.dirname(path), e['universe_artifact'])
        try:
            with open(art, 'r') as f:
                e = dict(e, universe=set(json.load(f)['tickers']))
        except Exception as ex:
            skipped.append((ident, f"artifact unreadable: {ex}"))
            fail_open_alarm("edge_registry", f"{ident} artifact unreadable: {ex}",
                            count=1, notify=False)
            continue
        entries.append(e)
    return {'entries': entries, 'skipped': skipped, 'hash': _registry_hash(path)}


def get_registry():
    global _cache
    if _cache is None:
        try:
            _cache = load_registry()
        except Exception as ex:
            fail_open_alarm("edge_registry", f"registry load failed: {ex}", count=1)
            _cache = {'entries': [], 'skipped': [('*', str(ex))], 'hash': 'load-failed'}
    return _cache


def _reset_cache():
    global _cache
    _cache = None


def approved_universe(strategy_fn):
    """Frozen ticker set for an APPROVED registry strategy; None if not governed."""
    for e in get_registry()['entries']:
        if e['strategy_fn'] == strategy_fn and e['status'] == 'APPROVED':
            return e['universe']
    return None


def startup_summary():
    r = get_registry()
    n_app = sum(1 for e in r['entries'] if e['status'] == 'APPROVED')
    n_sh = sum(1 for e in r['entries'] if e['status'] == 'SHADOW')
    return (f"registry @{r['hash']}: {n_app} approved, {n_sh} shadow, "
            f"{len(r['skipped'])} skipped")
```

- [ ] **Step 4: Run to verify pass**

Run: `./venv/bin/python -m pytest tests/test_registry_loader.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/registry_loader.py tests/test_registry_loader.py
git commit -m "feat(registry): loader — schema + compatibility gate + universe + banner (M1)"
```

---

### Task 3: Selector switch (TDD, parity-proven)

**Files:**
- Modify: `scheduler/scanner.py:642-664` (`_edge_selectable`)
- Test: `tests/test_registry_selector.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_registry_selector.py
"""_edge_selectable: registry-governed strategies use the frozen universe;
ungoverned strategies keep the legacy live wf_edge query; parity guaranteed."""
import sqlite3
import pytest

import engine.registry_loader as rl
from scheduler.scanner import _edge_selectable


@pytest.fixture
def wfdb(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "wf.db"))
    conn.execute("CREATE TABLE wf_edge (ticker TEXT, strategy TEXT, expectancy_pct REAL)")
    conn.executemany("INSERT INTO wf_edge VALUES (?,?,?)", [
        ("AAAA", "NR7 Breakout", 2.0),
        ("BBBB", "NR7 Breakout", -1.0),          # negative → not selectable
        ("AAAA", "momentum", 1.0),               # ungoverned strategy
    ])
    return conn


def _govern(monkeypatch, universe):
    monkeypatch.setattr(rl, "approved_universe",
                        lambda s: set(universe) if s == "NR7 Breakout" else None)


def test_governed_uses_frozen_universe_not_db(wfdb, monkeypatch):
    _govern(monkeypatch, {"AAAA"})
    # BBBB not in frozen set → NR7 not selectable, even if wf_edge changed later
    assert "NR7 Breakout" in _edge_selectable(wfdb, "AAAA", ["NR7 Breakout"])
    assert _edge_selectable(wfdb, "BBBB", ["NR7 Breakout"]) == []


def test_parity_frozen_equals_legacy_query(wfdb, monkeypatch):
    # freeze == current wf_edge>0 set → outputs identical to the legacy behavior
    _govern(monkeypatch, {"AAAA"})   # exactly the wf_edge>0 NR7 set in this fixture
    for tk in ("AAAA", "BBBB"):
        legacy = [r[0] for r in wfdb.execute(
            "SELECT strategy FROM wf_edge WHERE ticker=? AND expectancy_pct>0 "
            "AND strategy='NR7 Breakout'", (tk,))]
        new = _edge_selectable(wfdb, tk, ["NR7 Breakout"])
        assert set(new) == set(legacy)


def test_ungoverned_strategy_keeps_live_query(wfdb, monkeypatch):
    _govern(monkeypatch, {"AAAA"})
    out = _edge_selectable(wfdb, "AAAA", ["NR7 Breakout", "momentum"])
    assert set(out) == {"NR7 Breakout", "momentum"}   # momentum via legacy wf_edge


def test_registry_unavailable_falls_back_to_legacy(wfdb, monkeypatch):
    monkeypatch.setattr(rl, "approved_universe", lambda s: None)   # not governed
    out = _edge_selectable(wfdb, "AAAA", ["NR7 Breakout"])
    assert out == ["NR7 Breakout"]                    # legacy path still works
```

- [ ] **Step 2: Run to verify failure**

Run: `./venv/bin/python -m pytest tests/test_registry_selector.py -q`
Expected: FAIL — governed tests fail (`BBBB` returns NR7 via the legacy query; the
frozen-universe branch doesn't exist yet). The fallback test may already pass.

- [ ] **Step 3: Implement the switch** — replace `_edge_selectable`'s body:

```python
def _edge_selectable(conn, ticker: str, candidates) -> list:
    """Strategies with a live edge for `ticker`.

    Registry-governed strategies (spec §6, M1 inversion): eligibility comes from
    the FROZEN universe artifact in registry/ — production no longer reads
    research's wf_edge for them. Ungoverned strategies keep the legacy live
    wf_edge query (positive pooled OOS expectancy, Phase 2C / audit C-6).
    Governed results first, then ungoverned by expectancy DESC.
    """
    if candidates is not None and not candidates:
        return []
    from engine.registry_loader import approved_universe
    governed, ungoverned = [], []
    scan = candidates if candidates is not None else None
    if scan is None:
        ungoverned = None          # legacy: scan every strategy in wf_edge
    else:
        for s in scan:
            uni = approved_universe(s)
            if uni is not None:
                if ticker in uni:
                    governed.append(s)
            else:
                ungoverned.append(s)
    result = list(governed)
    if ungoverned is None or ungoverned:
        sql = ("SELECT strategy FROM wf_edge "
               "WHERE ticker = ? AND expectancy_pct > 0")
        params = [ticker]
        if ungoverned is not None:
            sql += " AND strategy IN (%s)" % ",".join("?" * len(ungoverned))
            params += list(ungoverned)
        sql += " ORDER BY expectancy_pct DESC"
        try:
            for r in conn.execute(sql, params).fetchall():
                if r[0] not in result:
                    result.append(r[0])
        except Exception:
            pass
    return result
```

Note: `candidates=None` (the `get_ticker_best_strategies` path) keeps the pure legacy
scan-everything query, then governed strategies found by it are still correct because
the freeze equals the wf_edge state at migration; registry governance for that path
tightens naturally when wf_edge diverges — acceptable and documented (the adaptive
selector, the only trade-path caller, always passes explicit candidates).

- [ ] **Step 4: Run to verify pass (+ firm tests untouched)**

Run: `./venv/bin/python -m pytest tests/test_registry_selector.py tests/agent_firm/ tests/test_scheduler_firm_hook.py tests/test_edge_selector.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scheduler/scanner.py tests/test_registry_selector.py
git commit -m "feat(registry): selector inversion — governed strategies read frozen universe (M1)"
```

---

### Task 4: Startup wiring (banner + Telegram)

**Files:**
- Modify: `scheduler/__init__.py` (after `scheduler.start()`, beside the existing banner prints)
- Test: `tests/test_registry_loader.py` (append one test)

- [ ] **Step 1: Append the failing test**

```python
def test_startup_banner_helper_never_raises(monkeypatch):
    # announce_registry logs + telegrams best-effort; must never raise.
    import engine.registry_loader as rl2
    monkeypatch.setattr(rl2, "get_registry",
                        lambda: {'entries': [], 'skipped': [], 'hash': 'x'})
    sent = []
    rl2.announce_registry(telegram_fn=lambda m: sent.append(m))
    assert sent and "registry @x" in sent[0]

    def _boom(_m):
        raise RuntimeError("down")
    rl2.announce_registry(telegram_fn=_boom)   # must not raise
```

- [ ] **Step 2: Run to verify failure**

Run: `./venv/bin/python -m pytest tests/test_registry_loader.py -k banner -q`
Expected: FAIL — `announce_registry` missing

- [ ] **Step 3: Implement** (append to `engine/registry_loader.py`)

```python
def announce_registry(telegram_fn=None):
    """Log + best-effort Telegram the loaded registry state at startup."""
    msg = "📜 " + startup_summary()
    logger.info(msg)
    print(f"  {msg}")
    if telegram_fn is None:
        try:
            from utils.telegram import send_telegram as telegram_fn
        except Exception:
            return
    try:
        telegram_fn(msg)
    except Exception as ex:
        logger.debug("registry announce telegram failed: %s", ex)
```

And in `scheduler/__init__.py`, directly after the existing
`print("  💓 SCHEDULER HEARTBEAT: every 5 min (dead-man's-switch)")` line:

```python
    from engine.registry_loader import announce_registry
    announce_registry()
```

- [ ] **Step 4: Run to verify pass**

Run: `./venv/bin/python -m pytest tests/test_registry_loader.py -q && ./venv/bin/python -c "import scheduler"`
Expected: PASS + import OK

- [ ] **Step 5: Commit**

```bash
git add engine/registry_loader.py scheduler/__init__.py tests/test_registry_loader.py
git commit -m "feat(registry): startup banner + telegram announce (M1)"
```

---

### Task 5: Live parity check + manifest finalization

**Files:**
- Modify: `registry/manifests/NR7_BULL_v1.yaml` (fill code_commit + config_hash)

- [ ] **Step 1: Verify freeze parity against the live DB**

Run:
```bash
DB_PATH="/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db" ./venv/bin/python - <<'EOF'
import json, sqlite3, os
art = json.load(open('registry/artifacts/NR7_BULL_v1_tickers.json'))['tickers']
c = sqlite3.connect(os.environ['DB_PATH'])
live = sorted(r[0] for r in c.execute(
    "SELECT ticker FROM wf_edge WHERE strategy='NR7 Breakout' AND expectancy_pct>0"))
assert art == live, f"DRIFT: artifact {len(art)} vs live {len(live)}"
print(f"PARITY OK — {len(art)} tickers identical")
EOF
```
Expected: `PARITY OK — 35 tickers identical`

- [ ] **Step 2: Fill manifest provenance fields**

Run: `git rev-parse HEAD` and paste into `code_commit`; run
`./venv/bin/python -c "import hashlib,inspect;from engine.strategies import strategy_nr7_breakout;print(hashlib.sha256(inspect.getsource(strategy_nr7_breakout).encode()).hexdigest())"`
and paste into `config_hash`. Commit:

```bash
git add registry/manifests/NR7_BULL_v1.yaml
git commit -m "docs(registry): finalize NR7_BULL v1 manifest provenance (M1)"
```

---

### Task 6: Regression + finish + deploy

- [ ] **Step 1: Full suite**

Run: `./venv/bin/python -m pytest -q`
Expected: baseline 1088 passed + ~10 new registry tests, 3 skipped, no new failures.
(Known quirk: run `tests/agent_firm/` before `tests/test_scheduler_firm_hook.py` if
running subsets — import-order artifact, unrelated.)

- [ ] **Step 2: Finish the branch**

Use **superpowers:finishing-a-development-branch**: push, PR to `master` (body: spec link,
the inversion explained, parity proof, behavior-identical claim), wait CI, manual merge.

- [ ] **Step 3: Deploy**

Merge `origin/master` into prod branch `feat/tfb-context-filter` (remove any untracked
plan/spec-doc copies that block the merge — recurring pattern), restart via `./start.sh`
in a quiet slot, then verify:
```bash
grep "registry @" /tmp/app5001.log        # banner shows: 1 approved, 0 shadow, 0 skipped
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5001/    # 200
```
Also re-run the Task-5 parity check post-deploy (still identical), and confirm a Telegram
"📜 registry @…" message arrived.

---

## Self-Review Notes

- **Spec coverage (M1 items):** registry entry (T1), frozen artifact + freeze script (T1),
  approval manifest incl. config_hash/code_commit/corpus_snapshot (T1+T5), SCHEMA.md (T1),
  loader + ENGINE_VERSIONS + compat skip-with-alarm + hash banner (T2), selector inversion
  with legacy fallback (T3), startup wiring log+Telegram (T4), behavior-identity proof
  (T3 parity tests + T5/T6 live parity checks). M2–M4 untouched.
- **Type consistency:** `approved_universe(strategy_fn) -> set|None`, `load_registry ->
  {'entries','skipped','hash'}`, `announce_registry(telegram_fn=None)` used identically in
  impl, wiring, and tests.
- **Safety:** every failure path degrades to legacy behavior + alarm (never crashes the
  engine); production still never writes the registry; only NR7 is governed so blast
  radius is one strategy that currently fires zero trades.
- **Placeholder scan:** manifest `code_commit`/`config_hash` are execution-time fills with
  exact commands given (T5) — not deferred design.
