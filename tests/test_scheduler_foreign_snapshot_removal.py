"""Regression tests for run_foreign_snapshot removal (audit H-1, task P0.E1.S2.T2).

H-1 named three unregistered jobs: run_hourly_risk_bundle, run_eod_risk_summary
(both registered in P0.E1.S2.T1), and run_foreign_snapshot. Investigation
found run_foreign_snapshot to be dead/superseded, not merely unregistered:

- Its own `send_telegram` call was deliberately removed at some point (the
  audit's own account) — it now only computes a message and logs "no
  alert", never delivering it. Not an oversight; a completed deprecation
  with a stale docstring.
- Its entire computation (`flow_filter.get_top_foreign_accumulation`, same
  top_n=9999, same top-5 buy/sell split) is already folded into
  `scheduler/reports.py::flow_broker_report`'s "evening report" (explicit
  in-code comment: "Foreign accumulation top 5 — appended to evening
  report"), which — unlike run_foreign_snapshot — still calls
  `send_telegram` at the end of its body.
- It writes no data to the database and has no other callers; deleting it
  removes only itself, no downstream consumer is affected.

Decision: Option B (delete), not Option A (register) — registering it
alongside `flow_broker_report` (whenever H-2/P0.E1.S2.T3 registers that)
would permanently duplicate the same foreign-flow content in two Telegram
messages. Reviving a deliberately-disabled, superseded alert path is not
"restoring intended behavior."

flow_broker_report itself is out of scope here — it is one of the three
dead report functions H-2 names, owned by P0.E1.S2.T3.
"""
import ast
from pathlib import Path

import pytest
from apscheduler.schedulers.background import BackgroundScheduler

import scheduler as scheduler_pkg
import scheduler.jobs as scheduler_jobs

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_run_foreign_snapshot_symbol_no_longer_exists():
    assert not hasattr(scheduler_jobs, "run_foreign_snapshot")
    assert not hasattr(scheduler_pkg, "run_foreign_snapshot")


def test_no_source_reference_to_run_foreign_snapshot_remains():
    """No orphaned references anywhere under scheduler/ (import, add_job,
    docstring, or otherwise) — a plain substring scan, deliberately not
    limited to imports, so a stray comment would fail this too."""
    for path in (REPO_ROOT / "scheduler").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "run_foreign_snapshot" not in text, f"stale reference in {path}"


def test_scheduler_jobs_module_parses_with_no_dangling_holiday_skip_call():
    """AST-level check: no remaining `_holiday_skip("run_foreign_snapshot")`
    call anywhere in scheduler/jobs.py, and the module still parses cleanly
    (proves the deletion didn't leave a syntax error or an orphaned
    fragment)."""
    tree = ast.parse((REPO_ROOT / "scheduler" / "jobs.py").read_text(encoding="utf-8"))
    calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and getattr(n.func, "id", None) == "_holiday_skip"
        and n.args
        and isinstance(n.args[0], ast.Constant)
        and n.args[0].value == "run_foreign_snapshot"
    ]
    assert calls == []


@pytest.fixture
def registered_scheduler(monkeypatch):
    monkeypatch.setattr(BackgroundScheduler, "start", lambda self: None)
    monkeypatch.setattr("engine.watchlist.ensure_table", lambda *a, **k: None)
    monkeypatch.setattr("data.market_schema.ensure_market_data_schema", lambda *a, **k: None)
    monkeypatch.setattr("engine.registry_loader.announce_registry", lambda *a, **k: None)
    return scheduler_pkg.start_scheduler()


def test_start_scheduler_still_registers_cleanly_without_it(registered_scheduler):
    """The removal doesn't break scheduler bring-up, and (duplicate-prevention)
    no job anywhere references a function named run_foreign_snapshot."""
    jobs = registered_scheduler.get_jobs()
    assert len(jobs) > 0
    assert all(j.func.__name__ != "run_foreign_snapshot" for j in jobs)
    ids = [j.id for j in jobs]
    assert len(ids) == len(set(ids))  # still no duplicate ids after the edit


def test_get_top_foreign_accumulation_still_importable():
    """Thinness / no collateral damage: the shared data function
    run_foreign_snapshot used (and flow_broker_report still uses) was not
    touched by this deletion."""
    from flow_filter import get_top_foreign_accumulation  # noqa: F401


def test_flow_broker_report_still_contains_the_superseding_foreign_accumulation_block():
    """The successor path this decision relies on is still intact — this
    task must not have touched scheduler/reports.py at all (that's H-2 /
    P0.E1.S2.T3's separate task)."""
    text = (REPO_ROOT / "scheduler" / "reports.py").read_text(encoding="utf-8")
    assert "get_top_foreign_accumulation" in text
    assert "Foreign accumulation top 5" in text
    assert "def flow_broker_report" in text
