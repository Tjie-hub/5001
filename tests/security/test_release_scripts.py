"""scripts/release.sh + scripts/rollback.sh — immutable versioned releases,
atomic current-symlink switching, rollback."""
import json
import os
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RELEASE = str(REPO / "scripts" / "release.sh")
ROLLBACK = str(REPO / "scripts" / "rollback.sh")


def _mk_repo(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "hello.py").write_text("print('hi')\n")
    for cmd in (["git", "init", "-q"], ["git", "add", "."],
                ["git", "-c", "user.email=t@t", "-c", "user.name=t",
                 "commit", "-qm", "init"]):
        subprocess.run(cmd, cwd=src, check=True)
    return src


def _env(tmp_path, src):
    env = dict(os.environ)
    env.update(RELEASES_DIR=str(tmp_path / "releases"),
               CURRENT_LINK=str(tmp_path / "current"),
               PROJECT_DIR=str(src), SHARED_PATHS="")
    return env


def _commit_v2(src):
    time.sleep(1.1)  # version stamp has second granularity
    (src / "hello.py").write_text("print('v2')\n")
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-aqm", "v2"], cwd=src, check=True)


def test_release_creates_immutable_versioned_dir_with_manifest(tmp_path):
    src = _mk_repo(tmp_path)
    env = _env(tmp_path, src)
    subprocess.run([RELEASE], env=env, check=True, capture_output=True)
    releases = list((tmp_path / "releases").iterdir())
    assert len(releases) == 1
    rel = releases[0]
    meta = json.loads((rel / "release.json").read_text())
    assert {"version", "git_sha", "branch", "built_at"} <= set(meta)
    assert meta["version"] == rel.name
    assert (tmp_path / "current").resolve() == rel.resolve()
    assert not os.access(rel / "hello.py", os.W_OK)      # immutable code


def test_release_switch_and_rollback_restores_previous(tmp_path):
    src = _mk_repo(tmp_path)
    env = _env(tmp_path, src)
    subprocess.run([RELEASE], env=env, check=True, capture_output=True)
    first = (tmp_path / "current").resolve()
    _commit_v2(src)
    subprocess.run([RELEASE], env=env, check=True, capture_output=True)
    second = (tmp_path / "current").resolve()
    assert second != first
    subprocess.run([ROLLBACK], env=env, check=True, capture_output=True)
    assert (tmp_path / "current").resolve() == first


def test_rollback_to_named_version(tmp_path):
    src = _mk_repo(tmp_path)
    env = _env(tmp_path, src)
    subprocess.run([RELEASE], env=env, check=True, capture_output=True)
    first = (tmp_path / "current").resolve()
    _commit_v2(src)
    subprocess.run([RELEASE], env=env, check=True, capture_output=True)
    subprocess.run([ROLLBACK, first.name], env=env, check=True,
                   capture_output=True)
    assert (tmp_path / "current").resolve() == first


def test_rollback_list_marks_current(tmp_path):
    src = _mk_repo(tmp_path)
    env = _env(tmp_path, src)
    subprocess.run([RELEASE], env=env, check=True, capture_output=True)
    _commit_v2(src)
    subprocess.run([RELEASE], env=env, check=True, capture_output=True)
    out = subprocess.run([ROLLBACK, "--list"], env=env, check=True,
                         capture_output=True, text=True).stdout
    lines = [l for l in out.strip().splitlines() if l.strip()]
    assert len(lines) == 2
    current_name = (tmp_path / "current").resolve().name
    starred = [l for l in lines if l.startswith("*")]
    assert len(starred) == 1 and current_name in starred[0]


def test_rollback_with_nothing_older_fails(tmp_path):
    src = _mk_repo(tmp_path)
    env = _env(tmp_path, src)
    subprocess.run([RELEASE], env=env, check=True, capture_output=True)
    r = subprocess.run([ROLLBACK], env=env, capture_output=True, text=True)
    assert r.returncode != 0
    assert "no release" in r.stderr.lower()


def test_release_refuses_uncommitted_tracked_changes(tmp_path):
    src = _mk_repo(tmp_path)
    env = _env(tmp_path, src)
    (src / "hello.py").write_text("print('dirty')\n")  # uncommitted, tracked
    r = subprocess.run([RELEASE], env=env, capture_output=True, text=True)
    assert r.returncode != 0
    assert "uncommitted" in r.stderr.lower()
    assert not (tmp_path / "releases").exists()


def test_release_allows_uncommitted_changes_with_override(tmp_path):
    src = _mk_repo(tmp_path)
    env = _env(tmp_path, src)
    env["ALLOW_DIRTY_RELEASE"] = "1"
    (src / "hello.py").write_text("print('dirty')\n")  # uncommitted, tracked
    r = subprocess.run([RELEASE], env=env, capture_output=True, text=True)
    assert r.returncode == 0
    assert (tmp_path / "current").exists()


def test_shared_paths_symlinked_not_copied(tmp_path):
    src = _mk_repo(tmp_path)
    shared_db = src / "walkforward.db"
    shared_db.write_text("dbdata")
    env = _env(tmp_path, src)
    env["SHARED_PATHS"] = "walkforward.db"
    subprocess.run([RELEASE], env=env, check=True, capture_output=True)
    rel = (tmp_path / "current").resolve()
    assert (rel / "walkforward.db").is_symlink()
    assert (rel / "walkforward.db").resolve() == shared_db.resolve()
