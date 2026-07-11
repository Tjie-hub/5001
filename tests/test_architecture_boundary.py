"""Architecture boundary (spec §2): production may not import research/;
research may not import execution. Source-scan enforcement, same pattern as
tests/test_db_centralization.py (Phase 3C)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RESEARCH_IMPORT = re.compile(r"^\s*(from|import)\s+research[.\s]", re.M)
EXECUTION_IMPORT = re.compile(
    r"^\s*(from|import)\s+(scheduler|monitor|paper_trade|forward_testing|app)[.\s]", re.M)

# Trade-path + engine surface that must stay research-free. routes/ is part of
# the production Flask app (registered in app.py) — audit R-2 found it invisible
# to this scan while importing research.* at request time.
PRODUCTION_SCOPES = ["scheduler", "engine", "forward_testing", "data",
                     "screener", "routes"]
PRODUCTION_FILES = ["monitor.py", "paper_trade.py", "app.py",
                    "news_filter.py", "flow_filter.py", "stockbit_fetcher.py",
                    "routes_backtest_multi.py"]

# Documented exceptions — each must shrink over time, never grow silently.
# M3 emptied the original set. Phase A (audit R-2) widened the scan to routes/
# and found these pre-existing research-in-routes surfaces (backtest UI,
# optimizer endpoints, fastmover study trigger). Their retirement is the
# deferred routing redesign — new violations are still a CI failure.
_ROUTES_DEBT = {"routes/backtest.py", "routes/screener.py",
                "routes/portfolio.py", "routes_backtest_multi.py"}
ALLOWLIST = set(_ROUTES_DEBT)


def _py_files(scopes, files):
    for scope in scopes:
        yield from (ROOT / scope).rglob("*.py")
    for f in files:
        p = ROOT / f
        if p.exists():
            yield p


def test_production_does_not_import_research():
    offenders = []
    for p in _py_files(PRODUCTION_SCOPES, PRODUCTION_FILES):
        rel = str(p.relative_to(ROOT))
        if rel in ALLOWLIST:
            continue
        if RESEARCH_IMPORT.search(p.read_text(encoding="utf-8")):
            offenders.append(rel)
    assert not offenders, f"production imports research/: {offenders}"


def test_research_does_not_import_execution():
    offenders = []
    for p in (ROOT / "research").rglob("*.py"):
        if EXECUTION_IMPORT.search(p.read_text(encoding="utf-8")):
            offenders.append(str(p.relative_to(ROOT)))
    assert not offenders, f"research/ imports execution modules: {offenders}"


def test_allowlist_shrinks_only():
    # Shrink-only: entries may be removed as routes retire their research
    # imports, never added or swapped without a conscious edit + review here.
    assert ALLOWLIST <= _ROUTES_DEBT
    assert len(ALLOWLIST) <= 4
