"""Phase 3A — pure pipeline-health decision functions (no I/O)."""
import base64
import json
import time

from engine.pipeline_health import token_status


def _make_jwt(exp_ts, iat_ts=None):
    """Minimal 3-segment JWT with the given exp/iat (only the payload matters)."""
    hdr = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    body = {"exp": int(exp_ts)}
    if iat_ts is not None:
        body["iat"] = int(iat_ts)
    pay = base64.urlsafe_b64encode(json.dumps(body).encode()).rstrip(b"=").decode()
    return f"{hdr}.{pay}.sig"


def test_valid_token_far_from_expiry():
    now = 1_000_000
    tok = _make_jwt(now + 20 * 3600)          # 20h left
    s = token_status(tok, now_ts=now, warn_hours=6.0)
    assert s["status"] == "valid"
    assert round(s["hours_left"], 1) == 20.0
    assert s["healthy"] is True


def test_expiring_soon_within_warn_window():
    now = 1_000_000
    tok = _make_jwt(now + 3 * 3600)           # 3h left, warn=6h
    s = token_status(tok, now_ts=now, warn_hours=6.0)
    assert s["status"] == "expiring"
    assert s["healthy"] is False


def test_expired_token():
    now = 1_000_000
    tok = _make_jwt(now - 3600)               # expired 1h ago
    s = token_status(tok, now_ts=now)
    assert s["status"] == "expired"
    assert s["hours_left"] < 0
    assert s["healthy"] is False


def test_malformed_token_is_invalid():
    s = token_status("not-a-jwt", now_ts=1_000_000)
    assert s["status"] == "invalid"
    assert s["healthy"] is False


def test_empty_token_is_invalid():
    s = token_status("", now_ts=1_000_000)
    assert s["status"] == "invalid"
    assert s["healthy"] is False


from engine.pipeline_health import ohlcv_coverage


def test_coverage_healthy_at_full():
    s = ohlcv_coverage(count=950, universe=958, floor_pct=0.85)
    assert s["healthy"] is True
    assert s["severity"] == "ok"
    assert round(s["pct"], 3) == round(950 / 958, 3)


def test_coverage_warning_below_floor():
    s = ohlcv_coverage(count=800, universe=958, floor_pct=0.85)   # 83.5% < 85%
    assert s["healthy"] is False
    assert s["severity"] == "warning"


def test_coverage_critical_near_zero():
    s = ohlcv_coverage(count=20, universe=958, floor_pct=0.85)    # outage
    assert s["severity"] == "critical"
    assert s["healthy"] is False


def test_coverage_zero_universe_is_safe():
    s = ohlcv_coverage(count=0, universe=0)
    assert s["healthy"] is True            # nothing to cover -> no false alarm
    assert s["severity"] == "ok"


from engine.pipeline_health import prior_session_flow_gap, same_day_final_bars


# ── C1: same-day ohlcv finality (bootstrap audit 2026-09-16) ─────────────────

def test_same_day_final_bars_violation_before_eod():
    # the 2026-09-15 pre-open defect shape: final bars exist at 09:30 WIB
    s = same_day_final_bars(count=585, hour=9, minute=30)
    assert s["violation"] is True
    assert s["before_eod"] is True


def test_same_day_final_bars_zero_before_eod_is_ok():
    s = same_day_final_bars(count=0, hour=9, minute=30)
    assert s["violation"] is False


def test_same_day_final_bars_after_eod_not_a_violation():
    # from 16:15 the EOD scraper is the same-day final writer
    assert same_day_final_bars(count=824, hour=16, minute=15)["violation"] is False
    assert same_day_final_bars(count=824, hour=17, minute=0)["violation"] is False


def test_same_day_final_bars_boundary_minute():
    # 16:14 is still pre-authority; 16:15 is the authority minute
    assert same_day_final_bars(count=5, hour=16, minute=14)["violation"] is True
    assert same_day_final_bars(count=5, hour=16, minute=15)["violation"] is False


# ── C2: prior-session stockbit_flow zero coverage (bootstrap audit) ──────────

def test_prior_session_zero_tickers_alerts():
    # the 2026-08-25 shape: session completed (calendar row) but 0 flow rows
    s = prior_session_flow_gap("2026-08-25", 0)
    assert s["alert"] is True
    assert s["covered"] is False
    assert s["evaluable"] is True


def test_prior_session_covered_no_alert():
    s = prior_session_flow_gap("2026-08-26", 870)
    assert s["alert"] is False
    assert s["covered"] is True


def test_prior_session_partial_distinguishable_from_zero():
    s = prior_session_flow_gap("2026-08-26", 12)
    assert s["alert"] is False
    assert s["covered"] is True
    assert s["n_tickers"] == 12          # partial stays visible, never conflated


def test_prior_session_unknown_not_evaluable():
    # no calendar row before today: we cannot know what to expect — no alert
    s = prior_session_flow_gap(None, None)
    assert s["evaluable"] is False
    assert s["alert"] is False


def test_prior_session_missing_flow_table_shape():
    # job helper passes n_tickers=None when the calendar row exists but the
    # flow table has no rows at all — COUNT is 0, not None; guard the None path
    s = prior_session_flow_gap("2026-08-25", None)
    assert s["alert"] is True
    assert s["n_tickers"] == 0
