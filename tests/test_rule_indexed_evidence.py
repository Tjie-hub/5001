"""Rule-indexed OOS evidence: admission must read the study that was run under
the rule production executes, and must never fall back to the bare-rule study
for a gated strategy (that would be finding L-1 reintroduced one level up).
"""
import datetime as dt
import sqlite3

import pytest

from engine import admission
from engine import rule_identity as ri
from engine.wf_edge import (ensure_wf_edge_table, ensure_wf_edge_rule_table,
                            save_wf_edge_rule, WF_EDGE_RULE_DDL)

FRESH = dt.date.today().isoformat()
STALE = (dt.date.today() - dt.timedelta(days=admission.WF_EDGE_MAX_AGE_DAYS + 1)).isoformat()
GATED = "momentum"                 # live rule != researched rule
BYPASS = "Liquidity Sweep"         # live rule == researched rule


@pytest.fixture(autouse=True)
def _reset_admission_cache():
    """engine.admission caches "has this rule been researched?" per process and
    production resets it per scan cycle. Tests must do the same or a verdict
    computed against one in-memory DB leaks into the next test's."""
    admission.reset_evidence_cache()
    yield
    admission.reset_evidence_cache()


@pytest.fixture()
def db(monkeypatch):
    import engine.registry_loader as rl
    monkeypatch.setattr(rl, "registry_governance", lambda s: None)
    monkeypatch.setattr(admission, "manifest_rule_ids", lambda: {})
    admission.reset_evidence_cache()
    conn = sqlite3.connect(":memory:")
    ensure_wf_edge_table(conn)
    ensure_wf_edge_rule_table(conn)
    return conn


def _bare(conn, ticker, strategy, exp, n=60, last=None):
    conn.execute("INSERT OR REPLACE INTO wf_edge VALUES (?,?,?,?,?,?,?,?,?,?)",
                 (ticker, strategy, exp, 0.0, 55.0, 40.0, 0.4, n, 15, last or FRESH))
    conn.commit()


def _ruled(conn, ticker, strategy, exp, n=60, last=None, rule_id=None):
    save_wf_edge_rule(conn, ticker,
                      {strategy: rule_id or ri.live_rule_id(strategy)},
                      [{"strategy": strategy, "expectancy_pct": exp,
                        "expectancy_rp": 0.0, "win_rate": 55.0,
                        "consistency_pct": 40.0, "sharpe": 0.4,
                        "n_trades": n, "windows_tested": 15}],
                      last or FRESH, "run-1")
    conn.commit()
    admission.reset_evidence_cache()


class TestRuleIndexedLookup:

    def test_gated_strategy_is_not_admitted_on_bare_evidence(self, db):
        """The whole point: a strong bare-rule row must not admit a strategy
        production runs under a different rule."""
        _bare(db, "AAA", GATED, 9.9, n=5000)
        v = admission.evaluate(db, "AAA", GATED, disabled=set())
        assert not v.admitted
        assert v.stage == admission.STAGE_RULE_PARITY
        assert "wf-parity" in v.reason

    def test_gated_strategy_is_admitted_on_rule_indexed_evidence(self, db):
        _ruled(db, "AAA", GATED, 1.4)
        v = admission.evaluate(db, "AAA", GATED, disabled=set())
        assert v.admitted, v.reason
        assert v.evidence_source == "wf_edge_rule"
        assert v.wf_expectancy_pct == 1.4

    def test_evidence_under_a_different_rule_does_not_count(self, db):
        _ruled(db, "AAA", GATED, 5.0, rule_id="momentum@some_other_gate#deadbeef")
        v = admission.evaluate(db, "AAA", GATED, disabled=set())
        # a study exists for the strategy but not for the live rule
        assert not v.admitted
        assert v.stage == admission.STAGE_RULE_PARITY

    def test_rule_study_present_but_this_ticker_missing_is_an_evidence_gap(self, db):
        """Distinguish 'the rule was never researched' from 'researched, but this
        ticker had no qualifying sample' — different remedies."""
        _ruled(db, "OTHER", GATED, 1.4)
        v = admission.evaluate(db, "AAA", GATED, disabled=set())
        assert not v.admitted
        assert v.stage == admission.STAGE_OOS_EVIDENCE
        assert "wf_edge_rule" in v.reason

    def test_bare_evidence_still_serves_a_bypass_strategy(self, db):
        """The three strategies the live path exempts from the weekly gate have
        live == researched, so wf_edge IS their rule-valid study."""
        _bare(db, "AAA", BYPASS, 1.1)
        v = admission.evaluate(db, "AAA", BYPASS, disabled=set())
        assert v.admitted, v.reason
        assert v.evidence_source == "wf_edge"

    def test_gates_still_apply_to_rule_indexed_evidence(self, db):
        for exp, n, last, stage in [
            (-0.5, 60, FRESH, admission.STAGE_OOS_EVIDENCE),
            (1.5, 5, FRESH, admission.STAGE_OOS_EVIDENCE),
            (1.5, 60, STALE, admission.STAGE_STALENESS),
        ]:
            conn = sqlite3.connect(":memory:")
            ensure_wf_edge_table(conn); ensure_wf_edge_rule_table(conn)
            _ruled(conn, "AAA", GATED, exp, n=n, last=last)
            v = admission.evaluate(conn, "AAA", GATED, disabled=set())
            assert not v.admitted and v.stage == stage, (exp, n, last, v.stage)
            conn.close()

    def test_disabled_still_wins_over_rule_indexed_evidence(self, db):
        _ruled(db, "AAA", GATED, 3.0)
        v = admission.evaluate(db, "AAA", GATED, disabled={GATED})
        assert not v.admitted and v.stage == admission.STAGE_DISABLED


