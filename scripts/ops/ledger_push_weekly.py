"""J4 — weekly forward-ledger push (Fridays 17:30 WIB).

Pushes the week's forward-test ledger appends to GitHub, and nothing else:

  • operates only when the tree is on ops/hardening-2026-07-10 (any other
    branch — a research session, a deploy in progress — means skip, no alert);
  • `git add`s ONLY the already-tracked docs/research_programs/P-M/forward_*/
    ledger.json files that are modified (a new untracked ledger is never
    added by this job);
  • commits only when something is actually staged;
  • pushes, and if the push is REJECTED (non-fast-forward: someone else
    pushed first) sends ONE alert and stops — never pulls, rebases or
    force-pushes. The next Friday run retries on the same rule.

Runs after the 16:05 research_wf_refresh and well after the morning
recorders, so the ledgers hold the week's final state.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ops._common import OPS_PREFIX, repo_root, send_ops

BRANCH = "ops/hardening-2026-07-10"
LEDGER_PATHSPEC = "docs/research_programs/P-M/forward_*/ledger.json"
COMMIT_MESSAGE = "ledger: weekly forward-test appends (ops J4 auto-push)"


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True, timeout=300)


def modified_ledgers(root: Path) -> list[str]:
    out = git(root, "ls-files", "-m", "--", LEDGER_PATHSPEC)
    if out.returncode != 0:
        raise RuntimeError(f"git ls-files failed: {out.stderr.strip()}")
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def push_rejected(stderr: str) -> bool:
    return "rejected" in stderr.lower() or "non-fast-forward" in stderr.lower()


def main(argv: list[str] | None = None) -> int:
    dry = bool(argv and "--dry" in argv)
    root = repo_root()

    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if branch != BRANCH:
        print(f"skip: HEAD is on {branch!r}, not {BRANCH!r}")
        return 0

    files = modified_ledgers(root)
    if not files:
        print("no tracked ledger modifications — nothing to commit or push")
        return 0
    print("staging (tracked, modified only):", ", ".join(files))

    add = git(root, "add", "--", *files)
    if add.returncode != 0:
        send_ops(f"{OPS_PREFIX} ⚠️ weekly ledger push: git add failed — {add.stderr.strip()[-300:]}", dry=dry)
        return 0

    if git(root, "diff", "--cached", "--quiet").returncode == 0:
        print("nothing staged after add — exit")
        return 0

    commit = git(root, "commit", "-m", COMMIT_MESSAGE)
    if commit.returncode != 0:
        send_ops(f"{OPS_PREFIX} ⚠️ weekly ledger push: commit failed — {commit.stderr.strip()[-300:]}", dry=dry)
        return 0
    head = git(root, "rev-parse", "HEAD").stdout.strip()
    print(f"committed {head}")

    if dry:
        print(f"dry run: would push {head} to origin/{BRANCH}")
        return 0

    push = git(root, "push", "origin", BRANCH)
    if push.returncode != 0:
        kind = "REJECTED" if push_rejected(push.stderr) else "FAILED"
        send_ops(f"{OPS_PREFIX} ⚠️ weekly ledger push {kind} on {BRANCH} — "
                 f"no pull/rebase/force attempted, manual review needed.\n{push.stderr.strip()[-400:]}", dry=dry)
        return 0

    remote = git(root, "ls-remote", "origin", BRANCH).stdout.split()
    proof = f"remote {BRANCH} -> {remote[0]}" if remote else "remote ref not found?!"
    print(f"push OK; {proof}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
