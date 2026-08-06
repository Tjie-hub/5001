"""Tests for engine/platform_info.py -- the discovery layer behind
/api/v1/version, /api/v1/capabilities, /api/v1/resources (Production
Engine Phase 2, Workstream 2D). Pure aggregation over engine.config_info
(2B-3, unchanged) and routes.v1.openapi._PATHS (read, never mutated).
"""
from engine.platform_info import get_capabilities, get_resource_catalog, get_version_info


class TestGetVersionInfo:
    def test_reflects_config_summary_release_fields(self, monkeypatch):
        import engine.config_info as config_info_mod
        monkeypatch.setattr(
            config_info_mod, "get_config_summary",
            lambda: {"version": "1.2.3", "release_source": "release",
                     "git_sha": "abc1234", "built_at": "2026-08-01T00:00:00Z",
                     "database_backend": "sqlite", "timezone": "Asia/Jakarta",
                     "logging_level": "INFO"},
        )

        data = get_version_info()
        assert data["release_version"] == "1.2.3"
        assert data["release_source"] == "release"
        assert data["git_sha"] == "abc1234"
        assert data["built_at"] == "2026-08-01T00:00:00Z"

    def test_includes_api_version_and_openapi_url(self):
        data = get_version_info()
        assert data["api_version"] == "v1"
        assert data["openapi_url"] == "/api/v1/openapi.json"

    def test_working_tree_release_has_no_git_sha_or_built_at_keys(self, monkeypatch):
        import engine.config_info as config_info_mod
        monkeypatch.setattr(
            config_info_mod, "get_config_summary",
            lambda: {"version": "dev-abc123", "release_source": "working-tree",
                     "database_backend": "sqlite", "timezone": "Asia/Jakarta",
                     "logging_level": "INFO"},
        )
        data = get_version_info()
        assert "git_sha" not in data
        assert "built_at" not in data


class TestGetCapabilities:
    def test_reflects_runtime_config_flags(self, monkeypatch):
        import engine.config_info as config_info_mod
        monkeypatch.setattr(
            config_info_mod, "get_runtime_config",
            lambda: {"auth_mode": "enforce", "edge_score_mode": "shadow",
                     "sectors_app_mode": "off", "agent_firm_enabled": True,
                     "agent_firm_enforce": False, "agent_firm_governor_enabled": True},
        )

        data = get_capabilities()
        assert data["auth_mode"] == "enforce"
        assert data["agent_firm_enabled"] is True

    def test_includes_resource_group_names(self):
        data = get_capabilities()
        assert "resource_groups" in data
        assert isinstance(data["resource_groups"], list)
        assert "scheduler" in data["resource_groups"]


class TestGetResourceCatalog:
    def test_groups_paths_by_top_level_segment(self, monkeypatch):
        import routes.v1.openapi as openapi_mod
        monkeypatch.setattr(openapi_mod, "_PATHS", {
            "/api/v1/scheduler": {"get": {}},
            "/api/v1/scheduler/jobs": {"get": {}},
            "/api/v1/watchlists/current": {"get": {}},
        })

        catalog = get_resource_catalog()
        by_name = {g["name"]: g for g in catalog}
        assert set(by_name) == {"scheduler", "watchlists"}
        scheduler_paths = {e["path"] for e in by_name["scheduler"]["endpoints"]}
        assert scheduler_paths == {"/api/v1/scheduler", "/api/v1/scheduler/jobs"}

    def test_endpoint_entries_include_methods(self, monkeypatch):
        import routes.v1.openapi as openapi_mod
        monkeypatch.setattr(openapi_mod, "_PATHS", {
            "/api/v1/scheduler": {"get": {}},
        })
        catalog = get_resource_catalog()
        endpoint = catalog[0]["endpoints"][0]
        assert endpoint["methods"] == ["GET"]

    def test_real_paths_produce_a_nonempty_catalog(self):
        catalog = get_resource_catalog()
        names = {g["name"] for g in catalog}
        assert "scheduler" in names
        assert "watchlists" in names
        assert "candidates" in names
