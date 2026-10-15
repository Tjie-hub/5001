"""One trade-book download per ticker shared by the flow fetch, the screener scrape and the 18:30 cron (2026-10-15)."""
import pathlib
import sys
import types
from datetime import date, datetime, timedelta

import pytest

from data import tradebook_cache as tc

PAYLOAD = {"date": "2026-10-15", "buy": [], "sell": [], "net_values": [], "prices": [{"value": {"raw": "100"}}]}
T0 = datetime(2026, 10, 15, 16, 16, 0)


def test_put_then_get_respects_not_before():
    tc.put("bbca", PAYLOAD, now=T0)
    assert tc.get("BBCA", T0 - timedelta(minutes=1), now=T0) == PAYLOAD
    assert tc.get("BBCA", T0 + timedelta(seconds=1), now=T0) is None       # older than required
    assert tc.get("BBCA", T0, now=T0 + timedelta(days=1)) is None           # another day's file is never read
    assert tc.get("TLKM", T0, now=T0) is None


def test_empty_payload_is_not_cached():
    tc.put("BBCA", None, now=T0)
    tc.put("BBCA", {}, now=T0)
    assert tc.get("BBCA", T0 - timedelta(hours=1), now=T0) is None


def test_post_close_bound_and_recent_window():
    assert tc.post_close(T0) == datetime(2026, 10, 15, 16, 15)
    assert tc.recent(T0) == T0 - tc.REUSE_WINDOW


def test_prune_keeps_today_and_yesterday():
    for d in ("2026-10-12", "2026-10-14", "2026-10-15"):
        (tc.CACHE_DIR / d).mkdir(parents=True)
    assert tc.prune(date(2026, 10, 15)) == 1
    assert sorted(p.name for p in tc.CACHE_DIR.iterdir()) == ["2026-10-14", "2026-10-15"]


def test_cache_dir_is_isolated_in_tests():
    import data

    assert tc.CACHE_DIR != pathlib.Path(data.__file__).resolve().parent / "tradebook_cache"


def test_scraper_reuses_a_recent_payload_without_requesting(monkeypatch):
    from screener import idx_scraper

    tc.put("BBCA", PAYLOAD)
    calls = []
    monkeypatch.setattr(idx_scraper, "_fetch_tradebook_status", lambda t, tok: calls.append(t) or (200, PAYLOAD))
    monkeypatch.setattr(idx_scraper.time, "sleep", lambda s: None)
    statuses = {}
    idx_scraper.fetch_all_stockbit(["BBCA", "TLKM"], "tok", trade_date="2026-10-15",
                                   statuses=statuses, reuse_after=tc.recent())
    assert calls == ["TLKM"] and statuses == {"BBCA": 200, "TLKM": 200}
    calls.clear()
    idx_scraper.fetch_all_stockbit(["BBCA"], "tok", trade_date="2026-10-15")   # FINAL pass: no reuse
    assert calls == ["BBCA"]


def test_scraper_fetch_writes_the_cache(monkeypatch):
    from screener import idx_scraper

    class R:
        status_code = 200

        def json(self):
            return {"data": PAYLOAD}

    monkeypatch.setattr(idx_scraper.requests, "get", lambda *a, **k: R())
    assert idx_scraper._fetch_tradebook_status("ASII", "tok") == (200, PAYLOAD)
    assert tc.get("ASII", tc.recent()) == PAYLOAD


def test_1830_fetch_reuses_post_close_payload_and_never_for_history(monkeypatch):
    import stockbit_fetcher as sf

    requested = []
    monkeypatch.setattr(sf, "_request_tradebook", lambda t, p, h: requested.append((t, p.get("date"))) or PAYLOAD)
    now = datetime.now()
    tc.put("BBCA", PAYLOAD, now=now)
    flow = sf.fetch_flow("tok", "BBCA")
    assert flow["last_price"] == 100
    if now >= tc.post_close(now):            # a 16:15+ payload exists: no request
        assert requested == []
    else:                                    # before 16:15 today's payload is not final: fetched again
        assert requested == [("BBCA", None)]
    requested.clear()
    sf.fetch_flow("tok", "BBCA", date="2025-10-01")
    assert requested == [("BBCA", "2025-10-01")]


def test_1830_fetch_ignores_a_pre_close_payload(monkeypatch):
    import stockbit_fetcher as sf

    now = datetime.now()
    if now < tc.post_close(now):
        pytest.skip("needs the wall clock after 16:15 to put a payload strictly before the bound today")
    tc.put("BBCA", PAYLOAD, now=tc.post_close(now) - timedelta(minutes=5))
    requested = []
    monkeypatch.setattr(sf, "_request_tradebook", lambda t, p, h: requested.append(t) or PAYLOAD)
    sf.fetch_flow("tok", "BBCA")
    assert requested == ["BBCA"]


def test_post_close_sweep_runs_screener_eod_then_flow(monkeypatch):
    import scheduler.jobs as jobs

    order = []
    fake = types.ModuleType("screener.screener_jobs")
    fake.run_eod = lambda send_telegram=None: order.append("eod")
    monkeypatch.setitem(sys.modules, "screener.screener_jobs", fake)
    monkeypatch.setattr(jobs, "_run_flow_fetch", lambda: order.append("flow") or (jobs._STOCKBIT_SWEEP.locked() and order.append("locked")))
    jobs.run_post_close_sweep()
    assert order == ["eod", "flow", "locked"] and not jobs._STOCKBIT_SWEEP.locked()


def test_flow_fetch_runs_even_if_the_eod_scrape_raises(monkeypatch):
    import scheduler.jobs as jobs

    def boom(send_telegram=None):
        raise RuntimeError("token")

    order = []
    fake = types.ModuleType("screener.screener_jobs")
    fake.run_eod = boom
    monkeypatch.setitem(sys.modules, "screener.screener_jobs", fake)
    monkeypatch.setattr(jobs, "_run_flow_fetch", lambda: order.append("flow"))
    jobs.run_post_close_sweep()
    assert order == ["flow"]


def test_no_1605_flow_slot_and_one_post_close_job():
    import inspect
    import scheduler

    src = inspect.getsource(scheduler.start_scheduler) if hasattr(scheduler, "start_scheduler") else inspect.getsource(scheduler)
    assert "(16,5)" not in src
    assert "run_post_close_sweep" in src
