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


def test_detect_gaps_brpt_shaped_suspension():
    """
    BRPT-shaped: last bar 2026-05-13, resume 2026-05-25, ~-28% gap-down.
    Trading days strictly between 5/13 and 5/25, given IDX 2026 holidays:
      5/14 Kenaikan Isa Al Masih (holiday)   — excluded
      5/15 Fri                               — TRADING (1)
      5/16, 5/17 weekend                     — excluded
      5/18, 5/19, 5/20, 5/21 Mon-Thu         — TRADING (2,3,4,5)
      5/22 Waisak holiday                    — excluded
      5/23, 5/24 weekend                     — excluded
    Total missing trading days: 5.
    """
    df = _df([
        ("2026-05-13", 2100.0, 2110.0, 2080.0, 2080.0, 50_000_000),
        ("2026-05-25", 1495.0, 1565.0, 1495.0, 1565.0, 200_000_000),
    ])
    events = detect_gaps(df, detected_at="2026-05-28T00:00:00+00:00")
    assert len(events) == 1
    ev = events[0]
    assert ev.last_normal_date == "2026-05-13"
    assert ev.resume_date == "2026-05-25"
    assert ev.missing_td == 5
    assert ev.classification == "suspension"
    assert ev.gap_pct == pytest.approx((1495.0 - 2080.0) / 2080.0, rel=1e-6)
    assert ev.detected_at == "2026-05-28T00:00:00+00:00"
    # ticker is set by scan_all, not by detect_gaps
    assert ev.ticker == ""


def test_detect_gaps_data_gap_when_price_continuous():
    """
    4 missing trading days but price moves only 0.5% → classify as data_gap.
    2026-04-06 (Mon) -> 2026-04-13 (Mon).
    Strictly between: 4/7 Tue, 4/8 Wed, 4/9 Thu, 4/10 Fri = 4 trading days.
    (4/3 Good Friday is *before* the start so doesn't affect this gap.)
    """
    df = _df([
        ("2026-04-06", 100.0, 101.0, 99.0, 100.0, 1000),
        ("2026-04-13", 100.5, 101.5, 100.0, 100.5, 1100),
    ])
    events = detect_gaps(df, detected_at="2026-05-28T00:00:00+00:00")
    assert len(events) == 1
    ev = events[0]
    assert ev.missing_td == 4
    assert ev.classification == "data_gap"
    assert ev.gap_pct == pytest.approx(0.005, rel=1e-6)


def test_detect_gaps_long_holiday_cluster_returns_empty():
    """
    Idul Fitri cluster: bar on 2026-03-18 (Wed), next bar on 2026-03-25 (Wed).
    Strictly between, IDX 2026 calendar:
      3/19 Cuti Bersama Idul Fitri        — excluded
      3/20 Idul Fitri day 1               — excluded
      3/21, 3/22 weekend                  — excluded
      3/23 Cuti Bersama Idul Fitri        — excluded
      3/24 Cuti Bersama Idul Fitri        — excluded
    Total missing trading days: 0 → no event, despite a 7-calendar-day gap.
    """
    df = _df([
        ("2026-03-18", 100.0, 101.0, 99.0, 100.0, 1000),
        ("2026-03-25", 102.0, 103.0, 101.0, 102.0, 1100),
    ])
    assert detect_gaps(df) == []


def test_detect_gaps_normal_weekend_returns_empty():
    """Fri -> Mon, no missing trading days."""
    df = _df([
        ("2026-04-10", 100.0, 101.0, 99.0, 100.0, 1000),
        ("2026-04-13", 100.5, 101.5, 100.0, 100.5, 1100),
    ])
    assert detect_gaps(df) == []
