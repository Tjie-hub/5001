"""Read-only configuration APIs (Production Engine Phase 2, Workstream 2B
Task 2B-3). See docs/superpowers/specs/2026-08-06-2b3-config-api-design.md.

Thin controllers over engine.config_info's two allowlisted aggregation
functions -- no env reads here, no storage access here.
"""
from engine import config_info
from routes.v1 import api_v1_bp
from routes.v1.envelope import ok


@api_v1_bp.route("/config", methods=["GET"])
def config_summary():
    return ok(config_info.get_config_summary())


@api_v1_bp.route("/config/runtime", methods=["GET"])
def config_runtime():
    return ok(config_info.get_runtime_config())
