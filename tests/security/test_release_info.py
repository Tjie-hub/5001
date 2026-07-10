"""utils.release — which build is running."""
import importlib
import sqlite3

from utils import release


def test_working_tree_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(release, "_BASE", tmp_path)  # no manifest, no git repo
    info = release.release_info()
    assert info["source"] == "working-tree"
    assert info["version"].startswith("dev-")


def test_manifest_wins(tmp_path, monkeypatch):
    (tmp_path / "release.json").write_text(
        '{"version": "20260711-abc1234", "git_sha": "abc", "built_at": "t"}')
    monkeypatch.setattr(release, "_BASE", tmp_path)
    assert release.release_info()["version"] == "20260711-abc1234"


def test_git_fallback_in_real_repo():
    info = release.release_info()
    assert info["version"] and info["version"] != ""


def test_health_includes_version(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE scheduled_signals (scan_time TEXT)")
    conn.execute("CREATE TABLE paper_trades (ticker TEXT, status TEXT)")
    conn.commit()
    conn.close()
    monkeypatch.setenv("DB_PATH", str(db))
    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    c = app_module.app.test_client()
    body = c.get("/health").get_json()
    assert "version" in body and body["version"]
