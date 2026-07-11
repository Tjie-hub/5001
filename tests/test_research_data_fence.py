"""M4-lite (spec 2026-07-08): wf_scores / wf_edge / backtest_cache are research
data products — ONLY research/ may write them. Production reads are unchanged
and allowed; this fence covers the WRITE side. DAO exception: engine/wf_edge.py
holds the table's write SQL, but its data-write fn is only callable from
research/ (rule W2)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Same scope convention as tests/test_architecture_boundary.py (Phase A /
# audit R-2 widened both to routes/).
PRODUCTION_SCOPES = ["scheduler", "engine", "forward_testing", "data",
                     "screener", "routes"]
PRODUCTION_FILES = ["monitor.py", "paper_trade.py", "app.py",
                    "news_filter.py", "flow_filter.py", "stockbit_fetcher.py",
                    "routes_backtest_multi.py"]

RESEARCH_TABLES = ("wf_scores", "wf_edge", "backtest_cache")
# Data-writes only. CREATE TABLE IF NOT EXISTS (ensure-schema by readers) is
# deliberately allowed — schema-safety, not a data write.
WRITE_SQL = re.compile(
    r"(INSERT(?:\s+OR\s+\w+)?\s+INTO|UPDATE|REPLACE\s+INTO|DELETE\s+FROM|DROP\s+TABLE)"
    r"\s+(?:%s)\b" % "|".join(RESEARCH_TABLES), re.I | re.S)

# DAO exception — shrink-only, never grow silently.
DAO_ALLOWLIST = {"engine/wf_edge.py"}

# Pre-existing write debt surfaced when the scan widened to routes/ (Phase A,
# audit R-2): the backtest UI's cache-refresh endpoint writes backtest_cache
# from the production process. Retirement belongs to the deferred routing
# redesign; shrink-only, new violations still fail CI.
_ROUTES_WRITE_DEBT = {"routes/backtest.py"}


def _py_files():
    for scope in PRODUCTION_SCOPES:
        yield from (ROOT / scope).rglob("*.py")
    for f in PRODUCTION_FILES:
        p = ROOT / f
        if p.exists():
            yield p


def test_w1_no_research_table_writes_in_production():
    offenders = []
    for p in _py_files():
        rel = str(p.relative_to(ROOT))
        if rel in DAO_ALLOWLIST or rel in _ROUTES_WRITE_DEBT:
            continue
        if WRITE_SQL.search(p.read_text(encoding="utf-8")):
            offenders.append(rel)
    assert not offenders, (
        "production writes research tables (only research/ may): %s" % offenders)


def test_w1_routes_write_debt_shrinks_only():
    assert _ROUTES_WRITE_DEBT <= {"routes/backtest.py"}


def test_w2_save_wf_edge_only_called_from_research():
    offenders = []
    for p in _py_files():
        rel = str(p.relative_to(ROOT))
        if rel in DAO_ALLOWLIST:          # the definition itself
            continue
        src = p.read_text(encoding="utf-8")
        if re.search(r"\bsave_wf_edge\s*\(", src):
            offenders.append(rel)
    assert not offenders, f"production calls save_wf_edge (research-only): {offenders}"


def test_dao_allowlist_shrinks_only():
    assert len(DAO_ALLOWLIST) == 1
