"""Tests for the premarket briefing additions: external macro + news digest."""
import sqlite3

import pytest

from engine.external_macro import (
    build_external_macro_block,
    compute_changes,
    macro_bias,
)
from engine.news_digest import build_news_block, get_ticker_news_digest


# ── external macro ──────────────────────────────────────────────────────────
def test_compute_changes_basic():
    ch = compute_changes([100, 101, 102, 103, 104, 110])  # 6 closes
    assert ch["last"] == 110
    assert ch["d1"] == pytest.approx((110 - 104) / 104)
    assert ch["d5"] == pytest.approx((110 - 100) / 100)
    assert ch["suspect"] is False


def test_compute_changes_flags_glitch_bar():
    # KOSPI-style -9.99% single-bar drop must be flagged suspect
    ch = compute_changes([9114.55, 8203.84])
    assert ch["d1"] == pytest.approx(-0.0999, abs=1e-3)
    assert ch["suspect"] is True


def test_compute_changes_insufficient_data():
    assert compute_changes([100]) is None
    assert compute_changes([]) is None


def test_macro_block_marks_suspect_and_na():
    data = [
        {"name": "KOSPI", "ok": True, "last": 8203.84, "d1": -0.0999, "d5": -0.06, "suspect": True},
        {"name": "Nikkei", "ok": True, "last": 69788.0, "d1": -0.0355, "d5": 0.005, "suspect": False},
        {"name": "DXY", "ok": False},
    ]
    block = build_external_macro_block(data)
    assert "KOSPI" in block and "⚠verify" in block      # glitch flagged
    assert "Nikkei" in block and "▼-3.55%" in block      # normal move
    assert "DXY: N/A" in block                            # fetch failure graceful


def test_macro_bias():
    up = lambda n, d: {"name": n, "ok": True, "suspect": False, "d1": d}
    assert macro_bias([up("KOSPI", 0.01), up("Nikkei", 0.02), up("S&P500", 0.01)]) == "risk-on 🟢"
    assert macro_bias([up("KOSPI", -0.01), up("Nikkei", -0.02), up("S&P500", -0.01)]) == "risk-off 🔴"
    # suspect rows are excluded from the read
    assert macro_bias([{"name": "KOSPI", "ok": True, "suspect": True, "d1": -0.1}]) == "n/a"


# ── news digest ─────────────────────────────────────────────────────────────
@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.executescript(
        "CREATE TABLE news_mentions (ticker TEXT, date TEXT, count INT, headlines_json TEXT);"
        "CREATE TABLE idx_tickers (ticker TEXT PRIMARY KEY);"
    )
    # PADA/LABA/BANK are real ticker codes but word-collision noise (in NOISE_TICKERS)
    c.executemany("INSERT INTO idx_tickers VALUES (?)",
                  [("BBNI",), ("RAJA",), ("BBRI",), ("PADA",), ("LABA",), ("BANK",)])
    c.executemany(
        "INSERT INTO news_mentions VALUES (?,?,?,?)",
        [
            ("XXXX", "2026-06-23", 99, '["not in idx_tickers"]'),  # not a ticker → dropped
            ("PADA", "2026-06-23", 84, '["word noise pada"]'),     # noise blocklist → dropped
            ("LABA", "2026-06-23", 26, '["word noise laba"]'),     # noise blocklist → dropped
            ("BANK", "2026-06-23", 23, '["generic banking"]'),     # noise blocklist → dropped
            ("BBNI", "2026-06-23", 20, '["BBNI Cetak Laba Rp9,1 Triliun - Bareksa"]'),
            ("RAJA", "2026-06-23", 12, '["Emiten RAJA Stock Split 1:5 - CNBC"]'),
            ("BBRI", "2026-06-23", 8, "[]"),                       # no headline
        ],
    )
    c.commit()
    return c


def test_news_digest_filters_word_noise(conn):
    digest = get_ticker_news_digest(conn, "2026-06-23", top_n=5)
    tickers = [d["ticker"] for d in digest]
    assert not ({"XXXX", "PADA", "LABA", "BANK"} & set(tickers))  # noise + non-tickers gone
    assert tickers == ["BBNI", "RAJA", "BBRI"]                    # only genuine, by count


def test_news_block_renders_headlines(conn):
    digest = get_ticker_news_digest(conn, "2026-06-23", top_n=5)
    block = build_news_block(digest)
    assert "BBNI" in block and "Cetak Laba" in block
    assert "BBRI" in block            # included even with no headline
    assert "<" not in block.replace("<b>", "").replace("</b>", "")  # HTML-safe


def test_news_block_empty(conn):
    assert "None for real tickers" in build_news_block([])
