"""
config.py — Central configuration module.
Reads .env once and exports all env-backed settings.
All modules should import from here instead of calling os.getenv directly.

Note: app.py and scheduler.py retain their own os.getenv() calls for test-reload
compatibility (importlib.reload picks up monkeypatched env vars at reload time).
"""
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

_BASE = Path(__file__).parent
load_dotenv(_BASE / ".env")

# Release manifest written by scripts/release.sh; absent in a working tree.
# Module-level so tests can point it elsewhere.
_RELEASE_MANIFEST = _BASE / "release.json"

DB_PATH = os.getenv("DB_PATH", str(_BASE / "data" / "walkforward.db"))
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


class ConfigError(RuntimeError):
    """Mandatory configuration is missing or invalid — refuse to start."""


def validate_config() -> None:
    """Fail fast at startup when mandatory configuration is missing
    (audit §5 / hardening Phase 5). Reads the environment fresh so tests can
    monkeypatch. Raises ConfigError listing every problem at once."""
    problems: list[str] = []

    db_path = os.getenv("DB_PATH", DB_PATH)
    if not Path(db_path).exists():
        problems.append(f"DB_PATH does not exist: {db_path}")

    # Telegram is the alerting safety net — a prod process without it fails
    # silently, which is exactly what this phase exists to prevent.
    if not os.getenv("TELEGRAM_TOKEN", TELEGRAM_TOKEN):
        problems.append("TELEGRAM_TOKEN is not set")
    if not os.getenv("TELEGRAM_CHAT_ID", TELEGRAM_CHAT_ID):
        problems.append("TELEGRAM_CHAT_ID is not set")

    if os.getenv("AGENT_FIRM_ENABLED", "").strip().lower() in ("1", "true", "yes"):
        mode = os.getenv("AGENT_FIRM_PROVIDER", "zai").strip().lower()
        order = ([p.strip() for p in
                  os.getenv("AGENT_FIRM_PROVIDER_ORDER", "claude,zai").split(",")]
                 if mode == "auto" else [mode])
        if "zai" in order and not (os.getenv("ZAI_API_KEY")
                                   or os.getenv("DEEPSEEK_API_KEY")):
            problems.append("agent firm enabled with zai provider but no "
                            "ZAI_API_KEY (or legacy DEEPSEEK_API_KEY) set")
        # provider compatibility: routing to claude needs the CLI on PATH
        if "claude" in order and shutil.which("claude") is None:
            problems.append("provider order includes claude but the claude CLI "
                            "is not on PATH")

    # --- security hardening: auth configuration ---
    auth_mode = os.getenv("AUTH_MODE", "off").strip().lower()
    if auth_mode not in ("off", "shadow", "enforce"):
        problems.append(f"AUTH_MODE invalid: {auth_mode!r} (off|shadow|enforce)")
    token_vars = ("AUTH_TOKEN_ADMIN", "AUTH_TOKEN_OPERATOR",
                  "AUTH_TOKEN_VIEWER", "AUTH_TOKEN_SCHEDULER")
    tokens = [t.strip() for v in token_vars
              for t in os.getenv(v, "").split(",") if t.strip()]
    if auth_mode == "enforce" and not tokens:
        problems.append("AUTH_MODE=enforce but no AUTH_TOKEN_* configured "
                        "(would lock everyone out of protected routes)")
    if any(len(t) < 16 for t in tokens):
        problems.append("an AUTH_TOKEN_* value is shorter than 16 chars")

    # --- DB compatibility: a non-empty DB must contain the core tables.
    # A brand-new DB (no tables) is allowed: init_runtime bootstraps it
    # right after validation.
    if Path(db_path).exists():
        try:
            import sqlite3 as _sq
            with _sq.connect(db_path) as _c:
                have = {r[0] for r in _c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
            if have:
                for tbl in ("scheduled_signals", "paper_trades"):
                    if tbl not in have:
                        problems.append(f"DB missing required table: {tbl} "
                                        f"(is DB_PATH pointing at the right file?)")
        except Exception as e:
            problems.append(f"DB compatibility check failed: {e}")

    # --- secret file permissions (fail closed on group/world access) ---
    for name in (".env", ".stockbit_token"):
        p = _BASE / name
        if p.exists() and (p.stat().st_mode & 0o077):
            problems.append(f"{name} is group/world accessible — chmod 600 it")

    # --- release manifest (present only when running from a built release) ---
    if _RELEASE_MANIFEST.exists():
        try:
            import json as _json
            meta = _json.loads(_RELEASE_MANIFEST.read_text())
            missing = [k for k in ("version", "git_sha", "built_at")
                       if k not in meta]
            if missing:
                problems.append(f"release.json missing keys: {', '.join(missing)}")
        except Exception as e:
            problems.append(f"release.json unreadable: {e}")

    if problems:
        raise ConfigError("startup config validation failed:\n  - "
                          + "\n  - ".join(problems))
