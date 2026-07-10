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
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.db_backup import DEFAULT_DB, verify

logger = logging.getLogger("db_restore")


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

    work = args.work_dir or Path(tempfile.mkdtemp(prefix="db_restore_"))
    work.mkdir(parents=True, exist_ok=True)
    try:
        restored = decompress(args.backup, work)
        meta = load_meta(args.backup)
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
