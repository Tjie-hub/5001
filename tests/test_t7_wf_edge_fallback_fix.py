"""D-031 (docs/roadmap/DECISION_LOG.md, ratified 2026-08-20) -- regression
tests for the fail-closed fix to scheduler.scanner._edge_selectable()'s
candidates=None branch.

Bug: `_edge_selectable(conn, ticker, None)` (reached from
`get_ticker_best_strategies()`, reached from `adaptive_strategy_selector()`'s
BULL-regime fallback at scanner.py:906) never called `registry_governance()`
-- it treated every positive `wf_edge` row as sufficient authorization,
including for a strategy the Edge Registry holds at SHADOW. Verified live
against production data before the fix: `NR7 Breakout` -- demoted
`APPROVED -> SHADOW` one day earlier by D-029 specifically for insufficient
evidence -- had 43 tickers with positive `wf_edge.expectancy_pct`, any of
which could have silently re-admitted it through this path.

Fix (D-031 Decision 1): `candidates=None` is now Registry-only -- a strategy
found via the unconstrained wf_edge scan must independently clear
`registry_governance()` (APPROVED, ticker in its frozen universe) before
selection. No legacy exception applies to this path (unlike the explicit-
candidates branch, D-031 Decision 2 / Option C, which is deliberately left
unchanged and is covered by the existing tests/test_edge_selector.py and
tests/test_registry_selector.py suites).

Real on-disk registry + wf_edge fixtures throughout (not mocking
registry_governance() itself) -- same discipline as
tests/test_t7_fail_closed_admission.py, proving the fix at the actual
admission boundary. No production/mutable data touched: every fixture is
tmp_path-scoped.
"""
import sqlite3

import numpy as np
import pandas as pd
import pytest
import yaml

import engine.registry_loader as rl
from scheduler.scanner import _edge_selectable, adaptive_strategy_selector, get_ticker_best_strategies


# ---------------------------------------------------------------------------
# Fixtures -- real on-disk registry (mirrors test_t7_fail_closed_admission.py)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _fresh_cache():
    rl._reset_cache()
    yield
    rl._reset_cache()


def _point_at(monkeypatch, path):
    monkeypatch.setattr(rl, "REGISTRY_PATH", path)
    rl._reset_cache()


def _valid_manifest(reg_dir, name, approved):
    man = reg_dir / "manifests"
    man.mkdir(parents=True, exist_ok=True)
    ev = {"gate_decision": {"final_state": "PROMOTE_TO_FORWARD_TEST"}}
    if approved:
        ev["forward"] = {"verdict": "GO", "n": 17, "exp_pct": 0.63}
    (reg_dir / name).write_text(yaml.safe_dump({"evidence": ev}))


def _mk_registry(tmp_path, entries, tickers):
    """Real on-disk edge_registry.yaml + universe artifact + manifests,
    pointed at via _point_at(). `entries` is a list of dicts merged onto a
    minimal valid schema; each entry's `manifest` gets a matching valid
    evidence file so validate_evidence() loads it cleanly (not testing the
    evidence-validation path here -- that's tests/test_registry_loader.py)."""
    reg = tmp_path / "registry"
    (reg / "artifacts").mkdir(parents=True)
    (reg / "artifacts" / "u.json").write_text(
        __import__("json").dumps({"tickers": list(tickers)})
    )
    out = []
    for e in entries:
        base = dict(
            id=e["id"], version=1, status=e["status"], strategy_fn=e["strategy_fn"],
            regimes=["BULL_MODERATE"], universe_artifact="artifacts/u.json",
            risk_category="test", owner="t", approved="2026-08-20",
            manifest=f"manifests/{e['id']}.yaml",
            requires=dict(data_schema=1, exit_kernel=1, regime_model=1, engine_version=1),
            changelog="v1",
        )
        out.append(base)
        _valid_manifest(reg, f"manifests/{e['id']}.yaml", approved=(e["status"] == "APPROVED"))
    (reg / "edge_registry.yaml").write_text(yaml.safe_dump(out))
    return str(reg / "edge_registry.yaml")


