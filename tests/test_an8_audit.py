"""Tests for the AN-8 grep-audit tool (P0.E1.S2.T4).

`scripts/audits/an8_unregistered_jobs.py` is the repository-wide audit
proving no scheduler-exported capability is imported-but-unregistered
(AN-8) beyond the 6 originally-named H-1/H-2 jobs (all dispositioned by
P0.E1.S2.T1/T2/T3) and the one new finding it itself surfaced
(`run_vpin_backfill`, allowlisted pending P0.E1.S2.T6).

These tests exercise the audit's own logic against small, synthetic
source trees rather than the real (large, slow-changing) repository, so
a future accidental regression in the audit's detection logic is caught
independently of whatever the real scheduler package looks like then.
"""
import importlib.util
import sys
import textwrap
from pathlib import Path

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audits" / "an8_unregistered_jobs.py"


def _load_module_against(tmp_repo: Path):
    """Import the audit module fresh, pointed at a synthetic repo root."""
    spec = importlib.util.spec_from_file_location("an8_unregistered_jobs_test", _SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.REPO_ROOT = tmp_repo
    mod.SCHEDULER_INIT = tmp_repo / "scheduler" / "__init__.py"
    mod.CANDIDATE_SOURCE_FILES = [
        tmp_repo / "scheduler" / "utils.py",
        tmp_repo / "scheduler" / "scanner.py",
        tmp_repo / "scheduler" / "jobs.py",
        tmp_repo / "scheduler" / "reports.py",
    ]
    return mod


def _write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


@pytest.fixture
def synthetic_repo(tmp_path):
    """A minimal repo: one registered job, one externally-called helper,
    one genuinely orphaned function — the three dispositions the audit
    must distinguish."""
    _write(tmp_path / "scheduler" / "jobs.py", """\
        def run_registered_job():
            pass

        def helper_used_elsewhere():
            pass

        def run_truly_orphaned():
            pass
        """)
    _write(tmp_path / "scheduler" / "reports.py", "")
    _write(tmp_path / "scheduler" / "scanner.py", "")
    _write(tmp_path / "scheduler" / "utils.py", "")
    _write(tmp_path / "scheduler" / "__init__.py", """\
        from scheduler.jobs import (
            run_registered_job,
            helper_used_elsewhere,
            run_truly_orphaned,
        )

        def start_scheduler():
            scheduler.add_job(run_registered_job, id="x")
        """)
    _write(tmp_path / "some_route.py", """\
        from scheduler.jobs import helper_used_elsewhere
        helper_used_elsewhere()
        """)
    return tmp_path


def test_registered_job_is_clean(synthetic_repo):
    mod = _load_module_against(synthetic_repo)
    ok, clean, violations = mod.audit()
    assert any(line.startswith("run_registered_job: registered") for line in clean)
    assert not any("run_registered_job" in v for v in violations)


def test_externally_called_helper_is_clean(synthetic_repo):
    mod = _load_module_against(synthetic_repo)
    ok, clean, violations = mod.audit()
    assert any(line.startswith("helper_used_elsewhere: externally referenced") for line in clean)
    assert not any("helper_used_elsewhere" in v for v in violations)


def test_orphaned_function_is_flagged(synthetic_repo):
    mod = _load_module_against(synthetic_repo)
    ok, clean, violations = mod.audit()
    assert ok is False
    assert any("run_truly_orphaned" in v for v in violations)


def test_allowlisted_orphan_is_clean_but_still_visible(synthetic_repo):
    mod = _load_module_against(synthetic_repo)
    mod.ALLOWLIST = {"run_truly_orphaned": "known finding, tracked as TEST-TASK-1"}
    ok, clean, violations = mod.audit()
    assert ok is True
    assert any(line.startswith("run_truly_orphaned: allowlisted") for line in clean)
    assert violations == []


def test_own_def_line_does_not_count_as_external_reference(synthetic_repo):
    """A function's docstring/body mentioning its own name (e.g. a
    recursive call or a self-referential comment) must not by itself
    make it look 'used' if nothing else in the repo calls it — only the
    literal `def name(` line is excluded, not every mention inside it."""
    _write(synthetic_repo / "scheduler" / "jobs.py", """\
        def run_registered_job():
            pass

        def run_self_referential_only():
            \"\"\"See run_self_referential_only for details.\"\"\"
            pass
        """)
    _write(synthetic_repo / "scheduler" / "__init__.py", """\
        from scheduler.jobs import (
            run_registered_job,
            run_self_referential_only,
        )

        def start_scheduler():
            scheduler.add_job(run_registered_job, id="x")
        """)
    mod = _load_module_against(synthetic_repo)
    ok, clean, violations = mod.audit()
    assert any("run_self_referential_only" in v for v in violations)


def test_real_repo_an8_audit_matches_current_allowlist():
    """Integration check against the actual repository: the only
    unregistered-and-otherwise-unreferenced candidate must be exactly
    the one this task's own investigation found and allowlisted."""
    sys.path.insert(0, str(_SCRIPT_PATH.parent))
    try:
        import an8_unregistered_jobs as real_mod
        ok, clean, violations = real_mod.audit()
    finally:
        sys.path.pop(0)
    assert ok is True, f"unexpected AN-8 violations: {violations}"
