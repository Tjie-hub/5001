"""API v1 -- Production Engine Phase 2, Workstream A (2026-08-06).

See docs/superpowers/specs/2026-08-06-api-v1-foundation-design.md for the
approved design. Deliberately minimal: a versioned envelope + error-handling
scaffold proven against the Production Status Registry endpoints, not the
full generic toolkit (pagination/filtering/etc.) described in the original
Phase 2 brief -- those are deferred until a real consumer needs them.
"""
from flask import Blueprint

from routes.v1.envelope import ok, register_error_handlers

api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")
register_error_handlers(api_v1_bp)


@api_v1_bp.route("/", methods=["GET"])
def api_root():
    return ok({"name": "idx-walkforward-5001 API", "version": "v1", "status": "ok"})


from routes.v1 import openapi  # noqa: E402,F401 -- registers /openapi.json on api_v1_bp
from routes.v1 import status  # noqa: E402,F401 -- registers /status/* on api_v1_bp
from routes.v1 import scheduler  # noqa: E402,F401 -- registers /scheduler* on api_v1_bp
from routes.v1 import metrics  # noqa: E402,F401 -- registers /metrics* on api_v1_bp
from routes.v1 import config  # noqa: E402,F401 -- registers /config* on api_v1_bp
from routes.v1 import health  # noqa: E402,F401 -- registers /health on api_v1_bp
from routes.v1 import watchlists  # noqa: E402,F401 -- registers /watchlists* on api_v1_bp
from routes.v1 import snapshots  # noqa: E402,F401 -- registers /snapshots* on api_v1_bp
from routes.v1 import reports  # noqa: E402,F401 -- registers /reports* on api_v1_bp
from routes.v1 import candidates  # noqa: E402,F401 -- registers /candidates* on api_v1_bp
