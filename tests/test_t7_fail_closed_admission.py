"""T7 invariant #8 -- fail-closed runtime, proven at the ACTUAL production
admission boundary: a real on-disk registry fixture read by the real
engine.registry_loader.load_registry()/get_registry(), consumed by the real
engine.registry_loader.registry_governance() and the real
scheduler.scanner.adaptive_strategy_selector()/scan_momentum_signals() gates
added in commit 842ac79 -- not by mocking registry_governance() itself, which
is what tests/test_registry_selector.py and tests/test_adaptive_strategy.py
already do for the selector-logic unit tests.

Scope note: `scheduler.scanner._edge_selectable()`'s legacy `wf_edge>0`
fallback for NON-registry strategies is a separate, pre-existing, explicitly
flagged issue (Audit/T7_PRODUCTION_EXECUTION_BOUNDARY_AUDIT.md §4.4,
"wf_edge dual-use") and is deliberately untouched this session -- the
invariants proven here apply to the counter-trend/momentum admission gates
that DO require real Registry admission, not to that legacy channel.
"""
import json
import yaml
import pytest
import numpy as np
import pandas as pd

import engine.registry_loader as rl
from scheduler.scanner import adaptive_strategy_selector, scan_momentum_signals


def _bear_df(n=40):
    """Declining-price synthetic OHLCV that detect_regime() classifies BEAR --
    a flat/noisy series detects SIDEWAYS instead, which would make 'Crash
    Recovery' absent from the regime map entirely and trivially pass any
    exclusion assertion regardless of whether the admission gate works."""
    close = np.maximum(np.linspace(1000, 1000 * (1 - 30 / 100 * n / 10), n), 50.0)
    dates = pd.bdate_range("2025-01-02", periods=n)
    return pd.DataFrame({
        "date": [d.strftime("%Y-%m-%d") for d in dates],
        "open": close * 0.99, "high": close * 1.02, "low": close * 0.97,
        "close": close, "volume": np.full(n, 1_000_000.0),
    })


def _mk_registry(tmp_path, entries, tickers=("BEAR_T", "AAAA")):
    reg = tmp_path / "registry"
    (reg / "artifacts").mkdir(parents=True)
    art = reg / "artifacts" / "u.json"
    art.write_text(json.dumps({"tickers": list(tickers)}))
    for e in entries:
        e.setdefault("universe_artifact", "artifacts/u.json")
    (reg / "edge_registry.yaml").write_text(yaml.safe_dump(entries))
    return reg, str(reg / "edge_registry.yaml")


def _cr_entry(**kw):
    """A Crash Recovery entry -- the real counter-trend-book strategy_fn."""
    base = dict(id="CR_TEST", version=1, status="APPROVED",
                strategy_fn="Crash Recovery", regimes=["BEAR"],
                risk_category="counter-trend", owner="t", approved="2026-08-19",
                manifest="manifests/cr.yaml",
                requires=dict(data_schema=1, exit_kernel=1,
                              regime_model=1, engine_version=1),
                changelog="v1")
    base.update(kw)
    return base


def _valid_manifest(reg_dir, name="manifests/cr.yaml", approved=True):
    man = reg_dir / "manifests"
    man.mkdir(parents=True, exist_ok=True)
    ev = {"gate_decision": {"final_state": "PROMOTE_TO_FORWARD_TEST"}}
    if approved:
        ev["forward"] = {"verdict": "GO", "n": 17, "exp_pct": 0.63}
    (reg_dir / name).write_text(yaml.safe_dump({"evidence": ev}))


@pytest.fixture(autouse=True)
def _fresh_cache():
    rl._reset_cache()
    yield
    rl._reset_cache()


def _point_at(monkeypatch, path):
    monkeypatch.setattr(rl, "REGISTRY_PATH", path)
    rl._reset_cache()


# --------------------------------------------------------------------------
# 1. Missing registry -> no trade
# --------------------------------------------------------------------------

