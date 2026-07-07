# tests/test_fundamental_refresh.py
import os
import sqlite3
from datetime import date, timedelta
from unittest.mock import patch
import pandas as pd
import pytest

from scheduler import _detect_price_shock, _load_stockbit_token


def _flat_df(n=20, close=1000.0):
    return pd.DataFrame({"close": [close] * n, "date": ["2026-01-01"] * n})


def _shock_df(window=5, base=1000.0, drop_pct=0.25):
    closes = [base] + [base * (1 - drop_pct)] * window
    return pd.DataFrame({"close": closes, "date": ["2026-01-01"] * (window + 1)})


class TestDetectPriceShock:
    def test_flat_price_no_shock(self):
        assert _detect_price_shock(_flat_df()) is False

    def test_25pct_drop_is_shock(self):
        assert _detect_price_shock(_shock_df()) is True

    def test_none_df_returns_false(self):
        assert _detect_price_shock(None) is False

    def test_too_short_returns_false(self):
        df = pd.DataFrame({"close": [1000, 700], "date": ["2026-01-01", "2026-01-02"]})
        assert _detect_price_shock(df, window=5) is False

    def test_exactly_20pct_drop_is_shock(self):
        closes = [1000.0] + [800.0] * 5
        df = pd.DataFrame({"close": closes, "date": ["2026-01-01"] * 6})
        assert _detect_price_shock(df, pct=0.20) is True

    def test_19pct_drop_not_shock(self):
        closes = [1000.0] + [810.0] * 5
        df = pd.DataFrame({"close": closes, "date": ["2026-01-01"] * 6})
        assert _detect_price_shock(df, pct=0.20) is False


class TestLoadStockbitToken:
    def test_valid_jwt_returned(self, tmp_path):
        tf = tmp_path / ".stockbit_token"
        tf.write_text("eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig")
        assert _load_stockbit_token(str(tf)).startswith("eyJ")

    def test_missing_file_returns_none(self, tmp_path):
        assert _load_stockbit_token(str(tmp_path / "nofile")) is None

    def test_non_jwt_content_returns_none(self, tmp_path):
        tf = tmp_path / ".stockbit_token"
        tf.write_text("not-a-jwt-token")
        assert _load_stockbit_token(str(tf)) is None

    def test_empty_file_returns_none(self, tmp_path):
        tf = tmp_path / ".stockbit_token"
        tf.write_text("")
        assert _load_stockbit_token(str(tf)) is None

    def test_malformed_token_returns_none(self, tmp_path):
        tf = tmp_path / ".stockbit_token"
        tf.write_text("eyJoZWxsby13b3JsZA")  # starts with eyJ but no dots
        assert _load_stockbit_token(str(tf)) is None


from scheduler import check_keystats_freshness


