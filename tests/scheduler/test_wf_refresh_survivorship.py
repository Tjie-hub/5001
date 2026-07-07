"""Phase 2B item 2.4: refresh_wf_scores must score every ticker in the OHLCV
corpus, not just currently-active idx_tickers (survivorship)."""
import sqlite3

import numpy as np
import pandas as pd
import pytest


def _df(n=400, seed=1):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2021-07-05", periods=n)
    close = 1000 + np.cumsum(rng.normal(0, 6, n))
    close = np.maximum(close, 100.0)
    return pd.DataFrame({"date": dates, "open": close, "high": close + 8,
                         "low": close - 8, "close": close,
                         "volume": rng.uniform(1e6, 3e6, n)})


@pytest.fixture()
def wf_db(tmp_path, monkeypatch):
    import research.jobs as jobs
    db = str(tmp_path / "wf.db")
    monkeypatch.setattr(jobs, "DB_PATH", db)
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE idx_tickers (ticker TEXT PRIMARY KEY, status TEXT)")
    conn.execute("INSERT INTO idx_tickers VALUES ('LIVE','active')")
    # DELISTED is in the corpus but NOT active — must still be scored.
    conn.commit()
    conn.close()
    # Corpus has both tickers; the active list has only LIVE.
    monkeypatch.setattr(jobs, "_load_ohlcv_bulk",
                        lambda final_only=False: {"LIVE": _df(), "DELISTED": _df(seed=2)})
    return db


def test_refresh_scores_delisted_ticker_in_corpus(wf_db):
    from research.jobs import refresh_wf_scores
    refresh_wf_scores()
    conn = sqlite3.connect(wf_db)
    scored = {r[0] for r in conn.execute("SELECT DISTINCT ticker FROM wf_scores")}
    conn.close()
    assert "DELISTED" in scored, "survivorship: corpus ticker not scored"
    assert "LIVE" in scored
