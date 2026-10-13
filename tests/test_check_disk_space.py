"""Disk-space guard (2026-10-13): the SSD hit 99% and the nightly backups failed
three times in a row (10-10, 10-12 x2) without anyone being told. The guard warns
at 85% used and escalates at 90%, once per level per day, and it must get through
the TELEGRAM_OFF blackout like the backup alerts do."""
import collections
import re
from pathlib import Path

import scripts.check_disk_space as chk
from utils import notify_policy as np

ROOT = Path(__file__).resolve().parents[1]
Usage = collections.namedtuple("Usage", "total used free")
GB = 1024 ** 3


def _usage(pct):
    return lambda path: Usage(total=100 * GB, used=pct * GB, free=(100 - pct) * GB)


def _run(pct, **kw):
    sent = []
    rc = chk.check(paths=("/",), usage_fn=_usage(pct),
                   send=lambda msg, **k: sent.append((msg, k)), **kw)
    return rc, sent


def test_below_warn_is_silent():
    rc, sent = _run(84)
    assert rc == 0 and sent == []


def test_warn_level_sends_once_with_its_own_subject():
    rc, sent = _run(85)
    assert rc == 0 and len(sent) == 1
    msg, kw = sent[0]
    assert kw["event"] == "system.disk_low"
    assert kw["subject"].endswith(":warn")
    assert "85%" in msg


def test_critical_level_uses_a_separate_dedup_subject():
    _, warn = _run(86)
    _, crit = _run(90)
    assert crit[0][1]["subject"].endswith(":critical")
    assert crit[0][1]["subject"] != warn[0][1]["subject"]
    assert "CRITICAL" in crit[0][0]


def test_message_gives_free_space():
    _, sent = _run(92)
    assert "8.0 GB free" in sent[0][0]


def test_unreadable_path_is_reported_not_silent():
    def boom(path):
        raise OSError("gone")
    sent = []
    rc = chk.check(paths=("/nope",), usage_fn=boom,
                   send=lambda msg, **k: sent.append((msg, k)))
    assert rc == 1 and len(sent) == 1


def test_event_is_registered_and_survives_the_blackout():
    assert np.EVENTS["system.disk_low"][0] == np.TIER_SEND
    assert "system.disk_low" in np.BLACKOUT_EXEMPT


def test_cron_wrap_exempts_disk_guard_job():
    src = (ROOT / "scripts" / "cron_wrap.sh").read_text()
    assert re.search(r"\|disk_guard[|)]", src)


def test_systemd_unit_pair_exists_and_is_persistent():
    svc = (ROOT / "deploy" / "systemd" / "idx-disk-guard.service").read_text()
    tmr = (ROOT / "deploy" / "systemd" / "idx-disk-guard.timer").read_text()
    assert "cron_wrap.sh disk_guard" in svc
    assert "Persistent=true" in tmr and "OnCalendar=hourly" in tmr
