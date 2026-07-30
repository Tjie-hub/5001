"""
config.py — Central configuration module.
Reads .env once and exports all env-backed settings.
All modules should import from here instead of calling os.getenv directly.

Note (H-7, P0.E2.S2.T1): app.py and data/db.py retain their own
os.getenv("DB_PATH", default_db_path()) calls for test-reload compatibility
(importlib.reload picks up monkeypatched env vars at reload time without
needing `config` itself reloaded first) -- verified against actual test
usage, not assumed; the old version of this note also named "scheduler.py",
but no test reload()s any scheduler/ submodule standalone, so that package
now imports DB_PATH from here like everything else.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

_BASE = Path(__file__).parent
load_dotenv(_BASE / ".env")


def default_db_path() -> str:
    """Canonical default for DB_PATH when the env var is unset (H-7).

    Pure path math, no env read — the single source of truth every module's
    own ``os.getenv("DB_PATH", default_db_path())`` falls back to. Most
    modules should just ``from config import DB_PATH`` instead; this exists
    for the handful (``app.py``, ``data/db.py``) that must keep their own
    ``os.getenv`` call for importlib.reload-based test isolation (env var
    changes take effect without needing `config` itself reloaded first).
    """
    return str(_BASE / "data" / "walkforward.db")


def resolve_db_path(raw: str) -> str:
    """Make any DB_PATH value (env var, .env, or the default) absolute (H-7).

    This repo's own .env ships ``DB_PATH=data/walkforward.db`` — relative —
    so every module's raw ``os.getenv("DB_PATH", ...)`` was resolving to a
    relative path in the common case (env var set), not just in the unset
    fallback case. A relative DB_PATH only works if the process's cwd
    happens to be the repo root at launch; resolving it here, once, removes
    that dependency everywhere it's consumed.
    """
    p = Path(raw)
    if not p.is_absolute():
        p = _BASE / p
    return str(p)


DB_PATH = resolve_db_path(os.getenv("DB_PATH", default_db_path()))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/telegram/updates")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "")

# Edge-score pipeline mode: off | shadow | enforce (env EDGE_SCORE_MODE).
#   off     — system behaves exactly as before (default).
#   shadow  — deterministic edge vetoes run and are logged; no trade impact.
#   enforce — only survivors reach the firm; size_mult = round(edge, 2).
EDGE_SCORE_MODE = os.getenv("EDGE_SCORE_MODE", "off").strip().lower()


def edge_mode() -> str:
    """Current edge-score mode (re-read from env each call)."""
    return os.getenv("EDGE_SCORE_MODE", EDGE_SCORE_MODE).strip().lower()
