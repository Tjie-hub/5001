"""Regression (2026-10-16): the coverage fallback ran on the VPIN block's connection after `with db.txn()` had closed
it, so every EOD run from 10-15 logged "Cannot operate on a closed database" and skipped it; and it read the whole
ohlcv table into pandas (the OOM class of 10-14)."""
from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "screener" / "screener_jobs.py").read_text()


def _block():
    a = SRC.index("# ── Coverage fallback")
    return SRC[a:SRC.index("Coverage fallback error", a)]


def test_fallback_opens_its_own_connection():
    assert "with db.txn() as conn:" in _block()


def test_fallback_reads_only_the_missing_tickers():
    b = _block()
    assert "SELECT * FROM ohlcv ORDER BY ticker" not in b and "WHERE ticker = ?" in b