def _make_keystats_db(tmp_path, fetch_date_str=None):
    """Minimal stockbit_keystats table; optionally insert one BRPT row."""
    db = str(tmp_path / "test.db")
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE stockbit_keystats (
            ticker TEXT NOT NULL,
            fetch_date TEXT NOT NULL,
            pe_ttm REAL, pbv REAL, roe REAL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (ticker, fetch_date)
        )
    """)
    if fetch_date_str:
        conn.execute(
            "INSERT INTO stockbit_keystats (ticker, fetch_date, pe_ttm, pbv, roe, updated_at) "
            "VALUES (?,?,?,?,?,?)",
            ("BRPT", fetch_date_str, 10.0, 2.0, 15.0, "2026-01-01T00:00:00")
        )
    conn.commit()
    conn.close()
    return db


class TestCheckKeystatsFreshness:
    def test_no_row_passes(self, tmp_path):
        db = _make_keystats_db(tmp_path)
        ok, reason = check_keystats_freshness("BRPT", None, _db_path=db)
        assert ok is True
        assert reason == "no_data"

    def test_fresh_data_passes(self, tmp_path):
        db = _make_keystats_db(tmp_path, date.today().isoformat())
        ok, reason = check_keystats_freshness("BRPT", _flat_df(), _db_path=db)
        assert ok is True
        assert reason == "OK"

    def test_stale_no_shock_passes(self, tmp_path):
        old = (date.today() - timedelta(days=45)).isoformat()
        db = _make_keystats_db(tmp_path, old)
        ok, reason = check_keystats_freshness("BRPT", _flat_df(), _db_path=db)
        assert ok is True
        assert reason.startswith("stale:")

    def test_stale_shock_no_token_blocks(self, tmp_path):
        old = (date.today() - timedelta(days=45)).isoformat()
        db = _make_keystats_db(tmp_path, old)
        missing = str(tmp_path / "notoken")
        ok, reason = check_keystats_freshness(
            "BRPT", _shock_df(), _db_path=db, _token_file=missing
        )
        assert ok is False
        assert "stale_shock" in reason
        assert "no_token" in reason

    def test_stale_shock_fetch_empty_blocks(self, tmp_path):
        old = (date.today() - timedelta(days=45)).isoformat()
        db = _make_keystats_db(tmp_path, old)
        tf = tmp_path / ".stockbit_token"
        tf.write_text("eyJmYWtlLnRva2Vu.payload.sig")
        with patch("stockbit_fetcher.fetch_keystats", return_value=None):
            ok, reason = check_keystats_freshness(
                "BRPT", _shock_df(), _db_path=db, _token_file=str(tf)
            )
        assert ok is False
        assert "fetch_empty" in reason

    def test_stale_shock_fetch_error_blocks(self, tmp_path):
        old = (date.today() - timedelta(days=45)).isoformat()
        db = _make_keystats_db(tmp_path, old)
        tf = tmp_path / ".stockbit_token"
        tf.write_text("eyJmYWtlLnRva2Vu.payload.sig")
        with patch("stockbit_fetcher.fetch_keystats", side_effect=Exception("timeout")):
            ok, reason = check_keystats_freshness(
                "BRPT", _shock_df(), _db_path=db, _token_file=str(tf)
            )
        assert ok is False
        assert "fetch_error" in reason

    def test_stale_shock_refresh_success(self, tmp_path):
        old = (date.today() - timedelta(days=45)).isoformat()
        db = _make_keystats_db(tmp_path, old)
        tf = tmp_path / ".stockbit_token"
        tf.write_text("eyJmYWtlLnRva2Vu.payload.sig")
        mock_stats = {"ticker": "BRPT", "pe_ttm": 8.0, "roe": 12.0, "pbv": 2.0}
        with patch("stockbit_fetcher.fetch_keystats", return_value=mock_stats) as mock_fetch, \
             patch("stockbit_fetcher.save_keystats", return_value=None) as mock_save:
            ok, reason = check_keystats_freshness(
                "BRPT", _shock_df(), _db_path=db, _token_file=str(tf)
            )
        assert ok is True
        assert "refreshed" in reason
        mock_fetch.assert_called_once_with("eyJmYWtlLnRva2Vu.payload.sig", "BRPT")
        mock_save.assert_called_once()

    def test_allow_refetch_false_blocks_without_network(self, tmp_path):
        """Stale+shock with allow_refetch=False returns a block and never
        touches the network (the batch pre-pass owns refetching)."""
        old = (date.today() - timedelta(days=45)).isoformat()
        db = _make_keystats_db(tmp_path, old)
        tf = tmp_path / ".stockbit_token"
        tf.write_text("eyJmYWtlLnRva2Vu.payload.sig")
        with patch("stockbit_fetcher.fetch_keystats",
                   side_effect=AssertionError("must not fetch in-loop")):
            ok, reason = check_keystats_freshness(
                "BRPT", _shock_df(), _db_path=db, _token_file=str(tf),
                allow_refetch=False,
            )
        assert ok is False
        assert "stale_shock" in reason
        assert "not_refreshed" in reason

    def test_allow_refetch_false_still_allows_fresh(self, tmp_path):
        db = _make_keystats_db(tmp_path, date.today().isoformat())
        ok, reason = check_keystats_freshness(
            "BRPT", _flat_df(), _db_path=db, allow_refetch=False,
        )
        assert ok is True
        assert reason == "OK"

    def test_allow_refetch_false_stale_no_shock_allows(self, tmp_path):
        old = (date.today() - timedelta(days=45)).isoformat()
        db = _make_keystats_db(tmp_path, old)
        ok, reason = check_keystats_freshness(
            "BRPT", _flat_df(), _db_path=db, allow_refetch=False,
        )
        assert ok is True
        assert reason.startswith("stale:")
