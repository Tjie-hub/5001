"""Agent firm configuration via environment variables.

All settings have sensible defaults. The firm is OFF by default to ensure
Phase 1 production deploy has zero behavioral impact.
"""

import logging
import os
from pathlib import Path

_log = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


FIRM_ENABLED = _env_bool("AGENT_FIRM_ENABLED", False)
FIRM_ENFORCE = _env_bool("AGENT_FIRM_ENFORCE", False)

DAILY_SPEND_CAP_USD = float(os.getenv("AGENT_FIRM_DAILY_CAP", "5.0"))
KILL_SWITCH_FILE = Path(os.getenv("AGENT_FIRM_KILL_FILE", "/tmp/agent_firm.disable"))

MODEL_ID = os.getenv("AGENT_FIRM_MODEL", "glm-5.2")

ZAI_API_KEY = os.getenv("ZAI_API_KEY", "")
ZAI_BASE_URL = os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4")
if not ZAI_API_KEY and os.getenv("DEEPSEEK_API_KEY"):
    _log.warning("DEEPSEEK_API_KEY is deprecated — rename to ZAI_API_KEY")
    ZAI_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
if not os.getenv("ZAI_BASE_URL") and os.getenv("DEEPSEEK_BASE_URL"):
    _log.warning("DEEPSEEK_BASE_URL is deprecated — rename to ZAI_BASE_URL")
    ZAI_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", ZAI_BASE_URL)

PRICE_INPUT_PER_M = float(os.getenv("AGENT_FIRM_PRICE_IN", "0.435"))
PRICE_OUTPUT_PER_M = float(os.getenv("AGENT_FIRM_PRICE_OUT", "0.870"))

PER_AGENT_TIMEOUT_S = float(os.getenv("AGENT_FIRM_AGENT_TIMEOUT", "75"))

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_MAX_RESULTS = int(os.getenv("AGENT_FIRM_TAVILY_MAX", "5"))

# --- Provider routing (Firm LLM Provider Abstraction, 2026-07-08) ----------

PROVIDER_MODE = os.getenv("AGENT_FIRM_PROVIDER", "zai")
PROVIDER_ORDER = [
    p.strip() for p in os.getenv("AGENT_FIRM_PROVIDER_ORDER", "claude,zai").split(",")
    if p.strip()
]

CLAUDE_MODEL = os.getenv("AGENT_FIRM_CLAUDE_MODEL", "sonnet")
CLAUDE_MAX_CONCURRENT = int(os.getenv("AGENT_FIRM_CLAUDE_MAX_CONCURRENT", "4"))
CLAUDE_MAX_CALLS_PER_DAY = int(os.getenv("AGENT_FIRM_CLAUDE_MAX_CALLS_PER_DAY", "200"))

CIRCUIT_FAILURES = int(os.getenv("AGENT_FIRM_CIRCUIT_FAILURES", "3"))
CIRCUIT_COOLDOWN_S = float(os.getenv("AGENT_FIRM_CIRCUIT_COOLDOWN", "30"))

CONNECTION_TIMEOUT_S = float(os.getenv("AGENT_FIRM_CONNECTION_TIMEOUT", "10"))
READ_TIMEOUT_S = float(os.getenv("AGENT_FIRM_READ_TIMEOUT", "60"))
OVERALL_TIMEOUT_S = float(os.getenv("AGENT_FIRM_OVERALL_TIMEOUT", "75"))
CLAUDE_CONNECTION_TIMEOUT_S = os.getenv("AGENT_FIRM_CLAUDE_CONNECTION_TIMEOUT") or None
CLAUDE_READ_TIMEOUT_S = os.getenv("AGENT_FIRM_CLAUDE_READ_TIMEOUT") or None
CLAUDE_OVERALL_TIMEOUT_S = os.getenv("AGENT_FIRM_CLAUDE_OVERALL_TIMEOUT") or None


_runtime: dict | None = None


def set_mode(enabled: bool, enforce: bool) -> None:
    global _runtime
    _runtime = {"enabled": enabled, "enforce": enforce}


def get_enforce() -> bool:
    return _runtime["enforce"] if _runtime is not None else FIRM_ENFORCE


def get_enabled() -> bool:
    """Runtime-aware enabled flag (mirrors get_enforce); ignores the kill switch."""
    return _runtime["enabled"] if _runtime is not None else FIRM_ENABLED


def is_active() -> bool:
    enabled = _runtime["enabled"] if _runtime is not None else FIRM_ENABLED
    if not enabled:
        return False
    if KILL_SWITCH_FILE.exists():
        return False
    return True