class TestRuleStudyTable:

    def test_primary_key_separates_rules(self, db):
        _ruled(db, "AAA", GATED, 1.0)
        _ruled(db, "AAA", GATED, 2.0, rule_id="momentum@other#ffff")
        n = db.execute("SELECT COUNT(*) FROM wf_edge_rule WHERE ticker='AAA'").fetchone()[0]
        assert n == 2

    def test_rows_without_a_known_rule_id_are_refused(self, db):
        """Unlabelled evidence is the defect this table removes."""
        written = save_wf_edge_rule(db, "AAA", {}, [
            {"strategy": GATED, "expectancy_pct": 1.0, "expectancy_rp": 0.0,
             "win_rate": 50.0, "consistency_pct": 50.0, "sharpe": 0.1,
             "n_trades": 40, "windows_tested": 15}], FRESH)
        assert written == 0

    def test_ddl_keys_on_rule_id(self):
        assert "PRIMARY KEY (ticker, strategy, rule_id)" in WF_EDGE_RULE_DDL

    def test_wf_edge_is_left_untouched_by_the_parity_study(self, db):
        """wf_edge is the frozen bare-rule record and must not be migrated."""
        _bare(db, "AAA", GATED, -0.5)
        _ruled(db, "AAA", GATED, 1.4)
        assert db.execute("SELECT expectancy_pct FROM wf_edge WHERE ticker='AAA'"
                          ).fetchone()[0] == -0.5


class TestParityJobContract:

    def test_job_measures_only_the_gated_strategies(self):
        """The three bypass strategies already have rule-valid evidence; re-running
        them would waste hours and produce a duplicate of wf_edge."""
        import inspect
        from research import jobs
        src = inspect.getsource(jobs.refresh_wf_edge_rule)
        assert "_WEEKLY_GATE_BYPASS" in src
        assert "WEEKLY_MTF_FILTER" in src
        assert "save_wf_edge_rule" in src

    def test_job_does_not_touch_wf_edge_or_wf_scores(self):
        import inspect
        from research import jobs
        src = inspect.getsource(jobs.refresh_wf_edge_rule)
        assert "save_wf_edge(" not in src
        assert "INSERT OR REPLACE INTO wf_scores" not in src

    def test_job_raises_the_warmup_for_the_weekly_gate(self):
        import inspect
        from research import jobs
        from engine.filters_mtf import WARMUP_BARS
        src = inspect.getsource(jobs.refresh_wf_edge_rule)
        assert "warmup_bars=WARMUP_BARS" in src
        assert WARMUP_BARS >= 160

    def test_walk_forward_defaults_are_unchanged(self):
        """The parity run parameterises warm-up and roster; the existing weekly
        wf-refresh job must be bit-identical to before."""
        import inspect
        from research.walkforward_multi import run_walk_forward
        sig = inspect.signature(run_walk_forward)
        assert sig.parameters["warmup_bars"].default is None
        assert sig.parameters["strategies"].default is None


class TestEvidenceCacheLifecycle:
    """The web process is long-lived (gunicorn workers=1). A cached "no study
    exists" answer must not outlive the study that fixes it."""

    def test_cache_is_reset_each_scan_cycle(self):
        import inspect
        from scheduler import scanner, jobs
        assert "reset_evidence_cache" in inspect.getsource(
            scanner.scheduled_multi_strategy_scan)
        assert "reset_evidence_cache" in inspect.getsource(
            jobs.run_premarket_firm_scan)

    def test_reset_makes_new_evidence_visible(self, db):
        v1 = admission.evaluate(db, "AAA", GATED, disabled=set())
        assert v1.stage == admission.STAGE_RULE_PARITY
        _ruled(db, "AAA", GATED, 1.4)          # study lands (calls reset)
        v2 = admission.evaluate(db, "AAA", GATED, disabled=set())
        assert v2.admitted, v2.reason

    def test_stale_cache_would_hide_new_evidence(self, db):
        """Characterises WHY the reset is needed: without it the negative answer
        sticks."""
        admission.evaluate(db, "AAA", GATED, disabled=set())      # caches False
        save_wf_edge_rule(db, "AAA", {GATED: ri.live_rule_id(GATED)},
                          [{"strategy": GATED, "expectancy_pct": 1.4,
                            "expectancy_rp": 0.0, "win_rate": 55.0,
                            "consistency_pct": 40.0, "sharpe": 0.4,
                            "n_trades": 60, "windows_tested": 15}], FRESH, "r")
        db.commit()                                               # no reset
        assert not admission.evaluate(db, "AAA", GATED, disabled=set()).admitted
        admission.reset_evidence_cache()
        assert admission.evaluate(db, "AAA", GATED, disabled=set()).admitted


class TestEvidenceCadence:
    """Freshness is a gate; a gate nobody feeds is a deadlock with extra steps."""

    def test_parity_study_is_scheduled(self):
        from pathlib import Path
        cron = Path(__file__).resolve().parents[1] / "deploy" / "crontab"
        text = cron.read_text()
        assert "research.cli wf-parity" in text
        assert "research_wf_parity" in text          # wrapped like every other job

    def test_schedule_is_at_least_as_frequent_as_the_staleness_window(self):
        """A weekly study against a 14-day staleness gate leaves one full cycle
        of slack for a missed run. Tightening WF_EDGE_MAX_AGE_DAYS below the
        cadence would silently brick admission."""
        assert admission.WF_EDGE_MAX_AGE_DAYS >= 14
