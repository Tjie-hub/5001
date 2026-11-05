"""Regression tests for the yfinance per-symbol delisted-error noise filter.

The daily incremental fetch (staged-entry fills 09:10/10:10) and the scraper
backfills probe the whole active universe; every ticker without a bar for the
requested window (suspended for the day, or the 2026-07-18 IDX delisting
batch) makes yfinance log one ERROR per symbol — 139 distinct tickers and
~3,500 ERROR lines in 2.5 weeks (logs/app.log(.1), 10-21..11-06). The filter
downgrades ONLY the per-symbol "$TICK.JK: possibly delisted..." lines to
DEBUG so the INFO-level file handler drops them; the batch summaries
("N Failed downloads:" header + "['TICK.JK', ...]" ticker lists) stay at
ERROR so every run still surfaces exactly which symbols failed.
"""
import io
import logging

import pytest

from utils.logging_config import YfinanceNoiseFilter


def _emit_through(logger, msg, level=logging.ERROR, handler_level=logging.INFO):
    """Emit `msg` via `logger` and return whether the INFO handler saw it."""
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setLevel(handler_level)
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    logger.log(level, msg)
    handler.flush()
    return buf.getvalue()


@pytest.fixture()
def yf_logger():
    """A dedicated logger with the noise filter attached, restored after."""
    logger = logging.getLogger('yfinance_test_probe')
    filt = YfinanceNoiseFilter()
    logger.addFilter(filt)
    yield logger, filt
    logger.removeFilter(filt)
    logger.handlers = []
    logger.propagate = True


class TestYfinanceNoiseFilter:
    def test_per_symbol_delisted_line_downgraded_to_debug(self, yf_logger):
        logger, filt = yf_logger
        out = _emit_through(
            logger,
            "$WSKT.JK: possibly delisted; no price data found  "
            "(1d 2026-07-18 -> 2026-11-04) (Yahoo error = \"No data found, symbol may be delisted\")",
        )
        assert out == "", "per-symbol delisted ERROR must be dropped by an INFO handler"

    def test_batch_summary_header_kept_at_error(self, yf_logger):
        logger, _ = yf_logger
        out = _emit_through(logger, "\n41 Failed downloads:")
        assert "41 Failed downloads" in out, "batch header must survive at ERROR"

    def test_ticker_list_summary_kept_at_error(self, yf_logger):
        logger, _ = yf_logger
        out = _emit_through(
            logger,
            "['WSKT.JK', 'HOTL.JK']: possibly delisted; no price data found  "
            "(1d 2026-07-18 -> 2026-11-04)",
        )
        assert "WSKT" in out, "ticker-list summary line must survive at ERROR"

    def test_index_symbol_form_matched(self, yf_logger):
        logger, _ = yf_logger
        out = _emit_through(logger, "$^JKSE: possibly delisted; no price data found  (1d d1 -> d2)")
        assert out == ""

    def test_unrelated_error_unchanged(self, yf_logger):
        logger, filt = yf_logger
        out = _emit_through(logger, "Connection reset by peer")
        assert "Connection reset by peer" in out
        assert filt.symbols_suppressed == 0

    def test_counter_counts_only_suppressed_symbols(self, yf_logger):
        logger, filt = yf_logger
        _emit_through(logger, "$WSKT.JK: possibly delisted; no price data found (1d a -> b)")
        _emit_through(logger, "$ABBA.JK: possibly delisted; no price data found (1d a -> b)")
        _emit_through(logger, "\n2 Failed downloads:")
        assert filt.symbols_suppressed == 2
