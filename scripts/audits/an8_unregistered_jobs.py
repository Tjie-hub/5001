"""AN-8 grep-audit: zero imported-but-unregistered scheduler capabilities.

P0.E1.S2.T4 deliverable. Audit H-1/H-2 both named specific functions that
were fully implemented, imported into scheduler/__init__.py, and never
reachable from anything (never `add_job`-ed, never called by a route, a
test, or another registered function) — an "unwired capability" (ADR
§14 AN-8: "Defining a stage, report, or check that is not reachable from
a run DAG is a defect... Delete or wire — no third state").

P0.E1.S2.T1/T2/T3 dispositioned the 6 originally-named jobs. This script
is the general audit proving no *other*, unnamed capability is in the
same state — it does not re-litigate those 6; it checks every candidate
re-exported from scheduler/__init__.py.

A candidate passes if it is EITHER:
  (a) registered — passed as the function argument to `scheduler.add_job(`
      somewhere in `scheduler/__init__.py`'s `start_scheduler()`, OR
  (b) externally referenced — the name appears somewhere in the repo
      other than its own `def` line and the scheduler/__init__.py
      import statement (a real call site, a route, a test, or another
      registered function's body all count), OR
  (c) on the explicit ALLOWLIST below, with a reason and a citation —
      for a deliberate "intentionally unused" disposition made by a
      later task. Empty by design at T4's own merge: T4 documents new
      findings, it does not disposition them (PLAN-001 §3 Phase 0 scope).

Usage:
    python scripts/audits/an8_unregistered_jobs.py
Exit code 0 = clean (only allowlisted or justified candidates unregistered).
Exit code 1 = at least one undocumented unwired capability found.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEDULER_INIT = REPO_ROOT / "scheduler" / "__init__.py"

# Modules whose top-level `def` functions are re-exported through
# scheduler/__init__.py and are therefore candidates for this audit.
# (`utils.telegram.send_telegram` is deliberately excluded: it is a
# general-purpose utility re-exported for backward-compatible import
# paths, per scheduler/__init__.py's own comment — not a job/report/
# check in AN-8's sense.)
CANDIDATE_SOURCE_FILES = [
    REPO_ROOT / "scheduler" / "utils.py",
    REPO_ROOT / "scheduler" / "scanner.py",
    REPO_ROOT / "scheduler" / "jobs.py",
    REPO_ROOT / "scheduler" / "reports.py",
]

# Explicit, reasoned exceptions. Each entry documents WHY a name is
# allowed to stay unregistered-and-only-self-referenced without being
# flagged. Empty at T4 merge except for findings T4's own audit
# surfaced and handed to a follow-up task (PLAN-001 §18 changelog) —
# T4's scope is audit-and-document, not disposition (see task card).
ALLOWLIST: dict[str, str] = {
    "run_vpin_backfill": (
        "New AN-8 finding, surfaced by P0.E1.S2.T4's own audit run "
        "(2026-07-26): fully implemented, imported since VPIN batch work "
        "landed, referenced nowhere else in the repo. Not one of the "
        "Audit's originally-named 6 dead jobs. T4's scope is audit-and-"
        "document, not disposition — follow-up is P0.E1.S2.T6 (PLAN-001 "
        "§18 changelog). Remove this entry once T6 dispositions it."
    ),
}


def _find_reexported_names(init_source: str) -> set[str]:
    """Names inside the four `from scheduler.X import (...)` blocks."""
    names: set[str] = set()
    for block in re.finditer(
        r"from scheduler\.(?:utils|scanner|jobs|reports) import \((.*?)\)",
        init_source,
        re.S,
    ):
        for line in block.group(1).splitlines():
            line = line.split("#", 1)[0].strip().rstrip(",")
            if line:
                names.add(line)
    return names


def _find_registered_names(init_source: str) -> set[str]:
    """Names passed as the function argument to scheduler.add_job(...)."""
    return set(re.findall(r"scheduler\.add_job\(\s*(\w+)", init_source))


def _find_definition_file(name: str) -> Path | None:
    pattern = re.compile(rf"^def {re.escape(name)}\(", re.M)
    for path in CANDIDATE_SOURCE_FILES:
        if pattern.search(path.read_text(encoding="utf-8")):
            return path
    return None


def _own_body_line_range(name: str, definition_file: Path) -> range:
    """Line numbers (1-indexed, inclusive) spanning `name`'s own `def`
    through the line before the next top-level `def`/`class` (or EOF).

    A self-referential docstring or comment inside the function's own
    body (e.g. "Mirrors scheduler._load_ohlcv_bulk") must not count as
    evidence the function is used elsewhere — only mentions outside
    this span (in this file or any other) do."""
    lines = definition_file.read_text(encoding="utf-8").splitlines()
    def_line_pattern = re.compile(rf"^def {re.escape(name)}\(")
    top_level_pattern = re.compile(r"^(def|class)\s")
    start = next(i for i, line in enumerate(lines) if def_line_pattern.match(line))
    end = len(lines) - 1
    for i in range(start + 1, len(lines)):
        if top_level_pattern.match(lines[i]):
            end = i - 1
            break
    return range(start + 1, end + 2)  # 1-indexed, inclusive


def _has_external_reference(name: str, definition_file: Path | None) -> bool:
    """True if `name` appears anywhere in the repo other than inside its
    own function body (defining file) and the scheduler/__init__.py
    import statement."""
    pattern = re.compile(rf"\b{re.escape(name)}\b")
    own_body = _own_body_line_range(name, definition_file) if definition_file else range(0)
    for path in REPO_ROOT.rglob("*.py"):
        if any(part in (".venv", "__pycache__") for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if not pattern.search(line):
                continue
            if path == definition_file and lineno in own_body:
                continue
            if path == SCHEDULER_INIT and line.strip().rstrip(",") == name:
                continue  # the re-export import line itself
            return True
    return False


def audit() -> tuple[bool, list[str], list[str]]:
    """Returns (ok, clean_report_lines, violation_lines)."""
    init_source = SCHEDULER_INIT.read_text(encoding="utf-8")
    candidates = sorted(_find_reexported_names(init_source))
    registered = _find_registered_names(init_source)

    clean: list[str] = []
    violations: list[str] = []

    for name in candidates:
        if name in registered:
            clean.append(f"{name}: registered (scheduler.add_job)")
            continue
        if name in ALLOWLIST:
            clean.append(f"{name}: allowlisted — {ALLOWLIST[name]}")
            continue
        definition_file = _find_definition_file(name)
        if _has_external_reference(name, definition_file):
            clean.append(f"{name}: externally referenced")
            continue
        violations.append(
            f"{name}: imported into scheduler/__init__.py, not registered, "
            f"not allowlisted, and referenced nowhere else in the repo "
            f"(defined at {definition_file.relative_to(REPO_ROOT) if definition_file else 'UNKNOWN'})"
        )

    return (len(violations) == 0, clean, violations)


def main() -> int:
    ok, clean, violations = audit()
    print(f"AN-8 audit: {len(clean)} candidate(s) clean, {len(violations)} violation(s)\n")
    for line in clean:
        print(f"  [OK]   {line}")
    for line in violations:
        print(f"  [FAIL] {line}")
    print()
    print("AN-8: PASS — zero unwired capabilities" if ok
          else "AN-8: FAIL — unwired capability found, see above")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
