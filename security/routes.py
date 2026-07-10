"""Session login endpoints so a browser can use the UI under AUTH_MODE=enforce
without frontend changes (backend-only migration path, hardening Phase 1)."""
from flask import Blueprint, g, jsonify, request, session

from security import auth

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    token = (request.get_json(silent=True) or {}).get("token", "")
    role = auth.resolve_role(token)
    if role is None:
        from security.audit_trail import record_audit_event
        record_audit_event("auth_failure", resource="/auth/login", method="POST",
                           outcome="blocked", ip=request.remote_addr,
                           detail="invalid login token")
        return jsonify({"error": "invalid token"}), 401
    session["api_token"] = token
    return jsonify({"ok": True, "role": role})


@auth_bp.route("/auth/logout", methods=["POST"])
def logout():
    session.pop("api_token", None)
    return jsonify({"ok": True})


@auth_bp.route("/auth/whoami", methods=["GET"])
def whoami():
    return jsonify({"mode": auth.auth_mode(),
                    "role": g.get("auth_role"),
                    "fingerprint": g.get("auth_fp")})
