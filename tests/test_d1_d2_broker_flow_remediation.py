"""D1/D2 remediation regression suite
(docs/research_programs/P-M/D1_D2_PRODUCTION_SEMANTIC_AUDIT_2026-09-10.md).

D2: broker_flow.lot and broker_flow.value are already signed (BUY positive, SELL negative);
broker_flow.lot_value is unsigned on BOTH sides. The correct net construction is SUM(lot) or
SUM(value) directly -- never SUM(lot_value WHERE side='BUY') - SUM(lot_value WHERE side='SELL'),
which computes a different, wrong quantity (and, per the audit, side/sign occasionally
disagree, so even the side filter alone is not reliable).

D1: broker_flow.investor_type is a BROKERAGE ownership classification (foreign-owned / local /
government-owned), not an end-investor class. 'Asing' means "foreign-owned brokerage", never
"foreign investor", "institutional investor", or "retail investor".

This suite has two parts:
  1. A static source-scan guard (belt-and-suspenders, same pattern as
     tests/test_research_data_fence.py) that fails CI if the D2 anti-pattern is reintroduced
     anywhere in production code.
  2. Targeted regressions for the sites fixed in this remediation that don't already have
     dedicated coverage elsewhere (tests/test_agent_firm_context.py,
     tests/test_dashboard_watchlist.py, tests/test_dashboard_risk.py cover the
     agent-firm-context and dashboard sites).
"""
import re
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

PRODUCTION_SCOPES = ["scheduler", "engine", "forward_testing", "data",
                     "screener", "routes"]
PRODUCTION_FILES = ["monitor.py", "paper_trade.py", "app.py",
                    "flow_filter.py", "stockbit_fetcher.py"]

# The D2 anti-pattern signature: a file that both aggregates lot_value AND filters on both
# sides of `side` is (per the audit's exhaustive search) always the
# SUM(lot_value WHERE side='BUY') - SUM(lot_value WHERE side='SELL') defect -- no legitimate
# production use of lot_value needs both side filters in the same file (raw ingestion/backfill
# tools store side + lot_value per row but never filter+aggregate by side).
_LOT_VALUE_SUM = re.compile(r"SUM\s*\(\s*lot_value\s*\)", re.I)
_SIDE_BUY = re.compile(r"side\s*=\s*['\"]BUY['\"]")
_SIDE_SELL = re.compile(r"side\s*=\s*['\"]SELL['\"]")


def _production_py_files():
    for scope in PRODUCTION_SCOPES:
        d = ROOT / scope
        if d.is_dir():
            yield from d.rglob("*.py")
    for f in PRODUCTION_FILES:
        p = ROOT / f
        if p.is_file():
            yield p


def test_no_buy_minus_sell_lot_value_anti_pattern_in_production():
    """D2 static guard: no production file computes
    SUM(lot_value) WHERE side=BUY minus SUM(lot_value) WHERE side=SELL. Add any new file that
    legitimately needs both side filters alongside lot_value (raw storage, not net-flow
    aggregation) to this test's understanding rather than silently allowlisting it."""
    offenders = []
    for path in _production_py_files():
        text = path.read_text(errors="ignore")
        if _LOT_VALUE_SUM.search(text) and _SIDE_BUY.search(text) and _SIDE_SELL.search(text):
            offenders.append(path.relative_to(ROOT).as_posix())
    assert not offenders, (
        f"D2 anti-pattern (SUM(lot_value) split by side='BUY'/'SELL') reintroduced in: "
        f"{offenders}. Use SUM(lot) (share net) or SUM(value) (signed IDR net) instead -- "
        f"see docs/research_programs/P-M/D1_D2_PRODUCTION_SEMANTIC_AUDIT_2026-09-10.md."
    )


def test_agent_firm_flow_prompt_does_not_claim_institutional_or_foreign_investor():
    """D1 guard: the live LLM prompt must not instruct the model to reason about
    'institutional' or 'foreign investor' money from investor_type='Asing' data -- the
    audit's B.1 finding, and the highest-severity site (it gates live paper-trade signals).
    The prompt is allowed to name those terms only to explicitly forbid them."""
    prompt = (ROOT / "engine/agent_firm/prompts/flow_v1.md").read_text()
    lowered = prompt.lower()
    # The original defect: instructing the LLM to treat the data AS institutional/foreign
    # investor money. Must be gone.
    assert "institutional and/or foreign money is genuinely" not in lowered
    assert "decide whether institutional" not in lowered
    # The prompt must instead explicitly forbid that framing.
    assert "not characterize this as" in lowered or "not " in lowered and "institutional" in lowered
    assert "foreign-owned brokerage" in lowered or "foreign-owned brokerages" in lowered
    # The field name must be present and self-describing -- not the old ambiguous name.
    assert "net_foreign_owned_brokerage_lots_14d" in prompt
    assert "net_foreign_14d" not in prompt


class TestPremarketRevisionForeignNet:
    """D2 + D1 regression for engine/premarket_revision.py::_overnight_foreign_net()."""

    def _db(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE broker_flow (ticker TEXT, trade_date TEXT, "
                     "broker_code TEXT, side TEXT, lot INT, value REAL, investor_type TEXT)")
        return conn

    def test_uses_signed_sum_value_not_buy_minus_sell_lot_value(self):
        from engine.premarket_revision import _overnight_foreign_net

        conn = self._db()
        # side/sign intentionally disagree on row 1 (BUY with a negative value) -- the
        # documented vendor rounding artifact (audit §C, "3,585 BUY rows have lot<0").
        conn.execute("INSERT INTO broker_flow VALUES ('BBRI', '2026-09-09', 'BK1', 'BUY', "
                     "?, ?, 'Asing')", (-20, -2_000_000_000))
        conn.execute("INSERT INTO broker_flow VALUES ('BBRI', '2026-09-09', 'BK2', 'SELL', "
                     "?, ?, 'Asing')", (5, 500_000_000))
        conn.execute("INSERT INTO broker_flow VALUES ('BBRI', '2026-09-09', 'BK3', 'BUY', "
                     "?, ?, 'Asing')", (90, 9_000_000_000))

        result = _overnight_foreign_net(conn, "BBRI", "2026-09-09")

        correct_sum_value = -2_000_000_000 + 500_000_000 + 9_000_000_000  # == 7.5B
        assert result is not None
        assert result["net_value"] == correct_sum_value == 7_500_000_000

    def test_below_materiality_threshold_returns_none(self):
        from engine.premarket_revision import _overnight_foreign_net, FOREIGN_NET_MATERIAL

        conn = self._db()
        conn.execute("INSERT INTO broker_flow VALUES ('BBCA', '2026-09-09', 'BK1', 'BUY', "
                     "1, ?, 'Asing')", (FOREIGN_NET_MATERIAL - 1,))
        result = _overnight_foreign_net(conn, "BBCA", "2026-09-09")
        assert result is None

    def test_reason_text_does_not_claim_end_investor_identity(self):
        """D1: the revision reason text must not read as an end-investor claim -- it should
        say 'foreign-owned-brokerage', not bare 'foreign'."""
        from engine.premarket_revision import revise

        conn = self._db()
        conn.execute("INSERT INTO broker_flow VALUES ('BBRI', '2026-09-09', 'BK1', 'BUY', "
                     "?, ?, 'Asing')", (100, 10_000_000_000))
        base_rows = [{"ticker": "BBRI", "rank": 1}]
        decisions = revise(conn, base_rows, base_date="2026-09-09", plan_date="2026-09-10")
        d = next(d for d in decisions if d.ticker == "BBRI")
        assert "foreign-owned-brokerage" in d.reason
