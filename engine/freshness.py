"""engine/freshness.py — P0.E2.S1.T2: minimal last-bar freshness guard.

Audit H-3: no scan loop or the monitor checked a ticker's last OHLCV bar
date before treating it as tradeable — a stale bar (feed gap, suspension,
token death) was silently evaluated as if it were current. This is the
deliberately minimal Phase 0 guard (skip + count + one aggregated alert per
run); the full per-ticker Certifier flag (`per_ticker_flags`, versioned
thresholds) is Phase 1 scope (PLAN-001 P1.E4.S1) and is not built here.
"""
from datetime import date, timedelta
from typing import Optional, Union

from engine.calendar_filter import is_trading_day


def is_fresh(last_date: Union[str, date, None], as_of: Optional[date] = None,
             max_age_sessions: int = 1) -> bool:
    """True if `last_date` is within `max_age_sessions` IDX trading sessions
    of `as_of` (default: today). `None` is never fresh. Weekends/holidays
    don't count against a ticker — a Friday bar is still fresh on the
    following Monday.
    """
    if last_date is None:
        return False
    if as_of is None:
        as_of = date.today()
    last = last_date if isinstance(last_date, date) else date.fromisoformat(str(last_date)[:10])
    if last >= as_of:
        return True
    sessions_between = 0
    d = last
    while d < as_of:
        d += timedelta(days=1)
        is_open, _ = is_trading_day(d)
        if is_open:
            sessions_between += 1
    return sessions_between <= max_age_sessions
