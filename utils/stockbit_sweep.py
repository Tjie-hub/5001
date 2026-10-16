"""One lock for every full-universe Stockbit trade-book sweep in the app process.

The flow fetch, the screener scrape (scheduled, its 17:30 EOD retry, and a run started from the screener page)
each request trade-book/chart for all ~958 tickers on the one shared token. Until 2026-10-15 they overlapped at
13:30/13:35, 14:30/14:35 and 16:05/16:15; the 2026-10-16 review found the page-started run and the retry still
took no lock. gunicorn runs exactly one worker (gunicorn.conf.py), so a threading.Lock covers the whole app;
separate processes (CLI runs, the jurnal26 monitors) are outside it.
"""
import threading

SWEEP_LOCK = threading.Lock()
