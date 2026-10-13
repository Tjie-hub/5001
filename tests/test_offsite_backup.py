"""Weekly off-SSD copy of the newest verified nightly backup (2026-10-13).

The SSD is the only place the nightly backups lived; one disk failure would take
the live DB and every backup together. This copies the newest verified backup to
the USB archive drive, hash-checks it, and keeps 8 weeks there."""
import json
import re
from pathlib import Path

import pytest

import scripts.offsite_backup as ob

ROOT = Path(__file__).resolve().parents[1]


def _mk(src, day, payload=b"x" * 100):
    f = src / f"walkforward-202610{day:02d}-213000.db.zst"
    f.write_bytes(payload + bytes([day]))
    (src / f"walkforward-202610{day:02d}-213000.meta.json").write_text(json.dumps({"d": day}))
    return f


def _run(src, dest, **kw):
    kw.setdefault("ismount", lambda p: True)
    kw.setdefault("verify", lambda p: None)
    return ob.run(src, dest, **kw)


def test_copies_newest_backup_with_matching_hash(tmp_path):
    src, dest = tmp_path / "s", tmp_path / "d"
    src.mkdir()
    _mk(src, 8); newest = _mk(src, 12)
    out = _run(src, dest)
    assert out.name == newest.name
    assert out.read_bytes() == newest.read_bytes()
    assert (dest / "walkforward-20261012-213000.meta.json").exists()
    sums = (dest / "SHA256SUMS").read_text()
    assert newest.name in sums and "20261008" not in sums


def test_refuses_when_drive_not_mounted(tmp_path):
    src = tmp_path / "s"; src.mkdir(); _mk(src, 12)
    with pytest.raises(ob.OffsiteError, match="not mounted"):
        _run(src, tmp_path / "d", ismount=lambda p: False)
    assert not (tmp_path / "d").exists()


def test_refuses_when_backup_fails_verification(tmp_path):
    src = tmp_path / "s"; src.mkdir(); _mk(src, 12)
    def bad(p):
        raise ob.OffsiteError("zstd -t failed")
    with pytest.raises(ob.OffsiteError):
        _run(src, tmp_path / "d", verify=bad)
    assert not list((tmp_path / "d").glob("walkforward-*")) if (tmp_path / "d").exists() else True


def test_no_backup_to_copy_is_an_error(tmp_path):
    src = tmp_path / "s"; src.mkdir()
    with pytest.raises(ob.OffsiteError, match="no backup"):
        _run(src, tmp_path / "d")


def test_already_copied_is_skipped_not_recopied(tmp_path):
    src, dest = tmp_path / "s", tmp_path / "d"
    src.mkdir(); _mk(src, 12)
    first = _run(src, dest)
    mtime = first.stat().st_mtime_ns
    again = _run(src, dest)
    assert again == first and first.stat().st_mtime_ns == mtime


def test_hash_mismatch_removes_partial_and_raises(tmp_path, monkeypatch):
    src, dest = tmp_path / "s", tmp_path / "d"
    src.mkdir(); _mk(src, 12)
    real = ob.sha256
    calls = {"n": 0}
    def flaky(p):
        calls["n"] += 1
        return real(p) if calls["n"] == 1 else "0" * 64
    monkeypatch.setattr(ob, "sha256", flaky)
    with pytest.raises(ob.OffsiteError, match="hash mismatch"):
        _run(src, dest)
    assert not list(dest.glob("walkforward-*"))


def test_prunes_to_newest_keep_and_rewrites_sums(tmp_path):
    src, dest = tmp_path / "s", tmp_path / "d"
    src.mkdir()
    for d in range(1, 6):
        _mk(src, d)
        _run(src, dest, keep=3)
    names = sorted(p.name for p in dest.glob("walkforward-*.db.zst"))
    assert names == [f"walkforward-202610{d:02d}-213000.db.zst" for d in (3, 4, 5)]
    assert not (dest / "walkforward-20261001-213000.meta.json").exists()
    sums = (dest / "SHA256SUMS").read_text()
    assert "20261001" not in sums and "20261005" in sums


def test_refuses_without_enough_free_space(tmp_path, monkeypatch):
    src = tmp_path / "s"; src.mkdir(); _mk(src, 12)
    import collections
    U = collections.namedtuple("U", "total used free")
    monkeypatch.setattr(ob.shutil, "disk_usage", lambda p: U(10**9, 10**9, 5))
    with pytest.raises(ob.OffsiteError, match="free"):
        _run(src, tmp_path / "d")


def test_systemd_unit_pair_runs_weekly_via_wrapper_after_the_drill():
    svc = (ROOT / "deploy/systemd/idx-offsite-backup.service").read_text()
    tmr = (ROOT / "deploy/systemd/idx-offsite-backup.timer").read_text()
    assert "cron_wrap.sh offsite_backup" in svc
    assert "Persistent=true" in tmr
    assert re.search(r"OnCalendar=Sun \*-\*-\* 1[0-9]:", tmr)


def test_nightly_service_keeps_four_daily_two_weekly():
    svc = (ROOT / "deploy/systemd/idx-db-backup.service").read_text()
    assert "--keep-daily 4" in svc and "--keep-weekly 2" in svc


def test_offsite_job_alerts_through_blackout_and_is_heartbeat_watched():
    wrap = (ROOT / "scripts/cron_wrap.sh").read_text()
    assert "|offsite_backup" in wrap
    import scripts.check_backup_heartbeat as hb
    assert any("off-SSD" in n for n, _, _ in hb.DEFAULT_CHECKS)
