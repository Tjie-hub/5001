"""Platform / integration APIs (Production Engine Phase 2, Workstream 2D).
See docs/superpowers/specs/2026-08-06-2d-integration-apis-design.md.

GET /api/v1/ (root) already exists from Workstream A Task 1 and is
untouched here. Thin controllers over engine.platform_info's pure
aggregation functions -- no business data, no new data source.
"""
import engine.platform_info as platform_info_mod
from routes.v1 import api_v1_bp
from routes.v1.envelope import ok


@api_v1_bp.route("/version", methods=["GET"])
def platform_version():
    return ok(platform_info_mod.get_version_info())


@api_v1_bp.route("/capabilities", methods=["GET"])
def platform_capabilities():
    return ok(platform_info_mod.get_capabilities())


@api_v1_bp.route("/resources", methods=["GET"])
def platform_resources():
    return ok({"resources": platform_info_mod.get_resource_catalog()})


@api_v1_bp.route("/runtime", methods=["GET"])
def platform_runtime():
    """Status-footer read model (environment, snapshot, freshness, health)."""
    return ok(platform_info_mod.get_runtime_status())
