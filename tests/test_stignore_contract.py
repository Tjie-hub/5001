"""P1-12: guard against the .stignore corruption-hardening block silently
regressing again. On 2026-08-15 this file's SQLite-exclusion rules (from
commit 520800c, the fix for the 2026-07-29 Syncthing/WAL corruption of
data/walkforward.db's ticks table) were found wholesale-replaced with an
unrelated dev-tooling ignore list in a working tree, with zero overlap --
Syncthing reads .stignore live from disk and is a bidirectional watcher, so
that regression re-exposed both walkforward.db and the newly-split
research.db to the exact race that caused the original incident. Nothing
caught it until it was noticed by accident. This test is the automated
catch."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STIGNORE = (ROOT / ".stignore").read_text()

# The patterns that must never be dropped -- see .stignore's own header
# comment for the "why", and Audit/INCIDENT_VPIN_DB_CORRUPTION_2026-07-29.md
# for the incident this exists to prevent a repeat of.
REQUIRED_PATTERNS = [
    "*.db",
    "*.db-wal",
    "*.db-shm",
    "*.db-journal",
    "*.sync-conflict-*.db",
    "*.sync-conflict-*.db-wal",
    "*.sync-conflict-*.db-shm",
    "logs/",
    # Added 2026-08-15 (P1-11): aside-copy snapshots (*.corrupt_*.bak,
    # *.pre_recovery_cutover_*.bak) don't end in *.db, so the patterns
    # above miss them -- found sitting unexcluded, multi-GB, eligible for
    # sync neither device needs.
    "*.bak",
    "*.bak-wal",
    "*.bak-shm",
]


def test_stignore_excludes_live_sqlite_databases():
    lines = {l.strip() for l in STIGNORE.splitlines()}
    missing = [p for p in REQUIRED_PATTERNS if p not in lines]
    assert not missing, (
        f".stignore is missing corruption-hardening pattern(s): {missing}. "
        "These exclude live WAL-mode SQLite databases and their sidecar/"
        "conflict files from Syncthing's bidirectional sync -- removing them "
        "re-exposes data/walkforward.db and data/research.db to the exact "
        "race that corrupted the ticks table on 2026-07-29. Do not remove "
        "without first addressing why they were added (see .stignore's own "
        "header comment)."
    )


def test_stignore_does_not_exclude_itself():
    """A regression that also excluded .stignore from sync would let two
    devices' copies silently diverge with neither side able to detect it via
    this same test (each device would only ever see its own local copy)."""
    lines = {l.strip() for l in STIGNORE.splitlines()}
    assert ".stignore" not in lines
