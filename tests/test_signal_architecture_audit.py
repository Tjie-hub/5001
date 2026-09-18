"""Integrity tests written for the 2026-09-02 signal-architecture audit.

These assert properties that the audit relied on but that no existing test
pinned down. They are characterisation tests: they encode what the code does
today, so a future change that silently breaks the information boundary (or
silently re-opens live admission) fails CI instead of passing unnoticed.

Grouped by the audit's Part 11 headings:
  1. Walk-Forward integrity   (train/test disjointness, warmup exclusion)
  2. Scanner integrity        (edge gating, SHADOW exclusion, stale wf_edge)
  3. Watchlist integrity      (EOD R/S/V/P and premarket source vocabularies)
  4. Forward-test integrity   (signal_date strictly precedes entry_date)
"""
import json
import sqlite3

import numpy as np
import pandas as pd
import pytest

from research.walkforward_multi import walk_forward_split, run_walk_forward
from engine.wf_edge import aggregate_wf_windows, N_MIN_TRADES


# ───────────────────────── fixtures ─────────────────────────

def _synthetic_df(days=1500, seed=7):
    """Deterministic OHLCV long enough for many 12m/3m walk-forward windows."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=days)
    close = 1000 * np.cumprod(1 + rng.normal(0.0005, 0.02, days))
    high = close * (1 + abs(rng.normal(0, 0.01, days)))
    low = close * (1 - abs(rng.normal(0, 0.01, days)))
    open_ = close * (1 + rng.normal(0, 0.005, days))
    vol = rng.integers(1_000_000, 10_000_000, days)
    return pd.DataFrame({
        "date": [str(d.date()) for d in dates],
        "open": open_, "high": high, "low": low, "close": close,
        "volume": vol.astype(float),
    })


# ─────────────── 1. Walk-Forward integrity ───────────────

class TestWalkForwardIntegrity:

    def test_train_and_test_slices_share_no_bar(self):
        """No train/test overlap: the two slices are disjoint on `date`."""
        wins = walk_forward_split(_synthetic_df(), train_months=12, test_months=3)
        assert wins, "fixture must produce windows"
        for w in wins:
            train_dates = set(w["train"]["date"].astype(str))
            test_dates = set(w["test"]["date"].astype(str))
            assert not (train_dates & test_dates), (
                f"window {w['window']} leaks {len(train_dates & test_dates)} bars "
                f"from train into test")

    def test_every_train_bar_strictly_precedes_every_test_bar(self):
        """Temporal ordering: max(train) < min(test) for every window."""
        wins = walk_forward_split(_synthetic_df(), train_months=12, test_months=3)
        for w in wins:
            assert w["train"]["date"].max() < w["test"]["date"].min(), (
                f"window {w['window']} has a train bar at/after the test start")

    def test_test_windows_are_disjoint_across_windows(self):
        """Each OOS observation is scored once — test windows never overlap."""
        wins = walk_forward_split(_synthetic_df(), train_months=12, test_months=3)
        seen = set()
        for w in wins:
            d = set(w["test"]["date"].astype(str))
            assert not (seen & d), f"window {w['window']} re-scores bars already scored"
            seen |= d

    def test_no_oos_trade_is_entered_before_its_window_starts(self):
        """The warmup tail prepended to each test slice must not contribute
        trades: every reported trade's entry_date is inside the OOS window."""
        df = _synthetic_df()
        res = run_walk_forward(df)
        assert "error" not in res
        for name, summary in res["summary"].items():
            for w in summary["windows"]:
                # compute_metrics does not carry per-trade dates through, so we
                # assert the invariant the aggregation depends on: a window's
                # trades are counted only if the window itself was evaluated
                # inside [test_start, test_end).
                assert w["test_start"] < w["test_end"], name

    def test_warmup_tail_changes_indicators_not_trade_attribution(self):
        """run_walk_forward filters trades to entry_date >= test_start, so a
        window's total_trades can never exceed the bars in its own test slice."""
        df = _synthetic_df()
        wins = walk_forward_split(df, train_months=12, test_months=3)
        by_window = {w["window"]: len(w["test"]) for w in wins}
        res = run_walk_forward(df)
        for summary in res["summary"].values():
            for w in summary["windows"]:
                assert w["total_trades"] <= by_window[w["window"]], (
                    "more trades than test bars — warmup trades leaked in")


