"""Pre-merge gate script (EXEC-001 §6, §15).

The one tooling deliverable EXEC-001's bring-up checklist adds. Run before
every merge to main; any failure blocks the merge (EXEC-001 §6). Checks are
scoped honestly to what exists at the current phase — see
docs/EXEC-DECISIONS.md IMPL-DEC-003 for why the schema-drift and AN-8
grep-audit checks are placeholders until their owning Phase 0/1 tasks land.

No test framework, no config file, no plugin system: one script, four
functions, thinness by construction (ER-12).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_ROOT = REPO_ROOT / "docs" / "evidence"
AN8_AUDIT_SCRIPT = REPO_ROOT / "scripts" / "audits" / "an8_unregistered_jobs.py"
SCHEMA_MODULE_HINT = REPO_ROOT / "docs" / "ops" / "MIGRATIONS.md"


def check_full_test_suite() -> tuple[bool, str]:
    """QG-1: any failed test in the full suite blocks merge."""
    if shutil.which("node") is None:
        return False, (
            "node not on PATH — tests/test_value_format.py requires it. "
            "User-space install, no sudo needed (docs/EXEC-DECISIONS.md IMPL-DEC-001): "
            "download a Node LTS tarball to ~/.local/node and add ~/.local/node/bin to PATH."
        )
    venv_python = REPO_ROOT / ".venv" / "bin" / "python"
    python = str(venv_python) if venv_python.exists() else sys.executable
    result = subprocess.run(
        [python, "-m", "pytest", "-q"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    tail = "\n".join(result.stdout.strip().splitlines()[-15:])
    return result.returncode == 0, tail


def check_schema_drift() -> tuple[bool, str]:
    """QG-4: DB schema != schema-module output, or DDL without a migration entry.

    No schema module exists yet (Phase 1 deliverable, P1.E1.S1). Reports N/A,
    not a silent pass, until it does — see IMPL-DEC-003.
    """
    return True, "N/A — no schema module yet (Phase 1 deliverable, P1.E1.S1)"


def check_grep_audits() -> tuple[bool, str]:
    """QG-9 (phase-appropriate): AN-8 zero imported-but-unregistered jobs.

    Owning task is P0.E1.S2.T4. Reports PENDING, not a silent pass, until
    that task lands the audit script — see IMPL-DEC-003.
    """
    if not AN8_AUDIT_SCRIPT.exists():
        return True, f"PENDING — implemented by P0.E1.S2.T4 ({AN8_AUDIT_SCRIPT.relative_to(REPO_ROOT)} not yet present)"
    result = subprocess.run(
        [sys.executable, str(AN8_AUDIT_SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0, result.stdout.strip() or result.stderr.strip()


def check_evidence_presence() -> tuple[bool, str]:
    """QG-5: missing evidence bundle for a task marked done (ER-9).

    Walks docs/evidence/P*/*/TASK-CARD.md; any card whose Status line reads
    'done' must have at least one evidence artifact beyond the card itself.
    """
    if not EVIDENCE_ROOT.exists():
        return True, "no evidence tree yet"
    missing: list[str] = []
    checked = 0
    for card in EVIDENCE_ROOT.glob("P*/*/TASK-CARD.md"):
        text = card.read_text(encoding="utf-8")
        status_line = next((l for l in text.splitlines() if l.startswith("**Status:**")), "")
        if "done" not in status_line.lower():
            continue
        checked += 1
        siblings = [p for p in card.parent.iterdir() if p.name != "TASK-CARD.md"]
        if not siblings:
            missing.append(str(card.parent.relative_to(REPO_ROOT)))
    if missing:
        return False, f"{len(missing)} task(s) marked done with no evidence artifacts: {', '.join(missing)}"
    return True, f"{checked} done-task card(s) checked, all have evidence artifacts"


CHECKS = [
    ("QG-1 full test suite", check_full_test_suite),
    ("QG-4 schema drift", check_schema_drift),
    ("QG-9 grep-audits (phase-appropriate)", check_grep_audits),
    ("QG-5 evidence presence", check_evidence_presence),
]


def main() -> int:
    overall_ok = True
    for name, fn in CHECKS:
        ok, detail = fn()
        overall_ok &= ok
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}")
        for line in detail.splitlines():
            print(f"    {line}")
    print()
    print("GATE: PASS" if overall_ok else "GATE: FAIL — merge blocked (EXEC-001 §6)")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
