"""Config hygiene guards (hardening Phase 5): no machine-specific absolute
paths and no duplicated dotenv loading in production code. Same source-scan
pattern as tests/test_architecture_boundary.py."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PRODUCTION_SCOPES = ["scheduler", "engine", "forward_testing", "data",
                     "screener", "routes", "utils"]
PRODUCTION_FILES = ["monitor.py", "paper_trade.py", "app.py", "wsgi.py",
                    "news_filter.py", "flow_filter.py", "stockbit_fetcher.py",
                    "config.py", "routes_backtest_multi.py"]

HARDCODED_HOME = re.compile(r"/home/tjiesar")
DOTENV_CALL = re.compile(r"^\s*load_dotenv\(", re.M)

# config.py is the single dotenv authority. auto_token.py is a standalone
# cron script that does not import config — allowed until it does.
# engine/agent_firm/config.py loads .env too (RCA 2026-07-13): when this
# module is imported standalone (smoke test, CLI, ad-hoc script) nothing
# else loads .env first, so provider API keys read empty. override=False
# means it never clobbers whatever root config.py already loaded.
DOTENV_ALLOWED = {"config.py", "engine/agent_firm/config.py"}


def _py_files():
    for scope in PRODUCTION_SCOPES:
        yield from (ROOT / scope).rglob("*.py")
    for f in PRODUCTION_FILES:
        p = ROOT / f
        if p.exists():
            yield p


def test_no_hardcoded_home_paths_in_production_code():
    offenders = []
    for p in _py_files():
        if HARDCODED_HOME.search(p.read_text(encoding="utf-8")):
            offenders.append(str(p.relative_to(ROOT)))
    assert not offenders, (
        f"machine-specific /home/tjiesar paths (use config.DB_PATH / "
        f"repo-relative paths): {offenders}")


def test_dotenv_loaded_only_in_config():
    offenders = []
    for p in _py_files():
        # .as_posix() (not str()) so the DOTENV_ALLOWED match is platform-
        # independent — same fix as test_architecture_boundary.py/
        # test_db_centralization.py/test_research_data_fence.py (RC1 audit
        # R-1, 2026-07-28): str(Path.relative_to(...)) uses native separators,
        # which silently broke this allowlist match on Windows.
        rel = p.relative_to(ROOT).as_posix()
        if rel in DOTENV_ALLOWED:
            continue
        if DOTENV_CALL.search(p.read_text(encoding="utf-8")):
            offenders.append(rel)
    assert not offenders, (
        f"duplicated load_dotenv() (config.py is the single loader): {offenders}")
