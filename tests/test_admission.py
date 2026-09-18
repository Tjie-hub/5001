"""Admission chain: engine/admission.py, engine/rule_identity.py.

Covers the two gates added by the 2026-09-02 audit (rule parity L-1, evidence
staleness S-2) plus the pre-existing ones they were folded in with, so the
composite admission decision is pinned in one place.
"""
import datetime as dt
import sqlite3

import pytest

from engine import admission
from engine import rule_identity as ri


FRESH = dt.date.today().isoformat()


@pytest.fixture(autouse=True)
def _reset_admission_cache():
    """engine.admission caches "has this rule been researched?" per process and
    production resets it per scan cycle. Tests must do the same or a verdict
    computed against one in-memory DB leaks into the next test's."""
    admission.reset_evidence_cache()
    yield
    admission.reset_evidence_cache()
STALE = (dt.date.today() - dt.timedelta(days=admission.WF_EDGE_MAX_AGE_DAYS + 1)).isoformat()


def _db(rows=()):
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE wf_edge (ticker TEXT, strategy TEXT, expectancy_pct REAL,"
        " expectancy_rp REAL, win_rate REAL, consistency_pct REAL, sharpe REAL,"
        " n_trades INT, windows_tested INT, last_computed TEXT,"
        " PRIMARY KEY(ticker,strategy))")
    for r in rows:
        conn.execute("INSERT INTO wf_edge VALUES (?,?,?,?,?,?,?,?,?,?)", r)
    return conn


def _edge(ticker, strategy, exp, n=60, last=None):
    return (ticker, strategy, exp, 0.0, 55.0, 40.0, 0.4, n, 15, last or FRESH)


@pytest.fixture()
def unregistered(monkeypatch):
    import engine.registry_loader as rl
    monkeypatch.setattr(rl, "registry_governance", lambda s: None)
    monkeypatch.setattr(admission, "manifest_rule_ids", lambda: {})


@pytest.fixture()
def parity(monkeypatch):
    """Declare live == researched so non-parity concerns can be tested alone."""
    monkeypatch.setattr(ri, "live_gates", lambda strategy: ())


# ─────────────────── rule identity (L-1) ───────────────────

class TestRuleIdentity:

    def test_live_rule_differs_when_production_adds_a_gate(self):
        assert ri.live_rule_id("NR7 Breakout") != ri.research_rule_id("NR7 Breakout")

    def test_bypass_strategies_have_parity(self):
        for s in ("Crash Recovery", "Panic Rebound", "Liquidity Sweep"):
            ok, why = ri.rule_parity(s)
            assert ok, why

    def test_gated_strategies_do_not_have_parity(self):
        for s in ("NR7 Breakout", "Trend Following Breakout", "momentum"):
            ok, why = ri.rule_parity(s)
            assert not ok
            assert "weekly_mtf_trend" in why

    def test_bypass_set_matches_the_live_scanner(self):
        """rule_identity mirrors engine.strategies._WEEKLY_GATE_BYPASS; if the
        live path's bypass set moves, this module must move with it or the
        parity claim becomes a lie."""
        from engine.strategies import _WEEKLY_GATE_BYPASS
        assert set(ri._WEEKLY_GATE_BYPASS) == set(_WEEKLY_GATE_BYPASS)

    def test_manifest_declaration_closes_the_mismatch(self):
        """The documented remedy: re-run the walk-forward with the production
        gate applied and record the resulting id in the registry manifest."""
        declared = ri.live_rule_id("NR7 Breakout")
        ok, why = ri.rule_parity("NR7 Breakout", declared)
        assert ok, why

    def test_rule_id_is_stable_and_gate_sensitive(self):
        a = ri.rule_id("X", ())
        b = ri.rule_id("X", ())
        c = ri.rule_id("X", ("weekly_mtf_trend",))
        assert a == b and a != c


# ─────────────────── admission gates ───────────────────

