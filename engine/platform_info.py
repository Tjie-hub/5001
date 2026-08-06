"""Platform discovery layer (Production Engine Phase 2, Workstream 2D).
Backs /api/v1/version, /api/v1/capabilities, /api/v1/resources. See
docs/superpowers/specs/2026-08-06-2d-integration-apis-design.md.

Pure aggregation -- no new data source. Version/capability fields are
engine.config_info (2B-3) unchanged; the resource catalog is read from
routes.v1.openapi's own _PATHS dict (already the single source of truth
for every registered v1 endpoint), never a second hardcoded list.
"""
import engine.config_info as config_info_mod

API_VERSION = "v1"
OPENAPI_URL = "/api/v1/openapi.json"


def get_version_info() -> dict:
    summary = config_info_mod.get_config_summary()
    data = {
        "api_version": API_VERSION,
        "release_version": summary.get("version"),
        "release_source": summary.get("release_source"),
        "openapi_url": OPENAPI_URL,
    }
    if "git_sha" in summary:
        data["git_sha"] = summary["git_sha"]
    if "built_at" in summary:
        data["built_at"] = summary["built_at"]
    return data


def get_resource_catalog() -> list[dict]:
    import routes.v1.openapi as openapi_mod

    groups: dict[str, list[dict]] = {}
    for path, methods in openapi_mod._PATHS.items():
        segment = path.removeprefix("/api/v1/").split("/")[0] or "root"
        groups.setdefault(segment, []).append({
            "path": path,
            "methods": sorted(m.upper() for m in methods),
        })

    return [
        {"name": name, "endpoints": sorted(endpoints, key=lambda e: e["path"])}
        for name, endpoints in sorted(groups.items())
    ]


def get_capabilities() -> dict:
    data = dict(config_info_mod.get_runtime_config())
    data["resource_groups"] = sorted(g["name"] for g in get_resource_catalog())
    return data
