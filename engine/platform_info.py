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


def get_runtime_status() -> dict:
    """Status-footer read model (Phase 9 B5 blocker U-2: "backend-owned").

    Every field is derived from existing production state — nothing hardcoded:

      * environment — utils.release's own source distinction
        ("working-tree" -> dev, "release" -> release); never a fabricated
        env name.
      * snapshot    — the latest watchlist_snapshot row (date + strategy),
        i.e. the most recent production snapshot actually written by the
        premarket/EOD trade-plan jobs.
      * freshness   — latest bar/flow dates the pipelines have stored.
      * components  — engine.health.get_health()'s component states
        (database, scheduler), the same source /api/v1/health serves.
    """
    import sqlite3
    from data.db import connect as db_connect

    import config
    from engine.health import get_health

    release = config_info_mod.get_config_summary()
    source = (release.get("release_source") or "working-tree")
    environment = "release" if source == "release" else "dev"

    snapshot = None
    freshness = {"ohlcv": None, "stockbit_flow": None}
    conn = db_connect(config.DB_PATH, read_only=True)
    try:
        row = conn.execute(
            "SELECT date, strategy FROM watchlist_snapshot "
            "ORDER BY date DESC LIMIT 1"
        ).fetchone()
        if row:
            snapshot = {"date": row[0], "strategy": row[1]}
        row = conn.execute("SELECT MAX(date) FROM ohlcv").fetchone()
        freshness["ohlcv"] = row[0] if row else None
        row = conn.execute("SELECT MAX(trade_date) FROM stockbit_flow").fetchone()
        freshness["stockbit_flow"] = row[0] if row else None
    except sqlite3.Error:
        pass
    finally:
        conn.close()

    health = get_health(config.DB_PATH)

    return {
        "environment": environment,
        "release_source": source,
        "version": release.get("version"),
        "timezone": "WIB (UTC+7)",
        "snapshot": snapshot,
        "freshness": freshness,
        "components": health.get("components", {}),
        "overall": health.get("overall"),
    }
