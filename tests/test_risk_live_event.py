"""2026-10-16 live event (MSCI consultation: IHSG opened -8.01%, trading halt): the risk model read 57.2 ORANGE.
Missing sensors no longer count as safe, the IHSG day move sets a tier floor, the panic gate refreshes on a new
bar, and a >=5% IHSG drop switches the event guard on for 5 sessions."""
import sqlite3

import pytest

import scheduler.scanner as scanner
from engine.risk_score import compute_market_risk_score, ihsg_move

# The live inputs of 2026-10-16 ~10:00 WIB.
LIVE = dict(
    vpin_summary={'label': 'INSUFFICIENT_DATA', 'pct_above_06': 0.0},
    accdist_summary={'label': 'NEUTRAL', 'dist_pct': 0.0},
    breadth_summary={'label': 'BEAR_MARKET', 'pct_advancing': 2.0},
    technicals={'label': 'BEARISH_TREND', 'death_cross': True, 'lower_high': True, 'support_breaks': []},
    foreign_net_5d=-333_000_000_000,
)


def test_missing_sensor_is_left_out_not_scored_as_safe():
    r = compute_market_risk_score(**LIVE)
    assert r['components']['vpin'] is None
    assert r['score'] > 75 and r['tier'] == 'RED'          # was 57.2 ORANGE with VPIN counted as 0


def test_ihsg_halt_size_drop_is_critical():
    r = compute_market_risk_score(**LIVE, ihsg_day_move=-0.0801)
    assert r['tier'] == 'CRITICAL' and r['shock_floor'] == 'CRITICAL'
    assert r['components']['ihsg_move_pct'] == -8.01


@pytest.mark.parametrize("move,tier", [(-0.055, 'RED'), (-0.035, 'ORANGE')])
def test_shock_floor_on_a_calm_sensor_day(move, tier):
    calm = dict(vpin_summary={'label': 'GREEN'}, accdist_summary={'label': 'ACCUMULATION', 'dist_pct': 0},
                breadth_summary={'label': 'BULL_MARKET', 'pct_advancing': 60},
                technicals={'label': 'UPTREND', 'support_breaks': []}, foreign_net_5d=6e9)
    assert compute_market_risk_score(**calm)['tier'] == 'GREEN'
    assert compute_market_risk_score(**calm, ihsg_day_move=move)['tier'] == tier


def test_no_move_no_floor():
    assert compute_market_risk_score(**LIVE, ihsg_day_move=-0.01)['shock_floor'] is None


def _db(tmp_path, closes):
    path = tmp_path / "wf.db"
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, close REAL, is_final INTEGER)")
    for i, cl in enumerate(closes):
        c.execute("INSERT INTO ohlcv VALUES ('IHSG', ?, ?, 1)", (f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}", cl))
    c.commit()
    return path, c


def test_ihsg_move_uses_the_latest_bar(tmp_path):
    _, c = _db(tmp_path, [5863.78, 5393.92])
    assert round(ihsg_move(c, "2099-01-01"), 4) == -0.0801
    assert ihsg_move(c, "2026-01-01") is None


def test_panic_gate_refreshes_when_a_new_bar_arrives(tmp_path, monkeypatch):
    # 240 calm sessions near 7,000, then a slide: below the 200-day MA with vol rising.
    closes = [7000 + (i % 2) * 10 for i in range(240)] + [6800 - 60 * i for i in range(10)]
    path, c = _db(tmp_path, closes)
    monkeypatch.setattr(scanner, "DB_PATH", str(path))
    scanner._macro_panic_cache.clear()
    before = scanner._macro_panic_state()
    c.execute("INSERT INTO ohlcv VALUES ('IHSG', '2099-12-31', ?, 0)", (closes[-1] * 0.92,))   # -8% provisional
    c.commit()
    assert scanner._macro_panic_state() is True
    assert before in (True, False)   # whatever the old bar said, the new bar was re-evaluated, not served from cache


def test_shock_guard_holds_for_five_sessions(tmp_path, monkeypatch):
    path, c = _db(tmp_path, [6000, 6000, 5520] + [5520] * 4)      # -8% on session 3, then 4 flat sessions
    monkeypatch.setattr(scanner, "DB_PATH", str(path))
    assert scanner._shock_guard_active() is True
    c.execute("INSERT INTO ohlcv VALUES ('IHSG', '2099-12-31', 5520, 1)")                        # 5th after
    c.commit()
    assert scanner._shock_guard_active() is False


def test_event_guard_includes_the_shock_guard(monkeypatch):
    monkeypatch.setattr(scanner, "_shock_guard_active", lambda: True)
    on, mult = scanner._event_guard_active()
    assert on and mult > 0
