"""Nightly data self-heal (2026-10-13). A failed data job used to need a human to
audit every table and re-run the backfills by hand. This finds gaps in the last
few sessions, runs the existing idempotent backfill tools for just those, and
reports only when there was something to fix."""
import re
import sqlite3
from pathlib import Path

import scripts.data_heal as dh
from utils import notify_policy as np

ROOT = Path(__file__).resolve().parents[1]
DATES = ["2026-10-07", "2026-10-08", "2026-10-09", "2026-10-12", "2026-10-13"]


class Env:
    """Fake world: gap state that fake tools can repair."""
    def __init__(self, bars=None, broker=None, token=True, repair=True, rc=0):
        self.bars, self.broker = dict(bars or {}), dict(broker or {})
        self.token, self.repair, self.rc = token, repair, rc
        self.tools, self.sent = [], []

    def gaps(self, conn, dates):
        return {"bars": {d: n for d, n in self.bars.items() if d in dates and n},
                "broker": {d: s for d, s in self.broker.items() if d in dates}}

    def run_tool(self, argv, timeout):
        self.tools.append(argv)
        if self.repair:
            if any("backfill_flow_bars" in a for a in argv):
                self.bars.clear()
            else:
                for d in argv[argv.index("--dates") + 1].split(","):
                    self.broker.pop(d, None)
        return self.rc

    def send(self, msg, **kw):
        self.sent.append((msg, kw))

    def go(self, **kw):
        return dh.heal(None, dates=DATES, gaps_fn=self.gaps, run_tool=self.run_tool,
                       ensure_token=lambda: "tok" if self.token else None,
                       send=self.send, **kw)


def test_clean_state_is_silent_and_runs_nothing():
    e = Env()
    assert e.go() == 0
    assert e.tools == [] and e.sent == []


def test_bars_gap_is_repaired_and_reported_once():
    e = Env(bars={"2026-10-12": 40})
    assert e.go() == 0
    assert len(e.tools) == 1
    argv = e.tools[0]
    assert "tools/backfill_flow_bars.py" in " ".join(argv)
    assert argv[argv.index("--date-from") + 1] == "2026-10-12"
    assert argv[argv.index("--date-to") + 1] == "2026-10-13"     # exclusive bound
    assert len(e.sent) == 1 and e.sent[0][1]["event"] == "data.heal_repaired"
    assert "2026-10-12" in e.sent[0][0]


def test_unrepaired_gap_is_reported_as_needing_attention():
    e = Env(bars={"2026-10-12": 40}, repair=False, rc=3)
    e.go()
    assert len(e.sent) == 1 and e.sent[0][1]["event"] == "data.heal_failed"
    assert "2026-10-12" in e.sent[0][0] and "40" in e.sent[0][0]


def test_no_token_means_no_tools_and_one_alert():
    e = Env(bars={"2026-10-12": 40}, token=False)
    assert e.go() == 0
    assert e.tools == []
    assert len(e.sent) == 1 and e.sent[0][1]["event"] == "data.heal_failed"
    assert "token" in e.sent[0][0].lower()


def test_broker_gap_runs_the_broker_tool_for_the_oldest_two_dates():
    e = Env(broker={"2026-10-08": "PARTIAL", "2026-10-09": "MISSING", "2026-10-12": "PARTIAL"})
    e.go(max_broker_dates=2)
    argv = e.tools[0]
    assert "tools/backfill_broker_flow_gap.py" in " ".join(argv)
    assert argv[argv.index("--dates") + 1] == "2026-10-08,2026-10-09"
    # third date remains for the next night, so the run is reported as unfinished
    assert e.sent[0][1]["event"] == "data.heal_failed"
    assert "2026-10-12" in e.sent[0][0]


def test_gaps_outside_the_window_are_ignored():
    e = Env(bars={"2026-09-01": 900})
    e.go()
    assert e.tools == [] and e.sent == []


def test_recent_dates_returns_last_n_ascending():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT)")
    c.executemany("INSERT INTO ohlcv VALUES ('A', ?)", [(f"2026-10-{d:02d}",) for d in range(1, 11)])
    assert dh.recent_dates(c, 3) == ["2026-10-08", "2026-10-09", "2026-10-10"]


def test_events_registered_and_survive_the_blackout():
    for ev in ("data.heal_repaired", "data.heal_failed", "data.token_expired",
               "data.token_refresh_failed", "data.flow_fetch_failed", "data.flow_gap",
               "data.flow_coverage", "data.eod_degraded", "data.broker_period_failed"):
        assert ev in np.EVENTS, ev
        assert ev in np.BLACKOUT_EXEMPT, ev
        assert np.EVENTS[ev][0] == np.TIER_SEND, ev


def test_cron_wrap_exempts_data_jobs():
    src = (ROOT / "scripts/cron_wrap.sh").read_text()
    for job in ("auto_token", "stockbit_ohlcv", "stockbit_flow", "data_heal"):
        assert re.search(rf"[|(\s]{job}[|)]", src), job


def test_unit_pair_runs_weekday_evenings_after_the_vendor_window():
    svc = (ROOT / "deploy/systemd/idx-data-heal.service").read_text()
    tmr = (ROOT / "deploy/systemd/idx-data-heal.timer").read_text()
    assert "cron_wrap.sh data_heal" in svc
    assert "Persistent=true" in tmr
    assert re.search(r"OnCalendar=Mon\.\.Fri \*-\*-\* 22:45", tmr)   # after the 18:00-22:30 window


def test_chronic_partial_broker_days_are_not_gaps_but_outages_are():
    row = lambda st, exp, act: {"status": st, "expected": exp, "actual": act}
    assert not dh.is_broker_gap(row("COMPLETE", 800, 800))
    assert not dh.is_broker_gap(row("PARTIAL", 869, 623))    # 72%: normal vendor behaviour
    assert not dh.is_broker_gap(row("PARTIAL", 869, 435))    # just above 50%
    assert dh.is_broker_gap(row("PARTIAL", 869, 300))        # 35%: real hole
    assert dh.is_broker_gap(row("MISSING", 826, 0))
