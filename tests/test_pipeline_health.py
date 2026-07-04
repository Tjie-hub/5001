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
