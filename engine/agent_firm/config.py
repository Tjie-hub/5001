"""Agent firm configuration via environment variables.

All settings have sensible defaults. The firm is OFF by default to ensure
Phase 1 production deploy has zero behavioral impact.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

_log = logging.getLogger(__name__)

# Ensure .env is populated before the os.getenv() calls below run. The app's
# root config.py also calls load_dotenv(), but when this module is imported
# standalone (smoke test, CLI tool, ad-hoc script) nothing else loads .env
# first — so ZAI_API_KEY and friends read as empty and every provider call
# fails with a spurious 401. load_dotenv defaults to override=False, so
# explicitly-set env vars (CI, tests via monkeypatch, systemd Environment=)
# still win. (RCA 2026-07-13: standalone smoke run returned `degraded` with
# "token expired" purely because the key was never loaded into the process.)
#
# The path is overridable via AGENT_FIRM_ENV_PATH so tests can point at an
# empty temp file (or /dev/null) to exercise pure defaults in isolation from
# the real repo .env.
_ENV_PATH = Path(
    os.getenv("AGENT_FIRM_ENV_PATH")
    or (Path(__file__).resolve().parents[2] / ".env")
)
load_dotenv(_ENV_PATH)


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

# ZAI concurrency cap (RCA 2026-07-13): the firm fans out with unbounded
# asyncio.gather(), and ZAI has no client-side throttle — under a 50+ req/s
# burst it trips 429 code 1302 ("Rate limit reached for requests"), opening
# the circuit and contributing to spurious "all providers down" alerts.
# Mirrors CLAUDE_MAX_CONCURRENT's role for the Claude CLI semaphore.
ZAI_MAX_CONCURRENT = int(os.getenv("AGENT_FIRM_ZAI_MAX_CONCURRENT", "4"))

CIRCUIT_FAILURES = int(os.getenv("AGENT_FIRM_CIRCUIT_FAILURES", "3"))
CIRCUIT_COOLDOWN_S = float(os.getenv("AGENT_FIRM_CIRCUIT_COOLDOWN", "30"))

# --- Quota-aware routing (RCA 2026-07-10) -----------------------------------
# When a provider reports a session/usage-window limit, the Router holds it
# out of rotation until the advertised reset time (+ buffer) instead of
# rediscovering the exhaustion on every circuit-breaker cooldown.
QUOTA_HOLD_ENABLED = _env_bool("AGENT_FIRM_QUOTA_HOLD", True)
QUOTA_RESET_BUFFER_S = float(os.getenv("AGENT_FIRM_QUOTA_RESET_BUFFER", "60"))
# Hold applied when the limit message carries no parseable reset time.
QUOTA_FALLBACK_HOLD_S = float(os.getenv("AGENT_FIRM_QUOTA_FALLBACK_HOLD", "900"))
# Safety cap: never hold a provider longer than this, however far away the
# parsed reset claims to be.
QUOTA_MAX_HOLD_S = float(os.getenv("AGENT_FIRM_QUOTA_MAX_HOLD", str(6 * 3600)))

QUOTA_ALERTS_ENABLED = _env_bool("AGENT_FIRM_QUOTA_ALERTS", True)
ALERT_MIN_INTERVAL_S = float(os.getenv("AGENT_FIRM_ALERT_MIN_INTERVAL", "1800"))
# Alert escalation after this many session-limit hits without a recovery.
QUOTA_REPEAT_THRESHOLD = int(os.getenv("AGENT_FIRM_QUOTA_REPEAT_THRESHOLD", "3"))

# --- Adaptive provider governor (R-7 Tier 1, issuance-rate pacing) ---------
# Process-singleton AIMD controller (engine/agent_firm/providers/governor.py)
# that paces per-provider request ISSUE RATE -- fixes z.ai HTTP 429 code 1302
# bursts a per-tick-rebuilt token bucket couldn't prevent (state survives
# router rebuilds). Enabled by default for zai, the provider with the
# burst-limit failure mode; Claude's constraint is the subscription window
# already handled by the quota-hold settings above, so it stays un-governed
# unless added to AGENT_FIRM_GOVERNOR_PROVIDERS. Defaults mirror the tuned
# values validated by scripts/replay_governor_ab.py's A/B replay.
GOVERNOR_ENABLED = _env_bool("AGENT_FIRM_GOVERNOR_ENABLED", True)
GOVERNOR_PROVIDERS = [
    p.strip() for p in os.getenv("AGENT_FIRM_GOVERNOR_PROVIDERS", "zai").split(",")
    if p.strip()
]
GOVERNOR_RATE_MAX = float(os.getenv("AGENT_FIRM_GOVERNOR_RATE_MAX", "3.0"))
GOVERNOR_RATE_MIN = float(os.getenv("AGENT_FIRM_GOVERNOR_RATE_MIN", "0.5"))
GOVERNOR_BURST = float(os.getenv("AGENT_FIRM_GOVERNOR_BURST", "3.0"))
GOVERNOR_AI_STEP = float(os.getenv("AGENT_FIRM_GOVERNOR_AI_STEP", "0.5"))
GOVERNOR_AI_INTERVAL_S = float(os.getenv("AGENT_FIRM_GOVERNOR_AI_INTERVAL_S", "10.0"))
GOVERNOR_MD_FACTOR = float(os.getenv("AGENT_FIRM_GOVERNOR_MD_FACTOR", "0.5"))
GOVERNOR_POST_DECREASE_COOLDOWN_S = float(
    os.getenv("AGENT_FIRM_GOVERNOR_POST_DECREASE_COOLDOWN_S", "30.0"))

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
