"""Regression tests for the ensure_valid_token() manual-token fallback bypass
(second, compounding root cause of the 2026-07-27 stockbit_flow outage).

Every production cron invokes stockbit_fetcher.py with an explicit
`--token "$(cat .stockbit_token)"` argument (see deploy/crontab). Before this
fix, ensure_valid_token() returned None immediately whenever that manual
token was invalid -- silently skipping the auto_refresh()/credential_login()
fallback that already existed (and works) for the no-manual-token branch a
few lines below in the same function. See
docs/audit/STOCKBIT_TOKEN_REFRESH_HARDENING.md.
"""
import pytest

import stockbit_fetcher as sf
import auto_token as at


@pytest.fixture(autouse=True)
def no_telegram(monkeypatch):
    monkeypatch.setattr(sf, "send_telegram", lambda *a, **k: None)


def test_valid_manual_token_returned_directly(monkeypatch):
    monkeypatch.setattr(sf, "verify_token", lambda t: True)
    assert sf.ensure_valid_token("good-token") == "good-token"


def test_invalid_manual_token_falls_back_to_auto_refresh(monkeypatch):
    """The core regression: a stale --token argument (exactly what every
    production cron passes) must not be a dead end."""
    monkeypatch.setattr(sf, "verify_token", lambda t: t == "fresh-token")
    monkeypatch.setattr(at, "auto_refresh", lambda: "fresh-token")
    monkeypatch.setattr(at, "verify_token", lambda t: t == "fresh-token")
    written = {}
    monkeypatch.setattr(at, "_write_token_atomic", lambda tok, **k: written.setdefault("token", tok))

    result = sf.ensure_valid_token("stale-token")

    assert result == "fresh-token"
    assert written["token"] == "fresh-token"


def test_invalid_manual_token_falls_back_to_credential_login_when_auto_refresh_fails(monkeypatch):
    monkeypatch.setattr(sf, "verify_token", lambda t: t == "cred-token")
    monkeypatch.setattr(at, "auto_refresh", lambda: None)
    monkeypatch.setattr(at, "credential_login", lambda: "cred-token")
    monkeypatch.setattr(at, "verify_token", lambda t: t == "cred-token")
    written = {}
    monkeypatch.setattr(at, "_write_token_atomic", lambda tok, **k: written.setdefault("token", tok))

    result = sf.ensure_valid_token("stale-token")

    assert result == "cred-token"
    assert written["token"] == "cred-token"


def test_invalid_manual_token_with_all_fallbacks_failing_returns_none_not_crash(monkeypatch):
    monkeypatch.setattr(sf, "verify_token", lambda t: False)
    monkeypatch.setattr(at, "auto_refresh", lambda: None)
    monkeypatch.setattr(at, "credential_login", lambda: None)

    result = sf.ensure_valid_token("stale-token")

    assert result is None


def test_no_manual_token_still_uses_chrome_extraction_first(monkeypatch):
    monkeypatch.setattr(sf, "extract_token_from_chrome", lambda: "chrome-token")
    monkeypatch.setattr(sf, "verify_token", lambda t: t == "chrome-token")

    result = sf.ensure_valid_token(None)

    assert result == "chrome-token"
