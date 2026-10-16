"""FWD-PM-HALTARB-001 recorder (D-100): ARB rounding, event days, no back-fill, deferral until t+5."""
import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "halt_arb", ROOT / "docs/research_programs/P-M/forward_halt_arb/run_recorder.py")
rec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rec)


def test_arb_price_matches_the_live_floors_of_2026_10_16():
    # previous close -> the ARB Stockbit showed that morning
    assert rec.arb_price(3100) == 2640    # BBRI
    assert rec.arb_price(2230) == 1900    # TLKM
    assert rec.arb_price(6075) == 5175    # BBCA
    assert rec.arb_price(448) == 382      # TOWR


def test_event_days_use_the_low_vs_prior_close():
    ihsg = [("d0", 6000, 6000), ("d1", 5500, 5600), ("d2", 5200, 5300)]   # d1 -8.3% low, d2 -7.1%
    assert [e[0] for e in rec.event_days(ihsg)] == ["d1"]


def _db(tmp_path, days, ihsg_lows):
    """IHSG + two names: AAA touches ARB on the event day, BBB does not."""
    c = sqlite3.connect(tmp_path / "wf.db")
    c.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, "
              "volume REAL, is_final INTEGER)")
    for k, d in enumerate(days):
        c.execute("INSERT INTO ohlcv VALUES ('IHSG',?,6000,6000,?,6000,0,1)", (d, ihsg_lows.get(d, 6000)))
        ev = d in ihsg_lows
        c.execute("INSERT INTO ohlcv VALUES ('AAA',?,1000,1000,?,1000,1e7,1)", (d, 850 if ev else 1000))
        c.execute("INSERT INTO ohlcv VALUES ('BBB',?,1000,1000,?,1000,1e7,1)", (d, 950 if ev else 1000))
    c.commit()
    return c


def _ledger(opened="2026-10-16"):
    return {"opened_utc": f"{opened}T09:00:00+00:00", "event_days": [], "rows": []}


def _days(n, start=(2026, 11, 2)):
    from datetime import date, timedelta
    d0 = date(*start)
    return [(d0 + timedelta(days=i)).isoformat() for i in range(n)]


def test_writes_only_after_t5_and_never_backfills(tmp_path):
    days = _days(30)
    ev = days[24]                                                      # needs 21+ prior sessions for ADV
    c = _db(tmp_path, days[:27], {ev: 5400})                           # only t+2 exists
    led = _ledger()
    assert rec.record(c, led) == 0 and led["event_days"] == []         # deferred, not written
    later = tmp_path / "later"
    later.mkdir()
    c = _db(later, days, {ev: 5400})                                   # the same day, t+5 now closed
    assert rec.record(c, led) == 1                                     # AAA touched 850 = ARB(1000)
    assert led["rows"][0]["ticker"] == "AAA" and led["rows"][0]["entry_arb"] == 850
    assert led["event_days"][0]["n_liquid"] == 2 and led["event_days"][0]["n_arb_touch"] == 1
    assert rec.record(c, led) == 0                                     # idempotent


def test_refuses_days_before_opening_and_the_motivating_day(tmp_path):
    days = _days(30, start=(2026, 9, 20))                              # 2026-10-14 is index 24
    c = _db(tmp_path, days, {days[24]: 5400, "2026-10-16": 5400})
    assert rec.record(c, _ledger(opened="2026-10-16")) == 0
