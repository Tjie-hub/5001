"""J5 — daily ops health check (weekdays 17:10 WIB), Telegram ONLY on anomaly.

The healthy state is silent (one log line for cron_wrap); a message is sent
exactly when one of these expectations is violated:

  1. Syncthing folder fdds3-owznl stays PAUSED — the .git/index overwrite
     mitigation. Unpaused = the Windows side can clobber this tree again.
  2. Exactly 4 .git/index.sync-conflict-* artifacts exist. Those four are the
     accepted steady state (2026-08-15/21, 09-21, 09-22); a fifth means new
     sync damage, fewer than 4 means someone cleaned them without a note.
  3. The production tree is checked out on ops/hardening-2026-07-10.
  4. idx-walkforward.service (systemd --user, gunicorn :5001) is active.
  5. After P3 deploys (run_staged_entry_fills present in scheduler/jobs.py):
     today's logs/app.log must contain at least one "staged fills:" marker —
     the 09:10/10:10 WIB jobs log it unconditionally after resolving (an
     all-zero run included). Absence on a weekday means the job did not run;
     before blaming the scheduler, cross-check whether today was an IDX
     holiday (_holiday_skip returns early without the marker).
  6. audit_events provider_switch rows whose detail carries the stuck
     reset-time "resumes ~2026-07-10T11:20:00+00:00" did not increase vs
     yesterday's stored count (state: logs/ops_health_state.json; first run
     only records the baseline).
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ops._common import OPS_PREFIX, now_wib, repo_root, send_ops

SYNCTHING_CONFIG = Path.home() / ".local" / "state" / "syncthing" / "config.xml"
SYNCTHING_API = "http://127.0.0.1:8384"
SYNCTHING_FOLDER = "fdds3-owznl"
EXPECTED_SYNC_CONFLICTS = 4
SERVICE_UNIT = "idx-walkforward.service"
EXPECTED_BRANCH = "ops/hardening-2026-07-10"
STAGED_FILL_MARKER = "staged fills:"
STAGED_FILL_SYMBOL = "def run_staged_entry_fills"
STUCK_DETAIL = "resumes ~2026-07-10T11:20:00+00:00"
STATE_FILE = "logs/ops_health_state.json"

_API_KEY_RE = re.compile(r"<apikey>([^<]+)</apikey>")


def syncthing_api_key(config_path: Path = SYNCTHING_CONFIG) -> str:
    return _API_KEY_RE.search(config_path.read_text(encoding="utf-8")).group(1)


def syncthing_folder_paused(folder: str = SYNCTHING_FOLDER,
                             api_base: str = SYNCTHING_API,
                             api_key: str | None = None) -> bool:
    api_key = api_key or syncthing_api_key()
    req = urllib.request.Request(
        f"{api_base}/rest/config/folders/{folder}",
        headers={"X-API-Key": api_key})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return bool(json.load(resp).get("paused"))


def count_sync_conflicts(git_dir: Path) -> int:
    return len(list(git_dir.glob("*sync-conflict*")))


def current_branch(root: Path) -> str:
    out = subprocess.run(["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
                         capture_output=True, text=True, timeout=60)
    return out.stdout.strip()


def service_active(unit: str = SERVICE_UNIT) -> bool:
    out = subprocess.run(["systemctl", "--user", "is-active", unit],
                         capture_output=True, text=True, timeout=60)
    return out.stdout.strip() == "active"


def staged_fill_markers_today(app_log: Path, today) -> int:
    """Count "staged fills:" log lines whose JSON "time" falls on today (WIB)."""
    from scripts.ops._common import WIB
    n = 0
    if not app_log.is_file():
        return 0
    with open(app_log, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if STAGED_FILL_MARKER not in line:
                continue
            try:
                rec = json.loads(line)
                when = datetime.fromisoformat(rec["time"]).astimezone(WIB)
            except Exception:
                continue
            if when.date() == today:
                n += 1
    return n


def stuck_provider_switch_count(db_path: Path) -> int:
    if not db_path.is_file():
        return 0
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM audit_events WHERE action = ? AND detail LIKE ?",
            ("provider_switch", f"%{STUCK_DETAIL}%")).fetchone()
        return int(row[0])
    except sqlite3.OperationalError:  # no audit_events table yet → nothing recorded
        return 0
    finally:
        conn.close()


def load_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def evaluate(root: Path, today, *,
             paused=syncthing_folder_paused,
             conflicts=count_sync_conflicts,
             branch=current_branch,
             active=service_active,
             markers=staged_fill_markers_today,
             stuck_count=stuck_provider_switch_count,
             state: dict | None = None) -> tuple[list[str], dict]:
    """Returns (anomalies, new_state). All probes are injectable for tests."""
    anomalies: list[str] = []
    try:
        if not paused():
            anomalies.append(f"Syncthing folder {SYNCTHING_FOLDER} is UNPAUSED "
                             "(expected paused — .git/index overwrite mitigation)")
    except Exception as exc:
        anomalies.append(f"Syncthing folder state unreadable: {exc}")

    n_conf = conflicts(root / ".git")
    if n_conf != EXPECTED_SYNC_CONFLICTS:
        anomalies.append(f".git sync-conflict artifact count is {n_conf}, expected "
                         f"{EXPECTED_SYNC_CONFLICTS}")

    br = branch(root)
    if br != EXPECTED_BRANCH:
        anomalies.append(f"production tree is on branch {br!r}, expected {EXPECTED_BRANCH!r}")

    if not active():
        anomalies.append(f"{SERVICE_UNIT} (gunicorn :5001) is not active")

    jobs_py = root / "scheduler" / "jobs.py"
    if jobs_py.is_file() and STAGED_FILL_SYMBOL in jobs_py.read_text(encoding="utf-8"):
        if markers(root / "logs" / "app.log", today) == 0:
            anomalies.append("no 'staged fills:' marker in today's app.log — P3 staged-entry "
                             "fill job (09:10/10:10 WIB) apparently did not run "
                             "(rule out an IDX holiday before acting)")

    state = state if state is not None else {}
    prev = state.get("provider_switch_stuck")
    new_state = dict(state)
    db_path = Path(os.getenv("DB_PATH") or "data/walkforward.db")
    if not db_path.is_absolute():
        db_path = root / db_path
    new_state["provider_switch_stuck"] = stuck_count(db_path)
    new_state["as_of"] = today.isoformat()
    if prev is not None and new_state["provider_switch_stuck"] > prev:
        anomalies.append(f"audit_events provider_switch rows containing "
                         f"'{STUCK_DETAIL}' increased: {prev} -> {new_state['provider_switch_stuck']}")
    return anomalies, new_state


def main(argv: list[str] | None = None) -> int:
    dry = bool(argv and "--dry" in argv)
    root = repo_root()
    today = now_wib().date()
    anomalies, new_state = evaluate(root, today)
    state_path = root / STATE_FILE
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(new_state, indent=2) + "\n", encoding="utf-8")
    if anomalies:
        send_ops(f"{OPS_PREFIX} ⚠️ ops health anomalies ({today}):\n" +
                 "\n".join(f"• {a}" for a in anomalies),
                 event="ops.health_daily", dry=dry)
    else:
        print(f"ops health OK ({today}); state={new_state}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
