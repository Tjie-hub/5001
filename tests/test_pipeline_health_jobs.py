"""Phase 3A scheduler jobs: alert on token expiry / thin OHLCV coverage."""
import base64
import json
import sqlite3
import time
from unittest.mock import MagicMock


def _make_jwt(exp_ts):
    hdr = base64.urlsafe_b64encode(b'{"alg":"HS256"}').rstrip(b"=").decode()
    pay = base64.urlsafe_b64encode(json.dumps({"exp": int(exp_ts)}).encode()).rstrip(b"=").decode()
    return f"{hdr}.{pay}.sig"


def test_token_health_alerts_when_expired(tmp_path, monkeypatch):
    import scheduler.jobs as jobs
    tf = tmp_path / ".stockbit_token"
    tf.write_text(_make_jwt(time.time() - 3600))        # expired 1h ago
    sent = MagicMock()
    monkeypatch.setattr(jobs, "send_telegram", sent)
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: False)
    jobs.run_token_health_check(token_file=str(tf))
    assert sent.called
    assert "token" in sent.call_args[0][0].lower()


def test_token_health_silent_when_valid(tmp_path, monkeypatch):
    import scheduler.jobs as jobs
    tf = tmp_path / ".stockbit_token"
    tf.write_text(_make_jwt(time.time() + 20 * 3600))   # 20h left
    sent = MagicMock()
    monkeypatch.setattr(jobs, "send_telegram", sent)
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: False)
    jobs.run_token_health_check(token_file=str(tf))
    assert not sent.called                              # healthy -> no noise


def _cov_db(tmp_path, day, n_tickers, universe):
    db = str(tmp_path / "cov.db")
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, close REAL)")
    conn.execute("CREATE TABLE idx_tickers (ticker TEXT PRIMARY KEY, status TEXT)")
    conn.execute("INSERT INTO ohlcv VALUES ('IHSG',?,7000)", (day,))
    for i in range(universe):
        conn.execute("INSERT INTO idx_tickers VALUES (?, 'active')", (f"T{i}",))
    for i in range(n_tickers):
        conn.execute("INSERT INTO ohlcv VALUES (?,?,100)", (f"T{i}", day))
    conn.commit()
    conn.close()
    return db


def test_coverage_check_alerts_on_thin_day(tmp_path, monkeypatch):
    import scheduler.jobs as jobs
    db = _cov_db(tmp_path, "2026-07-06", n_tickers=100, universe=958)   # 10%
    monkeypatch.setattr(jobs, "DB_PATH", db)
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: False)
    sent = MagicMock(); monkeypatch.setattr(jobs, "send_telegram", sent)
    jobs.run_ohlcv_coverage_check(date_str="2026-07-06")
    assert sent.called
    assert "coverage" in sent.call_args[0][0].lower()


def test_coverage_check_silent_when_full(tmp_path, monkeypatch):
    import scheduler.jobs as jobs
    db = _cov_db(tmp_path, "2026-07-06", n_tickers=950, universe=958)   # 99%
    monkeypatch.setattr(jobs, "DB_PATH", db)
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: False)
    sent = MagicMock(); monkeypatch.setattr(jobs, "send_telegram", sent)
    jobs.run_ohlcv_coverage_check(date_str="2026-07-06")
    assert not sent.called
