"""Regression tests for fetch_broker_flow()'s retry/backoff behavior.

Prior to this, fetch_broker_flow() made exactly one HTTP request and returned
None on ANY non-200 status, with no distinction between a transient 429 and
a genuine HTTP failure. This mirrors fetch_flow()'s already-proven 429/
Retry-After backoff ladder onto fetch_broker_flow(), and adds a distinct
RateLimitExceeded exception so callers (the IDX80 broker-flow backfill) can
tell "rate limited after exhausting retries" apart from "HTTP/API failure"
in their own logging, per the broker-flow backfill agent's reliability
reporting requirement.
"""
from unittest.mock import patch, MagicMock

import pytest

import stockbit_fetcher as sf


def _resp(status_code, headers=None, brokers_buy=None, brokers_sell=None, to="2026-07-31"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.json.return_value = {
        "data": {
            "to": to,
            "broker_summary": {
                "brokers_buy": brokers_buy or [],
                "brokers_sell": brokers_sell or [],
            },
            "bandar_detector": {},
        }
    }
    return resp


def test_429_then_200_succeeds_without_raising(monkeypatch):
    monkeypatch.setattr(sf.time, "sleep", lambda *a, **k: None)
    responses = [_resp(429, headers={"Retry-After": "1"}), _resp(200)]
    with patch("stockbit_fetcher.requests.get", side_effect=responses) as mock_get:
        result = sf.fetch_broker_flow("tok", "BBCA", "2026-07-31")
    assert result is not None
    assert mock_get.call_count == 2


def test_429_backoff_honors_retry_after_header(monkeypatch):
    slept = []
    monkeypatch.setattr(sf.time, "sleep", lambda s: slept.append(s))
    responses = [_resp(429, headers={"Retry-After": "7"}), _resp(200)]
    with patch("stockbit_fetcher.requests.get", side_effect=responses):
        sf.fetch_broker_flow("tok", "BBCA", "2026-07-31")
    assert slept == [7]


def test_429_without_retry_after_uses_default_ladder(monkeypatch):
    slept = []
    monkeypatch.setattr(sf.time, "sleep", lambda s: slept.append(s))
    responses = [_resp(429), _resp(200)]
    with patch("stockbit_fetcher.requests.get", side_effect=responses):
        sf.fetch_broker_flow("tok", "BBCA", "2026-07-31")
    assert slept == [20]  # 20 * (attempt 1)


def test_sustained_429_raises_rate_limit_exceeded(monkeypatch):
    monkeypatch.setattr(sf.time, "sleep", lambda *a, **k: None)
    responses = [_resp(429) for _ in range(4)]
    with patch("stockbit_fetcher.requests.get", side_effect=responses):
        with pytest.raises(sf.RateLimitExceeded):
            sf.fetch_broker_flow("tok", "BBCA", "2026-07-31")


def test_non_429_http_failure_returns_none_not_raises(monkeypatch):
    monkeypatch.setattr(sf.time, "sleep", lambda *a, **k: None)
    with patch("stockbit_fetcher.requests.get", return_value=_resp(500)):
        result = sf.fetch_broker_flow("tok", "BBCA", "2026-07-31")
    assert result is None


def test_plain_200_still_works_unchanged(monkeypatch):
    monkeypatch.setattr(sf.time, "sleep", lambda *a, **k: None)
    with patch("stockbit_fetcher.requests.get", return_value=_resp(200)):
        result = sf.fetch_broker_flow("tok", "BBCA", "2026-07-31")
    assert result is not None
    assert result["broker_rows"] == []
