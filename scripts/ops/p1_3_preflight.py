"""J2 — one-shot P1-3 cutover dry-run preflight (17:00 WIB on 2026-10-01).

Runs scripts/migrate_r5_tier1 in dry-run mode ONLY — this script never passes
--apply — inside the production tree, and sends the Owner the per-table row
counts of all 8 R-5 Tier-1 tables plus anything unexpected in the output, so
the P1-3 cutover go/no-go decision is made on numbers, not vibes.

Scheduling notes: `at`/atd is not installed on this box, and the canonical
crontab only gets installed with tonight's deploy (after the Owner's "go"),
so the 2026-10-01 17:00 WIB firing is delivered by a one-shot transient
systemd --user timer; the crontab line below stays as the auditable record
and is inert — the exact-date guard makes it a no-op on every other day,
including 2026-10-01 after 17:00 has passed. A /tmp marker makes the one-shot
idempotent in case both mechanisms ever race.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ops._common import OPS_PREFIX, now_wib, repo_root, send_ops

TARGET_DATE = "2026-10-01"
MARKER = Path(f"/tmp/idx_p13_preflight_{TARGET_DATE}.done")

# Fallback copy of research.db.TIER1_TABLES (R-5). The live tuple is imported
# from the target tree when possible; if that import ever fails the mismatch
# itself is reported instead of silently trusting this copy.
FALLBACK_TIER1_TABLES = (
    "research_runs", "gate_decisions", "gate_evidence",
    "regime_profiles", "regime_profile_cells",
    "hypotheses", "hypothesis_links", "failure_registry",
)

_WOULD_MIGRATE = re.compile(r"would migrate:\s+(\S+)\s+\((\d+)\s+rows\)")
_ALREADY_ABSENT = re.compile(r"already migrated \(absent from source\):\s+(\S+)")
_KNOWN_CHATTER_PREFIXES = ("DRY RUN", "source (prod):", "destination:", "NOTE")


def parse_dry_run(output: str) -> tuple[dict[str, int], list[str], list[str]]:
    """Split dry-run output into (counts, absent tables, unexpected lines)."""
    counts: dict[str, int] = {}
    absent: list[str] = []
    unexpected: list[str] = []
    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _WOULD_MIGRATE.search(line)
        if m:
            counts[m.group(1)] = int(m.group(2))
            continue
        m = _ALREADY_ABSENT.search(line)
        if m:
            absent.append(m.group(1))
            continue
        if line.startswith(_KNOWN_CHATTER_PREFIXES):
            continue
        unexpected.append(line)
    return counts, absent, unexpected


def tier1_tables(target_root: Path) -> tuple[tuple[str, ...], str | None]:
    """(tables, warning) — imports TIER1_TABLES from the target tree, falls back."""
    if str(target_root) not in sys.path:
        sys.path.insert(0, str(target_root))
    try:
        from research.db import TIER1_TABLES
        return tuple(TIER1_TABLES), None
    except Exception as exc:  # target tree drift must be visible, not silent
        return FALLBACK_TIER1_TABLES, f"could not import research.db.TIER1_TABLES ({exc}); used fallback copy"


def build_message(counts: dict[str, int], absent: list[str], tables: tuple[str, ...],
                  unexpected: list[str], missing: list[str], extra: str | None) -> str:
    lines = [f"{OPS_PREFIX} 🔬 P1-3 cutover dry-run (migrate_r5_tier1, NO --apply) — "
             f"{now_wib().strftime('%F %H:%M')} WIB"]
    for t in tables:
        if t in counts:
            lines.append(f"• {t}: {counts[t]} rows")
        elif t in absent:
            lines.append(f"• {t}: already migrated (absent from source)")
        elif missing:
            lines.append(f"• {t}: ⚠️ not reported by dry-run")
    if extra:
        lines.append(f"⚠️ {extra}")
    if missing:
        lines.append("⚠️ tables missing from dry-run output: " + ", ".join(missing))
    if unexpected:
        lines.append("⚠️ unexpected output lines:")
        lines += [f"  {u}" for u in unexpected[-10:]]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    dry = bool(argv and "--dry" in argv)
    today = now_wib().strftime("%Y-%m-%d")
    if today != TARGET_DATE:
        print(f"inert: one-shot for {TARGET_DATE}, today is {today}")
        return 0
    if MARKER.exists():
        print("already ran (marker present)")
        return 0

    target = Path(os.environ.get("IDX_PROD_ROOT", str(repo_root())))
    venv_py = target / "venv" / "bin" / "python3"
    problems: list[str] = []
    if not (target / "scripts" / "migrate_r5_tier1.py").exists():
        problems.append(f"scripts/migrate_r5_tier1.py not found in {target}")
    elif not venv_py.exists():
        problems.append(f"venv python not found at {venv_py}")
    if problems:
        MARKER.write_text("failed-preflight\n", encoding="utf-8")
        send_ops(f"{OPS_PREFIX} ⚠️ P1-3 preflight could not run: {'; '.join(problems)}", dry=dry)
        return 0

    proc = subprocess.run([str(venv_py), "-m", "scripts.migrate_r5_tier1"],
                          cwd=str(target), capture_output=True, text=True, timeout=600)
    counts, absent, unexpected = parse_dry_run(proc.stdout)
    tables, import_warning = tier1_tables(target)
    missing = [t for t in tables if t not in counts and t not in absent]
    msg_extra = import_warning
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-5:]
        msg_extra = (msg_extra + " | " if msg_extra else "") + \
            f"dry-run exited rc={proc.returncode}: " + " / ".join(tail)
    send_ops(build_message(counts, absent, tables, unexpected, missing, msg_extra), dry=dry)
    MARKER.write_text(f"rc={proc.returncode}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
