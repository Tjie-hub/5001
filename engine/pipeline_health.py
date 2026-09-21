"""Phase 3A — pure data-pipeline health decisions (audit Phase 3).

Stdlib-only (base64/json/time) so it imports without pandas/yfinance/playwright
and unit-tests trivially. Scheduler jobs in scheduler/jobs.py wrap these with
DB reads + Telegram alerts.
"""
import base64
import json
import time

CRITICAL_PCT = 0.25   # below this = likely outage (not just thin illiquid names)


def _decode_jwt_payload(token: str) -> dict:
    """Decode a JWT's middle segment. Raises on malformed input."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("not a 3-segment JWT")
    seg = parts[1]
    seg += "=" * (-len(seg) % 4)          # pad base64url
    return json.loads(base64.urlsafe_b64decode(seg))


def token_status(token: str, now_ts: float = None, warn_hours: float = 6.0) -> dict:
    """Classify a Stockbit JWT by time-to-expiry.

    Returns {status, healthy, hours_left, exp}. status ∈
    {'valid','expiring','expired','invalid'}. A silently-dead token (the
    2026-07-04 incident) surfaces as 'expired'; 'expiring' warns before the
    24h JWT lapses so the refresh cron's failure is caught pre-emptively.
    """
    now = time.time() if now_ts is None else now_ts
    if not token:
        return {"status": "invalid", "healthy": False, "hours_left": None, "exp": None}
    try:
        exp = int(_decode_jwt_payload(token)["exp"])
    except Exception:
        return {"status": "invalid", "healthy": False, "hours_left": None, "exp": None}

    hours_left = (exp - now) / 3600.0
    if hours_left <= 0:
        status = "expired"
    elif hours_left <= warn_hours:
        status = "expiring"
    else:
        status = "valid"
    return {"status": status, "healthy": status == "valid",
            "hours_left": hours_left, "exp": exp}


def ohlcv_coverage(count: int, universe: int, floor_pct: float = 0.85) -> dict:
    """Classify OHLCV ticker coverage for one trading day.

    count = distinct tickers with a bar; universe = active tickers. Below
    floor_pct -> 'warning' (thin day); below CRITICAL_PCT -> 'critical'
    (outage, e.g. the token-death day printed ~0). universe==0 is safe (no
    false alarm on an empty/uninitialised DB).
    """
    if universe <= 0:
        return {"count": count, "universe": universe, "pct": 1.0,
                "severity": "ok", "healthy": True}
    pct = count / universe
    if pct < CRITICAL_PCT:
        severity = "critical"
    elif pct < floor_pct:
        severity = "warning"
    else:
        severity = "ok"
    return {"count": count, "universe": universe, "pct": pct,
            "severity": severity, "healthy": severity == "ok"}


# ── Bootstrap guards (bootstrap readiness audit 2026-09-16, items C1/C2) ─────

EOD_FINAL_WIB = (16, 15)   # 16:15 EOD screener is the only same-day final writer


def same_day_final_bars(count: int, hour: int, minute: int) -> dict:
    """C1: before the 16:15 WIB EOD authority, the current WIB day must have
    ZERO is_final=1 ohlcv bars — a same-day final bar means the gap-filler
    wrote unsettled data as settled (the 2026-09-15 pre-open defect: 585 rows
    dated that day, inserted before WIB open). After 16:15 the EOD scraper
    legitimately writes final bars and the count is not a violation.

    Returns {count, before_eod, violation}. Pure alert decision; the caller
    owns the DB read and the alert.
    """
    before_eod = (hour, minute) < EOD_FINAL_WIB
    return {"count": count, "before_eod": before_eod,
            "violation": before_eod and count > 0}


def prior_session_flow_gap(prior_session, n_tickers) -> dict:
    """C2: zero-coverage detection for the previous expected trading session.

    prior_session = latest trading_calendar date strictly before today (the
    calendar row is written by the 16:15 EOD authority, so it proves the
    session completed); n_tickers = distinct tickers in stockbit_flow for it.
    Alerts only when a completed session has ZERO tickers — the 2026-08-25
    gap class, which the same-day monitor (check_flow_coverage) misses when
    the outage day's own runs never fire. Partial coverage (small n) is
    reported but never alerts here; same-day thin coverage remains
    check_flow_coverage's baseline-median job.
    """
    evaluable = prior_session is not None
    n = n_tickers if n_tickers is not None else 0
    covered = evaluable and n > 0
    return {"session": prior_session, "n_tickers": n,
            "evaluable": evaluable, "covered": covered,
            "alert": evaluable and not covered}
