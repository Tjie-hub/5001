"""
config.py — Central configuration module.
Reads .env once and exports all env-backed settings.
All modules should import from here instead of calling os.getenv directly.

Note: app.py and scheduler.py retain their own os.getenv() calls for test-reload
compatibility (importlib.reload picks up monkeypatched env vars at reload time).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

_BASE = Path(__file__).parent
load_dotenv(_BASE / ".env")

DB_PATH = os.getenv("DB_PATH", str(_BASE / "data" / "walkforward.db"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/telegram/updates")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "")
