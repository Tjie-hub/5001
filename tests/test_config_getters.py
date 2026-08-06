"""Tests for config.py's sectors_app_mode() getter -- Production Engine
Phase 2, Workstream 2B Task 2B-3. Mirrors the existing edge_mode() getter
exactly (env re-read per call, lowercased, defaults to "off"). Added so
routes/v1/config.py has a real service-layer accessor for SECTORS_APP_MODE
instead of reading os.getenv directly -- scheduler/scanner.py's own inline
read of the same var is untouched.
"""
import config


def test_defaults_to_off(monkeypatch):
    monkeypatch.delenv("SECTORS_APP_MODE", raising=False)
    assert config.sectors_app_mode() == "off"


def test_reads_env_each_call(monkeypatch):
    monkeypatch.setenv("SECTORS_APP_MODE", "enforce")
    assert config.sectors_app_mode() == "enforce"

    monkeypatch.setenv("SECTORS_APP_MODE", "shadow")
    assert config.sectors_app_mode() == "shadow"


def test_lowercases_and_strips(monkeypatch):
    monkeypatch.setenv("SECTORS_APP_MODE", "  ENFORCE  ")
    assert config.sectors_app_mode() == "enforce"
