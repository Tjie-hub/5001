"""Regression tests for ensure_valid_token().

Two incidents shaped it:

2026-07-27 — the manual-token fallback bypass. Every production cron invokes
stockbit_fetcher.py with an explicit `--token "$(cat .stockbit_token)"`
argument (see deploy/crontab). Before that fix, ensure_valid_token() returned
None immediately whenever that manual token was invalid -- silently skipping
the auto_refresh()/credential_login() fallback. See
docs/audit/STOCKBIT_TOKEN_REFRESH_HARDENING.md.

2026-09-21/22 — server-side revocation while the exp claim was still valid.
verify_token()'s bool collapse made every network error / 5xx / rate limit
look like a dead token, and a login that is not needed may itself revoke the
account's other sessions. Since the hardening, ONLY an auth rejection
(401/403) reaches the login fallback; transient statuses are retried with
backoff and an inconclusive verdict aborts the run without a login.
"""
from unittest.mock import MagicMock

import pytest

import stockbit_fetcher as sf
import auto_token as at


@pytest.fixture(autouse=True)
def no_telegram(monkeypatch):
    monkeypatch.setattr(sf, "send_telegram", lambda *a, **k: None)


@pytest.fixture
def no_login(monkeypatch):
    """The fallback chain, instrumented: must stay unreached unless 401/403."""
    m = MagicMock(side_effect=lambda: 'fresh-token')
    monkeypatch.setattr(at, "auto_refresh", m)
    monkeypatch.setattr(at, "verify_token", lambda t: t == 'fresh-token')
    monkeypatch.setattr(at, "credential_login", lambda: 'cred-token')
    monkeypatch.setattr(at, "_write_token_atomic", lambda tok, **k: None)
    return m


_NOSLEEP = lambda s: None  # noqa: E731


def test_valid_manual_token_returned_directly(monkeypatch):
    monkeypatch.setattr(sf, "token_status", lambda t: 200)
    assert sf.ensure_valid_token("good-token", sleep=_NOSLEEP) == "good-token"


def test_revoked_manual_token_falls_back_to_auto_refresh(monkeypatch, no_login):
    """The core 2026-07-27 regression: a stale --token argument (exactly what
    every production cron passes) must not be a dead end."""
    monkeypatch.setattr(sf, "token_status", lambda t: 401)

    result = sf.ensure_valid_token("stale-token", sleep=_NOSLEEP)

    assert result == "fresh-token"
    assert no_login.call_count == 1


def test_403_is_treated_like_401(monkeypatch, no_login):
    monkeypatch.setattr(sf, "token_status", lambda t: 403)

    assert sf.ensure_valid_token("stale-token", sleep=_NOSLEEP) == "fresh-token"


def test_revoked_manual_token_falls_back_to_credential_login_when_auto_refresh_fails(
        monkeypatch):
    monkeypatch.setattr(sf, "token_status", lambda t: 401)
    monkeypatch.setattr(at, "auto_refresh", lambda: None)
    monkeypatch.setattr(at, "credential_login", lambda: 'cred-token')
    monkeypatch.setattr(at, "verify_token", lambda t: t == 'cred-token')
    written = {}
    monkeypatch.setattr(at, "_write_token_atomic", lambda tok, **k: written.setdefault("token", tok))

    result = sf.ensure_valid_token("stale-token", sleep=_NOSLEEP)

    assert result == "cred-token"
    assert written["token"] == "cred-token"


def test_revoked_manual_token_with_all_fallbacks_failing_returns_none_not_crash(monkeypatch):
    monkeypatch.setattr(sf, "token_status", lambda t: 401)
    monkeypatch.setattr(at, "auto_refresh", lambda: None)
    monkeypatch.setattr(at, "credential_login", lambda: None)

    assert sf.ensure_valid_token("stale-token", sleep=_NOSLEEP) is None


def test_persistent_5xx_never_logs_in(monkeypatch, no_login):
    """A 5xx says nothing about the token — an inconclusive verdict aborts
    without a login (the 2026-09-21/22 rule)."""
    monkeypatch.setattr(sf, "token_status", lambda t: 503)

    result = sf.ensure_valid_token("stale-token", sleep=_NOSLEEP)

    assert result is None
    assert no_login.call_count == 0


def test_transient_5xx_recovers_without_login(monkeypatch, no_login):
    seq = iter([503, 200])
    monkeypatch.setattr(sf, "token_status", lambda t: next(seq))

    result = sf.ensure_valid_token("stale-token", sleep=_NOSLEEP)

    assert result == "stale-token"
    assert no_login.call_count == 0


def test_network_error_is_inconclusive_and_never_logs_in(monkeypatch, no_login):
    monkeypatch.setattr(sf, "token_status", lambda t: None)

    result = sf.ensure_valid_token("stale-token", sleep=_NOSLEEP)

    assert result is None
    assert no_login.call_count == 0


def test_429_is_inconclusive_not_revoked(monkeypatch, no_login):
    monkeypatch.setattr(sf, "token_status", lambda t: 429)

    assert sf.ensure_valid_token("stale-token", sleep=_NOSLEEP) is None
    assert no_login.call_count == 0


def test_no_manual_token_still_uses_chrome_extraction_first(monkeypatch):
    monkeypatch.setattr(sf, "extract_token_from_chrome", lambda: "chrome-token")
    monkeypatch.setattr(sf, "token_status", lambda t: 200 if t == "chrome-token" else 401)

    assert sf.ensure_valid_token(None, sleep=_NOSLEEP) == "chrome-token"


def test_missing_chrome_token_goes_straight_to_refresh(monkeypatch, no_login):
    monkeypatch.setattr(sf, "extract_token_from_chrome", lambda: None)

    assert sf.ensure_valid_token(None, sleep=_NOSLEEP) == "fresh-token"
    assert no_login.call_count == 1
