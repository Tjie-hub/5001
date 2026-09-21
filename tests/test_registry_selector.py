"""_edge_selectable: registry-governed strategies use the frozen universe;
ungoverned strategies keep the legacy live wf_edge query; parity guaranteed."""
import datetime as _dt
import sqlite3
import pytest

import engine.registry_loader as rl
from scheduler.scanner import _edge_selectable


# Admission reads n_trades and last_computed as well (audit 2026-09-02: thin
# samples and stale evidence are now gates), so the fixture carries the real
# wf_edge shape rather than a three-column stub.
_FRESH = _dt.date.today().isoformat()


@pytest.fixture
def wfdb(tmp_path, monkeypatch):
    # Rule parity (audit L-1) has its own suite (tests/test_admission.py);
    # declare parity here so this file keeps testing registry governance.
    import engine.rule_identity as _ri
    monkeypatch.setattr(_ri, "live_gates", lambda strategy: ())
    import scheduler.scanner as _sc
    monkeypatch.setattr(_sc, "_get_disabled_strategies", lambda: set())
    conn = sqlite3.connect(str(tmp_path / "wf.db"))
    conn.execute(
        "CREATE TABLE wf_edge (ticker TEXT, strategy TEXT, expectancy_pct REAL,"
        " expectancy_rp REAL, win_rate REAL, consistency_pct REAL, sharpe REAL,"
        " n_trades INTEGER, windows_tested INTEGER, last_computed TEXT)")
    conn.executemany("INSERT INTO wf_edge VALUES (?,?,?,0,55,40,0.4,60,15,?)", [
        ("AAAA", "NR7 Breakout", 2.0, _FRESH),
        ("BBBB", "NR7 Breakout", -1.0, _FRESH),  # negative → not selectable
        ("CCCC", "NR7 Breakout", 3.0, _FRESH),   # POSITIVE but outside frozen set
        ("AAAA", "momentum", 1.0, _FRESH),       # ungoverned strategy
    ])
    return conn


def _govern(monkeypatch, universe):
    import scheduler.scanner  # noqa: F401  (ensure module imported)
    monkeypatch.setattr(rl, "registry_governance",
                        lambda s: set(universe) if s == "NR7 Breakout" else None)


def test_governed_uses_frozen_universe_not_db(wfdb, monkeypatch):
    _govern(monkeypatch, {"AAAA"})
    assert "NR7 Breakout" in _edge_selectable(wfdb, "AAAA", ["NR7 Breakout"])
    assert _edge_selectable(wfdb, "BBBB", ["NR7 Breakout"]) == []
    # THE DRIFT CASE: CCCC has POSITIVE wf_edge but is NOT in the frozen set —
    # governance must exclude it (legacy live-query would have included it).
    assert _edge_selectable(wfdb, "CCCC", ["NR7 Breakout"]) == []


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
    monkeypatch.setattr(rl, "registry_governance", lambda s: None)   # no entry at all
    out = _edge_selectable(wfdb, "AAAA", ["NR7 Breakout"])
    assert out == ["NR7 Breakout"]                    # legacy path still works


def test_shadow_strategy_excluded_never_falls_back_to_legacy(wfdb, monkeypatch):
    # T7.P1.WS4.01: a SHADOW-governed strategy must never fall through to the
    # ungoverned legacy wf_edge query, even though it has positive expectancy
    # there (AAAA/"NR7 Breakout" = +2.0 in the wfdb fixture).
    monkeypatch.setattr(rl, "registry_governance",
                        lambda s: "SHADOW" if s == "NR7 Breakout" else None)
    assert _edge_selectable(wfdb, "AAAA", ["NR7 Breakout"]) == []


def test_shadow_demotion_from_approved_strictly_reduces_reach(wfdb, monkeypatch):
    # Critical safety invariant: APPROVED -> SHADOW must never WIDEN production
    # reach. Simulate the demotion by flipping the same strategy's governance
    # state and confirm the selectable set shrinks to empty, not to the wider
    # legacy wf_edge set.
    monkeypatch.setattr(rl, "registry_governance",
                        lambda s: {"AAAA"} if s == "NR7 Breakout" else None)
    approved_out = set(_edge_selectable(wfdb, "AAAA", ["NR7 Breakout"]))
    monkeypatch.setattr(rl, "registry_governance",
                        lambda s: "SHADOW" if s == "NR7 Breakout" else None)
    shadow_out = set(_edge_selectable(wfdb, "AAAA", ["NR7 Breakout"]))
    assert shadow_out.issubset(approved_out) and shadow_out == set()
