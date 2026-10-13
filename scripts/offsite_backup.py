#!/usr/bin/env python3
"""Weekly off-SSD copy of the newest verified nightly backup (2026-10-13).

The nightly backups lived only on the same SSD as the live DB, so one disk
failure would have taken both. This copies the newest walkforward backup to the
USB archive drive, proves the copy by sha256, and keeps the newest --keep weeks
there. Cold storage only: nothing the scheduler reads ever lives on that drive.

Refuses (non-zero exit -> cron_wrap alert, exempt from the TELEGRAM_OFF
blackout) when the drive is not mounted -- it is /etc/fstab `nofail`, so an
unmounted path would otherwise silently fill the SSD -- when the backup fails
`zstd -t`, when there is no room, or when the copy's hash differs.

Dest is a dedicated directory so pruning can never touch the older archived
backups in idx-archive/backups.
"""
import argparse
import hashlib
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.db_backup import DEFAULT_DEST, _backup_re  # noqa: E402

logger = logging.getLogger("offsite_backup")

MOUNT = "/mnt/storage2tb"
DEFAULT_OFFSITE = Path(MOUNT) / "idx-archive" / "backups_weekly"
KEEP_WEEKS = 8


class OffsiteError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def _verify(path: Path) -> None:
    """Integrity-test the compressed file itself before shipping it."""
    tool = ["zstd", "-t", "-q"] if path.suffix == ".zst" else ["gzip", "-t"]
    r = subprocess.run(tool + [str(path)], capture_output=True, text=True)
    if r.returncode != 0:
        raise OffsiteError(f"{path.name} failed {tool[0]} -t: {r.stderr.strip()[:200]}")


def _backups(directory: Path, prefix: str):
    rx = _backup_re(prefix)
    return sorted(p for p in directory.iterdir() if rx.match(p.name)) if directory.exists() else []


def _meta(p: Path) -> Path:
    return p.with_name(p.name.split(".db.")[0] + ".meta.json")


def run(src_dir: Path, dest_dir: Path, keep: int = KEEP_WEEKS, prefix: str = "walkforward",
        mount: str = MOUNT, ismount=os.path.ismount, verify=_verify) -> Path:
    if mount and not ismount(mount):
        raise OffsiteError(f"{mount} is not mounted -- refusing to write to the SSD instead")
    found = _backups(src_dir, prefix)
    if not found:
        raise OffsiteError(f"no backup to copy in {src_dir}")
    src = found[-1]
    target = dest_dir / src.name
    if target.exists() and target.stat().st_size == src.stat().st_size:
        logger.info("already off-SSD: %s", src.name)
        return target
    verify(src)
    dest_dir.mkdir(parents=True, exist_ok=True)
    need, free = int(src.stat().st_size * 1.1), shutil.disk_usage(dest_dir).free
    if free < need:
        raise OffsiteError(f"only {free / 1e9:.1f} GB free in {dest_dir}, need {need / 1e9:.1f} GB")

    want = sha256(src)
    part = target.with_name(target.name + ".part")
    try:
        shutil.copyfile(src, part)
        if sha256(part) != want:
            raise OffsiteError(f"hash mismatch copying {src.name}")
        part.replace(target)
    finally:
        part.unlink(missing_ok=True)
    if _meta(src).exists():
        shutil.copyfile(_meta(src), _meta(target))

    for old in _backups(dest_dir, prefix)[:-keep] if keep else []:
        old.unlink(missing_ok=True)
        _meta(old).unlink(missing_ok=True)
        logger.info("pruned off-SSD %s", old.name)
    sums = dest_dir / "SHA256SUMS"
    lines = {}
    if sums.exists():
        for ln in sums.read_text().splitlines():
            digest, _, name = ln.partition("  ")
            if name:
                lines[name] = digest
    lines[target.name] = want
    sums.write_text("".join(f"{d}  {n}\n" for n, d in sorted(lines.items())
                            if (dest_dir / n).exists()))
    logger.info("off-SSD copy verified: %s (%s)", target.name, want[:12])
    return target


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, default=DEFAULT_DEST)
    ap.add_argument("--dest", type=Path, default=DEFAULT_OFFSITE)
    ap.add_argument("--keep", type=int, default=KEEP_WEEKS)
    args = ap.parse_args(argv)
    try:
        run(args.src, args.dest, keep=args.keep)
    except OffsiteError as e:
        logger.error("off-SSD backup failed: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
