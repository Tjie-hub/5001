"""Tests for news_filter's RSS fetch — the network leg of the 08:00/17:00
News Mentions Fetch job.

Root-cause coverage for the 2026-07-24 production incident: run_news_batch
held one SQLite write connection open across ~958 tickers (committing every
20), and each ticker's fetch went through feedparser.parse(url) with no
network timeout. A single stalled Google News request could therefore block
the write connection — and every other job sharing the DB — indefinitely.

The incident had two independent halves and these tests pin both:
  * the network leg must be bounded and degrade gracefully on timeout, never
    hang or raise out of fetch_news_for_ticker; and
  * run_news_batch must not hold a database connection while fetching. A
    per-request timeout caps ONE request, not the transaction — 958 bounded
    requests still add up to a long-held write lock. The batch therefore
    fetches first and writes once, and the last test below fails if anyone
    moves DB work back inside the fetch loop.
"""
import requests

import news_filter

_SAMPLE_RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><title>Contoh berita BBCA</title><pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate></item>
</channel></rss>"""


def test_fetch_news_for_ticker_bounds_network_call_with_timeout(monkeypatch):
    calls = {}

    class _FakeResponse:
        content = _SAMPLE_RSS

    def _fake_get(url, timeout=None, **kwargs):
        calls["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(news_filter.requests, "get", _fake_get)

    news_filter.fetch_news_for_ticker("BBCA")

    assert calls.get("timeout") is not None, "RSS fetch must pass an explicit timeout"
    assert 0 < calls["timeout"] <= 15


def test_fetch_news_for_ticker_degrades_on_timeout(monkeypatch):
    def _fake_get(url, timeout=None, **kwargs):
        raise requests.exceptions.Timeout("simulated stalled feed")

    monkeypatch.setattr(news_filter.requests, "get", _fake_get)

    count, headlines = news_filter.fetch_news_for_ticker("BBCA")  # must not raise

    assert count == 0
    assert headlines == []


def test_run_news_batch_holds_no_db_connection_while_fetching(monkeypatch):
    """The DB half of the 2026-07-24 incident.

    Bounding the network leg caps a single request; it does not cap the write
    transaction. This pins the compute-then-write shape: every connection must
    be opened AFTER the last fetch returns, so the write lock is never held
    across the sweep. Regressing to a connection opened before the loop (even
    one committing every N tickers) fails here.
    """
    order = []

    def _fake_fetch(ticker, today=None):
        order.append(("fetch", ticker))
        return 0, []

    real_connect = news_filter.db_connect

    def _tracking_connect(*a, **kw):
        order.append(("connect", None))
        return real_connect(*a, **kw)

    monkeypatch.setattr(news_filter, "fetch_news_for_ticker", _fake_fetch)
    monkeypatch.setattr(news_filter, "db_connect", _tracking_connect)

    news_filter.run_news_batch(tickers=["BBCA", "BBRI", "TLKM"], delay=0)

    kinds = [k for k, _ in order]
    assert "fetch" in kinds, "test did not exercise the fetch loop"
    assert "connect" in kinds, "batch never opened a connection"
    last_fetch = max(i for i, (k, _) in enumerate(order) if k == "fetch")
    first_connect = min(i for i, (k, _) in enumerate(order) if k == "connect")
    assert first_connect > last_fetch, (
        "run_news_batch opened a DB connection before the fetch sweep finished — "
        "that is the held-write-lock shape of the 2026-07-24 incident"
    )


class _Resp:
    def __init__(self, status, content=b"<rss><channel></channel></rss>"):
        self.status_code = status
        self.content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code} Client Error")


def test_fetch_news_for_ticker_retries_once_on_transient_404(monkeypatch):
    calls = []

    def _fake_get(url, **kwargs):
        calls.append(url)
        return _Resp(404 if len(calls) == 1 else 200)

    monkeypatch.setattr(news_filter.requests, "get", _fake_get)
    monkeypatch.setattr(news_filter.time, "sleep", lambda s: None)

    count, headlines = news_filter.fetch_news_for_ticker("ABDA")

    assert len(calls) == 2
    assert (count, headlines) == (0, [])


def test_fetch_news_for_ticker_retry_is_bounded_to_one(monkeypatch):
    calls = []

    def _fake_get(url, **kwargs):
        calls.append(url)
        return _Resp(404)

    monkeypatch.setattr(news_filter.requests, "get", _fake_get)
    monkeypatch.setattr(news_filter.time, "sleep", lambda s: None)

    assert news_filter.fetch_news_for_ticker("ABDA") == (0, [])  # must not raise
    assert len(calls) == 2


def test_fetch_news_for_ticker_does_not_retry_on_timeout(monkeypatch):
    calls = []

    def _fake_get(url, **kwargs):
        calls.append(url)
        raise requests.exceptions.Timeout("simulated stalled feed")

    monkeypatch.setattr(news_filter.requests, "get", _fake_get)

    assert news_filter.fetch_news_for_ticker("ABDA") == (0, [])
    assert len(calls) == 1
