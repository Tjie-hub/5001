"""Shared fixtures for agent_firm tests."""
import os
import sqlite3
from pathlib import Path

import pytest


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
