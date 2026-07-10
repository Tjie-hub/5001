"""Authorization middleware (security hardening Phases 1-2).

One before_request hook enforces security.route_policy for every request.
Fail-closed: unknown rules require admin; unknown AUTH_MODE == enforce.
AUTH_MODE=off short-circuits after credential resolution, so behavior is
byte-identical to the pre-hardening app until the operator opts in.

A companion after_request hook writes the audit trail for successful
state-changing requests on protected routes (hardening Phase 6).
"""
import logging
from flask import g, jsonify, request, session

from security import auth
from security.route_policy import required_level

log = logging.getLogger("security")


def _extract_token():
    hdr = request.headers.get("Authorization", "")
    if hdr.startswith("Bearer "):
        return hdr[7:].strip()
    if request.headers.get("X-API-Key"):
        return request.headers["X-API-Key"].strip()
    if request.args.get("api_key"):
        return request.args["api_key"].strip()
    return session.get("api_token")


def _audit_action(rule: str, required: str) -> str:
    if rule.endswith("/config") or "premover_mode" in rule:
        return "config_change"
    if required == auth.ADMIN:
        return "admin_action"
    return "operational_action"


def init_security(app):
    @app.before_request
    def _authorize():
        token = _extract_token()
        role = auth.resolve_role(token)
        g.auth_role = role
        g.auth_fp = auth.token_fingerprint(token)
        mode = auth.auth_mode()
        g.auth_mode = mode

        rule = request.url_rule.rule if request.url_rule else None
        if rule is None:            # no matching route -> Flask 404s, nothing to protect
            return None
        required = required_level(rule, request.method)
        g.auth_required = required
        if auth.has_access(role, required):
            return None
        if mode == "off":
            return None
        # denial path: audit it, block only in enforce
        from security.audit_trail import record_audit_event
        record_audit_event(
            "auth_failure", actor_role=role, actor_fingerprint=g.auth_fp,
            resource=rule, method=request.method,
            outcome="blocked" if mode == "enforce" else "shadow_allowed",
            ip=request.remote_addr,
            detail=f"required={required}",
        )
        if mode == "shadow":
            log.warning("shadow-auth: %s %s would be denied (role=%s required=%s)",
                        request.method, rule, role, required)
            return None
        status = 401 if role is None else 403
        return jsonify({"error": "unauthorized" if status == 401 else "forbidden",
                        "required": required}), status

    @app.after_request
    def _audit_mutations(response):
        rule = request.url_rule.rule if request.url_rule else None
        required = g.get("auth_required")
        if (rule is not None
                and g.get("auth_mode", "off") != "off"
                and required in (auth.OPERATOR, auth.ADMIN)
                and request.method in ("POST", "PUT", "DELETE")
                and response.status_code < 400):
            from security.audit_trail import record_audit_event
            record_audit_event(
                _audit_action(rule, required),
                actor_role=g.get("auth_role"), actor_fingerprint=g.get("auth_fp"),
                resource=rule, method=request.method,
                outcome=f"http_{response.status_code}",
                ip=request.remote_addr,
            )
        return response
