"""J3 — {FQ} month-end keystats snapshot (weekdays 17:15 WIB).

Self-guarding to the last weekday of the month: the cron entry fires every
weekday but this exits quietly unless no remaining calendar day of the month
is a weekday. IDX holidays inside the final week are not modeled — a holiday
on the true last trading day means the snapshot runs the (trading) weekday
before it, which the append-only fq_keystats_snapshot table tolerates fine.

READY requires all of, in order:
  1. data/research.db exists,
  2. research/fq_snapshot.py exists on the checked-out branch (the keystats
     code merges separately — until then this reports NOT READY, which is
     exactly what the Owner's 2026-10-28 readiness check expects to see),
  3. .stockbit_token holds a JWT whose exp is comfortably in the future
     (refreshed daily at 08:40 WIB by auto_token),
  4. no rows exist yet in fq_keystats_snapshot for this month.
Otherwise: one "[OPS] snapshot NOT READY: <reasons>" message, exit 0.

When READY, calls `venv/bin/python3 -m research.fq_snapshot --limit 50` ONCE
(Owner decision 2026-10-01: single run per month-end, not a cover-the-
universe loop — the module re-selects its top-50 by ADV60 every run anyway)
and reports the partial result as N/50 captured this run. All of this job's
own DB reads are read-only (mode=ro); only the module writes.
"""
from __future__ import annotations

import base64
import json
import sqlite3
import subprocess
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ops._common import OPS_PREFIX, now_wib, repo_root, send_ops

UNIVERSE_SIZE = 200
RUN_LIMIT = 50            # matches the module's MAX_TICKERS_PER_RUN cap
RUN_TIMEOUT_S = 900       # 50 tickers × (~1.5 s interval + fetch) ≈ 2–3 min
TOKEN_EXPIRY_MARGIN_S = 300


def is_weekday(d: date) -> bool:
    return d.weekday() < 5


def is_last_weekday_of_month(d: date) -> bool:
    """True when no remaining calendar day of d's month is a weekday."""
    nxt = d + timedelta(days=1)
    while nxt.month == d.month and nxt.year == d.year:
        if is_weekday(nxt):
            return False
        nxt += timedelta(days=1)
    return True


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def token_status(token_path: Path, now_ts: float | None = None) -> str | None:
    """None when the token looks valid, else a human-readable reason."""
    if not token_path.is_file():
        return f"no token file at {token_path} (auto_token.py runs 08:40 WIB)"
    token = token_path.read_text(encoding="utf-8").strip()
    if not token:
        return "token file is empty — run auto_token.py"
    parts = token.split(".")
    if len(parts) != 3:
        return "token is not a JWT"
    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return "token payload not decodable"
    exp = claims.get("exp")
    if not isinstance(exp, (int, float)):
        return "token has no exp claim"
    now_ts = time.time() if now_ts is None else now_ts
    if exp <= now_ts + TOKEN_EXPIRY_MARGIN_S:
        return f"token exp is in {int(exp - now_ts)}s (< {TOKEN_EXPIRY_MARGIN_S}s margin) — refresh due"
    return None


def distinct_captured(research_db: Path, month: str) -> int:
    """Read-only count of distinct tickers snapshotted for `month`."""
    if not research_db.is_file():
        return 0
    conn = sqlite3.connect(f"file:{research_db}?mode=ro", uri=True)
    try:
        row = conn.execute(
            "SELECT COUNT(DISTINCT ticker) FROM fq_keystats_snapshot WHERE snapshot_month = ?",
            (month,)).fetchone()
        return int(row[0])
    except sqlite3.OperationalError:  # table not created yet → nothing captured
        return 0
    finally:
        conn.close()


def parse_run_output(stdout: str) -> dict:
    """Parse the module's JSON result; tolerate stray log lines around it."""
    text = stdout.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise


def snapshot_guards(root: Path, research_db: Path, module_path: Path,
                    token_path: Path, month: str, now_ts: float | None = None) -> list[str]:
    reasons: list[str] = []
    if not research_db.is_file():
        reasons.append(f"data/research.db not found at {research_db}")
    if not module_path.is_file():
        reasons.append("research/fq_snapshot.py not on the checked-out branch (keystats merge pending)")
    tok = token_status(token_path, now_ts=now_ts)
    if tok:
        reasons.append(f"Stockbit token: {tok}")
    if not reasons and distinct_captured(research_db, month) > 0:
        reasons.append(f"fq_keystats_snapshot already has rows for {month}")
    return reasons


def run_snapshot(venv_py: Path, root: Path, limit: int = 50) -> subprocess.CompletedProcess:
    return subprocess.run([str(venv_py), "-m", "research.fq_snapshot", "--limit", str(limit)],
                          cwd=str(root), capture_output=True, text=True, timeout=RUN_TIMEOUT_S)


def main(argv: list[str] | None = None) -> int:
    dry = bool(argv and "--dry" in argv)
    today = now_wib().date()
    if not is_weekday(today) or not is_last_weekday_of_month(today):
        print(f"not the last weekday of the month ({today}); nothing to do")
        return 0

    root = repo_root()
    month = month_key(today)
    reasons = snapshot_guards(root, root / "data" / "research.db",
                              root / "research" / "fq_snapshot.py",
                              root / ".stockbit_token", month)
    if reasons:
        send_ops(f"{OPS_PREFIX} snapshot NOT READY: " + "; ".join(reasons), dry=dry)
        return 0

    venv_py = root / "venv" / "bin" / "python3"
    try:
        proc = run_snapshot(venv_py, root, limit=RUN_LIMIT)
        result = parse_run_output(proc.stdout)
    except Exception as exc:
        send_ops(f"{OPS_PREFIX} ⚠️ {{FQ}} snapshot run failed: {exc}", dry=dry)
        return 0
    captured = result.get("captured", [])
    failed = result.get("failed", [])
    lines = [f"{OPS_PREFIX} 📸 {{FQ}} keystats snapshot {month}: "
             f"{len(captured)}/{RUN_LIMIT} tickers this run "
             f"(single-run partial by design; universe {UNIVERSE_SIZE})"]
    if any("auth" in str(reason).lower() for _tkr, reason in failed):
        lines.append("⚠️ Stockbit token rejected (401/403) — refresh via auto_token.py and re-check")
    if failed:
        lines.append(f"⚠️ {len(failed)} per-ticker failure(s) reported by the module")
    send_ops("\n".join(lines), dry=dry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
