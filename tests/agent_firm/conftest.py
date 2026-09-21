"""Shared fixtures for agent_firm tests."""
import os
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _fresh_governor():
    """The adaptive provider governor is a PROCESS singleton (state persists
    across router rebuilds by design). Reset it around every agent_firm test so
    one test's AIMD decrease can't leak pacing state into the next."""
    from engine.agent_firm.providers.governor import reset_governor
    reset_governor()
    yield
    reset_governor()


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Empty SQLite DB at a temp path with agent firm tables created."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    # Reload the data.db module so DB_PATH is picked up
    import importlib
    from data import db
    importlib.reload(db)
    db.init_db()
    yield db_path
