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
    man_dir = tmp_path / "registry" / "manifests"
    man_dir.mkdir(parents=True)
    valid_evidence = {"evidence": {
        "gate_decision": {"final_state": "PROMOTE_TO_FORWARD_TEST"},
        "forward": {"verdict": "GO", "n": 17, "exp_pct": 0.63}}}
    (man_dir / "x.yaml").write_text(yaml.safe_dump(valid_evidence))
    monkeypatch.setattr(rl, "REGISTRY_PATH", path)
    rl._reset_cache()
    assert rl.approved_universe("NR7 Breakout") == {"AAAA", "BBBB"}
    assert rl.approved_universe("nonexistent") is None
    s = rl.startup_summary()
    assert "1 approved" in s and "1 shadow" in s and "0 skipped" in s
    rl._reset_cache()


def test_unverified_violation_entry_is_excluded_from_entries(tmp_path, monkeypatch):
    # An APPROVED entry with no valid evidence receipt, and not in the grandfathered
    # _LIFECYCLE_DEBT allowlist, must be REJECTED (excluded from entries), not just
    # flagged as a violation while still loading.
    alarms = []
    monkeypatch.setattr(rl, "fail_open_alarm", lambda *a, **k: alarms.append(a) or "")
    path = _mk_registry(tmp_path, [_entry(id="FAKE_EDGE")])
    r = rl.load_registry(path=path)
    assert r["entries"] == []
    assert len(r["violations"]) == 1
    assert r["violations"][0][0] == "FAKE_EDGE_v1"
    assert r["debt"] == []


def test_valid_evidence_entry_loads_via_real_manifest(tmp_path, monkeypatch):
    # Positive path, end-to-end through load_registry (not just validate_evidence
    # in isolation): a SHADOW entry backed by a real on-disk manifest with a
    # genuine PROMOTE receipt must load cleanly, outside the debt allowlist.
    monkeypatch.setattr(rl, "fail_open_alarm", lambda *a, **k: None)
    path = _mk_registry(tmp_path, [_entry(id="REAL_EDGE", status="SHADOW",
                                          strategy_fn="Real")])
    man_dir = tmp_path / "registry" / "manifests"
    man_dir.mkdir(parents=True)
    (man_dir / "x.yaml").write_text(yaml.safe_dump(
        {"evidence": {"gate_decision": {"final_state": "PROMOTE_TO_FORWARD_TEST"}}}))
    r = rl.load_registry(path=path)
    assert [e['id'] for e in r['entries']] == ['REAL_EDGE']
    assert r['violations'] == [] and r['debt'] == []


def test_malformed_manifest_yaml_rejects_only_that_entry(tmp_path, monkeypatch):
    # A manifest that parses but isn't a mapping (e.g. a YAML list) must not
    # crash load_registry for the whole file -- it must reject just that entry.
    monkeypatch.setattr(rl, "fail_open_alarm", lambda *a, **k: None)
    path = _mk_registry(tmp_path, [_entry(id="BAD_MANIFEST", status="SHADOW",
                                          strategy_fn="Bad"),
                                   _entry(id="OK_EDGE", status="SHADOW",
                                          strategy_fn="Ok", manifest="manifests/ok.yaml")])
    man_dir = tmp_path / "registry" / "manifests"
    man_dir.mkdir(parents=True)
    (man_dir / "x.yaml").write_text(yaml.safe_dump(["not", "a", "mapping"]))
    (man_dir / "ok.yaml").write_text(yaml.safe_dump(
        {"evidence": {"gate_decision": {"final_state": "PROMOTE_TO_FORWARD_TEST"}}}))
    r = rl.load_registry(path=path)
    assert [e['id'] for e in r['entries']] == ['OK_EDGE']
    assert any(v[0] == 'BAD_MANIFEST_v1' for v in r['violations'])


def test_registry_governance_returns_universe_for_approved(tmp_path, monkeypatch):
    monkeypatch.setattr(rl, "fail_open_alarm", lambda *a, **k: None)
    path = _mk_registry(tmp_path, [_entry()])   # NR7_BULL, debt-grandfathered APPROVED
    monkeypatch.setattr(rl, "REGISTRY_PATH", path)
    rl._reset_cache()
    assert rl.registry_governance("NR7 Breakout") == {"AAAA", "BBBB"}
    rl._reset_cache()


def test_registry_governance_returns_shadow_sentinel_for_shadow_only(tmp_path, monkeypatch):
    monkeypatch.setattr(rl, "fail_open_alarm", lambda *a, **k: None)
    man_dir = tmp_path / "registry" / "manifests"
    man_dir.mkdir(parents=True)
    (man_dir / "x.yaml").write_text(yaml.safe_dump(
        {"evidence": {"gate_decision": {"final_state": "PROMOTE_TO_FORWARD_TEST"}}}))
    path = _mk_registry(tmp_path, [_entry(id="SH_EDGE", status="SHADOW",
                                          strategy_fn="Shadowy")])
    monkeypatch.setattr(rl, "REGISTRY_PATH", path)
    rl._reset_cache()
    assert rl.registry_governance("Shadowy") == "SHADOW"
    rl._reset_cache()


def test_registry_governance_returns_none_when_not_registered(tmp_path, monkeypatch):
    monkeypatch.setattr(rl, "fail_open_alarm", lambda *a, **k: None)
    path = _mk_registry(tmp_path, [_entry()])
    monkeypatch.setattr(rl, "REGISTRY_PATH", path)
    rl._reset_cache()
    assert rl.registry_governance("nonexistent") is None
    rl._reset_cache()


def test_startup_banner_helper_never_raises(monkeypatch):
    # announce_registry logs + telegrams best-effort; must never raise.
    monkeypatch.setattr(rl, "get_registry",
                        lambda: {'entries': [], 'skipped': [], 'hash': 'x'})
    sent = []
    rl.announce_registry(telegram_fn=lambda m: sent.append(m))
    assert sent and "registry @x" in sent[0]

    def _boom(_m):
        raise RuntimeError("down")
    rl.announce_registry(telegram_fn=_boom)   # must not raise
