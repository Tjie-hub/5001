"""J1 — daily owner to-do reminders (08:30 WIB).

Reads ops/owner_todo.json — {"items": [{"date": "YYYY-MM-DD", "text": "..."}]} —
and sends one Telegram message listing the items whose date equals today
(WIB). Nothing due → no message, exit 0: this job must be silent on empty
days, not a daily "nothing to do" ping.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ops._common import OPS_PREFIX, now_wib, repo_root, send_ops


def load_items(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    items = data.get("items", [])
    if not isinstance(items, list):
        raise ValueError(f"{path}: 'items' must be a list")
    return [it for it in items if isinstance(it, dict)]


def items_due(items: list[dict], today: str) -> list[str]:
    """Texts of items whose date is exactly `today`; malformed rows are skipped."""
    due = []
    for it in items:
        text = str(it.get("text", "")).strip()
        if it.get("date") == today and text:
            due.append(text)
    return due


def build_message(today: str, due: list[str]) -> str:
    lines = [f"{OPS_PREFIX} 📋 Owner to-do for {today}:"]
    lines += [f"• {text}" for text in due]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    dry = bool(argv and "--dry" in argv)
    today = now_wib().strftime("%Y-%m-%d")
    items = load_items(repo_root() / "ops" / "owner_todo.json")
    due = items_due(items, today)
    if not due:
        print(f"no owner to-do items due {today}")
        return 0
    send_ops(build_message(today, due), dry=dry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
