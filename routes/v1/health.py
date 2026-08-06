"""Aggregated operational health (Production Engine Phase 2, Workstream 2B
Task 2B-4). See docs/superpowers/specs/2026-08-06-2b4-health-api-design.md.

Always 200 -- the API call itself succeeded; health state lives in the
body (data.overall / data.components), matching app.py's existing /health
route's own convention.
"""
import config
from engine import health as health_mod
from routes.v1 import api_v1_bp
from routes.v1.envelope import ok


@api_v1_bp.route("/health", methods=["GET"])
def health():
    return ok(health_mod.get_health(config.DB_PATH))
