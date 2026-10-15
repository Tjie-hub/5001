"""The scheduled Stockbit sweeps (flow fetch, screener scrape) never run at the same time (2026-10-15)."""
import sys
import threading
import types

import scheduler.jobs as jobs


def test_screener_eod_waits_for_a_running_flow_fetch(monkeypatch):
    inside, release, order = threading.Event(), threading.Event(), []

    def slow_fetch():
        order.append("flow start")
        inside.set()
        release.wait(5)
        order.append("flow end")

    fake = types.ModuleType("screener.screener_jobs")
    fake.run_eod = lambda send_telegram=None: order.append("scrape")
    monkeypatch.setitem(sys.modules, "screener.screener_jobs", fake)
    monkeypatch.setattr(jobs, "_run_flow_fetch", slow_fetch)

    t1 = threading.Thread(target=jobs.run_flow_fetch)
    t1.start()
    assert inside.wait(5)
    t2 = threading.Thread(target=jobs._run_screener_eod)
    t2.start()
    t2.join(0.3)
    assert t2.is_alive() and order == ["flow start"]   # the scrape is held while the fetch runs
    release.set()
    t1.join(5)
    t2.join(5)
    assert order == ["flow start", "flow end", "scrape"]


def test_lock_is_released_when_the_fetch_raises(monkeypatch):
    def boom():
        raise RuntimeError("x")

    monkeypatch.setattr(jobs, "_run_flow_fetch", boom)
    try:
        jobs.run_flow_fetch()
    except RuntimeError:
        pass
    assert not jobs._STOCKBIT_SWEEP.locked()


def test_batch_pace_matches_the_screener_scrape():
    import flow_filter
    from screener import idx_scraper

    assert flow_filter.FLOW_PACE == idx_scraper.DELAY
