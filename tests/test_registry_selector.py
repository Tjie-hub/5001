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
        ("CCCC", "NR7 Breakout", 3.0),           # POSITIVE but outside frozen set
        ("AAAA", "momentum", 1.0),               # ungoverned strategy
    ])
    return conn


def _govern(monkeypatch, universe):
    import scheduler.scanner  # noqa: F401  (ensure module imported)
    monkeypatch.setattr(rl, "approved_universe",
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
    monkeypatch.setattr(rl, "approved_universe", lambda s: None)   # not governed
    out = _edge_selectable(wfdb, "AAAA", ["NR7 Breakout"])
    assert out == ["NR7 Breakout"]                    # legacy path still works