@pytest.fixture()
def wf_db(tmp_path, monkeypatch):
    """Real temp wf_edge table, patched into scanner.DB_PATH."""
    import scheduler.scanner as scanner
    db = str(tmp_path / "wf.db")
    monkeypatch.setattr(scanner, "DB_PATH", db)
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE wf_edge (
        ticker TEXT, strategy TEXT, expectancy_pct REAL, expectancy_rp REAL,
        win_rate REAL, consistency_pct REAL, sharpe REAL, n_trades INTEGER,
        windows_tested INTEGER, last_computed TEXT, PRIMARY KEY(ticker,strategy))""")
    conn.commit()
    conn.close()
    return db


def _insert_edge(db, ticker, strategy, expectancy_pct):
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT OR REPLACE INTO wf_edge VALUES (?,?,?,?,?,?,?,?,?,?)",
        (ticker, strategy, expectancy_pct, 0.0, 55.0, 40.0, 0.4, 60, 15, "2026-08-20"),
    )
    conn.commit()
    conn.close()


def _bull_df(n=90):
    """Steady uptrend -> detect_regime() returns BULL."""
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    close = 1000 + np.arange(n) * 8.0
    return pd.DataFrame({"date": dates, "open": close - 2, "high": close + 6,
                         "low": close - 6, "close": close,
                         "volume": np.full(n, 1e6)})


# ---------------------------------------------------------------------------
# 1-3. candidates=None: the core D-031 Decision 1 fix
# ---------------------------------------------------------------------------

def test_none_candidates_approved_strategy_eligible(tmp_path, monkeypatch, wf_db):
    """1. candidates=None + APPROVED strategy -> eligible if all other
    conditions pass (positive wf_edge, ticker in the frozen universe)."""
    reg_path = _mk_registry(
        tmp_path,
        [{"id": "T1", "status": "APPROVED", "strategy_fn": "Trend Following Breakout"}],
        tickers=("BBCA",),
    )
    _point_at(monkeypatch, reg_path)
    _insert_edge(wf_db, "BBCA", "Trend Following Breakout", 1.5)

    conn = sqlite3.connect(wf_db)
    got = _edge_selectable(conn, "BBCA", None)
    conn.close()
    assert got == ["Trend Following Breakout"]


def test_none_candidates_shadow_strategy_not_eligible(tmp_path, monkeypatch, wf_db):
    """2. candidates=None + SHADOW strategy -> NOT eligible, even with
    positive wf_edge expectancy for the ticker."""
    reg_path = _mk_registry(
        tmp_path,
        [{"id": "T1", "status": "SHADOW", "strategy_fn": "Trend Following Breakout"}],
        tickers=("BBCA",),
    )
    _point_at(monkeypatch, reg_path)
    _insert_edge(wf_db, "BBCA", "Trend Following Breakout", 1.5)

    conn = sqlite3.connect(wf_db)
    got = _edge_selectable(conn, "BBCA", None)
    conn.close()
    assert got == []


def test_none_candidates_unregistered_strategy_not_eligible(tmp_path, monkeypatch, wf_db):
    """3. candidates=None + unregistered strategy (no registry entry at
    all) -> NOT eligible. This is the D-031 Decision 1 policy line: no
    legacy exception on this path, unlike the explicit-candidates branch."""
    reg_path = _mk_registry(tmp_path, [], tickers=("BBCA",))
    _point_at(monkeypatch, reg_path)
    _insert_edge(wf_db, "BBCA", "Trend Following Breakout", 1.5)

    conn = sqlite3.connect(wf_db)
    got = _edge_selectable(conn, "BBCA", None)
    conn.close()
    assert got == []


# ---------------------------------------------------------------------------
# 4-5. Explicit candidates: existing (correct) behavior must be preserved
# ---------------------------------------------------------------------------

def test_explicit_candidates_approved_still_selected(tmp_path, monkeypatch, wf_db):
    """4. explicit candidates + APPROVED -> unchanged: still selected."""
    reg_path = _mk_registry(
        tmp_path,
        [{"id": "T1", "status": "APPROVED", "strategy_fn": "Trend Following Breakout"}],
        tickers=("BBCA",),
    )
    _point_at(monkeypatch, reg_path)

    conn = sqlite3.connect(wf_db)
    got = _edge_selectable(conn, "BBCA", ["Trend Following Breakout"])
    conn.close()
    assert got == ["Trend Following Breakout"]


def test_explicit_candidates_shadow_still_rejected(tmp_path, monkeypatch, wf_db):
    """5. explicit candidates + SHADOW -> unchanged: still rejected, and
    does NOT fall back to the legacy wf_edge query for that strategy
    (T7.P1.WS4.01, pre-existing and untouched by this fix)."""
    reg_path = _mk_registry(
        tmp_path,
        [{"id": "T1", "status": "SHADOW", "strategy_fn": "Trend Following Breakout"}],
        tickers=("BBCA",),
    )
    _point_at(monkeypatch, reg_path)
    _insert_edge(wf_db, "BBCA", "Trend Following Breakout", 1.5)

    conn = sqlite3.connect(wf_db)
    got = _edge_selectable(conn, "BBCA", ["Trend Following Breakout"])
    conn.close()
    assert got == []


def test_explicit_candidates_unregistered_still_uses_legacy_exception(tmp_path, monkeypatch, wf_db):
    """D-031 Decision 2 / Option C: the explicit-candidates branch's bounded
    legacy exception for genuinely unregistered strategies is UNCHANGED by
    this fix -- must not be broadened or narrowed."""
    reg_path = _mk_registry(tmp_path, [], tickers=("BBCA",))
    _point_at(monkeypatch, reg_path)
    _insert_edge(wf_db, "BBCA", "Trend Following Breakout", 1.5)

    conn = sqlite3.connect(wf_db)
    got = _edge_selectable(conn, "BBCA", ["Trend Following Breakout"])
    conn.close()
    assert got == ["Trend Following Breakout"]


# ---------------------------------------------------------------------------
# 6. Empty candidates
# ---------------------------------------------------------------------------

def test_empty_candidates_fail_closed(tmp_path, monkeypatch, wf_db):
    """6. empty candidates -> fail closed (returns [] before even touching
    the registry or wf_edge)."""
    reg_path = _mk_registry(
        tmp_path,
        [{"id": "T1", "status": "APPROVED", "strategy_fn": "Trend Following Breakout"}],
        tickers=("BBCA",),
    )
    _point_at(monkeypatch, reg_path)
    _insert_edge(wf_db, "BBCA", "Trend Following Breakout", 1.5)

    conn = sqlite3.connect(wf_db)
    got = _edge_selectable(conn, "BBCA", [])
    conn.close()
    assert got == []


# ---------------------------------------------------------------------------
# 7. The real NR7_BULL/SHADOW scenario, structurally reproduced
# ---------------------------------------------------------------------------

def test_demoted_strategy_cannot_reenter_through_fallback(tmp_path, monkeypatch, wf_db):
    """7. A strategy explicitly demoted APPROVED -> SHADOW cannot re-enter
    live selection through the candidates=None fallback. Structurally
    reproduces the real production scenario found this session (NR7 Breakout
    demoted by D-029, 43 tickers with positive wf_edge expectancy) using the
    real strategy_fn name and a real SHADOW registry entry, entirely on
    tmp_path-scoped data -- no production DB or registry file touched."""
    reg_path = _mk_registry(
        tmp_path,
        [{"id": "NR7_BULL", "status": "SHADOW", "strategy_fn": "NR7 Breakout"}],
        tickers=("KREN", "PIPA", "MDRN"),
    )
    _point_at(monkeypatch, reg_path)
    # Mirrors the real finding: multiple tickers with strong positive
    # pooled expectancy for the now-SHADOW strategy.
    _insert_edge(wf_db, "KREN", "NR7 Breakout", 5.765)
    _insert_edge(wf_db, "PIPA", "NR7 Breakout", 5.592)
    _insert_edge(wf_db, "MDRN", "NR7 Breakout", 5.117)

    conn = sqlite3.connect(wf_db)
    for ticker in ("KREN", "PIPA", "MDRN"):
        got = _edge_selectable(conn, ticker, None)
        assert "NR7 Breakout" not in got, f"{ticker}: SHADOW strategy re-entered via fallback"
        assert got == []
    conn.close()

    # get_ticker_best_strategies() is the same call, one layer up.
    for ticker in ("KREN", "PIPA", "MDRN"):
        assert get_ticker_best_strategies(ticker) == []


# ---------------------------------------------------------------------------
# 8. End-to-end: adaptive_strategy_selector()'s fallback cannot bypass Registry
# ---------------------------------------------------------------------------

def test_adaptive_selector_fallback_cannot_bypass_registry(tmp_path, monkeypatch, wf_db):
    """8. adaptive_strategy_selector() (the real trade-path caller) must not
    surface a SHADOW strategy through its unconstrained fallback. BULL
    regime (no counter-trend candidates -> fallback-eligible), no BULL-map
    candidate has positive wf_edge (constrained _edge_selectable yields
    nothing), but the SHADOW strategy DOES have positive wf_edge for this
    ticker -- before the fix this would have leaked through
    get_ticker_best_strategies(); after the fix it must not."""
    import scheduler.scanner as scanner
    monkeypatch.setattr(scanner, "_get_disabled_strategies", lambda: set())
    monkeypatch.setattr(scanner, "_macro_panic_state", lambda: False)
    monkeypatch.setattr(scanner, "_event_guard_active", lambda: (False, 1.0))

    reg_path = _mk_registry(
        tmp_path,
        [{"id": "NR7_BULL", "status": "SHADOW", "strategy_fn": "NR7 Breakout"}],
        tickers=("KREN",),
    )
    _point_at(monkeypatch, reg_path)
    # NR7 Breakout is in the BULL_MODERATE/BULL_STRONG regime map, so the
    # CONSTRAINED branch already excludes it (pre-existing, correct
    # behavior) -- give it a positive edge to prove that, and give it NO
    # other BULL-map candidate a positive edge, so the fallback triggers.
    _insert_edge(wf_db, "KREN", "NR7 Breakout", 5.765)

    got = adaptive_strategy_selector("KREN", _bull_df())
    assert "NR7 Breakout" not in got, f"SHADOW strategy leaked through adaptive_strategy_selector: {got}"
    assert got == []
