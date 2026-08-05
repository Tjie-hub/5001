# AF-9 — Release Hygiene Fix (Blockers 1 & 2 from AF-8)

**Date:** 2026-07-29 · **Status:** Fix + validation. Scope: exactly the two blockers AF-8 identified.
No commit made, no feature/business-logic/architecture change made.

---

## Blocker 1 — Executable Bit Restoration

**Files whose executable bit was restored (10):**
`scripts/release.sh`, `scripts/rollback.sh`, `scripts/wait_for_health.sh`, `scripts/cron_wrap.sh`,
`start.sh`, `run_telegram.sh`, `chart-viewer/start.sh`, `_archive/patch_rr_ratio.sh`,
`_archive/update_fetch_report.py`, `auto_token.py`.

**Method:** `chmod +x` on all 10, then `git update-index --chmod=+x` to correct the git **index**
mode directly — the reliable fix on this Windows/NTFS checkout, where `git.exe`'s own worktree-stat
check disagreed with what MSYS `chmod`/`ls` reported (a platform quirk, not a repo defect; see
caveat below). For `scripts/release.sh` specifically — the one file with a genuine, pre-existing
content diff (the `ALLOW_DIRTY_RELEASE` guard AF-8 already reviewed and approved) — `update-index
--chmod` initially also picked up and staged that content, so it was re-pointed at HEAD's exact,
unmodified blob (`git update-index --cacheinfo 100755,<HEAD-blob>,scripts/release.sh`) to isolate
the mode fix from the content, which remains exactly where it was: unstaged, in the working tree,
untouched by this fix.

**Confirmation file contents were unchanged:**
- All 9 non-`release.sh` files: `git diff --cached` is completely empty (no content staged) and
  `git diff` (working tree vs. index) shows only a mode line, zero content hunks.
- `scripts/release.sh`: `git diff --cached` is empty; its content diff (12 lines, the
  `ALLOW_DIRTY_RELEASE` guard) is unchanged from what AF-8 already documented and remains unstaged,
  exactly as before this fix — this task did not touch, stage, or alter it.
- **Definitive proof of what would actually be committed:** `git write-tree` (side-effect-free —
  writes the index as a tree object without creating a commit or moving `HEAD`, which stayed at
  `197da2c` throughout):
  ```
  100755 blob 6dd1397... _archive/patch_rr_ratio.sh
  100755 blob 0018e99... _archive/update_fetch_report.py
  100755 blob 5c85a6f... auto_token.py
  100755 blob 0bde69a... chart-viewer/start.sh
  100755 blob 5560578... run_telegram.sh
  100755 blob 31bc810... scripts/cron_wrap.sh
  100755 blob bfe261b... scripts/release.sh   ← same blob hash as HEAD's — content byte-identical
  100755 blob 0beb662... scripts/rollback.sh
  100755 blob 9f7e795... scripts/wait_for_health.sh
  100755 blob 93ce8f0... start.sh
  ```
  All 10 are `100755`. `scripts/release.sh`'s blob hash (`bfe261b...`) matches `HEAD`'s own blob
  hash exactly — proof its content is byte-identical to what's already committed; the pending
  `ALLOW_DIRTY_RELEASE` content change lives only in the working tree, unstaged, as it should.

**Known caveat (environmental, not a defect in this fix):** `git status`/`git diff` (working-tree
view) still cosmetically report all 10 files as modified, because this specific Windows/git-bash
checkout's `git.exe` perceives the worktree file's executable bit as unset even after `chmod +x`
(confirmed via `ls -la` showing `-rwxr-xr-x` while `git diff` still reports `100755 => 100644`).
This does **not** affect what gets committed — proven above via `write-tree` — but it does mean a
plain `git add` on any of these exact 10 paths (without an explicit `--chmod=+x`) would likely
re-read the worktree's perceived mode and silently regress the fix. **Recommendation for whoever
finalizes the commit:** either commit directly from the current index without re-`git add`-ing these
paths, or re-run `git update-index --chmod=+x <path>` as the last operation on them before
committing. This class of quirk does not exist on the actual Ubuntu deploy target.

---

## Blocker 2 — Provider Governor Exclusion

**Confirmed the Governor is excluded from this release:**
- `engine/agent_firm/providers/governor.py` and its four test files
  (`tests/agent_firm/providers/test_governor.py`, `test_quota_hydration_edge_cases.py`,
  `test_quota_scenarios.py`, `test_quota_state_persistence.py`) are all `??` (untracked) in
  `git status` — never `git add`ed by this fix or anything prior. Untracked files are excluded from
  any commit by default; no action was needed to exclude them beyond confirming they remain
  untracked.
- Re-confirmed zero references to the Governor anywhere in the live request path: `router.py`,
  `factory.py`, and `firm.py` contain no mention of `governor` (grep, zero matches). Production does
  not, and cannot, depend on it.
