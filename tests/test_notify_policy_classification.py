"""CI classification gate for the 2026-10-06 notification curation brief.

Like tests/security/test_route_policy.py for routes: an AST scan of the
production tree fails on any send_telegram() call whose event= id is missing
or not registered in utils/notify_policy.EVENTS. This is the enforcement that
keeps the "no unclassified sends" property true as call sites are added.

Scope: the deploy surface. Excluded: tests/, migrations/applied (historical
patch records), scratchpad/ (owner ad-hoc tools — at runtime an unclassified
send is suppressed + logged, the safe default), .worktrees/ (stale checkouts),
docs/, logs/, venv/. The dynamic send in engine/registry_loader.py is covered
by test_registry_loader_announce_is_classified below (ast can't see through
its callable alias).
"""
import ast
import os
import re
from pathlib import Path

import utils.notify_policy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"tests", "migrations", "venv", "logs", ".git", "docs",
             "Claude outputs", "scratchpad", ".worktrees", "__pycache__",
             "node_modules"}


def _send_telegram_calls():
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            path = Path(dirpath) / fn
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == "send_telegram"):
                    yield path, node


def test_every_send_telegram_call_has_a_registered_event():
    bad = []
    n = 0
    for path, node in _send_telegram_calls():
        n += 1
        kw = {k.arg: k for k in node.keywords}
        if "event" not in kw:
            bad.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno} — no event=")
            continue
        val = kw["event"].value
        if isinstance(val, ast.Constant):
            if val.value not in np.EVENTS:
                bad.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno} — "
                           f"event {val.value!r} not in notify_policy.EVENTS")
        elif not (isinstance(val, ast.Name) and val.id == "event"):
            # dynamic pass-through is only acceptable for a parameter literally
            # named `event` (the _send helper pattern in screener_jobs.py)
            bad.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno} — "
                       f"event= is not a registered literal (ast: {ast.dump(val)[:60]})")
    assert n >= 60, f"scan found only {n} call sites — walker broken?"
    assert not bad, "Unclassified telegram sends:\n" + "\n".join(bad)


def test_senders_route_through_the_policy_gate():
    """Every sender muscle must call the single gate before touching the wire."""
    for fname, pattern in [
        ("utils/telegram.py", r"decide\(event"),
        ("stockbit_fetcher.py", r"decide\(event"),
        ("auto_token.py", r"decide\(event"),
        ("routes/telegram.py", r'decide\("bot\.reply"'),
    ]:
        src = (REPO_ROOT / fname).read_text()
        assert re.search(pattern, src), f"{fname} bypasses the notify_policy gate"


def test_cron_wrap_honors_off_and_daily_dedup():
    src = (REPO_ROOT / "scripts" / "cron_wrap.sh").read_text()
    assert "TELEGRAM_OFF" in src
    assert "cronfail_${JOB}_$(date +%F)" in src


def test_registry_loader_announce_is_classified():
    src = (REPO_ROOT / "engine" / "registry_loader.py").read_text()
    assert 'telegram_fn(msg, event="system.registry_announce")' in src


def test_digest_flush_job_registered_at_17_45():
    src = (REPO_ROOT / "scheduler" / "__init__.py").read_text()
    assert "notify_evening_digest" in src
    assert "flush_digest" in src
    assert "hour=17, minute=45" in src
