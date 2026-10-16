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


def test_page_started_screener_run_and_eod_retry_share_the_lock():
    # review 2026-10-16: both took no lock. One lock object for scheduler, retry and the screener page.
    import inspect

    import screener.routes as routes
    from utils.stockbit_sweep import SWEEP_LOCK

    assert jobs._STOCKBIT_SWEEP is SWEEP_LOCK
    assert "with SWEEP_LOCK" in inspect.getsource(routes)
    assert "with _STOCKBIT_SWEEP" in inspect.getsource(jobs.run_eod_retry_job)
