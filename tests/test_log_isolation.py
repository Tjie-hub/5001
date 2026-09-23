"""The suite must never write production log files (see tests/conftest.py for the incident)."""
import logging
from pathlib import Path

import auto_token  # module-level import, like every test that exercises it

REPO = Path(__file__).resolve().parents[1]


def test_auto_token_log_is_redirected():
    assert REPO not in Path(auto_token.LOG_FILE).resolve().parents


def test_app_import_does_not_log_into_repo_logs():
    import app  # noqa: F401  (setup_logging() runs at import)
    files = [Path(h.baseFilename).resolve() for h in logging.getLogger().handlers
             if hasattr(h, "baseFilename")]
    assert all(REPO not in f.parents for f in files), files