class TestAdmission:

    def test_admits_on_fresh_positive_evidence_with_parity(self, unregistered, parity):
        conn = _db([_edge("AAA", "momentum", 1.5)])
        v = admission.evaluate(conn, "AAA", "momentum", disabled=set())
        assert v.admitted, v.reason
        assert v.stage == admission.STAGE_ADMITTED
        assert v.wf_expectancy_pct == 1.5

    def test_disabled_blocks_first(self, unregistered, parity):
        conn = _db([_edge("AAA", "momentum", 1.5)])
        v = admission.evaluate(conn, "AAA", "momentum", disabled={"momentum"})
        assert not v.admitted and v.stage == admission.STAGE_DISABLED

    def test_rule_mismatch_blocks_even_with_strong_evidence(self, unregistered):
        """L-1: a production-only gate cannot silently invalidate an OOS claim."""
        conn = _db([_edge("AAA", "momentum", 9.9, n=5000)])
        v = admission.evaluate(conn, "AAA", "momentum", disabled=set())
        assert not v.admitted
        assert v.stage == admission.STAGE_RULE_PARITY

    def test_stale_evidence_blocks(self, unregistered, parity):
        """S-2: _edge_selectable never read last_computed at all."""
        conn = _db([_edge("AAA", "momentum", 1.5, last=STALE)])
        v = admission.evaluate(conn, "AAA", "momentum", disabled=set())
        assert not v.admitted and v.stage == admission.STAGE_STALENESS
        assert "old" in v.reason

    def test_unparseable_last_computed_blocks(self, unregistered, parity):
        conn = _db([_edge("AAA", "momentum", 1.5, last="x")])
        v = admission.evaluate(conn, "AAA", "momentum", disabled=set())
        assert not v.admitted and v.stage == admission.STAGE_STALENESS

    def test_thin_sample_blocks(self, unregistered, parity):
        conn = _db([_edge("AAA", "momentum", 1.5, n=admission.N_MIN_TRADES - 1)])
        v = admission.evaluate(conn, "AAA", "momentum", disabled=set())
        assert not v.admitted and v.stage == admission.STAGE_OOS_EVIDENCE

    def test_negative_and_zero_expectancy_block(self, unregistered, parity):
        for exp in (-0.01, 0.0):
            conn = _db([_edge("AAA", "momentum", exp)])
            v = admission.evaluate(conn, "AAA", "momentum", disabled=set())
            assert not v.admitted and v.stage == admission.STAGE_OOS_EVIDENCE

    def test_missing_row_blocks(self, unregistered, parity):
        conn = _db()
        v = admission.evaluate(conn, "AAA", "momentum", disabled=set())
        assert not v.admitted and v.stage == admission.STAGE_OOS_EVIDENCE

    def test_shadow_blocks_regardless_of_evidence(self, monkeypatch, parity):
        import engine.registry_loader as rl
        monkeypatch.setattr(rl, "registry_governance", lambda s: "SHADOW")
        monkeypatch.setattr(admission, "manifest_rule_ids", lambda: {})
        conn = _db([_edge("AAA", "NR7 Breakout", 5.0, n=1000)])
        v = admission.evaluate(conn, "AAA", "NR7 Breakout", disabled=set())
        assert not v.admitted and v.stage == admission.STAGE_REGISTRY
        assert v.registry_state == "SHADOW"

    def test_approved_outside_universe_blocks(self, monkeypatch, parity):
        import engine.registry_loader as rl
        monkeypatch.setattr(rl, "registry_governance", lambda s: {"BBCA"})
        monkeypatch.setattr(admission, "manifest_rule_ids", lambda: {})
        conn = _db()
        v = admission.evaluate(conn, "AAA", "NR7 Breakout", disabled=set())
        assert not v.admitted and v.stage == admission.STAGE_REGISTRY

    def test_approved_in_universe_admits_without_a_wf_edge_row(self, monkeypatch, parity):
        """Registry admission is receipt-bound (R-10) and carries its own frozen
        universe; it does not additionally require a live wf_edge row."""
        import engine.registry_loader as rl
        monkeypatch.setattr(rl, "registry_governance", lambda s: {"AAA"})
        monkeypatch.setattr(admission, "manifest_rule_ids", lambda: {})
        conn = _db()
        v = admission.evaluate(conn, "AAA", "NR7 Breakout", disabled=set())
        assert v.admitted and v.registry_state == "APPROVED"

    def test_registry_only_path_refuses_unregistered(self, unregistered, parity):
        conn = _db([_edge("AAA", "momentum", 1.5)])
        v = admission.evaluate(conn, "AAA", "momentum", disabled=set(),
                               require_registry=True)
        assert not v.admitted and v.stage == admission.STAGE_REGISTRY

    def test_every_verdict_carries_a_reason(self, unregistered):
        conn = _db([_edge("AAA", "momentum", -1.0)])
        for st in ("momentum", "NR7 Breakout", "Liquidity Sweep"):
            v = admission.evaluate(conn, "AAA", st, disabled={"Liquidity Sweep"})
            assert v.reason and v.rule_id and v.stage


class TestDiagnostics:

    def test_summarise_counts_blocking_stages(self, unregistered, parity):
        conn = _db([_edge("AAA", "momentum", 1.5), _edge("AAA", "conservative", -1.0)])
        vs = [admission.evaluate(conn, "AAA", s, disabled={"ORB"})
              for s in ("momentum", "conservative", "ORB")]
        counts = admission.summarise(vs)
        assert counts[admission.STAGE_ADMITTED] == 1
        assert counts[admission.STAGE_OOS_EVIDENCE] == 1
        assert counts[admission.STAGE_DISABLED] == 1

    def test_format_diagnostic_names_the_blocking_stages(self):
        line = admission.format_diagnostic(
            {admission.STAGE_DISABLED: 5, admission.STAGE_ADMITTED: 0}, scanned=10)
        assert "0 admitted" in line and "disabled=5" in line
