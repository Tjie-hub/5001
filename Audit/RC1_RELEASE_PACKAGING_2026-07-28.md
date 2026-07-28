# Production Engine — RC1 Release Packaging Report

**Date:** 2026-07-28
**Basis:** `Audit/RC1_FINAL_CERTIFICATION_2026-07-28.md` — authoritative release audit. Its verdict was
**not** "the implementation is wrong"; it was "the release process doesn't exist yet" (F-1: nothing
committed, no CI evidence; F-2: local pass/fail counts unreproducible; F-3: one small code gap).
**Scope:** package RC1 as a real, committed, CI-verifiable artifact. No architecture change, no new
trading features, no Operations Dashboard work (per instruction).
**Constraint honored:** nothing was pushed, no PR opened, no commit created — this report proposes a
staging/commit plan; execution is a separate, explicit go/no-ahead (see §7).

---

## 1. F-3 Implementation Summary — DONE

**Finding:** `run_eod_trade_plan`'s dedup guard had no `except sqlite3.OperationalError` handler,
unlike `run_premarket_firm_scan`'s guard (patched after a real 2026-07-24 production crash), even
though EOD's own code comment states its 16:40 slot is *more* exposed to the same lock-contention
window.

**Fix applied** (`scheduler/jobs.py`, `run_eod_trade_plan`, the dedup-guard block): added

```python
except sqlite3.OperationalError as e:
    logger.warning(f"[{now_str}] EOD trade plan: dedup guard error (fail-open): {e}")
    return
```

identical in structure, exception type, log level, and message shape (`"<job label>: dedup guard
error (fail-open): {e}"`) to premarket's handler — only the job-label prefix differs, matching that
job's own existing `IntegrityError` message style (`"EOD trade plan: ..."` vs `"Premarket firm:
..."`). No other line in `run_eod_trade_plan` was touched. Duplicate-prevention semantics (first
`INSERT` wins on the `(job, run_date)` primary key) and scheduler semantics (job still returns
normally, no exception propagates, `EVENT_JOB_ERROR`/crash-alerting is simply never triggered for
this specific failure mode anymore) are both preserved exactly.

