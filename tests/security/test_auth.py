"""Tests for security.auth — token→role resolution, mode parsing, rank checks."""
from security import auth


def test_auth_mode_default_off(monkeypatch):
    monkeypatch.delenv("AUTH_MODE", raising=False)
    assert auth.auth_mode() == "off"


def test_auth_mode_values(monkeypatch):
    for v in ("off", "shadow", "enforce", " ENFORCE "):
        monkeypatch.setenv("AUTH_MODE", v)
        assert auth.auth_mode() == v.strip().lower()


def test_auth_mode_unknown_fails_closed(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "banana")
    assert auth.auth_mode() == "enforce"


def test_resolve_role_from_env(monkeypatch):
    monkeypatch.setenv("AUTH_TOKEN_ADMIN", "adm-token-0123456789")
    monkeypatch.setenv("AUTH_TOKEN_VIEWER", "view-a-0123456789, view-b-0123456789")
    assert auth.resolve_role("adm-token-0123456789") == "admin"
    assert auth.resolve_role("view-b-0123456789") == "viewer"
    assert auth.resolve_role("wrong") is None
    assert auth.resolve_role(None) is None
    assert auth.resolve_role("") is None


def test_role_ranks_and_access():
    assert auth.has_access("admin", "viewer")
    assert auth.has_access("admin", "admin")
    assert auth.has_access("operator", "operator")
    assert auth.has_access("scheduler", "operator")   # internal scheduler == operator rank
    assert not auth.has_access("viewer", "operator")
    assert not auth.has_access("operator", "admin")
    assert not auth.has_access(None, "viewer")
    assert auth.has_access(None, "public")
    assert not auth.has_access("viewer", "not-a-real-level")  # unknown requirement fails closed


def test_token_fingerprint_stable_and_short():
    fp = auth.token_fingerprint("adm-token-0123456789")
    assert fp == auth.token_fingerprint("adm-token-0123456789")
    assert len(fp) == 12
    assert "adm" not in fp
    assert auth.token_fingerprint(None) == "-"
