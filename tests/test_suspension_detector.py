import pandas as pd
import pytest

from engine.suspension_detector import GapEvent, detect_gaps


def _df(rows):
    """Build an OHLCV dataframe from a list of (date, o, h, l, c, v) tuples."""
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])


def test_gapevent_dataclass_fields():
    ev = GapEvent(
        ticker="X",
        last_normal_date="2026-01-05",
        resume_date="2026-01-12",
        missing_td=4,
        gap_pct=-0.15,
        classification="suspension",
        detected_at="2026-05-28T00:00:00+00:00",
    )
    assert ev.ticker == "X"
    assert ev.missing_td == 4
    assert ev.classification == "suspension"


def test_detect_gaps_empty_df_returns_empty_list():
    assert detect_gaps(pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])) == []


def test_detect_gaps_single_row_returns_empty_list():
    df = _df([("2026-04-13", 100.0, 101.0, 99.0, 100.0, 1000)])
    assert detect_gaps(df) == []


def test_detect_gaps_none_returns_empty_list():
    assert detect_gaps(None) == []
