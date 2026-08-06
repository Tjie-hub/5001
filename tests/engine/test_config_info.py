"""Tests for engine/config_info.py -- the read-only, allowlisted config
surface behind /api/v1/config and /api/v1/config/runtime (Production Engine
Phase 2, Workstream 2B Task 2B-3). See
docs/superpowers/specs/2026-08-06-2b3-config-api-design.md for the field
allowlist and exclusion rationale.
"""
import logging

from engine.config_info import get_config_summary, get_runtime_config


class TestConfigSummary:
    def test_reflects_release_info(self, monkeypatch):
        import utils.release as release_mod
        monkeypatch.setattr(release_mod, "release_info",
                             lambda: {"version": "1.2.3", "source": "release",
                                      "git_sha": "abc1234", "built_at": "2026-08-01T00:00:00Z"})

        data = get_config_summary()
        assert data["version"] == "1.2.3"
        assert data["release_source"] == "release"
        assert data["git_sha"] == "abc1234"
        assert data["built_at"] == "2026-08-01T00:00:00Z"

    def test_working_tree_release_has_no_git_sha_or_built_at_keys(self, monkeypatch):
        import utils.release as release_mod
        monkeypatch.setattr(release_mod, "release_info",
                             lambda: {"version": "dev-abc123", "source": "working-tree"})

        data = get_config_summary()
        assert data["version"] == "dev-abc123"
        assert data["release_source"] == "working-tree"
        assert "git_sha" not in data
        assert "built_at" not in data

    def test_static_facts(self):
        data = get_config_summary()
        assert data["database_backend"] == "sqlite"
        assert data["timezone"] == "Asia/Jakarta"

    def test_logging_level_reflects_effective_root_level(self):
        root = logging.getLogger()
        original = root.level
        try:
            root.setLevel(logging.WARNING)
            assert get_config_summary()["logging_level"] == "WARNING"
        finally:
            root.setLevel(original)


class TestRuntimeConfig:
    def test_reflects_auth_and_feature_flag_modes(self, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "enforce")
        monkeypatch.setenv("EDGE_SCORE_MODE", "shadow")
        monkeypatch.setenv("SECTORS_APP_MODE", "off")

        data = get_runtime_config()
        assert data["auth_mode"] == "enforce"
        assert data["edge_score_mode"] == "shadow"
        assert data["sectors_app_mode"] == "off"

    def test_reflects_agent_firm_flags(self, monkeypatch):
        import engine.agent_firm.config as firm_config
        monkeypatch.setattr(firm_config, "FIRM_ENABLED", True)
        monkeypatch.setattr(firm_config, "FIRM_ENFORCE", False)
        monkeypatch.setattr(firm_config, "GOVERNOR_ENABLED", True)

        data = get_runtime_config()
        assert data["agent_firm_enabled"] is True
        assert data["agent_firm_enforce"] is False
        assert data["agent_firm_governor_enabled"] is True

    def test_returns_exactly_the_allowlisted_keys(self):
        assert set(get_runtime_config()) == {
            "auth_mode", "edge_score_mode", "sectors_app_mode",
            "agent_firm_enabled", "agent_firm_enforce", "agent_firm_governor_enabled",
        }


class TestNoSecretsLeak:
    """The single most important guarantee this module makes: no configured
    secret value ever appears in either function's output, under any env
    state. Regression-tests the allowlist approach itself, not just one
    field at a time."""

    _SECRET_ENV = {
        "TELEGRAM_TOKEN": "sekret-telegram-token-value",
        "TELEGRAM_WEBHOOK_SECRET": "sekret-webhook-value",
        "FLASK_SECRET_KEY": "sekret-flask-key-value",
        "ZAI_API_KEY": "sekret-zai-key-value",
        "DEEPSEEK_API_KEY": "sekret-deepseek-key-value",
        "TAVILY_API_KEY": "sekret-tavily-key-value",
        "STOCKBIT_USER": "someone@example.com",
        "STOCKBIT_PASS": "sekret-stockbit-password",
        "AUTH_TOKEN_ADMIN": "sekret-admin-token-0123456789",
        "DB_PATH": "/home/someuser/private/path/to/walkforward.db",
    }

    def test_no_secret_or_private_path_values_in_summary_or_runtime(self, monkeypatch):
        for var, val in self._SECRET_ENV.items():
            monkeypatch.setenv(var, val)

        combined = repr(get_config_summary()) + repr(get_runtime_config())
        for var, val in self._SECRET_ENV.items():
            assert val not in combined, f"{var}'s value leaked into the config API output"

    def test_no_secret_field_names_present_as_keys(self):
        forbidden_keys = {
            "telegram_token", "telegram_webhook_secret", "flask_secret_key",
            "zai_api_key", "deepseek_api_key", "tavily_api_key",
            "stockbit_user", "stockbit_pass", "auth_token_admin",
            "auth_token_operator", "auth_token_viewer", "auth_token_scheduler",
            "db_path", "password", "secret", "token", "api_key", "credential",
        }
        keys = {k.lower() for k in get_config_summary()} | {k.lower() for k in get_runtime_config()}
        overlap = keys & forbidden_keys
        assert not overlap, f"forbidden-shaped key(s) present: {overlap}"
