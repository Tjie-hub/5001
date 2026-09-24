"""Freeze-then-run-once discipline for Rule Cards (D-055).

What must be impossible: running an unfrozen card, freezing twice, running after the
card / script / framework changed, running twice, or silently re-running after a crash.
"""
import json
import textwrap

import pytest
import yaml

from research.rulecard import runner

RULE = textwrap.dedent('''
    from research.rulecard import synthetic

    def load_panel(ctx):
        return synthetic.make_panel(n_tickers=80, years=4, effect_pct_per_month=-4.0,
                                    seed=3, shape="tail", low_adv_boost=2.0)

    def signal(panel):
        return synthetic.z_signal(panel)
''')


def _card():
    from tests.test_rulecard_engine import valid_card
    c = valid_card()
    c["power"].update(sigma_planning=1.0, literature_effect=4.0, n_months=40)
    return c                    # keeps the adv_tercile fingerprint: planted via low_adv_boost


@pytest.fixture
def card_dir(tmp_path):
    d = tmp_path / "RC-TEST"
    d.mkdir()
    (d / "CARD.yaml").write_text(yaml.safe_dump(_card(), sort_keys=False))
    (d / "rule.py").write_text(RULE)
    return d


def test_run_refuses_an_unfrozen_card(card_dir, tmp_path):
    with pytest.raises(runner.RefusedError, match="not frozen"):
        runner.run(card_dir / "CARD.yaml", tmp_path / "ledger.jsonl")


def test_freeze_needs_owner_and_happens_once(card_dir):
    with pytest.raises(runner.RefusedError, match="owner_approval"):
        runner.freeze(card_dir / "CARD.yaml", " ")
    rec = runner.freeze(card_dir / "CARD.yaml", "Owner test 2026-09-24")
    assert rec["framework_sha256"] == runner.framework_sha256()
    with pytest.raises(runner.RefusedError, match="frozen once"):
        runner.freeze(card_dir / "CARD.yaml", "again")


@pytest.mark.parametrize("target", ["CARD.yaml", "rule.py"])
def test_any_edit_after_freeze_refuses(card_dir, tmp_path, target):
    runner.freeze(card_dir / "CARD.yaml", "Owner test")
    p = card_dir / target
    p.write_text(p.read_text() + "\n# tweak\n")
    with pytest.raises(runner.RefusedError, match="changed since freeze"):
        runner.run(card_dir / "CARD.yaml", tmp_path / "ledger.jsonl")


def test_framework_change_after_freeze_refuses(card_dir, tmp_path, monkeypatch):
    runner.freeze(card_dir / "CARD.yaml", "Owner test")
    monkeypatch.setattr(runner, "framework_sha256", lambda: "0" * 64)
    with pytest.raises(runner.RefusedError, match="framework_sha256"):
        runner.run(card_dir / "CARD.yaml", tmp_path / "ledger.jsonl")


def test_one_real_run_writes_three_artefacts_and_one_ledger_line(card_dir, tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    runner.freeze(card_dir / "CARD.yaml", "Owner test")
    out = runner.run(card_dir / "CARD.yaml", ledger)
    assert (card_dir / "RESULT.json").exists() and (card_dir / "VERDICT.md").exists()
    assert not (card_dir / "RUN_STARTED.json").exists()
    assert all(c["status"] == "PASS" for c in out["checks"]), out["checks"]
    assert out["verdict"]["verdict"] == "PASS"
    lines = ledger.read_text().strip().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["result_classification"] == "PASS"
    assert "VERDICT: **PASS**" in (card_dir / "VERDICT.md").read_text()
    with pytest.raises(runner.RefusedError, match="Refusing to re-run"):
        runner.run(card_dir / "CARD.yaml", ledger)


def test_crashed_run_needs_an_explicit_recorded_resume(card_dir, tmp_path):
    runner.freeze(card_dir / "CARD.yaml", "Owner test")
    (card_dir / "RUN_STARTED.json").write_text(json.dumps({"started_utc": "x"}))
    with pytest.raises(runner.RefusedError, match="did not finish"):
        runner.run(card_dir / "CARD.yaml", tmp_path / "ledger.jsonl")
    out = runner.run(card_dir / "CARD.yaml", tmp_path / "ledger.jsonl", resume_after_crash=True)
    assert out["resumed_after_crash"] == {"started_utc": "x"}


def test_dry_run_needs_no_freeze_and_computes_no_returns(card_dir):
    out = runner.dry(card_dir / "CARD.yaml")
    assert out["months_valid"] > 0
    assert {c["code"] for c in out["checks"]} == {"LA-1", "ZV-1", "ID-1", "FILL-1"}
    assert not (card_dir / "RESULT.json").exists()
    assert list(card_dir.glob("DRY_*.json"))


def test_power_mode_never_calls_the_signal(card_dir):
    rule = (card_dir / "rule.py").read_text().replace(
        "return synthetic.z_signal(panel)", "raise AssertionError('signal() called in power mode')")
    (card_dir / "rule.py").write_text(rule)
    out = runner.power(card_dir / "CARD.yaml", seeds=3)
    assert out["signal_called"] is False and out["sigma_noise_floor"] > 0
    assert out["months_valid"] > 0 and list(card_dir.glob("POWER_*.json"))
