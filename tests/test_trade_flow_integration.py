"""Integration check for engine/trade_flow.py against the verified
broker-flow-v001 frozen snapshot (read-only).

Skipped unless the snapshot file exists — this is the Windows-side
production data source per DATABASE_ARCHITECTURE.md §5 (versioned
snapshots; the PC never opens the Dell's live DB). The test doubles as the
Trade Flow acceptance run: TOWR over a multi-session window vs the
single-day window it contains must agree exactly.

This test only ever opens the snapshot with SQLite URI mode=ro — it never
writes, never checkpoints WAL, and never touches the Dell.
"""
import os
import sqlite3

import pytest

from engine.trade_flow import get_trade_flow

SNAPSHOT = os.environ.get(
    "IDX_SNAPSHOT_DB",
    "D:/IDX-backups/walkforward_pre_integration_20260903.db",
)

pytestmark = pytest.mark.skipif(
    not os.path.exists(SNAPSHOT),
    reason=f"v001 snapshot not present at {SNAPSHOT}",
)


def _ro():
    return sqlite3.connect(f"file:{SNAPSHOT}?mode=ro", uri=True)


def test_towr_multiday_vs_single_day_consistency():
    multi = get_trade_flow(SNAPSHOT, "TOWR", "2026-08-31", "2026-09-01")
    assert multi is not None, "snapshot must contain TOWR flow bars"
    single = get_trade_flow(SNAPSHOT, "TOWR", "2026-09-01", "2026-09-01")

    mdates = [s["date"] for s in multi["sessions"]]
    assert mdates == ["2026-08-31", "2026-09-01"]

    # Day-level consistency: identical per-minute activity and identical
    # day totals; the cumulative LEVEL of the range is higher by design
    # (a range aggregates from its own start — Stockbit semantics).
    def diffs(seq):
        return [b - a for a, b in zip(seq, seq[1:])]

    n = len(single["series"]["time"])
    assert single["series"]["time"] == multi["series"]["time"][-n:]
    assert diffs(single["series"]["cum_buy"]) == diffs(multi["series"]["cum_buy"][-n:])
    assert diffs(single["series"]["cum_sell"]) == diffs(multi["series"]["cum_sell"][-n:])
    assert single["series"]["price"] == multi["series"]["price"][-n:]

    # Day-2 session totals are identical in both views; the multi-day range
    # totals are the SUM of all its sessions and equal the chained curves'
    # final point (single-day view only covers 09-01).
    d2_multi = next(s for s in multi["sessions"] if s["date"] == "2026-09-01")
    d2_single = single["sessions"][0]
    assert d2_single["buy_value"] == d2_multi["buy_value"]
    assert d2_single["sell_value"] == d2_multi["sell_value"]
    d1_multi = next(s for s in multi["sessions"] if s["date"] == "2026-08-31")
    assert single["totals"]["buy_value"] == d2_multi["buy_value"]
    assert multi["totals"]["buy_value"] == d1_multi["buy_value"] + d2_multi["buy_value"]
    assert multi["totals"]["buy_value"] == multi["series"]["cum_buy"][-1]
    assert multi["totals"]["sell_value"] == multi["series"]["cum_sell"][-1]
    assert multi["totals"]["net_value"] == multi["series"]["net_flow"][-1]


def test_towr_requested_03_sep_reports_missing_not_fabricated():
    flow = get_trade_flow(SNAPSHOT, "TOWR", "2026-09-01", "2026-09-03")
    dates = [s["date"] for s in flow["sessions"]]
    assert dates == ["2026-09-01"], "only ingested sessions may be returned"
    # 2026-09-02 is a calendar trading day in this snapshot with no TOWR
    # bars; 2026-09-03 is beyond the snapshot entirely. The engine must
    # surface the calendar-known gap and stay silent about the unknown day
    # rather than inventing either.
    assert flow["missing_sessions"] == ["2026-09-02"]
    assert flow["series"]["points"] > 300


def test_towr_cumulative_curves_monotone_and_net_consistent():
    flow = get_trade_flow(SNAPSHOT, "TOWR", "2026-08-25", "2026-09-01")
    s = flow["series"]
    assert s["cum_buy"] == sorted(s["cum_buy"])
    assert s["cum_sell"] == sorted(s["cum_sell"])
    assert all(b - sl == nf for b, sl, nf in
               zip(s["cum_buy"], s["cum_sell"], s["net_flow"]))
    # Sessions in the window every IDX calendar day 2026-08-25..09-01 except
    # any genuinely missing ingestion — reported honestly.
    assert len(flow["sessions"]) >= 5
    totals = flow["totals"]
    assert totals["net_value"] == totals["buy_value"] - totals["sell_value"]
    # Exact per-minute net_value sum stays within a few percent of the
    # de-cumulated lot×price estimate (intra-minute price drift only).
    assert totals["net_value_exact"] != 0
    drift = abs(totals["net_value"] - totals["net_value_exact"]) / abs(
        totals["net_value_exact"])
    assert drift < 0.05, f"lot×price valuation drifted {drift:.2%} from exact"
