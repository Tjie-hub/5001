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


# --- Pre-open capture (D-117/D-118) ---------------------------------------------------------------
# The 17:00 run's INSERT OR REPLACE erased every 08:00 row, so "was this headline out before the
# 09:00 open?" could not be answered for 111 of 119 days. The pre-market run now also writes
# news_mentions_premarket: written only by that run, first write wins, never after the open.

def _premarket_rows(ticker):
    conn = news_filter.db_connect(news_filter._DB_PATH)
    try:
        news_filter._ensure_premarket_table(conn)  # absent when no pre-market row was ever written
        return conn.execute(
            "SELECT count, headlines_json, captured_at FROM news_mentions_premarket WHERE ticker=?",
            (ticker,)).fetchall()
    finally:
        conn.close()


def _mentions_count(ticker):
    conn = news_filter.db_connect(news_filter._DB_PATH)
    try:
        return conn.execute("SELECT count FROM news_mentions WHERE ticker=?", (ticker,)).fetchone()[0]
    finally:
        conn.close()


def _at(hh, mm):
    from datetime import datetime
    return lambda: datetime.now().replace(hour=hh, minute=mm, second=0, microsecond=0)


def test_premarket_copy_survives_the_17_00_replace(monkeypatch):
    monkeypatch.setattr(news_filter, "fetch_news_for_ticker", lambda t, today=None: (2, ["a", "b"]))
    monkeypatch.setattr(news_filter, "_now", _at(8, 22))
    news_filter.run_news_batch(tickers=["BBCA"], delay=0, premarket=True)

    monkeypatch.setattr(news_filter, "fetch_news_for_ticker", lambda t, today=None: (5, list("abcde")))
    monkeypatch.setattr(news_filter, "_now", _at(17, 23))
    news_filter.run_news_batch(tickers=["BBCA"], delay=0)            # the 17:00 run

    assert _mentions_count("BBCA") == 5                               # news_mentions behaves as before
    rows = _premarket_rows("BBCA")
    assert len(rows) == 1 and rows[0][0] == 2 and '"a"' in rows[0][1]
    assert rows[0][2].endswith("08:22:00")


def test_premarket_first_capture_wins(monkeypatch):
    monkeypatch.setattr(news_filter, "_now", _at(8, 22))
    monkeypatch.setattr(news_filter, "fetch_news_for_ticker", lambda t, today=None: (1, ["first"]))
    news_filter.run_news_batch(tickers=["TLKM"], delay=0, premarket=True)
    monkeypatch.setattr(news_filter, "fetch_news_for_ticker", lambda t, today=None: (3, ["x", "y", "z"]))
    news_filter.run_news_batch(tickers=["TLKM"], delay=0, premarket=True)   # a manual re-run
    assert [r[0] for r in _premarket_rows("TLKM")] == [1]


def test_premarket_not_recorded_at_or_after_the_open(monkeypatch):
    # A late 08:00 job (service up after 08:00, misfire grace) must not label 09:xx headlines pre-open.
    monkeypatch.setattr(news_filter, "fetch_news_for_ticker", lambda t, today=None: (2, ["a", "b"]))
    monkeypatch.setattr(news_filter, "_now", _at(9, 0))
    news_filter.run_news_batch(tickers=["BBRI"], delay=0, premarket=True)
    assert _mentions_count("BBRI") == 2
    assert _premarket_rows("BBRI") == []


def test_regular_run_never_writes_premarket(monkeypatch):
    monkeypatch.setattr(news_filter, "fetch_news_for_ticker", lambda t, today=None: (2, ["a", "b"]))
    monkeypatch.setattr(news_filter, "_now", _at(8, 22))
    news_filter.run_news_batch(tickers=["ASII"], delay=0)            # premarket defaults to False
    assert _premarket_rows("ASII") == []


def test_scheduler_marks_only_the_08_00_slot_premarket():
    import inspect
    import scheduler
    calls = inspect.getsource(scheduler.start_scheduler).split("_add_job(")
    pre = [c for c in calls if 'id="news_fetch_premarket"' in c]
    eve = [c for c in calls if 'id="news_fetch",' in c]
    assert len(pre) == 1 and len(eve) == 1
    assert 'kwargs={"premarket": True}' in pre[0]
    assert "kwargs" not in eve[0]