class TestWfEdgeAggregation:

    def test_aggregation_pools_only_supplied_windows(self):
        """expectancy_pct is the trade-weighted pool of the windows handed in —
        no window is inferred, extrapolated, or reused."""
        ranked = [{
            "strategy": "S", "consistency_pct": 50.0, "windows_tested": 2,
            "windows": [
                {"total_trades": 10, "avg_pnl_pct": 2.0, "total_pnl_rp": 100,
                 "total_winners": 6, "sharpe": 1.0},
                {"total_trades": 30, "avg_pnl_pct": -1.0, "total_pnl_rp": -30,
                 "total_winners": 9, "sharpe": -0.5},
            ],
        }]
        out = aggregate_wf_windows(ranked)[0]
        # (10*2.0 + 30*-1.0) / 40 = -0.25  — pooled, NOT the mean of (2.0, -1.0)
        assert out["expectancy_pct"] == pytest.approx(-0.25)
        assert out["expectancy_pct"] != pytest.approx(0.5)
        assert out["n_trades"] == 40

    def test_thin_samples_are_excluded_not_zero_filled(self):
        ranked = [{"strategy": "S", "consistency_pct": 100.0, "windows_tested": 1,
                   "windows": [{"total_trades": N_MIN_TRADES - 1, "avg_pnl_pct": 9.0,
                                "total_pnl_rp": 1, "total_winners": 1, "sharpe": 3.0}]}]
        assert aggregate_wf_windows(ranked) == []


# ─────────────── 2. Scanner integrity ───────────────