- **Not repaired** — per the task's explicit instruction, no attempt was made to add the missing
  `GOVERNOR_*` config or wire it into `router.py`/`factory.py`. It remains known, incomplete, deferred
  work (as AF-8 recorded), not silently dropped.

---

## Validation

**✓ Executable bits restored** — proven via `git write-tree` above (all 10 files `100755` in what
would actually be committed).

**✓ `release.sh` accepts the working tree, mechanism confirmed** — the pytest-based test suite for
this script (`tests/security/test_release_scripts.py`) fails on this Windows box with
`OSError: [WinError 193] %1 is not a valid Win32 application` — Python's `subprocess.run` cannot
exec a `.sh` file directly on native Windows without a shell wrapper. This is a **pre-existing,
already-documented** Windows-tooling limitation (`Audit/FINAL_PRODUCTION_READINESS_CERTIFICATION.md`
§5 names this exact file among its enumerated pre-existing Windows-environment test artifacts) — not
introduced by this fix. To validate the actual mechanism, the script was invoked directly through a
real POSIX shell (the Bash tool) instead:
  ```
  $ bash scripts/release.sh
  ERROR: uncommitted tracked changes exist. `git archive HEAD` (what this script
  packages) silently omits them, so the release would not match what was tested.
  Commit or stash first. To force a one-off build anyway (e.g. a manual smoke
  build, never for a real deploy), re-run with ALLOW_DIRTY_RELEASE=1.
  exit code: 1
  ```
  **This refusal is correct and expected** — 50 tracked files remain genuinely, legitimately
  uncommitted (the certified WP1-4/AF-2 payload AF-8 already scoped for a separate, multi-commit
  strategy; committing that payload was never in scope for this task). The guard is not blocked by
  either Blocker 1 or Blocker 2 — it is doing exactly its job against real, expected, pending content.

**✓ Production-path tests pass — Governor failures remain isolated, nothing else hidden:**
```
pytest tests/agent_firm/ tests/test_trade_plan.py tests/test_bear_watchlist_ranking.py \
       tests/test_eod_trade_plan_job.py \
       --ignore=tests/agent_firm/providers/test_governor.py \
       --ignore=tests/agent_firm/providers/test_quota_hydration_edge_cases.py \
       --ignore=tests/agent_firm/providers/test_quota_scenarios.py \
       --ignore=tests/agent_firm/providers/test_quota_state_persistence.py \
       -q --continue-on-collection-errors
→ 329 passed, 0 failed, 0 errors
```
Exclusion is scoped to precisely the 4 broken files, **not** the whole `tests/agent_firm/providers/`
subtree — the other 135 tests in that subtree (circuit breaker, classification, alerts, metrics,
etc.) are included and passing, exactly as AF-8's evidence showed. No unrelated failure was hidden
by this exclusion — the pre-exclusion run (`348 passed, 9 failed, 1 error`, from AF-8/this session)
already established that every failure/error was confined to these 4 files; that fact is unchanged.

**✓ Governor failures remain isolated:**
```
pytest tests/agent_firm/providers/ -q --continue-on-collection-errors
→ 9 failed, 135 passed, 1 error
```
All 9 failures + 1 error trace to the same 4 files; nothing else in the subtree regressed.

---

## Deliverables

1. **Files whose executable bit was restored:** 10 — listed at the top of Blocker 1.
2. **Confirmation file contents were unchanged:** proven via `git diff --cached` (empty for all 10)
   and `git write-tree` (identical blob hashes to HEAD for the 9 pure-mode files; `release.sh`'s
   blob hash matches HEAD's exactly, confirming its pending content edit was never touched or staged
   by this fix).
3. **Confirmation the Governor is excluded:** confirmed untracked (`??`), confirmed unreferenced by
   `router.py`/`factory.py`/`firm.py`, confirmed not repaired.
4. **Validation results:** all four checkmarks above — mode fix proven at the object level,
   `release.sh`'s guard mechanism confirmed correct via direct invocation, 329/329 production-path
   tests passing with only the 4 Governor files excluded, Governor failures reconfirmed isolated
   (9 failed/1 error, unchanged, contained).
5. **Remaining release blockers:** **none from this task's scope.** The only reason `release.sh`
   still refuses is the same ~90-file legitimate payload AF-8 already planned a multi-commit strategy
   for — expected, not a new or residual blocker from either Blocker 1 or Blocker 2. One operational
   caveat carried forward (not a blocker): the Windows/git-bash worktree-stat quirk described above —
   relevant only to whoever runs the actual `git add`/`git commit` on this checkout.
6. **GO / NO-GO:** **GO on release hygiene** — both AF-8 blockers are resolved and validated. The
   next step is AF-8's own commit plan (Phase 3: multiple logical commits), which remains a separate,
   not-yet-authorized action — this task's scope stops here, as instructed.
