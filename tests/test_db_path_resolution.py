"""P0.E2.S2.T1 -- DB_PATH resolves to a single canonical absolute path (H-7).

Audit H-7: DB_PATH was independently resolved in 20+ modules -- eight of them
(paper_trade.py, scheduler/{scanner,jobs,reports,utils,__init__}.py,
engine/risk_alert.py, engine/regime_filter.py's __main__ block,
scripts/pattern_backtest.py) duplicated the exact same hardcoded absolute
path pointing at a nonexistent directory
(``/home/tjiesar/10 Projects/idx-walkforward-5001/...`` -- wrong username,
wrong layout, for anyone but the original author's machine); several more
(screener/brpt_filter.py, screener/reversal_filter.py,
screener/idx_scraper.py, news_filter.py, screener/calculator.py,
stockbit_fetcher.py) computed their own path from ``__file__`` and silently
ignored the ``DB_PATH`` env var entirely. This test proves neither class of
duplicate/divergent fallback remains in live code, and that the modules
which switched to ``from config import DB_PATH`` actually resolve to the
same value as the canonical source.
"""
import importlib
import pathlib

import config


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# H-7 targets live, importable modules -- same scope boundary the H-1/H-2/
# AN-8 audit used (scripts/audits/an8_unregistered_jobs.py): archived/dead
# code and already-applied one-off migration scripts are out of scope.
EXCLUDED_DIR_PARTS = {".venv", "__pycache__", ".git", "_archive", "tests", "node_modules"}

STALE_HARDCODED_PATH = "/home/tjiesar/10 Projects/idx-walkforward-5001"


def _live_python_files():
    for p in REPO_ROOT.rglob("*.py"):
        rel = p.relative_to(REPO_ROOT)
        if any(part in EXCLUDED_DIR_PARTS for part in rel.parts):
            continue
        if rel.parts[:2] == ("migrations", "applied"):
            continue
        yield p


def test_no_stale_hardcoded_db_path_remains():
    offenders = [str(p.relative_to(REPO_ROOT)) for p in _live_python_files()
                 if STALE_HARDCODED_PATH in p.read_text(encoding="utf-8", errors="ignore")]
    assert offenders == [], f"stale hardcoded DB_PATH fallback reintroduced in: {offenders}"


def test_default_db_path_is_absolute_and_targets_data_dir():
    default = config.default_db_path()
    assert pathlib.Path(default).is_absolute()
    assert pathlib.Path(default) == REPO_ROOT / "data" / "walkforward.db"


def test_config_db_path_falls_back_to_default_when_env_unset(monkeypatch):
    monkeypatch.delenv("DB_PATH", raising=False)
    importlib.reload(config)
    try:
        assert config.DB_PATH == config.default_db_path()
    finally:
        importlib.reload(config)


def test_relative_env_db_path_still_resolves_absolute(monkeypatch):
    """Root cause: this repo's own .env ships DB_PATH=data/walkforward.db --
    relative. Before this fix, os.getenv("DB_PATH", ...) returned that
    string verbatim in every module, so DB_PATH only worked when cwd
    happened to be the repo root at process launch. Reproduces .env's own
    relative value directly (not just testing resolve_db_path() in
    isolation) so a regression that re-introduces cwd-dependence is caught."""
    monkeypatch.setenv("DB_PATH", "data/walkforward.db")
    importlib.reload(config)
    try:
        assert pathlib.Path(config.DB_PATH).is_absolute()
        assert config.DB_PATH == str(REPO_ROOT / "data" / "walkforward.db")
    finally:
        importlib.reload(config)


def test_centralized_modules_resolve_to_config_db_path_by_default(monkeypatch):
    """Spot-check across the three previously-divergent categories: the
    two reload-dependent modules (app.py, data/db.py) that keep their own
    os.getenv() call, and a sample of the modules that now import DB_PATH
    directly -- all must agree with config.DB_PATH when DB_PATH is unset."""
    from data import db as data_db
    import paper_trade
    import scheduler.scanner as scanner
    import screener.brpt_filter as brpt_filter

    monkeypatch.delenv("DB_PATH", raising=False)
    importlib.reload(config)
    try:
        importlib.reload(data_db)
        assert data_db.DB_PATH == config.DB_PATH

        importlib.reload(paper_trade)
        assert paper_trade.DB_PATH == config.DB_PATH

        importlib.reload(scanner)
        assert scanner.DB_PATH == config.DB_PATH

        importlib.reload(brpt_filter)
        assert brpt_filter._DB_PATH == config.DB_PATH
    finally:
        importlib.reload(config)
        importlib.reload(data_db)
        importlib.reload(paper_trade)
        importlib.reload(scanner)
        importlib.reload(brpt_filter)
