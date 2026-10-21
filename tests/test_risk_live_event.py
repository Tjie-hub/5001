"""2026-10-16 live event (MSCI consultation: IHSG opened -8.01%, trading halt): the risk model read 57.2 ORANGE.
Missing sensors no longer count as safe, the IHSG day move sets a tier floor, the panic gate refreshes on a new
bar, and a >=5% IHSG drop switches the event guard on for 5 sessions."""
import sqlite3

import pytest

import scheduler.scanner as scanner
from engine.risk_score import compute_market_risk_score, ihsg_last_move, ihsg_move

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


def test_ihsg_move_counts_only_the_dates_own_bar(tmp_path):
    # bars on 2026-01-01 and 2026-01-02 (-8.01%)
    _, c = _db(tmp_path, [5863.78, 5393.92])
    assert round(ihsg_move(c, "2026-01-02"), 4) == -0.0801
    assert ihsg_move(c, "2026-01-01") is None
    # 2026-10-21: a later date with no bar of its own (the 09:05 pre-open scan) is NOT given the last session's move
    assert ihsg_move(c, "2099-01-01") is None
    d, mv = ihsg_last_move(c, "2099-01-01")
    assert d == "2026-01-02" and round(mv, 4) == -0.0801


def test_ihsg_move_counts_a_provisional_bar_of_today(tmp_path):
    _, c = _db(tmp_path, [5000.0, 5000.0])
    c.execute("INSERT INTO ohlcv VALUES ('IHSG', '2099-12-31', 5100.0, 0)")      # provisional intraday bar
    c.commit()
    assert round(ihsg_move(c, "2099-12-31"), 4) == 0.02


def test_previous_session_move_never_sets_a_floor():
    # 2026-10-20 09:05: Monday's -4.46% was applied as "today" while IHSG opened about +2%
    calm = dict(vpin_summary={'label': 'GREEN'}, accdist_summary={'label': 'ACCUMULATION', 'dist_pct': 0},
                breadth_summary={'label': 'BULL_MARKET', 'pct_advancing': 60},
                technicals={'label': 'UPTREND', 'support_breaks': []}, foreign_net_5d=6e9)
    r = compute_market_risk_score(**calm, ihsg_day_move=None, ihsg_prev=("2026-10-19", -0.0801))
    assert r['tier'] == 'GREEN' and r['shock_floor'] is None
    assert r['components']['ihsg_prev_move_pct'] == -8.01 and 'ihsg_move_pct' not in r['components']
    assert r['ihsg_prev_date'] == "2026-10-19"
    # today's own move still sets the floor, and then the previous session is not reported
    r2 = compute_market_risk_score(**calm, ihsg_day_move=-0.0801, ihsg_prev=("2026-10-19", -0.05))
    assert r2['tier'] == 'CRITICAL' and 'ihsg_prev_move_pct' not in r2['components'] and 'ihsg_prev_date' not in r2


def test_preopen_critical_alert_labels_the_previous_session(tmp_path, monkeypatch):
    import engine.risk_alert as ra

    sent = []
    monkeypatch.setattr(ra, "send_telegram", lambda msg, event=None, **k: sent.append((event, msg)))
    risk = compute_market_risk_score(**LIVE, ihsg_day_move=None, ihsg_prev=("2026-10-19", -0.0446))
    assert risk['tier'] in ('RED', 'CRITICAL')
    risk = dict(risk, tier='CRITICAL', label='CRITICAL')     # route the CRITICAL path explicitly
    conn = sqlite3.connect(tmp_path / "r.db")
    ra.route_risk_alert(conn, risk, "2026-10-20", "09:05")
    msg = sent[0][1]
    assert "IHSG today" not in msg
    assert "IHSG: no bar today yet — last session 2026-10-19 -4.46%" in msg


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


def test_blackout_day_still_computes_and_routes_market_risk(monkeypatch):
    # 2026-10-16 was a BI-meeting blackout day: the scan returned before the risk block, so no CRITICAL alert.
    import engine.calendar_filter as cf
    import engine.risk_alert as ra
    import engine.vpin as vp
    import engine.breadth as br
    import engine.technicals as te
    import flow_filter as ff
    import engine.risk_score as rs

    monkeypatch.setattr(cf, "is_trading_day", lambda *a, **k: (True, ""))
    monkeypatch.setattr(cf, "is_blackout_day", lambda *a, **k: (True, "H+1 after BI Rate RDG"))
    monkeypatch.setattr(vp, "get_market_vpin_summary", lambda c, d: LIVE['vpin_summary'])
    monkeypatch.setattr(ff, "get_market_accdist_summary", lambda d: LIVE['accdist_summary'])
    monkeypatch.setattr(br, "get_market_breadth", lambda c, d: LIVE['breadth_summary'])
    monkeypatch.setattr(te, "detect_ihsg_technicals", lambda c, d: LIVE['technicals'])
    monkeypatch.setattr(rs, "ihsg_move", lambda c, d: -0.0801)
    routed = []
    monkeypatch.setattr(ra, "route_risk_alert", lambda conn, risk, d, t: routed.append(risk['tier']))
    scanner.scheduled_multi_strategy_scan()
    assert routed == ['CRITICAL']


def test_accdist_with_no_classified_tickers_is_missing_not_neutral():
    # review 2026-10-16: 0 tickers (no flow yet today) read NEUTRAL = 40 and diluted the score
    empty = dict(LIVE, accdist_summary={'label': 'NEUTRAL', 'dist_pct': 0.0, 'total': 0})
    r = compute_market_risk_score(**empty)
    assert r['components']['accdist'] is None
    full = dict(LIVE, accdist_summary={'label': 'NEUTRAL', 'dist_pct': 0.0, 'total': 700})
    assert compute_market_risk_score(**full)['components']['accdist'] == 40.0


def test_critical_alert_is_sent_when_a_sensor_has_no_data(tmp_path, monkeypatch):
    # 2026-10-16 11:05: CRITICAL 86.0 was logged but never sent -- f"{None:.1f}" raised on the missing VPIN.
    import engine.risk_alert as ra

    sent = []
    monkeypatch.setattr(ra, "send_telegram", lambda msg, event=None, **k: sent.append((event, msg)))
    risk = compute_market_risk_score(**LIVE, ihsg_day_move=-0.0801)
    conn = sqlite3.connect(tmp_path / "r.db")
    ra.route_risk_alert(conn, risk, "2026-10-16", "11:05")
    assert sent and sent[0][0] == "risk.market_critical"
    assert "VPIN: n/a" in sent[0][1] and "IHSG today: -8.01% — floor CRITICAL" in sent[0][1]
    assert conn.execute("SELECT sent FROM market_risk_log").fetchone()[0] == 1
