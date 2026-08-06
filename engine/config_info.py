"""Read-only, allowlisted operational configuration (Production Engine Phase
2, Workstream 2B Task 2B-3). See
docs/superpowers/specs/2026-08-06-2b3-config-api-design.md for the full
field-by-field allowlist/exclusion rationale.

Deliberately an allowlist, not a redacted dump of every env var: a
blocklist/redaction approach is one missed pattern away from a leak the
next time a var is added; an allowlist can only under-expose. Every field
below is read through an existing config accessor (config.py,
security.auth, engine.agent_firm.config, utils.release, scheduler.WIB) --
this module adds no new env reads except by calling config.sectors_app_mode
(added alongside this task, itself just a getter over an existing var).
"""
import logging

import config
import scheduler
import security.auth as auth_mod
import utils.release as release_mod
from engine.agent_firm import config as firm_config


def get_config_summary() -> dict:
    """Build/release identity + static operational facts."""
    release = release_mod.release_info()
    data = {
        "version": release.get("version"),
        "release_source": release.get("source"),
        "database_backend": "sqlite",
        "timezone": str(scheduler.WIB),
        "logging_level": logging.getLevelName(logging.getLogger().getEffectiveLevel()),
    }
    if "git_sha" in release:
        data["git_sha"] = release["git_sha"]
    if "built_at" in release:
        data["built_at"] = release["built_at"]
    return data


def get_runtime_config() -> dict:
    """Mode / feature-flag surface -- off|shadow|enforce style toggles and
    the three agent-firm on/off flags, nothing more granular."""
    return {
        "auth_mode": auth_mod.auth_mode(),
        "edge_score_mode": config.edge_mode(),
        "sectors_app_mode": config.sectors_app_mode(),
        "agent_firm_enabled": firm_config.FIRM_ENABLED,
        "agent_firm_enforce": firm_config.FIRM_ENFORCE,
        "agent_firm_governor_enabled": firm_config.GOVERNOR_ENABLED,
    }