def test_missing_registry_file_admits_nothing(tmp_path, monkeypatch):
    _point_at(monkeypatch, str(tmp_path / "does_not_exist.yaml"))
    assert rl.registry_governance("Crash Recovery") is None
    assert rl.get_registry()["entries"] == []


def test_missing_registry_excludes_counter_trend_at_selector(tmp_path, monkeypatch):
    _point_at(monkeypatch, str(tmp_path / "does_not_exist.yaml"))
    monkeypatch.setattr("scheduler.scanner._edge_selectable", lambda *a, **k: [])
    monkeypatch.setattr("scheduler.scanner._get_disabled_strategies", lambda: set())
    monkeypatch.setattr("scheduler.scanner._event_guard_active", lambda: (False, 0.5))
    monkeypatch.setattr("scheduler.scanner._macro_panic_state", lambda: False)
    df = _bear_df()
    result = adaptive_strategy_selector("BEAR_T", df)
    assert "Crash Recovery" not in result


# --------------------------------------------------------------------------
# 2. Malformed registry -> no trade
# --------------------------------------------------------------------------

def test_malformed_registry_yaml_admits_nothing(tmp_path, monkeypatch):
    reg = tmp_path / "registry"
    reg.mkdir()
    bad = reg / "edge_registry.yaml"
    bad.write_text(":\n  this is not: [valid yaml")
    _point_at(monkeypatch, str(bad))
    assert rl.registry_governance("Crash Recovery") is None
    assert rl.get_registry()["hash"] == "load-failed"


# --------------------------------------------------------------------------
# 3/4. Invalid / missing evidence -> no trade
# --------------------------------------------------------------------------

def test_invalid_evidence_admits_nothing(tmp_path, monkeypatch):
    reg, path = _mk_registry(tmp_path, [_cr_entry()])
    _valid_manifest(reg, approved=False)          # SHADOW-level receipt only
    # entry is APPROVED but manifest lacks a forward GO -> invalid evidence
    _point_at(monkeypatch, path)
    assert rl.registry_governance("Crash Recovery") is None
    assert rl.get_registry()["violations"], "expected an un-grandfathered violation"


def test_missing_evidence_no_manifest_at_all_admits_nothing(tmp_path, monkeypatch):
    reg, path = _mk_registry(tmp_path, [_cr_entry(manifest=None)])
    _point_at(monkeypatch, path)
    assert rl.registry_governance("Crash Recovery") is None


# --------------------------------------------------------------------------
# 5. Missing receipt (manifest present, no gate_decision at all) -> no trade
# --------------------------------------------------------------------------

def test_missing_receipt_admits_nothing(tmp_path, monkeypatch):
    reg, path = _mk_registry(tmp_path, [_cr_entry()])
    man = reg / "manifests"
    man.mkdir(parents=True)
    (man / "cr.yaml").write_text(yaml.safe_dump({"evidence": {}}))  # no receipt
    _point_at(monkeypatch, path)
    assert rl.registry_governance("Crash Recovery") is None


# --------------------------------------------------------------------------
# 6. Non-admitted strategy (registry fine, strategy just absent) -> no trade
# --------------------------------------------------------------------------

def test_non_admitted_strategy_absent_from_registry(tmp_path, monkeypatch):
    reg, path = _mk_registry(tmp_path, [_cr_entry(strategy_fn="Some Other Strategy")])
    _valid_manifest(reg, name="manifests/cr.yaml", approved=True)
    _point_at(monkeypatch, path)
    assert rl.registry_governance("Crash Recovery") is None


# --------------------------------------------------------------------------
# 7. SHADOW -> no live trade, even with an otherwise-valid receipt
# --------------------------------------------------------------------------

def test_shadow_with_valid_receipt_never_admits_live_execution(tmp_path, monkeypatch):
    reg, path = _mk_registry(tmp_path, [_cr_entry(status="SHADOW")])
    _valid_manifest(reg, approved=False)   # SHADOW only needs the PROMOTE receipt
    _point_at(monkeypatch, path)
    gov = rl.registry_governance("Crash Recovery")
    assert gov == "SHADOW"
    assert not isinstance(gov, set)         # the selector's admission check requires a set


