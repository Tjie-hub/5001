"""Token authentication + role model (security hardening Phases 1-2).

AUTH_MODE (env):
  off     — no checks; legacy behavior (default, backward compatible)
  shadow  — credentials evaluated and audit-logged; requests never blocked
  enforce — unauthenticated/unauthorized requests rejected (fail closed)
Unknown values fail closed to `enforce`; validate_config rejects them at boot.

Tokens live only in env vars (comma-separated lists, one var per role):
  AUTH_TOKEN_ADMIN, AUTH_TOKEN_OPERATOR, AUTH_TOKEN_VIEWER, AUTH_TOKEN_SCHEDULER
Comparisons are constant-time; logs only ever see a sha256[:12] fingerprint.
"""
import hashlib
import hmac
import os

PUBLIC = "public"
VIEWER = "viewer"
OPERATOR = "operator"
SCHEDULER = "scheduler"
ADMIN = "admin"

ROLE_RANK = {VIEWER: 1, SCHEDULER: 2, OPERATOR: 2, ADMIN: 3}

_ROLE_ENV = {
    ADMIN: "AUTH_TOKEN_ADMIN",
    OPERATOR: "AUTH_TOKEN_OPERATOR",
    VIEWER: "AUTH_TOKEN_VIEWER",
    SCHEDULER: "AUTH_TOKEN_SCHEDULER",
}

VALID_MODES = ("off", "shadow", "enforce")


def auth_mode() -> str:
    mode = os.getenv("AUTH_MODE", "off").strip().lower()
    return mode if mode in VALID_MODES else "enforce"


def configured_tokens() -> dict:
    """token -> role, read fresh from env each call (tests monkeypatch)."""
    out = {}
    for role, var in _ROLE_ENV.items():
        for tok in (t.strip() for t in os.getenv(var, "").split(",")):
            if tok:
                out[tok] = role
    return out


def resolve_role(token):
    if not token:
        return None
    match = None
    # scan every candidate so lookup time doesn't depend on which token matched
    for candidate, role in configured_tokens().items():
        if hmac.compare_digest(candidate, token):
            match = role
    return match


def token_fingerprint(token) -> str:
    if not token:
        return "-"
    return hashlib.sha256(token.encode()).hexdigest()[:12]


def has_access(role, required) -> bool:
    if required == PUBLIC:
        return True
    if role is None:
        return False
    return ROLE_RANK.get(role, 0) >= ROLE_RANK.get(required, 99)
