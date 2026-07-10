"""SQLite backup with integrity verification and retention pruning (audit P-3).

Produces, per run:
  <dest>/walkforward-YYYYMMDD-HHMMSS.db.zst   (or .gz when zstd is absent)
  <dest>/walkforward-YYYYMMDD-HHMMSS.meta.json

The snapshot is taken with the sqlite3 online-backup API (WAL-safe, consistent
even while the app is writing), verified with PRAGMA integrity_check plus
per-table row counts BEFORE compression, and only then compressed. A backup
whose verification fails is deleted and the run exits non-zero so the cron
wrapper alarms.

Retention: keep the newest backup of each of the last --keep-daily days, plus
the newest backup of each of the last --keep-weekly ISO weeks. Everything
older is pruned.

Usage:
  python -m scripts.db_backup                 # defaults: prod DB, ~/backups/...
  python -m scripts.db_backup --db X --dest Y --keep-daily 7 --keep-weekly 4

Restore/verification counterpart: scripts/db_restore.py (see docs/OPERATIONS.md).
"""
import argparse
import datetime
import gzip
import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("db_backup")

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "walkforward.db"
DEFAULT_DEST = Path.home() / "backups" / "idx-walkforward-5001"

_BACKUP_RE = re.compile(r"^walkforward-(\d{8})-(\d{6})\.db\.(zst|gz)$")


def snapshot(db_path: Path, dest_dir: Path, now: datetime.datetime | None = None) -> Path:
    """Consistent point-in-time copy via the sqlite3 online-backup API."""
    now = now or datetime.datetime.now()
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / f"walkforward-{now:%Y%m%d-%H%M%S}.db"
    src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    dst = sqlite3.connect(out)
    try:
        with dst:
            src.backup(dst, pages=4096)
    finally:
        src.close()
        dst.close()
    logger.info("snapshot written: %s (%.1f MB)", out, out.stat().st_size / 1e6)
    return out


def verify(db_file: Path) -> dict:
    """PRAGMA integrity_check + per-table row counts. Raises on corruption."""
    conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
    try:
        status = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if status != "ok":
            raise RuntimeError(f"integrity_check failed: {status}")
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        counts = {t: conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                  for t in tables}
    finally:
        conn.close()
    meta = {
        "integrity": status,
        "tables": counts,
        "size_bytes": db_file.stat().st_size,
        "created": datetime.datetime.now().isoformat(timespec="seconds"),
        "source": str(db_file),
    }
    logger.info("verified %s: integrity=ok, %d tables, %d total rows",
                db_file.name, len(counts), sum(counts.values()))
    return meta


def write_meta(backup_file: Path, meta: dict) -> Path:
    meta_path = backup_file.parent / (backup_file.name.split(".db")[0] + ".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2))
    return meta_path


def compress(path: Path) -> Path:
    """zstd (fast, multi-thread) when available, else Python gzip."""
    if shutil.which("zstd"):
        out = path.with_suffix(path.suffix + ".zst")
        subprocess.run(["zstd", "-q", "-T0", "--rm", "-f", str(path), "-o", str(out)],
                       check=True)
    else:
        out = path.with_suffix(path.suffix + ".gz")
        with open(path, "rb") as f_in, gzip.open(out, "wb", compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out)
        path.unlink()
    logger.info("compressed → %s (%.1f MB)", out, out.stat().st_size / 1e6)
    return out


def _parse_backups(dest_dir: Path) -> list[tuple[datetime.datetime, Path]]:
    found = []
    for p in dest_dir.iterdir():
        m = _BACKUP_RE.match(p.name)
        if m:
            ts = datetime.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
            found.append((ts, p))
    return sorted(found)


def prune(dest_dir: Path, keep_daily: int = 7, keep_weekly: int = 4) -> list[Path]:
    """Keep newest per-day for keep_daily days + newest per-ISO-week for
    keep_weekly weeks; delete the rest (and their .meta.json). Returns deleted."""
    backups = _parse_backups(dest_dir)
    newest_per_day: dict[datetime.date, Path] = {}
    newest_per_week: dict[tuple[int, int], Path] = {}
    for ts, p in backups:  # sorted ascending → last write wins = newest
        newest_per_day[ts.date()] = p
        newest_per_week[ts.isocalendar()[:2]] = p

    keep_days = set(sorted(newest_per_day)[-keep_daily:]) if keep_daily else set()
    keep_weeks = set(sorted(newest_per_week)[-keep_weekly:]) if keep_weekly else set()
    keep = {newest_per_day[d] for d in keep_days} | {newest_per_week[w] for w in keep_weeks}

    deleted = []
    for _, p in backups:
        if p not in keep:
            meta = p.parent / (p.name.split(".db")[0] + ".meta.json")
            p.unlink()
            if meta.exists():
                meta.unlink()
            deleted.append(p)
            logger.info("pruned %s", p.name)
    return deleted


def run_backup(db_path: Path, dest_dir: Path, keep_daily: int = 7,
               keep_weekly: int = 4) -> Path:
    """Full cycle: snapshot → verify → meta → compress → prune."""
    logger.info("backup starting: %s → %s", db_path, dest_dir)
    snap = snapshot(db_path, dest_dir)
    try:
        meta = verify(snap)
    except Exception:
        snap.unlink(missing_ok=True)
        logger.error("backup FAILED verification — snapshot deleted")
        raise
    compressed = compress(snap)
    write_meta(compressed, meta)
    prune(dest_dir, keep_daily=keep_daily, keep_weekly=keep_weekly)
    logger.info("backup complete: %s", compressed.name)
    return compressed


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=Path(os.getenv("DB_PATH", DEFAULT_DB)))
    ap.add_argument("--dest", type=Path,
                    default=Path(os.getenv("BACKUP_DIR", DEFAULT_DEST)))
    ap.add_argument("--keep-daily", type=int, default=7)
    ap.add_argument("--keep-weekly", type=int, default=4)
    args = ap.parse_args(argv)
    try:
        run_backup(args.db, args.dest, args.keep_daily, args.keep_weekly)
    except Exception as e:
        logger.error("backup failed: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