def test_shadow_excluded_from_counter_trend_selection(tmp_path, monkeypatch):
    reg, path = _mk_registry(tmp_path, [_cr_entry(status="SHADOW")])
    _valid_manifest(reg, approved=False)
    _point_at(monkeypatch, path)
    monkeypatch.setattr("scheduler.scanner._edge_selectable", lambda *a, **k: [])
    monkeypatch.setattr("scheduler.scanner._get_disabled_strategies", lambda: set())
    monkeypatch.setattr("scheduler.scanner._event_guard_active", lambda: (False, 0.5))
    monkeypatch.setattr("scheduler.scanner._macro_panic_state", lambda: False)
    df = _bear_df()
    result = adaptive_strategy_selector("BEAR_T", df)
    assert "Crash Recovery" not in result


# --------------------------------------------------------------------------
# 8. Execution-model mismatch (requires{} vs ENGINE_VERSIONS) -> no trade
# --------------------------------------------------------------------------

def test_execution_model_mismatch_admits_nothing(tmp_path, monkeypatch):
    reg, path = _mk_registry(tmp_path, [_cr_entry(
        requires=dict(data_schema=1, exit_kernel=99,   # exit_kernel bumped -> mismatch
                      regime_model=1, engine_version=1))])
    _valid_manifest(reg, approved=True)
    _point_at(monkeypatch, path)
    assert rl.registry_governance("Crash Recovery") is None
    skipped_ids = {s[0] for s in rl.get_registry()["skipped"]}
    assert "CR_TEST_v1" in skipped_ids


# --------------------------------------------------------------------------
# 9. Admission exception (unreadable universe artifact) -> no unintended trade
# --------------------------------------------------------------------------

def test_unreadable_artifact_admits_nothing(tmp_path, monkeypatch):
    reg, path = _mk_registry(tmp_path,
        [_cr_entry(universe_artifact="artifacts/does_not_exist.json")])
    _valid_manifest(reg, approved=True)
    _point_at(monkeypatch, path)
    assert rl.registry_governance("Crash Recovery") is None


# --------------------------------------------------------------------------
# Positive control: real APPROVED admission with a valid receipt DOES select.
# Proves the above are genuine fail-closed gaps, not a broken gate that
# always excludes everything regardless of input.
# --------------------------------------------------------------------------

def test_valid_approved_admission_is_selected(tmp_path, monkeypatch):
    reg, path = _mk_registry(tmp_path, [_cr_entry()])
    _valid_manifest(reg, approved=True)
    _point_at(monkeypatch, path)
    gov = rl.registry_governance("Crash Recovery")
    assert isinstance(gov, set) and "BEAR_T" in gov

    monkeypatch.setattr("scheduler.scanner._edge_selectable", lambda *a, **k: [])
    monkeypatch.setattr("scheduler.scanner._get_disabled_strategies", lambda: set())
    monkeypatch.setattr("scheduler.scanner._event_guard_active", lambda: (False, 0.5))
    monkeypatch.setattr("scheduler.scanner._macro_panic_state", lambda: False)
    df = _bear_df()
    result = adaptive_strategy_selector("BEAR_T", df)
    assert "Crash Recovery" in result


# --------------------------------------------------------------------------
# Momentum gate: same missing/malformed-registry proof, distinct call site.
# --------------------------------------------------------------------------

def test_missing_registry_blocks_momentum_scan(tmp_path, monkeypatch):
    import engine.calendar_filter as cal
    import scheduler.scanner as scanner
    monkeypatch.setattr(cal, "is_trading_day", lambda: (True, "trading day"))
    monkeypatch.setattr(cal, "is_blackout_day", lambda: (False, ""))
    monkeypatch.setattr(scanner, "_get_disabled_strategies", lambda: set())
    _point_at(monkeypatch, str(tmp_path / "does_not_exist.yaml"))

    def _must_not_reach(*a, **k):
        raise AssertionError("scan proceeded past the registry admission gate")
    monkeypatch.setattr(scanner, "get_all_tickers", _must_not_reach)
    assert scan_momentum_signals() == []
