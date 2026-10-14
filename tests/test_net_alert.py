"""scripts/net_alert.py — Telegram alert for the ~/watch.sh internet watcher.

The watcher can only send AFTER the link is back (a down link cannot reach
Telegram), so the message is a recovery summary: when it went down, how long,
and the layer verdict the watcher logged.
"""
import importlib.util
from pathlib import Path

import utils.notify_policy as np

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("net_alert", ROOT / "scripts" / "net_alert.py")
na = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(na)

DOWN = 1791961200          # 2026-10-14 14:00:00 WIB
UP = DOWN + 215            # 3m35s later


def test_event_is_registered_and_survives_the_blackout():
    # An internet-outage alert that the TELEGRAM_OFF blackout swallows is useless.
    assert np.EVENTS["system.net_outage"][0] == np.TIER_SEND
    assert "system.net_outage" in np.BLACKOUT_EXEMPT


def test_outage_message_has_window_duration_and_verdict():
    sent = []
    rc = na.alert("internet", DOWN, UP, "BIZNET: ONT up but Biznet gateway 10.109.0.1 down",
                  min_s=60, send=lambda msg, **k: sent.append((msg, k)))
    assert rc == 0 and len(sent) == 1
    msg, kw = sent[0]
    assert "3m35s" in msg and "14:00:00" in msg and "14:03:35" in msg
    assert "BIZNET" in msg
    assert kw["event"] == "system.net_outage" and kw["subject"] == "internet"


def test_dns_message_is_labelled_dns():
    sent = []
    na.alert("dns", DOWN, UP, "LOCAL systemd-resolved fault", min_s=60,
             send=lambda msg, **k: sent.append((msg, k)))
    assert "DNS" in sent[0][0] and sent[0][1]["subject"] == "dns"


def test_short_blip_is_not_alerted():
    sent = []
    rc = na.alert("internet", DOWN, DOWN + 20, "x", min_s=60,
                  send=lambda msg, **k: sent.append(msg))
    assert rc == 0 and sent == []


def test_send_failure_never_raises():
    def boom(msg, **k):
        raise RuntimeError("telegram down")
    assert na.alert("internet", DOWN, UP, "x", min_s=60, send=boom) == 1


def test_fmt_duration():
    assert na.fmt_duration(45) == "45s"
    assert na.fmt_duration(215) == "3m35s"
    assert na.fmt_duration(3725) == "1h02m05s"


def test_script_loads_env_via_config():
    # ~/watch.sh runs this script outside cron_wrap.sh, so nothing else exports
    # TELEGRAM_*; without importing config the send silently returns False.
    import sys
    assert "config" in sys.modules
    assert na.config is sys.modules["config"]


def test_undelivered_send_is_reported_not_claimed():
    # send_telegram returns False for suppressed/unconfigured; that must surface.
    assert na.alert("internet", DOWN, UP, "x", min_s=60, send=lambda msg, **k: False) == 1
