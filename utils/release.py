"""utils/release.py — which build is running (security hardening Phase 4).

A built release carries release.json (written by scripts/release.sh); a
developer working tree falls back to the git short SHA. Never raises.
"""
import json
import subprocess
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent


def release_info() -> dict:
    manifest = _BASE / "release.json"
    if manifest.exists():
        try:
            info = json.loads(manifest.read_text())
            info.setdefault("source", "release")
            return info
        except Exception:
            return {"version": "invalid-manifest", "source": "release"}
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             cwd=_BASE, capture_output=True, text=True,
                             timeout=5).stdout.strip()
        return {"version": f"dev-{sha or 'unknown'}", "source": "working-tree"}
    except Exception:
        return {"version": "dev-unknown", "source": "working-tree"}
