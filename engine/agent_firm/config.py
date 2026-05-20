"""Agent firm configuration via environment variables.

All settings have sensible defaults. The firm is OFF by default to ensure
Phase 1 production deploy has zero behavioral impact.
"""

import os
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


FIRM_ENABLED = _env_bool("AGENT_FIRM_ENABLED", False)
FIRM_ENFORCE = _env_bool("AGENT_FIRM_ENFORCE", False)

DAILY_SPEND_CAP_USD = float(os.getenv("AGENT_FIRM_DAILY_CAP", "5.0"))
KILL_SWITCH_FILE = Path(os.getenv("AGENT_FIRM_KILL_FILE", "/tmp/agent_firm.disable"))

MODEL_ID = os.getenv("AGENT_FIRM_MODEL", "deepseek-v4-pro")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

PRICE_INPUT_PER_M = float(os.getenv("AGENT_FIRM_PRICE_IN", "0.435"))
PRICE_OUTPUT_PER_M = float(os.getenv("AGENT_FIRM_PRICE_OUT", "0.870"))

PER_AGENT_TIMEOUT_S = float(os.getenv("AGENT_FIRM_AGENT_TIMEOUT", "75"))


def is_active() -> bool:
    if not FIRM_ENABLED:
        return False
    if KILL_SWITCH_FILE.exists():
        return False
    return True
