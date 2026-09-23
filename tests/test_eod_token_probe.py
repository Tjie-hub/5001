"""16:05 live Stockbit token probe + EOD degraded-finalisation alert (2026-09-23).

Incident: 2026-09-21 and 2026-09-22 the token was revoked server-side mid-afternoon while its
exp claim still showed ~21h left. The expiry-only health check said "OK", and the 16:15 EOD run
got HTTP 401 on all 958 tickers, leaving each session provisional with no alert until the next
morning's 09:00 check.
"""
import inspect
from unittest.mock import MagicMock

import scheduler as sched
import scheduler.jobs as jobs


def _probe_env(tmp_path, monkeypatch, statuses, token="eyJ.x.y"):
    tf = tmp_path / ".stockbit_token"
    if token is not None:
        tf.write_text(token)
    seq = list(statuses)
    probe = MagicMock(side_effect=lambda tok: seq.pop(0))
    refresh = MagicMock(return_value=True)
    sent = MagicMock()
    monkeypatch.setattr(jobs, "_stockbit_probe_status", probe)
    monkeypatch.setattr(jobs, "_run_token_refresh", refresh)
    monkeypatch.setattr(jobs, "send_telegram", sent)
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: False)
    return str(tf), probe, refresh, sent


def test_probe_silent_when_token_live(tmp_path, monkeypatch):
    tf, probe, refresh, sent = _probe_env(tmp_path, monkeypatch, [200])
    jobs.run_token_live_probe(token_file=tf)
    assert probe.call_count == 1
    assert not refresh.called and not sent.called


def test_probe_refreshes_on_401_and_reports_recovery(tmp_path, monkeypatch):
    tf, probe, refresh, sent = _probe_env(tmp_path, monkeypatch, [401, 200])
    jobs.run_token_live_probe(token_file=tf)
    assert refresh.call_count == 1
    assert probe.call_count == 2                       # re-probed after refresh
    msg = " ".join(c[0][0] for c in sent.call_args_list).lower()
    assert "401" in msg and "recovered" in msg


def test_probe_alerts_loudly_when_refresh_does_not_recover(tmp_path, monkeypatch):
    tf, probe, refresh, sent = _probe_env(tmp_path, monkeypatch, [403, 401])
    jobs.run_token_live_probe(token_file=tf)
    assert refresh.call_count == 1
    msg = sent.call_args[0][0].lower()
    assert "16:15" in msg and "fail" in msg


def test_probe_does_not_relogin_on_transient_error(tmp_path, monkeypatch):
    # a 5xx/429/timeout says nothing about the token; a re-login could itself revoke a live session
    tf, probe, refresh, sent = _probe_env(tmp_path, monkeypatch, [503])
    jobs.run_token_live_probe(token_file=tf)
    assert not refresh.called
    assert sent.called and "inconclusive" in sent.call_args[0][0].lower()


def test_probe_treats_network_exception_as_inconclusive(tmp_path, monkeypatch):
    tf, probe, refresh, sent = _probe_env(tmp_path, monkeypatch, [None])
    jobs.run_token_live_probe(token_file=tf)
    assert not refresh.called
    assert "inconclusive" in sent.call_args[0][0].lower()


def test_probe_refreshes_when_token_file_missing(tmp_path, monkeypatch):
    tf, probe, refresh, sent = _probe_env(tmp_path, monkeypatch, [200], token=None)
    jobs.run_token_live_probe(token_file=tf)
    assert refresh.call_count == 1


def test_probe_reexported_and_registered_at_1605():
    assert sched.run_token_live_probe is jobs.run_token_live_probe
    source = inspect.getsource(sched.start_scheduler)
    idx = source.index("run_token_live_probe")
    window = source[max(0, idx - 300):idx + 300]
    assert "add_job" in window and "CronTrigger" in window
    assert "hour=16, minute=5," in window
    assert 'day_of_week="mon-fri"' in window


# ── EOD degraded-finalisation alert ─────────────────────────────────────────

def test_eod_alerts_when_finalisation_is_degraded():
    import screener.screener_jobs as sj
    sent = MagicMock()
    assert sj._alert_if_eod_degraded({"filled": 0, "total": 958}, "2026-09-22", sent) is True
    msg = sent.call_args[0][0]
    assert "0/958" in msg and "2026-09-22" in msg and "repair_provisional_bars" in msg


def test_eod_silent_on_normal_coverage():
    import screener.screener_jobs as sj
    sent = MagicMock()
    assert sj._alert_if_eod_degraded({"filled": 775, "total": 958}, "2026-09-16", sent) is False
    assert not sent.called


def test_eod_alert_threshold_catches_partial_days():
    import screener.screener_jobs as sj
    sent = MagicMock()
    # 2026-09-18 wrote 14/958 as FINAL with no alert
    assert sj._alert_if_eod_degraded({"filled": 14, "total": 958}, "2026-09-18", sent) is True


def test_eod_alert_is_failsoft_without_sender_or_on_send_error():
    import screener.screener_jobs as sj
    assert sj._alert_if_eod_degraded({"filled": 0, "total": 958}, "2026-09-22", None) is True
    boom = MagicMock(side_effect=RuntimeError("telegram down"))
    assert sj._alert_if_eod_degraded({"filled": 0, "total": 958}, "2026-09-22", boom) is True


def test_run_eod_wires_the_alert():
    import screener.screener_jobs as sj
    src = inspect.getsource(sj.run_eod)
    assert "_alert_if_eod_degraded(intraday_result" in src


def test_run_intraday_reports_filled_and_total():
    import screener.screener_jobs as sj
    src = inspect.getsource(sj.run_intraday)
    assert "'filled'" in src and "'total'" in src
