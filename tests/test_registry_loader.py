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
