"""Restore (or restore-verify) a backup produced by scripts/db_backup.py.

Default mode is --verify-only: decompress to a scratch path, run PRAGMA
integrity_check, and compare per-table row counts against the backup's
.meta.json. This is the "restore drill" — run it after every schema change
and at least quarterly (docs/OPERATIONS.md).

--apply additionally swaps the restored file into place:
  1. the current live DB is moved aside to <db>.pre_restore_<timestamp>
     (never deleted — reversibility), stale -wal/-shm are moved with it;
  2. the verified restored copy is moved to the live path.
Stop the app (systemctl stop idx-walkforward) before --apply.

Usage:
  python -m scripts.db_restore <backup.db.zst>                 # verify only
  python -m scripts.db_restore <backup.db.zst> --apply [--db PATH]
"""
import argparse
import datetime
import gzip
import json
import logging
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.db_backup import DEFAULT_DB, verify

logger = logging.getLogger("db_restore")

# Scratch for the decompressed copy. Not /tmp: since the Ubuntu 26.04 upgrade (2026-10-13) /tmp is a 3.6 GB
# tmpfs and the ~15 GB DB cannot fit -- the 2026-10-11 and 2026-10-18 weekly drills both died mid-decompress
# ("No space left on device" / "Disk quota exceeded") and left the partial file behind. /var/tmp is disk-backed.
DEFAULT_WORK_PARENT = Path(os.environ.get("IDX_RESTORE_WORK_DIR", "/var/tmp"))
SPACE_FACTOR = 1.1          # need ~the uncompressed size; 10% slack
UNKNOWN_RATIO = 6           # no meta: assume the .zst expands ~6x (observed 3.06 GB -> 15.2 GB = 5x)


def need_bytes(backup_file: Path, meta: dict | None) -> int:
    size = (meta or {}).get("size_bytes") or backup_file.stat().st_size * UNKNOWN_RATIO
    return int(size * SPACE_FACTOR)


def check_scratch(work_parent: Path, need: int) -> None:
    probe = work_parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    free = shutil.disk_usage(probe).free
    if free < need:
        raise RuntimeError(f"only {free / 1e9:.1f} GB free on {probe}, need ~{need / 1e9:.1f} GB to decompress "
                           f"-- pass --work-dir on a larger disk or set IDX_RESTORE_WORK_DIR")


def decompress(backup_file: Path, work_dir: Path) -> Path:
    out = work_dir / backup_file.name.rsplit(".", 1)[0]  # strip .zst/.gz
    if backup_file.suffix == ".zst":
        subprocess.run(["zstd", "-q", "-d", "-f", str(backup_file), "-o", str(out)],
                       check=True)
    elif backup_file.suffix == ".gz":
        with gzip.open(backup_file, "rb") as f_in, open(out, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    else:  # already a raw .db snapshot
        shutil.copy2(backup_file, out)
    logger.info("decompressed → %s (%.1f MB)", out, out.stat().st_size / 1e6)
    return out


def load_meta(backup_file: Path) -> dict | None:
    meta_path = backup_file.parent / (backup_file.name.split(".db")[0] + ".meta.json")
    if meta_path.exists():
        return json.loads(meta_path.read_text())
    logger.warning("no meta file found (%s) — row-count comparison skipped", meta_path.name)
    return None


def verify_restore(restored: Path, meta: dict | None) -> dict:
    """integrity_check + row-count equality against the backup meta. Raises on
    any mismatch."""
    fresh = verify(restored)  # raises unless integrity == ok
    if meta:
        mismatches = {
            t: (n, fresh["tables"].get(t))
            for t, n in meta["tables"].items()
            if fresh["tables"].get(t) != n
        }
        if mismatches:
            raise RuntimeError(f"row-count mismatch vs meta: {mismatches}")
        logger.info("row counts match meta for all %d tables", len(meta["tables"]))
    return fresh


def apply_restore(restored: Path, live_db: Path) -> Path:
    """Swap the verified restored file into place; current DB is kept aside."""
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    if live_db.exists():
        aside = live_db.with_name(live_db.name + f".pre_restore_{stamp}")
        shutil.move(live_db, aside)
        logger.info("live DB moved aside → %s", aside.name)
        for ext in ("-wal", "-shm"):
            side = live_db.with_name(live_db.name + ext)
            if side.exists():
                shutil.move(side, aside.with_name(aside.name + ext))
    shutil.move(restored, live_db)
    logger.info("restore applied → %s", live_db)
    return live_db


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("backup", type=Path)
    ap.add_argument("--apply", action="store_true",
                    help="swap the verified restore into place (default: verify only)")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB,
                    help="live DB path used with --apply")
    ap.add_argument("--work-dir", type=Path, default=None,
                    help="scratch dir for decompression (default: temp dir)")
    args = ap.parse_args(argv)

    meta = load_meta(args.backup)
    own_work = args.work_dir is None
    work = None
    try:
        parent = args.work_dir or DEFAULT_WORK_PARENT
        check_scratch(parent, need_bytes(args.backup, meta))  # before writing a byte
        if own_work:
            DEFAULT_WORK_PARENT.mkdir(parents=True, exist_ok=True)
            work = Path(tempfile.mkdtemp(prefix="db_restore_", dir=DEFAULT_WORK_PARENT))
        else:
            work = args.work_dir
            work.mkdir(parents=True, exist_ok=True)
        restored = decompress(args.backup, work)
        verify_restore(restored, meta)
        if args.apply:
            apply_restore(restored, args.db)
            logger.info("RESTORE APPLIED — restart the app to pick it up")
        else:
            restored.unlink()
            logger.info("RESTORE VERIFIED OK (dry run — nothing touched)")
    except Exception as e:
        logger.error("restore failed: %s", e)
        return 1
    finally:
        if own_work and work is not None:
            shutil.rmtree(work, ignore_errors=True)  # never leave a 15 GB partial behind
    return 0


if __name__ == "__main__":
    sys.exit(main())
