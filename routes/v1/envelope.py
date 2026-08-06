"""Standard response envelope + error handling for the API v1 layer.

Every /api/v1/* response -- success or error, controller-produced or a
framework-level 404/405/500 -- shares one JSON shape:

    success: {"ok": true,  "data": {...}, "meta": {...}}
    error:   {"ok": false, "error": {"code", "message", "details"}, "meta": {...}}

`meta` always carries `api_version`, `request_id` (reused from app.py's
existing `g.correlation_id` correlation-id assignment when present, else a
freshly generated uuid4 -- see app.py's `_assign_correlation_id`), and a UTC
ISO-8601 `timestamp`.

Note: this does NOT cover the 401/403 responses produced by
security/middleware.py's app-wide auth gate -- that gate runs in
`before_request`, before any blueprint view or error handler is reached, and
is shared, pre-existing infrastructure for every blueprint in this app, not
something Workstream A owns or should reshape.
"""
import logging
import uuid
from datetime import datetime, timezone

from flask import g, jsonify
from werkzeug.exceptions import HTTPException

API_VERSION = "v1"

_HTTP_STATUS_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
}


class ApiError(Exception):
    """Raise from a v1 controller for an expected failure; the blueprint's
    error handler (see register_error_handlers) turns it into the standard
    error envelope at the given HTTP status."""

    def __init__(self, code, http_status, message, details=None):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.message = message
        self.details = details or {}


def _meta() -> dict:
    request_id = g.get("correlation_id") or str(uuid.uuid4())
    return {
        "api_version": API_VERSION,
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def ok(data, status: int = 200):
    resp = jsonify({"ok": True, "data": data, "meta": _meta()})
    resp.status_code = status
    return resp


def err(code, message, details=None, status: int = 500):
    resp = jsonify({
        "ok": False,
        "error": {"code": code, "message": message, "details": details or {}},
        "meta": _meta(),
    })
    resp.status_code = status
    return resp


def register_error_handlers(bp) -> None:
    """Attach ApiError + generic HTTPException/500 handlers to a v1
    blueprint so every response under it shares the envelope shape, even
    ones no controller ever touches (bad route, wrong method, uncaught bug).

    Flask can only attribute an error to a blueprint once a route inside it
    has actually matched (e.g. a controller calling `abort(400)`); a 404 for
    a path that matches no route at all, or a 405 for a right-path/
    wrong-method request, both fail during routing itself, before Flask
    knows which blueprint "would" have owned it. Those two are handled by a
    separate app-level fallback, registered once this blueprint is attached
    to an app (via `record_once`) and scoped to this blueprint's own
    url_prefix so no other route's 404/405 behavior changes.
    """

    @bp.errorhandler(ApiError)
    def _handle_api_error(e: ApiError):
        return err(e.code, e.message, details=e.details, status=e.http_status)

    @bp.errorhandler(HTTPException)
    def _handle_http_exception(e: HTTPException):
        code = _HTTP_STATUS_CODES.get(e.code, "HTTP_ERROR")
        return err(code, e.description or e.name, status=e.code)

    @bp.errorhandler(Exception)
    def _handle_uncaught(e: Exception):
        logging.getLogger("routes.v1").exception("unhandled error in API v1")
        return err("INTERNAL_ERROR", "internal server error", status=500)

    def _register_prefix_scoped_routing_fallback(state):
        prefix = state.url_prefix or ""

        def _fallback(code, default_code_name):
            def _handler(e: HTTPException):
                from flask import request
                if not request.path.startswith(prefix):
                    return e  # not ours -- preserve default Flask behavior
                return err(_HTTP_STATUS_CODES.get(e.code, default_code_name),
                           e.description or e.name, status=e.code)
            return _handler

        state.app.register_error_handler(404, _fallback(404, "NOT_FOUND"))
        state.app.register_error_handler(405, _fallback(405, "METHOD_NOT_ALLOWED"))

    bp.record_once(_register_prefix_scoped_routing_fallback)
