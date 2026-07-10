"""Backup/restore protection cycle (audit P-3): snapshot → verify → compress →
meta → prune retention → restore-verify → apply."""
import datetime
import json
import sqlite3

import pytest

from scripts import db_backup, db_restore


@pytest.fixture
def src_db(tmp_path):
    db = tmp_path / "src.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE ohlcv (ticker TEXT, date TEXT, close REAL);
        CREATE TABLE paper_trades (id INTEGER PRIMARY KEY, ticker TEXT);
    """)
    conn.executemany("INSERT INTO ohlcv VALUES (?,?,?)",
                     [("BBCA", f"2026-07-{d:02d}", 100.0 + d) for d in range(1, 11)])
    conn.execute("INSERT INTO paper_trades (ticker) VALUES ('BBCA')")
    conn.commit()
    conn.close()
    return db


def test_full_backup_cycle_produces_verified_compressed_backup(src_db, tmp_path):
    dest = tmp_path / "backups"
    out = db_backup.run_backup(src_db, dest)
    assert out.exists() and out.name.startswith("walkforward-")
    assert out.suffix in (".zst", ".gz")
    meta = json.loads((dest / (out.name.split(".db")[0] + ".meta.json")).read_text())
    assert meta["integrity"] == "ok"
    assert meta["tables"]["ohlcv"] == 10
    assert meta["tables"]["paper_trades"] == 1


def test_snapshot_is_consistent_while_source_has_open_writer(src_db, tmp_path):
    # WAL mode + an uncommitted writer must not corrupt or block the snapshot.
    writer = sqlite3.connect(src_db)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("INSERT INTO ohlcv VALUES ('UNCOMMITTED','2026-01-01',1)")
    try:
        snap = db_backup.snapshot(src_db, tmp_path / "b")
        meta = db_backup.verify(snap)
        assert meta["tables"]["ohlcv"] == 10  # uncommitted row not included
    finally:
        writer.rollback()
        writer.close()


def test_verify_raises_on_corrupt_snapshot(tmp_path):
    bad = tmp_path / "bad.db"
    bad.write_bytes(b"SQLite format 3\x00" + b"\x00" * 400)
    with pytest.raises(Exception):
        db_backup.verify(bad)


def test_run_backup_deletes_snapshot_and_raises_when_verify_fails(src_db, tmp_path, monkeypatch):
    def boom(_):
        raise RuntimeError("integrity_check failed: corrupt")
    monkeypatch.setattr(db_backup, "verify", boom)
    dest = tmp_path / "backups"
    with pytest.raises(RuntimeError):
        db_backup.run_backup(src_db, dest)
    assert not list(dest.glob("*.db")), "failed snapshot must not be left behind"


def test_gzip_fallback_when_zstd_missing(src_db, tmp_path, monkeypatch):
    monkeypatch.setattr(db_backup.shutil, "which", lambda _: None)
    out = db_backup.run_backup(src_db, tmp_path / "b")
    assert out.suffix == ".gz"


def _fake_backup(dest, ts):
    name = f"walkforward-{ts:%Y%m%d-%H%M%S}.db.zst"
    (dest / name).write_bytes(b"x")
    (dest / name.split(".db")[0]).with_suffix(".meta.json").write_text("{}")
    return dest / name


def test_prune_keeps_daily_and_weekly_retention(tmp_path):
    dest = tmp_path / "b"
    dest.mkdir()
    base = datetime.datetime(2026, 7, 9, 21, 30)
    # 30 consecutive daily backups ending 2026-07-09
    files = [_fake_backup(dest, base - datetime.timedelta(days=i)) for i in range(30)]
    deleted = db_backup.prune(dest, keep_daily=7, keep_weekly=4)
    remaining = sorted(p.name for p in dest.glob("*.db.zst"))
    # newest 7 days always kept
    for i in range(7):
        assert files[i].name in remaining
    # older-than-7-days survivors must be newest-of-week only
    survivors_old = [n for n in remaining if n not in {f.name for f in files[:7]}]
    assert len(survivors_old) <= 4
    assert len(deleted) == 30 - len(remaining)
    # meta files pruned together with their backups
    assert len(list(dest.glob("*.meta.json"))) == len(remaining)


def test_prune_keeps_only_newest_backup_per_day(tmp_path):
    dest = tmp_path / "b"
    dest.mkdir()
    morning = _fake_backup(dest, datetime.datetime(2026, 7, 9, 8, 0))
    evening = _fake_backup(dest, datetime.datetime(2026, 7, 9, 21, 30))
    db_backup.prune(dest, keep_daily=7, keep_weekly=0)
    assert not morning.exists() and evening.exists()


def test_restore_verify_roundtrip(src_db, tmp_path):
    dest = tmp_path / "backups"
    backup = db_backup.run_backup(src_db, dest)
    rc = db_restore.main([str(backup), "--work-dir", str(tmp_path / "w")])
    assert rc == 0


def test_restore_verify_fails_on_rowcount_mismatch(src_db, tmp_path):
    dest = tmp_path / "backups"
    backup = db_backup.run_backup(src_db, dest)
    meta_path = dest / (backup.name.split(".db")[0] + ".meta.json")
    meta = json.loads(meta_path.read_text())
    meta["tables"]["ohlcv"] = 999  # tampered expectation
    meta_path.write_text(json.dumps(meta))
    rc = db_restore.main([str(backup), "--work-dir", str(tmp_path / "w")])
    assert rc == 1


def test_restore_apply_swaps_db_and_keeps_previous_aside(src_db, tmp_path):
    dest = tmp_path / "backups"
    backup = db_backup.run_backup(src_db, dest)
    live = tmp_path / "live.db"
    live.write_bytes(b"OLD")
    rc = db_restore.main([str(backup), "--apply", "--db", str(live),
                          "--work-dir", str(tmp_path / "w")])
    assert rc == 0
    conn = sqlite3.connect(live)
    assert conn.execute("SELECT COUNT(*) FROM ohlcv").fetchone()[0] == 10
    conn.close()
    aside = list(tmp_path.glob("live.db.pre_restore_*"))
    assert len(aside) == 1 and aside[0].read_bytes() == b"OLD"