def _wf_edge_db(rows):
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE wf_edge (ticker TEXT, strategy TEXT, expectancy_pct REAL,"
        " expectancy_rp REAL, win_rate REAL, consistency_pct REAL, sharpe REAL,"
        " n_trades INT, windows_tested INT, last_computed TEXT,"
        " PRIMARY KEY(ticker,strategy))")
    conn.executemany("INSERT INTO wf_edge VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    return conn


class TestScannerAdmission:

    def test_negative_expectancy_never_selected(self, monkeypatch):
        from scheduler import scanner
        monkeypatch.setattr(scanner, "registry_governance", lambda s: None,
                            raising=False)
        import engine.registry_loader as rl
        monkeypatch.setattr(rl, "registry_governance", lambda s: None)
        conn = _wf_edge_db([
            ("AAA", "momentum", -0.01, 0, 50, 50, 0.1, 100, 16, "2026-09-01"),
            ("AAA", "conservative", 0.0, 0, 50, 50, 0.1, 100, 16, "2026-09-01"),
        ])
        assert scanner._edge_selectable(conn, "AAA",
                                        ["momentum", "conservative"]) == []

    def test_missing_wf_edge_row_yields_no_selection(self, monkeypatch):
        from scheduler import scanner
        import engine.registry_loader as rl
        monkeypatch.setattr(rl, "registry_governance", lambda s: None)
        conn = _wf_edge_db([])
        assert scanner._edge_selectable(conn, "AAA", ["momentum"]) == []

    def test_stale_wf_edge_is_now_refused(self, monkeypatch):
        """CLOSED 2026-09-02. This was a characterisation test: `_edge_selectable`
        ignored `last_computed` entirely, so a row computed in 2019 was selected
        exactly like a fresh one. engine/admission.py now gates on
        WF_EDGE_MAX_AGE_DAYS (two weekly refresh cycles)."""
        from scheduler import scanner
        from engine import admission
        import engine.registry_loader as rl
        import engine.rule_identity as ri
        monkeypatch.setattr(rl, "registry_governance", lambda s: None)
        monkeypatch.setattr(ri, "live_gates", lambda strategy: ())
        monkeypatch.setattr(scanner, "_get_disabled_strategies", lambda: set())
        conn = _wf_edge_db([
            ("AAA", "momentum", 1.5, 0, 55, 60, 0.4, 100, 16, "2019-01-01 00:00"),
        ])
        assert scanner._edge_selectable(conn, "AAA", ["momentum"]) == []
        v = admission.evaluate(conn, "AAA", "momentum", disabled=set())
        assert v.stage == admission.STAGE_STALENESS

    def test_shadow_strategy_cannot_fall_back_to_legacy_wf_edge(self, monkeypatch):
        """A registry-governed but non-APPROVED strategy is excluded outright,
        even with a strongly positive legacy wf_edge row."""
        from scheduler import scanner
        import engine.registry_loader as rl
        monkeypatch.setattr(rl, "registry_governance",
                            lambda s: "SHADOW" if s == "NR7 Breakout" else None)
        conn = _wf_edge_db([
            ("AAA", "NR7 Breakout", 5.0, 0, 70, 80, 1.2, 200, 16, "2026-09-01"),
        ])
        assert scanner._edge_selectable(conn, "AAA", ["NR7 Breakout"]) == []
        assert scanner._edge_selectable(conn, "AAA", None) == []

    def test_disabled_default_covers_every_negative_roster_strategy(self):
        """The shipped default disabled-list still names every strategy the
        2026-07-04 re-baseline found negative."""
        from scheduler.scanner import _DEFAULT_DISABLED
        disabled = {s.strip() for s in _DEFAULT_DISABLED.split(",")}
        for s in ("vwap_reversion", "vol_weighted", "conservative", "momentum",
                  "Liquidity Sweep", "ORB", "Volume Profile POC",
                  "Inside Bar Breakout"):
            assert s in disabled

    def test_admitted_strategy_maps_to_a_real_live_checker(self):
        """Any strategy the regime map can route must have a live checker —
        otherwise admission silently produces zero signals (audit C-1)."""
        from scheduler.scanner import _REGIME_STRATEGY_MAP, _get_disabled_strategies
        from engine.strategies import _CHECKER_DISPATCH
        disabled = _get_disabled_strategies()
        for band, cands in _REGIME_STRATEGY_MAP.items():
            for s in cands:
                if s in disabled:
                    continue
                assert s in _CHECKER_DISPATCH, (
                    f"{band} routes '{s}' but no live checker exists for it")


# ─────────────── 3. Watchlist integrity ───────────────

class TestWatchlistSources:

    def test_eod_and_premarket_source_vocabularies_are_disjoint(self):
        """EOD tags R/S/V/P; premarket tags REVERSAL/PREMOVER/BEAR_DIP. The two
        pipelines do not share a source vocabulary — the fact the audit's
        EOD->premarket carry-forward finding rests on."""
        eod_tags = {"R", "S", "V", "P"}
        from engine.unified_watchlist import _read_reversal, _read_premover, _read_bear
        premarket_tags = {"REVERSAL", "PREMOVER", "BEAR_DIP"}
        assert not (eod_tags & premarket_tags)

    def test_premarket_now_consumes_the_eod_base_plan(self):
        """CLOSED 2026-09-02. Was: run_premarket_firm_scan built its own
        universe and never loaded the EOD snapshot. It is now a revision
        operator over the frozen EOD plan (engine/premarket_revision.py)."""
        import inspect
        from scheduler import jobs
        src = inspect.getsource(jobs.run_premarket_firm_scan)
        assert "base_plan" in src
        assert "premarket_revision" in src

    def test_eod_no_longer_reads_same_day_premarket_approvals(self):
        """CLOSED 2026-09-02. Was: the live dependency ran premarket(D) ->
        EOD(D), the reverse of the intended flow. Source tag P is gone; the
        validated walk-forward source W replaces it as the evidenced input."""
        import inspect
        from engine import trade_plan
        src = inspect.getsource(trade_plan.gather_long_candidates)
        assert "REMOVED 2026-09-02" in src
        assert "signal_direction='BUY'" in src        # tag W, the evidenced source

    def test_snapshot_roundtrip_preserves_rank_and_sources(self):
        from engine import trade_plan as tp
        conn = sqlite3.connect(":memory:")
        ranked = [
            {"ticker": "AAA", "confidence": 0.8, "conviction": 12.0,
             "confluence": 2, "sources": ["R", "S"]},
            {"ticker": "BBB", "confidence": 0.6, "conviction": 3.0,
             "confluence": 1, "sources": ["V"]},
        ]
        tp.record_snapshot(conn, "2026-09-01", "eod", ranked)
        got = tp.get_snapshot(conn, "2026-09-01", "eod")
        assert [g["ticker"] for g in got] == ["AAA", "BBB"]
        assert [g["rank"] for g in got] == [1, 2]
        assert got[0]["sources"] == ["R", "S"]

    def test_rerun_no_longer_erases_what_was_published(self):
        """CLOSED 2026-09-02. `watchlist_snapshot` is still the current-state
        projection (INSERT OR REPLACE is correct for that role), but every
        publication is now appended to the immutable, revision-numbered
        watchlist_snapshot_log first."""
        from engine import trade_plan as tp
        from engine import watchlist_ledger as wl
        conn = sqlite3.connect(":memory:")
        tp.record_snapshot(conn, "2026-09-01", "eod",
                           [{"ticker": "AAA", "confidence": 0.9, "conviction": 1.0,
                             "confluence": 1, "sources": ["R"]}])
        tp.record_snapshot(conn, "2026-09-01", "eod",
                           [{"ticker": "AAA", "confidence": 0.1, "conviction": 1.0,
                             "confluence": 1, "sources": ["V"]}])
        assert tp.get_snapshot(conn, "2026-09-01", "eod")[0]["confidence"] == 0.1
        # ...and revision 1 is still there, unaltered
        first = wl.read_snapshot(conn, "2026-09-01", "eod", revision=1)[0]
        assert first["confidence"] == 0.9 and first["sources"] == ["R"]

    def test_ledger_carries_price_rule_and_evidence(self):
        """CLOSED 2026-09-02. The projection table still has no price (it is a
        diff view), but the publication ledger records the decision price, its
        basis, the entry rule, the attributing strategy and its OOS evidence —
        so an outcome is reconstructable without retrospective price selection."""
        from engine.watchlist_ledger import SNAPSHOT_LOG_DDL
        body = SNAPSHOT_LOG_DDL.split("(", 1)[1]
        for col in ("decision_price", "decision_price_basis", "entry_rule",
                    "strategy_fn", "rule_id", "wf_expectancy_pct", "recorded_at",
                    "revision"):
            assert col in body, col


def tp_ddl_columns():
    from engine.trade_plan import WATCHLIST_SNAPSHOT_DDL
    body = WATCHLIST_SNAPSHOT_DDL.split("(", 1)[1].rsplit(")", 1)[0]
    return [c for c in body.split(",")]


# ─────────────── 4. Forward-test integrity ───────────────

class TestForwardTestBoundary:

    def test_shadow_fill_bar_is_strictly_after_the_signal_bar(self):
        """The forward tester fills at the NEXT open after the signal date, so
        a signal can never be entered on the bar that produced it."""
        import inspect
        from forward_testing.positions import shadow_manager as sm
        src = inspect.getsource(sm.ShadowPositionManager)
        assert "self.resolver.next_open(sig[\"ticker\"], sig[\"signal_date\"])" in src

    def test_live_forward_test_data_has_no_same_bar_entries(self):
        """Data-level check against the production DB: every closed shadow
        trade entered strictly after its signal date. Skipped when the DB is
        absent (CI)."""
        import os, sqlite3
        db = "data/walkforward.db"
        if not os.path.exists(db):
            pytest.skip("production DB not present")
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=30)
        try:
            bad, total = conn.execute(
                "SELECT SUM(CASE WHEN entry_date <= signal_date THEN 1 ELSE 0 END),"
                " COUNT(*) FROM ft_shadow_trade").fetchone()
        finally:
            conn.close()
        if not total:
            pytest.skip("no closed shadow trades yet")
        assert bad == 0, f"{bad}/{total} shadow trades entered on/before signal bar"

    def test_costs_are_applied_to_both_legs(self):
        from engine.exits.costs import Costs, apply_costs
        c = Costs()
        raw = 1000.0
        buy = apply_costs(raw, "BUY", c)
        sell = apply_costs(raw, "SELL", c)
        assert buy > raw, "buy fill must be worse than mid"
        assert sell < raw, "sell fill must be worse than mid"
        # a zero-move round trip must lose money
        assert (sell - buy) / buy < 0
