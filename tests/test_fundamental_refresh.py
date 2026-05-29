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