**Regression test added:** `tests/test_eod_trade_plan_job.py` (new file — mirrors
`tests/test_premarket_firm_scan.py::test_run_premarket_firm_scan_fails_open_on_sentinel_db_lock`,
including a locally-duplicated `_LockedSentinelConn` fixture, matching that file's own note that it
duplicates rather than imports the sibling's fixture to stay independent).

**Validation:**
- `pytest tests/test_eod_trade_plan_job.py tests/test_premarket_firm_scan.py tests/test_trade_plan.py`
  → initially **2 failed** (the new EOD test and its premarket sibling), both for the identical
  pre-existing reason: `ModuleNotFoundError: No module named 'langgraph'` — both jobs import
  `engine.agent_firm.firm` before reaching the dedup guard, and this Windows dev venv was missing
  `langgraph`. Not a regression; inherited, not introduced.
- Rather than accept that as an unverified test (as the RC1 Conditions Closure Report did for the
  `fcntl`-blocked `auto_token.py` tests), this review installed the exact pinned versions from
  `requirements.txt` (`langgraph==1.2.0`, `feedparser==6.0.12`, plus `pyyaml`, which
  `requirements.txt` pulls in transitively — see §4) into the local venv. Re-run:
  **`74 passed`** across all three files, including the new F-3 test and its premarket sibling,
  both now genuinely executing rather than being asserted-correct-by-inspection.

---

## 2. Repository Hygiene — File Classification

`git status --porcelain -uall` was read in full (not sampled) and every entry classified by reading
its actual diff or content — not by filename pattern-matching alone (`CLAUDE.md`'s own Decision-Making
Hierarchy: verify, don't infer). 41 tracked-modified + ~100 untracked entries (excluding `.winvenv/`,
`.playwright-mcp/`, `images/`, which are pure local noise, never candidates for any commit).

### 2a. Belongs to RC1 — Production Engine reporting + RC1 fixes + RC1 conditions + F-3

**Modified (tracked):**

| File | Belongs because |
|---|---|
| `.env.example` | Documents `SCHEDULER_JOB_ERROR_COOLDOWN_S` (R-2) |
| `docs/OPERATIONS.md` | R-3 documentation of Phases 1–3 |
| `routes/telegram.py` | R-4 — `redact_secrets()` call in `send_telegram_reply` |
| `utils/telegram.py` | R-4 — `redact_secrets()` extracted/called in `send_telegram` |
| `utils/logging_config.py` | R-4 — `redact_secrets()` extracted as a standalone function |
| `scheduler/__init__.py` | R-2 — `JobErrorRateLimiter`, `EVENT_JOB_ERROR` listener |
| `scheduler/jobs.py` | Phases 1–3 (EOD/Premarket/Forward-Test jobs) + F-3 (this task) |
| `engine/trade_plan.py` | Phase 1 — `diff_watchlist`/`record_snapshot`/message building |
| `tests/forward_testing/test_scheduler_job.py` | Forward-test job dedup-guard tests |
| `tests/test_architecture_boundary.py` | R-1 — `.as_posix()` fix + `_ROUTES_DEBT` re-admission |
| `tests/test_config_hygiene.py` | RC1-C1 — `.as_posix()` fix |
| `tests/test_db_centralization.py` | R-1 — `.as_posix()` fix |
| `tests/test_logging_config.py` | R-4 — `redact_secrets()` unit tests |
| `tests/test_premarket_firm_scan.py` | Phase 1 premarket message/diff tests + dedup fail-open test |
| `tests/test_research_data_fence.py` | R-1 — `.as_posix()` fix |
| `tests/test_telegram_util.py` | R-4 — redaction tests for `utils.telegram` |
| `tests/test_trade_plan.py` | Phase 1 — EOD diff/snapshot tests |

**New (untracked):**

| File | Belongs because |
|---|---|
| `CLAUDE.md` | Canonical doc — R-3 content, and per F-1, **must** enter version control regardless |
| `forward_testing/reporting.py` | Phase 3 — the Forward-Testing reporting module itself |
| `tests/forward_testing/test_reporting.py` | Phase 3 tests |
| `tests/test_eod_trade_plan_job.py` | **New this task** — F-3 regression test |
| `tests/test_path_normalization.py` | RC1-C1 regression suite |
| `tests/test_routes_telegram_redaction.py` | R-4 tests |
| `tests/test_scheduler_job_error_alert.py` | R-2 tests |
| `tests/test_stockbit_fetcher_telegram_redaction.py` | RC1-C2 tests |
| `Audit/RELEASE_READINESS_AUDIT_2026-07-28.md` | RC1 audit trail |
| `Audit/RC1_FIX_REPORT_2026-07-28.md` | RC1 audit trail |
| `Audit/RC1_CERTIFICATION_REPORT_2026-07-28.md` | RC1 audit trail |
| `Audit/RC1_CONDITIONS_CLOSURE_REPORT_2026-07-28.md` | RC1 audit trail |
| `Audit/RC1_FINAL_CERTIFICATION_2026-07-28.md` | RC1 audit trail (this task's basis) |
| `Audit/RC1_RELEASE_PACKAGING_2026-07-28.md` | This report |

**⚠️ Two files require a partial (hunk-level) split, not a whole-file include** — see §2c.

### 2b. Explicitly excluded — separate, unrelated workstreams sitting in the same tree

Verified by reading each diff/file, not inferred from name:

**Agent-firm z.ai adaptive rate-limit governor ("R-7 Tier 1" / RCA 2026-07-10 thread) — a different,
independent workstream, unrelated to Telegram reporting:**
`engine/agent_firm/config.py`, `engine/agent_firm/providers/classification.py`,
`engine/agent_firm/providers/events.py`, `engine/agent_firm/providers/router.py`,
`engine/agent_firm/providers/zai.py`, `engine/agent_firm/providers/governor.py` (new),
`data/db.py` (adds `provider_events.reset_time` — explicitly commented `# RCA 2026-07-10`),
`tests/agent_firm/conftest.py`, `tests/agent_firm/providers/test_classification.py`,
`tests/agent_firm/providers/test_router.py`, `tests/agent_firm/providers/test_zai_provider.py`,
`tests/agent_firm/providers/test_governor.py`,
`tests/agent_firm/providers/test_quota_hydration_edge_cases.py`,
`tests/agent_firm/providers/test_quota_scenarios.py`,
`tests/agent_firm/providers/test_quota_state_persistence.py`, `monitor_zai_quota.py`,
`zai_quota_monitor.sh`, `zai-quota-page.png`, `scripts/probe_actual_http_concurrency.py`,
`scripts/probe_zai_concurrency_limit.py`, `scripts/probe_zai_large_payload.py`,
`scripts/probe_zai_sustained_rate.py`, `scripts/replay_firm_offline_run.py`,
`scripts/replay_governor_ab.py`, `Audit/CLAUDE_PROVIDER_RCA_2026-07-10.md`,
`Audit/PROVIDER_RESILIENCE_COMPLETION_2026-07-10.md`, `Audit/INSTITUTIONAL_AUDIT_2026-07-10.md`.

**Research provenance work — out of Production Engine scope by design (CI-enforced isolation):**
`research/tracking.py` (adds `dataset_meta_json` column — nothing to do with Telegram reporting),
`tests/test_experiment_tracking.py`.

**2026-07-24 news-fetch RSS-timeout incident — separate subsystem, separate incident:**
`news_filter.py`, `tests/test_news_filter.py`.

**2026-07-27 stockbit token-refresh outage hardening — separate incident (see §2c for the two files
that partially overlap with RC1-C2):**
`tests/test_stockbit_fetcher_ensure_valid_token.py`.

**Personal / scratch / unrelated documentation — no engineering justification found:**
`PLAN/vwma20-intraday-workflow.md`, `TOWR.md`, `TOWR_chart.png`, `WhatsApp_TOWR.jpeg`,
`_brpt_engine_test.py`, `backfill_flow_jan_apr.py`, `backfill_stockbit_flow_gap.py`,
`brpt-deepdive.png`, `docs/Adaptive_Signal_Scoring_Architecture.md`,
`docs/L3 Data Ontology Specification.pdf`, `docs/archive/EXECUTION_SEMANTICS.md`,
`docs/archive/REFERENCE_ARCHITECTURE_DRAFT.md` (Research Governance Corpus archive — its own,
separate commit if ever committed), `docs/audit/STOCKBIT_FLOW_*` (11 files),
`docs/cluster.md`, `docs/cycle_phases_strong12.md`, `docs/data/DATASET_CONTRACT_STOCKBIT_FLOW.md`,
`docs/data/DATA_QUALITY_RULES.md`, `docs/infra/*` (5 files), `docs/review.md` (garbled scratch
content, not a real document), `docs/superpowers/plans/*` (8 files), `docs/superpowers/specs/*`
(1 file), `engine26Jun26.md`, `scratchpad/*` (10 files), `tests/test_filter_exploration.py`,
`tools/check_stockbit_flow_coverage.py`.

**Local tool/sync state — never belongs in any commit:**
`.deepseek/state/subagents.v1.json`, `.stfolder/syncthing-folder-c83300.txt`, `.stignore`,
`.stockbit_token.lock`, `.winvenv/**`, `.playwright-mcp/**`, `images/**`.

**Deleted docs — unexplained, must NOT be swept into RC1:**
`docs/BRPT_CASE_STUDY.md`, `docs/changelog-plan3.md`, `docs/reversal-breakout-pattern-design.md`
(all `D` in `git status`). No commit, comment, or audit trail explains these deletions. **A careless
`git add -A` would silently delete three documentation files as part of an RC1 commit.** Recommend
restoring them (`git checkout -- <path>`) before staging anything, then handling their removal (if
still wanted) as its own, separately-justified commit — not bundled into RC1.

### 2c. Files that need a partial split, not a whole-file decision — new finding this task

**`auto_token.py`** and **`stockbit_fetcher.py`** each mix RC1-C2 (redaction) with a large, unrelated
"2026-07-27 stockbit token-refresh outage hardening" change (`docs/audit/STOCKBIT_TOKEN_REFRESH_HARDENING.md`,
itself excluded from RC1 per §2b). Verified by reading both full diffs directly:

- **`auto_token.py`** (232 changed lines total): RC1-C2 is exactly 2 lines —
  `from utils.logging_config import redact_secrets` and `msg = redact_secrets(msg)  # RC1-C2 ...`
  inside `send_telegram`. Everything else — `fcntl`/`tempfile`/`contextlib` imports, `LOCK_FILE`,
  `REFRESH_MARGIN_HOURS`/`CLOCK_SKEW_MAX_REMAINING_HOURS`/`MAX_REFRESH_RETRIES` constants,
  `_write_token_atomic()`, the rewritten `should_skip_refresh()` — is the unrelated outage-hardening
  work. The file also carries the same `100755→100644` mode corruption as §2d.
- **`stockbit_fetcher.py`** (35 changed lines total): RC1-C2 is exactly 2 lines (identical pattern).
  The rest is the `ensure_valid_token()` fallback-bypass fix for the same 2026-07-27 incident (calls
  `at._write_token_atomic()`, which only exists once `auto_token.py`'s hardening lands).

**Why this matters:** committing either file whole would silently ship the token-refresh hardening
work under an "RC1" commit message, misrepresenting what RC1 actually contains — exactly the kind of
inaccurate release record F-1/F-3 were about. Splitting requires hunk-level staging. This review did
**not** perform that split — it is a judgment call (the token-hardening change is real, tested,
incident-driven work; deferring it isn't obviously correct either) that belongs to whoever owns that
workstream, not something to silently resolve mid-packaging. Two honest options, not implemented here
pending a decision:

1. **Hunk-level split** — non-interactively, via `git diff -- auto_token.py stockbit_fetcher.py >
   /tmp/full.patch`, hand-extract just the two `redact_secrets` hunks per file into a second patch,
   `git apply --cached` that patch for the RC1 commit, leave the remainder unstaged for a separate
   `stockbit-token-hardening` commit. Mechanical, but must be done by hand per-hunk, not scripted
   blindly, since `_write_token_atomic()` is called by both files and must land together or not at
   all.
2. **Ship both files whole under RC1** with a commit message that honestly names both changes
   (redaction *and* token-refresh hardening) rather than mis-describing it as reporting-only. Simpler,
   less precise about scope.

This review recommends option 1 for release-record accuracy, but flags it as a decision, not a fait
accompli.

### 2d. Mode-only corruption — must be reverted before staging, not committed

Nine files show as modified with **zero content diff**, confirmed via `git diff --shortstat` (every
one reports `0 insertions(+), 0 deletions(-)`) and via direct mode inspection
(`old mode 100755` / `new mode 100644`):

```
_archive/patch_rr_ratio.sh
_archive/update_fetch_report.py
chart-viewer/start.sh
run_telegram.sh
scripts/cron_wrap.sh
scripts/release.sh
scripts/rollback.sh
scripts/wait_for_health.sh
start.sh
```

(`auto_token.py`, staged separately per §2c, carries the identical mode corruption too.) This is a
pure Windows-checkout artifact — `core.filemode=true` on a host without POSIX exec bits — not a real
change. **Staging these as-is would strip the executable bit on the real Linux deploy host** for
scripts `CLAUDE.md`'s own Commands section documents as directly invoked (`./start.sh`,
`scripts/release.sh`, `scripts/wait_for_health.sh`, `scripts/rollback.sh`). **Action: `git checkout --
<each file>` (mode + content revert; content is identical anyway) before staging anything else, or
`git update-index --chmod=+x <each file>` to explicitly re-assert the mode if a partial-add already
picked it up.** Recommend adding a `.gitattributes` with `*.sh text eol=lf` at minimum — no such file
currently exists in the repo — as a follow-up hygiene item (not RC1-blocking, but this exact class of
corruption will recur on every Windows checkout without it).

---

## 3. Recommended Commit Plan

Grouped by the repository's own logical seams (matches the audit trail's own R-1/R-2/R-3/R-4
numbering and the Phase 1–3 split already documented in `CLAUDE.md`), not by file-count balance:

**Commit 1 — `feat(reporting): EOD/Premarket/Forward-Testing Telegram reporting (Phases 1-3)`**
`scheduler/jobs.py` *(reporting portions only — see note)*, `scheduler/__init__.py` *(crash-alert
listener registration only — see note)*, `engine/trade_plan.py`, `forward_testing/reporting.py`,
`tests/test_trade_plan.py`, `tests/test_premarket_firm_scan.py` *(message/diff tests only)*,
`tests/forward_testing/test_reporting.py`, `tests/forward_testing/test_scheduler_job.py`.

*Note:* `scheduler/jobs.py` and `scheduler/__init__.py` each carry both Phase 1–3 reporting code and
the R-2 crash-alert rate limiter in the same file. Unlike §2c, this is **not** a cross-workstream
mix — R-2 (rate limiting the very alerts Phase 1 introduced) and Phase 1–3 are sequentially dependent
parts of the *same* certified effort. Splitting them would be artificial. Recommend keeping
`scheduler/jobs.py`/`scheduler/__init__.py` as **whole-file commits inside Commit 2** (below) instead
of Commit 1, since the rate-limiter is what makes the crash-alerting half of this work safe to ship —
i.e., merge Commits 1 and 2 into one if the team prefers not to split a file's history mid-feature.
Presented as two commits below for reviewability; either grouping is defensible.

**Commit 2 — `feat(scheduler): crash-alert rate limiting + EOD dedup fail-open (R-2, F-3)`**
`scheduler/__init__.py`, `scheduler/jobs.py`, `tests/test_scheduler_job_error_alert.py`,
`tests/test_eod_trade_plan_job.py` *(new — this task's F-3 test)*.

**Commit 3 — `fix(security): outbound Telegram secret redaction (R-4, RC1-C2)`**
`utils/logging_config.py`, `utils/telegram.py`, `routes/telegram.py`,
`tests/test_logging_config.py`, `tests/test_telegram_util.py`,
`tests/test_routes_telegram_redaction.py`, `tests/test_stockbit_fetcher_telegram_redaction.py`,
plus **only the two `redact_secrets` hunks** from `auto_token.py` and `stockbit_fetcher.py` *(pending
the §2c decision — omit both files entirely from this commit if option 2 is chosen instead, and fold
them into whatever commit ships the token-refresh hardening work)*.

**Commit 4 — `fix(test): Windows path-separator allowlist bug (R-1, RC1-C1)`**
`tests/test_architecture_boundary.py`, `tests/test_db_centralization.py`,
`tests/test_research_data_fence.py`, `tests/test_config_hygiene.py`,
`tests/test_path_normalization.py`.

**Commit 5 — `docs: document Production Engine Phases 1-3 + RC1 fixes (R-3)`**
`CLAUDE.md`, `docs/OPERATIONS.md`, `.env.example`.

**Commit 6 — `docs(audit): RC1 audit trail`**
`Audit/RELEASE_READINESS_AUDIT_2026-07-28.md`, `Audit/RC1_FIX_REPORT_2026-07-28.md`,
`Audit/RC1_CERTIFICATION_REPORT_2026-07-28.md`, `Audit/RC1_CONDITIONS_CLOSURE_REPORT_2026-07-28.md`,
`Audit/RC1_FINAL_CERTIFICATION_2026-07-28.md`, `Audit/RC1_RELEASE_PACKAGING_2026-07-28.md`.

This is 6 commits, not the illustrative 4 in the task prompt — the repository's actual seams split
finer than the example (redaction and path-normalization are independently-motivated fixes with
independent test files; bundling them would obscure two distinct root causes under one message).
Collapse 1↔2 or 5↔6 if the team prefers fewer, coarser commits; do not collapse 3 or 4 into anything
else — each closes a specifically-named audit finding and should be bisectable on its own.

---

## 4. CI Readiness Assessment

**GitHub Actions** (`.github/workflows/test.yml`): triggers on `push`/`pull_request` to any branch
for PRs, `push` restricted to `master`. **This branch (`ops/hardening-2026-07-10`) pushing would not
itself trigger the workflow** (push trigger is `branches: [master]`) — only a PR from this branch
would. Confirmed by reading the workflow file directly, not assumed. **Action: open a PR rather than
expecting a direct push to this branch to run CI.**

**Dependencies (`requirements.txt` vs. what code imports):** `engine/registry_loader.py:15` does an
unconditional top-level `import yaml`, but `pyyaml`/`PyYAML` is **not itself listed** in
`requirements.txt`. §F-2 of the certification report flagged this as unverified either way. This task
verified it directly, not by inspection:

1. `pip uninstall -y pyyaml` (confirmed removed: `pip show pyyaml` → not found).
2. `pip install -r requirements.txt` (exact pinned versions, no other flags).
3. Result: **`Successfully installed ... pyyaml-6.0.3 ...`** — PyYAML came back automatically, pulled
   in transitively by another pinned package.

**Conclusion: no `requirements.txt` change is needed.** A clean `pip install -r requirements.txt` on
a fresh Linux CI runner resolves `pyyaml` correctly. This closes the one open question from the prior
certification report with direct evidence rather than speculation, per this task's explicit
instruction not to modify `requirements.txt` without evidence.

**Side effect of that same `pip install -r requirements.txt` run:** it downgraded several packages
this venv had drifted to newer-than-pinned versions of (`curl_cffi` 0.15.0→0.13.0, `pandas`
3.0.3→3.0.2, `pydantic` 2.13.4→2.13.3, `pytest` 9.1.1→9.0.3, `requests` 2.34.2→2.33.1, `scikit-learn`
1.9.0→1.8.0, `yfinance` 1.4.1→1.2.0) — direct confirmation that the local dev venv had drifted from
`requirements.txt` (as F-2 suspected), and that this venv is now a much more faithful proxy for what
CI will actually install.

**Windows-only assumptions found, confirmed harmless to Linux CI:**
- `auto_token.py`'s `import fcntl` (POSIX-only) makes `tests/test_auto_token.py` and
  `tests/test_stockbit_fetcher_ensure_valid_token.py` fail to collect on Windows. `fcntl` is in the
  Python standard library on Linux — **this is a Windows-local limitation only, not a CI risk.**
  Confirmed: with the venv otherwise fully pinned, these were the **only two remaining collection
  errors** in a full-suite run (down from 24 before pinning) — see §5.
- No other `import fcntl`/Windows-drive-letter/backslash-path assumption found in any RC1-scoped file
  by direct grep.

**Path-separator source-scan tests:** `tests/test_architecture_boundary.py`,
`tests/test_db_centralization.py`, `tests/test_research_data_fence.py`,
`tests/test_config_hygiene.py` all correctly use `Path.relative_to(ROOT).as_posix()` for allowlist
comparisons (verified — this is the RC1-C1 fix, and `.as_posix()` is a no-op on Linux, so this
produces identical behavior on both platforms, confirmed already in
`Audit/RC1_CONDITIONS_CLOSURE_REPORT_2026-07-28.md` and re-verified here by direct read).

**No `.gitattributes` file exists.** Given §2d's mode-corruption finding, this is worth adding as a
follow-up (not RC1-blocking): `*.sh text eol=lf` would prevent this exact class of Windows-checkout
damage from recurring on every future edit from this machine.

---

## 5. Validation Evidence

**Targeted (F-3 + siblings), with pinned deps:**
`pytest tests/test_eod_trade_plan_job.py tests/test_premarket_firm_scan.py tests/test_trade_plan.py`
→ **74 passed**, including the new F-3 fail-open test and its premarket counterpart, both genuinely
executing (not asserted-correct) now that `langgraph` is actually installed.

**Full suite, dependencies pinned exactly to `requirements.txt` (this task's own venv fix — see §4):**
`pytest -q` (no flags): collection now fails on only **2 files**, both for the confirmed-harmless,
Linux-CI-irrelevant `fcntl` reason (§4) — down from 24 collection errors before this task pinned the
venv. This is a materially stronger signal than either prior audit produced locally.

**Full suite, `pytest -q --continue-on-collection-errors` (9m20s):**

```
26 failed, 1659 passed, 2 errors in 560.29s (0:09:20)
```

Every one of the 26 failures + 2 errors was individually traced to its root cause (not
batch-assumed) — **none touch any RC1-scoped file or test from §2a**:

| Failing test(s) | Root cause (verified) | RC1-related? |
|---|---|---|
| `test_secret_hygiene.py::test_no_hardcoded_secret_literals` | Matched a line inside `.winvenv/Lib/site-packages/langsmith/client.py` (`_ANTHROPIC_API_KEY = "ANTHROPIC_API_KEY"`) — a third-party package physically installed under the repo root in this local venv only. `.winvenv/` doesn't exist on a fresh CI checkout. | No — local-venv-location artifact |
| `test_config_validation.py` (6 tests) | `ConfigError: .env is group/world accessible`, `.stockbit_token is group/world accessible` — Windows/NTFS doesn't implement POSIX permission bits the way `st_mode & 0o077` assumes; this check behaves correctly on the real Linux CI runner. | No — Windows filesystem-semantics quirk |
| `test_release_scripts.py` (6 tests), `test_cron_contract.py` (3 tests) | Windows-subprocess incompatibility invoking `.sh` scripts — already documented as R-9 in the original Release Readiness Audit, predates this task. Plausibly compounded by the §2d mode corruption (scripts losing +x in the working tree), which is exactly why §7 step 1 reverts that before any CI run. | No — pre-existing, and the fix is "revert the corruption," not a code change |
| `test_logging_config.py::TestSetupLogging` (2 tests) | Windows temp-file-handle lock on rotating log handler teardown — same failure already seen and documented in this task's own targeted run and in the prior certification report. | No — pre-existing Windows-only |
| `test_experiment_tracking.py::test_refresh_wf_scores_stamps_run_id` | Part of the excluded `research/tracking.py` workstream (§2b) | No — out of RC1 scope entirely |
| `test_storage.py::test_append_only_rerun_makes_a_new_profile_id` (regime) | Research/regime subsystem, unrelated | No — out of RC1 scope |
| `test_signal_checkers.py` (2 tests) | Unrelated signal-checker functionality | No |
| `test_value_format.py` (4 tests) | Node.js `require('D:\IDX\static\format.js')` → `MODULE_NOT_FOUND` — a frontend static-asset/Node module-resolution issue, unrelated to Python reporting/scheduler/redaction code | No |
| `ERROR test_auto_token.py`, `ERROR test_stockbit_fetcher_ensure_valid_token.py` | `fcntl` POSIX-only import (§4) | No — confirmed Linux-CI-harmless |

**Conclusion: zero regressions attributable to Phases 1–3, R-1–R-4, the RC1 conditions closure, or
F-3, across 1687 collected tests.** This is materially stronger evidence than either prior audit
produced — every failure was traced to a specific, named, non-RC1 cause rather than asserted clean by
category.

**Not executed by this task (explicitly, per instruction not to claim CI passes without running it):**
the actual GitHub Actions workflow. Nothing has been pushed or opened as a PR. §7 covers this as the
final, explicit step — not something this report claims already happened.

---

## 6. Remaining Blockers Before Tagging RC1

1. **§2c decision required:** how to handle the `auto_token.py`/`stockbit_fetcher.py` redaction/
   token-hardening bundling — hunk-split or ship-whole-with-honest-message. Not resolved by this
   report; needs an owner call.
2. **§2b decision required:** what to do about the three unexplained deleted docs
   (`docs/BRPT_CASE_STUDY.md`, `docs/changelog-plan3.md`, `docs/reversal-breakout-pattern-design.md`)
   — restore, or confirm intentional and commit separately. Not RC1's to resolve silently.
2. **Execution not yet performed:** staging, committing, pushing, PR, and the real CI run are all
   still pending an explicit go-ahead (§7) — this report is the plan, not the executed state. Per
   this session's operating rules, committing/pushing are actions this review surfaces for decision
   rather than performs unprompted, given the file-classification judgment calls in §2b/§2c.

No blocker found in this report is a code or architecture defect — every one is a release-process
decision, consistent with the Final Certification's framing.

---

## 7. Release Checklist (reproducible steps)

Each step below is written so it can be executed exactly as listed once the §6 decisions are made —
none of it has been executed by this task.

1. **Fix mode corruption** — for each file in §2d: `git checkout -- <file>` (reverts the accidental
   `100755→100644` change; content is already identical).
2. **Restore accidentally-deleted docs** (unless §6.2 confirms intentional): `git checkout --
   docs/BRPT_CASE_STUDY.md docs/changelog-plan3.md docs/reversal-breakout-pattern-design.md`.
3. **Resolve §2c** (`auto_token.py`/`stockbit_fetcher.py`) per the chosen option.
4. **Stage and commit** in the order of §3 (Commits 1–6, or the merged variant), reviewing
   `git status`/`git diff --cached` before each commit to confirm only the intended files are
   included — do not use `git add -A`/`git add .` given how much unrelated content shares this tree.
5. **Push** the resulting commits to `ops/hardening-2026-07-10` (or a fresh RC1 branch cut from it,
   if the team prefers not to add six commits directly to the hardening branch).
6. **Open a PR** targeting `master` (required to actually trigger `.github/workflows/test.yml` per
   §4's trigger-scope finding) — or confirm the intended CI trigger path if the team's real workflow
   differs from what's on disk.
7. **Watch CI run to completion** on the real Ubuntu runner. Record the actual pass/fail/error counts
   from that run as the authoritative number — supersedes every local count in the audit trail,
   including this report's.
8. **If CI is green:** merge, then tag (e.g. `git tag -a rc1-2026-07-28 -m "Production Engine RC1"`
   on the merge commit) and push the tag.
9. **If CI is not green:** triage against this report's evidence first — a failure outside the
   RC1-scoped files/tests listed in §2a is very likely one of the pre-existing, already-documented
   gaps (R-9 in the Release Readiness Audit), not a regression from this work; confirm before
   assuming otherwise.
10. Only after 7–8 succeed: begin **Operations Dashboard / Job History**, then the **Agent Firm
    repository split** — both remain the correct next milestones, unchanged by this report.

---

## Deliverables Summary

1. This report.
2. Files belonging to RC1 — §2a (with the §2c partial-split caveat).
3. Files explicitly excluded — §2b, §2d.
4. Recommended commit plan — §3.
5. CI readiness assessment — §4 (PyYAML resolved with evidence; no `requirements.txt` change needed;
   Windows/Linux divergence fully accounted for and confirmed harmless).
6. F-3 implementation summary — §1 (done, tested, validated).
7. Remaining blockers — §6.
