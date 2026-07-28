# Production Engine — Final RC1 Certification (Independent Review)

**Date:** 2026-07-28
**Role:** Independent Release Certification Board — final pass over
`Audit/RELEASE_READINESS_AUDIT_2026-07-28.md`, `Audit/RC1_CERTIFICATION_REPORT_2026-07-28.md`,
`Audit/RC1_CONDITIONS_CLOSURE_REPORT_2026-07-28.md`. Adversarial mandate: attempt to prove RC1 is
**not** ready. No prior report's claim was accepted without direct re-derivation from the live
repository (current file contents, live `git status`/`git diff`, live `pytest` runs).
**Constraint honored:** inspection only — no code, test, or documentation file was modified during
this certification.

---

## Executive Summary

**The three prior audits' technical claims about the code substantially hold up.** R-1 (architecture
boundary), R-2 (rate limiting), R-4 (redaction completeness), and both RC1 conditions (path
normalization, standalone-sender redaction) are genuinely fixed in the working tree, verified by
direct inspection and by re-running the relevant tests, not by trusting the prior reports' summaries.
The reporting layer (EOD/Premarket/Forward-Testing) is genuinely read-only/deterministic over
already-decided engine outputs, as claimed.

**But this certification finds one Critical and one High issue none of the three prior audits
surfaced, both about the state the "RC1" candidate is actually in — not about the code's logic:**

1. **(Critical) Nothing is committed.** Every file touched by Phases 1–3 and by both RC1 fix rounds —
   `scheduler/__init__.py`, `scheduler/jobs.py`, `engine/trade_plan.py`, `forward_testing/reporting.py`,
   `utils/telegram.py`, `utils/logging_config.py`, `auto_token.py`, `stockbit_fetcher.py`, every new
   test file, and `CLAUDE.md` itself — exists **only as uncommitted working-tree state** on top of
   HEAD (`c75f16e`, a research-governance commit unrelated to any of this work). There is no commit,
   no branch, no PR, and — because GitHub Actions triggers on `push`/`pull_request` — **no CI run has
   ever executed against this code.** Three audit reports "certified" this work using local,
   ad-hoc `pytest` runs on a Windows dev venv, never the actual CI gate the repository relies on
   (`CLAUDE.md`'s own Decision-Making Hierarchy: "a CI-enforced test is ground truth"). You cannot
   tag a version, cite a commit SHA, or open a PR against work that isn't committed. `git status`
   during this review additionally shows two unrelated uncommitted deletions
   (`docs/BRPT_CASE_STUDY.md`, `docs/changelog-plan3.md`, `docs/reversal-breakout-pattern-design.md`)
   sitting in the same tree — an accidental `git add -A`/commit here would ship unrelated destructive
   changes alongside RC1.

2. **(High) The prior audits' own reproducibility claims do not reproduce today.** The Conditions
   Closure Report states a full-suite run of **1452 passed / 55 failed / 6 errors**. Running the
   exact documented command (`pytest -q`, per `CLAUDE.md`'s own Commands section) on this same host
   right now does not produce those numbers — it does not produce *any* numbers: `pytest -q` aborts
   entirely with `Interrupted: 24 errors during collection`, because `feedparser`, `langgraph`, and
   `pyyaml` (all in `requirements.txt`, `pyyaml` **not** in `requirements.txt` despite
   `engine/registry_loader.py` importing it unconditionally) are currently missing from this venv.
   Forcing collection through (`--continue-on-collection-errors`) gives **1501 passed / 58 failed /
   30 errors** — passes, failures, *and* errors all differ from the audit trail's numbers. This is
   very likely environment drift in a local dev venv, not a real regression (see Finding F-2 for the
   detailed reconciliation), but it means the specific pass/fail/error counts in the audit trail are
   **not independently reproducible today**, and the only trustworthy signal — a real GitHub Actions
   run against committed code — has never happened for this candidate.

Beyond these two, one new **Medium** finding not previously reported: **`run_eod_trade_plan`'s dedup
guard has no fail-open handling for `sqlite3.OperationalError`, unlike its sibling `run_premarket_firm_scan`
guard, which was patched for exactly this failure mode after a real 2026-07-24 production crash** — and
the EOD job's own code comment states its 16:40 slot is *more* likely to hit write contention than
premarket's, not less (Finding F-3).

---

## Certification Decision

**NOT CERTIFIED** as an unconditional RC1 tag/ship point, but **the code is CERTIFIED WITH CONDITIONS
at the implementation level** — i.e., once the two process-blockers below are resolved (commit +
real CI green), and the one new Medium code finding is either fixed or explicitly accepted as debt,
there is no remaining implementation blocker known to this review.

This is a narrower "not certified" than it may sound: **no finding in this report says the reporting
logic, redaction, or rate-limiting is wrong.** The blockers are that the artifact being certified —
"RC1" — does not yet exist as a citable, CI-verified unit of work. Certifying a working tree that has
never been committed or run through CI would make the certification unfalsifiable by the same
CI-ground-truth standard this repository's own `CLAUDE.md` mandates.

---

## Findings

### F-1 — Critical — RC1 candidate is entirely uncommitted; zero CI evidence exists

**Evidence:**
- `git log -1`: HEAD is `c75f16e feat(tracking): capture runtime environment provenance in
  research_runs` — a research-governance commit with no relation to Telegram reporting, scheduler
  alerting, or redaction.
- `git status --porcelain -uall` shows 41 tracked files modified and dozens of new files untracked,
  including every file the three audit reports discuss as "fixed": `scheduler/__init__.py`,
  `scheduler/jobs.py`, `engine/trade_plan.py`, `forward_testing/reporting.py` (untracked — a brand
  new module, never `git add`ed), `utils/telegram.py`, `utils/logging_config.py`, `auto_token.py`,
  `stockbit_fetcher.py`, `tests/test_path_normalization.py`,
  `tests/test_stockbit_fetcher_telegram_redaction.py`, `tests/test_scheduler_job_error_alert.py`,
  `tests/test_routes_telegram_redaction.py`, `tests/test_auto_token.py`, and — notably — `CLAUDE.md`
  itself.
- `CLAUDE.md` is untracked (`??`) despite being described throughout this review's own system context
  as "checked into the codebase." Direct check: `git cat-file -e HEAD:CLAUDE.md` →
  `fatal: path 'CLAUDE.md' exists on disk, but not in 'HEAD'`. `git log --follow -- CLAUDE.md` shows
  it was last touched by commit `6ac9aa1 "Auto-sync from VS Code"` (2026-04-23), which **deleted** 14
  lines of the old `CLAUDE.md` and never restored the file — the elaborate governance manual this
  review (and R-3's "fix") relies on has **no git history at all**. A `git stash`, `git checkout .`,
  or disk loss on this machine would silently erase the canonical operating manual with no way to
  recover it from version control.
- `Audit/*.md` — every audit report in the trail, including the two "CERTIFIED" reports — is itself
  untracked. The certification record for this release exists nowhere but a local disk.
- `.github/workflows/test.yml` triggers only `on: push` / `on: pull_request`. Since nothing has been
  pushed, **no run of the actual CI gate has ever evaluated any line of this work.** Every "tests
  pass" claim in the audit trail is a local, ad-hoc `pytest` invocation on a Windows dev venv — a
  venv the audit trail itself repeatedly flags as having platform-specific gaps (missing `fcntl`,
  path-separator bugs) that don't exist on the real Linux CI runner. Local-only verification of code
  whose target environment is explicitly different is a materially weaker signal than the CI run this
  repository is designed to depend on.
- The same uncommitted tree also carries **unrelated deletions**: `docs/BRPT_CASE_STUDY.md`,
  `docs/changelog-plan3.md`, `docs/reversal-breakout-pattern-design.md` (all `D` in `git status`),
  plus dozens of unrelated untracked files (`Audit/CLAUDE_PROVIDER_RCA_2026-07-10.md`, scratch
  scripts, PDFs, screenshots). A careless `git add -A && git commit` to "ship RC1" would silently
  bundle these unrelated changes — including three documentation deletions nothing in this review's
  scope justifies — into the same commit.

**Why it matters:** RC1 as a concept implies a citable, immutable artifact — a tag or commit SHA that
can be deployed, rolled back to, and independently re-verified. What exists today is a live working
directory that could be altered or lost at any moment, with three "certification" documents whose
only evidence is that same mutable directory. This is exactly the class of gap `CLAUDE.md`'s own
Decision-Making Hierarchy warns about: "documents self-report, tests verify" — except here, the tests
that "verified" the work also never ran against anything durable.

**Required action:** Commit the Phase 1–3 + RC1-fix + RC1-conditions-closure changes as scoped,
reviewed commits (excluding the unrelated doc deletions and scratch files unless those are
independently intended); push to a branch; open a PR (or push directly per this repo's workflow) so
`.github/workflows/test.yml` actually runs on Linux; only then treat "tests pass" as verified. This
is a process/governance action, not a code change, and does not contradict this task's "inspect only,
don't implement" constraint — it is the prerequisite for certification to mean anything.

### F-2 — High — Prior audits' full-suite pass/fail/error counts do not reproduce on re-run

**Evidence:** `Audit/RC1_CONDITIONS_CLOSURE_REPORT_2026-07-28.md` §5 states "1452 passed / 55 failed
/ 6 errors" from a full-suite run. Re-running `pytest -q` (the exact command `CLAUDE.md` documents)
on this host right now:

```
!!!!!!!!!!!!!!!!!! Interrupted: 24 errors during collection !!!!!!!!!!!!!!!!!!!
24 errors in 6.47s
```

Zero tests execute — pytest's default behavior aborts the whole session on any collection error
without `--continue-on-collection-errors`. Forcing collection through instead:

```
58 failed, 1501 passed, 30 errors in 667.10s (0:11:07)
```

Neither the pass count, fail count, nor error count matches the audit trail's figures. Root cause,
verified directly: `pip show feedparser langgraph pyyaml` on this venv → `Package(s) not found:
feedparser, langgraph, pyyaml`, while `requirements.txt` pins `feedparser==6.0.12` and
`langgraph==1.2.0` (both present in the manifest but absent from the venv — the venv has drifted from
`requirements.txt`) and **`pyyaml` is not in `requirements.txt` at all**, despite
`engine/registry_loader.py:15` doing an unconditional top-level `import yaml`. This last point is a
finding in its own right: if nothing else in `requirements.txt` pulls in PyYAML transitively, the
real CI runner (`pip install -r requirements.txt` on a clean Ubuntu image) would hit the identical
`ModuleNotFoundError: No module named 'yaml'` that this venv hits — this was **not verified either
way** by this review (would require a clean-room `pip install`), and should be checked before relying
on CI green.

**Why it matters:** The prior audits' "full suite regression-free" claims are the single piece of
evidence offered that Phases 1–3 and both fix rounds introduced no regressions elsewhere in a
1500+-test suite. That evidence is not reproducible today on the same machine with the same command.
This doesn't mean a regression exists — the 3 additional failures/errors beyond the known set are, on
inspection, concentrated in files this review independently confirmed are environment-sensitive
(`test_edge_selector.py` errors trace to the same missing-package class) — but "not reproducible" and
"confirmed regression-free" are different claims, and the audit trail asserts the stronger one without
current support.

**What this review positively confirmed instead (narrower, but solid):** the RC1-relevant targeted
subset — `test_architecture_boundary.py`, `test_research_data_fence.py`, `test_db_centralization.py`,
`test_config_hygiene.py`, `test_path_normalization.py`, `test_logging_config.py`,
`test_telegram_util.py`, `test_routes_telegram_redaction.py`, `test_scheduler_job_error_alert.py`,
`test_stockbit_fetcher_telegram_redaction.py`, `forward_testing/test_reporting.py`,
`forward_testing/test_scheduler_job.py`, `test_premarket_firm_scan.py`, `test_trade_plan.py`,
`tests/security/test_secret_hygiene.py` — ran clean at **173 passed, 3 failed**, and all 3 failures
are the already-documented, environment-only issues (Windows temp-file handle lock,
`ModuleNotFoundError: No module named 'langgraph'`). This is real, direct evidence the RC1-scoped code
itself is sound; it just isn't the full-suite claim the audit trail makes.

**Required action:** Before trusting any full-suite number again, either (a) rebuild the local venv
from `requirements.txt` exactly and re-run, or (b) rely solely on the real CI run once F-1 is
resolved. Separately, verify `pyyaml` is actually available in the CI environment (transitively or
add it explicitly to `requirements.txt` if not) — this is a one-line, low-risk fix if needed, but
unverified either way by this review.

### F-3 — Medium — `run_eod_trade_plan`'s dedup guard lacks the fail-open handling its sibling job
was specifically patched to have, and the EOD job self-documents higher contention risk

**Evidence:** `scheduler/jobs.py:768-801` (`run_premarket_firm_scan`):

```python
try:
    _g.execute("INSERT INTO _job_sentinel VALUES ('premarket_firm', ?)", (date_str,))
except sqlite3.IntegrityError:
    logger.info(...); return
except sqlite3.OperationalError as e:
    logger.warning(f"...dedup guard error (fail-open): {e}"); return
```

`scheduler/jobs.py:956-963` (`run_eod_trade_plan`):

```python
with db_connect(DB_PATH) as _g:
    _g.execute("CREATE TABLE IF NOT EXISTS _job_sentinel ...")
    try:
        _g.execute("INSERT INTO _job_sentinel VALUES ('eod_trade_plan', ?)", (date_str,))
    except sqlite3.IntegrityError:
        logger.info(...); return
    # no except sqlite3.OperationalError
```

`tests/test_premarket_firm_scan.py::test_run_premarket_firm_scan_fails_open_on_sentinel_db_lock`'s
own docstring: *"Reproduces the 2026-07-24 08:35:30 production crash: run_premarket_firm_scan let
sqlite3.OperationalError propagate out of the scheduler job instead of failing open like the
bear-watchlist code path a few lines away."* — i.e., an unhandled `OperationalError` on this exact
dedup-insert pattern already crashed a production job once, and premarket was fixed for it. EOD's own
adjacent comment (`scheduler/jobs.py:953-955`): *"30s busy_timeout waits out transient writers (the
16:40 slot can overlap a long EOD write on the 2.5GB WAL db, unlike the quiet 08:35 premarket
slot)"* — the code's own author-supplied rationale states the EOD slot is *more* exposed to exactly
the condition premarket was hardened against, yet EOD has no equivalent guard. `run_forward_test_cycle`
is unaffected — its entire dedup block sits inside the function's own outer `try/except Exception`
(verified: `scheduler/jobs.py:1207...1289` wraps the whole body, catching everything including
`OperationalError` on the insert), matching its documented "never raise on any error" contract.

**Why it matters:** If the EOD dedup insert does hit lock contention beyond the 30s `busy_timeout`
(plausible per the code's own comment, on a "2.5GB WAL db" during a "long EOD write"), the resulting
unhandled `sqlite3.OperationalError` propagates out of `run_eod_trade_plan` entirely — the flagship
daily "consolidated trade plan" report simply does not send that day, surfaced only via the new
`EVENT_JOB_ERROR` crash alert rather than degrading gracefully like premarket does. This is now
observable (thanks to R-2's crash alerting) rather than silent, which limits the severity, but it is
an availability gap in exactly the report this whole effort was built to make more reliable, in the
exact failure mode already proven to occur in production once.

**Required action:** Add the same `except sqlite3.OperationalError as e: logger.warning(...); return`
branch to `run_eod_trade_plan`'s dedup guard, mirroring premarket's. Small, mechanical, same pattern
already proven — no design decision required. Not blocking if the team accepts the residual risk
explicitly (30s busy_timeout may already make this rare enough to defer), but it should be a
conscious decision, not an oversight.

---

## Validation of prior audit claims — what independently reproduced clean

- **Architecture boundary (R-1):** `routes/backtest.py`, `routes/screener.py`, `routes/portfolio.py`,
  `routes_backtest_multi.py` are the only `research.*` importers in production scope, all correctly
  re-admitted to `_ROUTES_DEBT` (4 entries, matching `CLAUDE.md`'s stated cap) with a dated,
  substantive justification comment (not a bare re-add). `_ROUTES_WRITE_DEBT = {"routes/backtest.py"}`
  matches. `pytest tests/test_architecture_boundary.py tests/test_research_data_fence.py
  tests/test_db_centralization.py` — all pass.
- **Path normalization (RC1-C1):** `tests/test_config_hygiene.py`'s `test_dotenv_loaded_only_in_config`
  correctly uses `.as_posix()`; the sibling `test_no_hardcoded_home_paths_in_production_code` was
  correctly left on `str(...)` since it's a diagnostic message, not an allowlist comparison — verified
  by reading both functions directly, not just trusting the closure report's characterization.
- **Redaction completeness (R-4 / RC1-C2):** all four `send_telegram` definitions repo-wide
  (`auto_token.py`, `stockbit_fetcher.py`, `utils/telegram.py`, and `routes/telegram.py`'s
  `send_telegram_reply`) call `redact_secrets()` — grepped every definition site directly, not just
  the two files the conditions report focused on. No fifth standalone sender found.
- **Rate limiting (R-2):** `JobErrorRateLimiter` correctly gates per-`job_id`, cooldown default 3600s,
  first failure always alerts, injectable clock for deterministic tests. Confirmed the one cosmetic
  gap the RC1 Certification Report already noted (`should_alert()` hardcodes `0` on the suppressed
  return for its `False` branch) — harmless, the sole caller ignores it.
- **Reporting determinism:** `forward_testing/reporting.py` and `engine/trade_plan.py`'s
  `diff_watchlist`/`record_snapshot` are genuinely read/aggregate-only over already-persisted columns
  — no score, rank, or decision is recomputed in either module, confirmed by reading the functions
  directly rather than trusting the module docstrings' self-description.
- **Cron schedule vs. documentation:** `scheduler/__init__.py` registers premarket at 08:35, EOD at
  16:40, forward-test at 18:30 — exact match to both `CLAUDE.md`'s and `docs/OPERATIONS.md`'s stated
  times.
- **Dedup guards / duplicate-send prevention:** all three jobs share the `_job_sentinel(job, run_date)`
  composite-primary-key table; first `INSERT` wins, atomic under WAL + `busy_timeout` — no
  check-then-insert TOCTOU gap in any of the three. (See F-3 for the one asymmetry found: EOD's
  narrower exception handling, not the guard's atomicity.)
- **Route classification:** `routes/telegram.py`'s endpoints are all classified in
  `security/route_policy.py` (`/telegram/updates` PUBLIC w/ HMAC, `/telegram/status` VIEWER, the
  mutating endpoints ADMIN) — no new unclassified route introduced by this work.
- **Documentation (R-3):** `CLAUDE.md`'s Scheduler section and `docs/OPERATIONS.md` both describe
  `watchlist_snapshot`, `EVENT_JOB_ERROR`/`JobErrorRateLimiter`, `SCHEDULER_JOB_ERROR_COOLDOWN_S`, and
  `forward_testing/reporting.py` accurately against the current code — genuinely no longer
  audit-report-only, **conditional entirely on F-1 being resolved** (an accurate document that isn't
  in version control isn't durably canonical).
- **No hardcoded secrets:** `tests/security/test_secret_hygiene.py` passed in the targeted run; no new
  secret-shaped literal found in any of the touched files by direct grep.

---

## Recommended Next Phase

**If the team accepts this report's framing** ("code-level CERTIFIED WITH CONDITIONS; release-process
NOT CERTIFIED until committed and CI-verified"):

1. Resolve F-1: stage and commit the Phase 1–3 + RC1-fix + RC1-conditions-closure work as scoped
   commits (leave the unrelated `docs/*` deletions and scratch files out unless separately intended),
   push, let the real CI run.
2. Resolve F-2 as a side effect of F-1 (CI is the authoritative signal once it exists) — separately
   confirm `pyyaml` resolves cleanly under a fresh `pip install -r requirements.txt` since it's not an
   explicit pin.
3. Decide on F-3 (apply the one-line `OperationalError` fail-open to `run_eod_trade_plan`, or
   explicitly accept the residual risk) — small enough to fold into the same commit series as F-1.
4. Once CI is green on committed HEAD, tag the RC1 version for real, and proceed to the previously
   agreed next phase: **Operations Dashboard / Job History**, then the Agent Firm repository split —
   both remain sound next steps; nothing in this review changes their scope or priority.

**No architecture change, feature redesign, or new implementation is required by this report.** Every
finding here is either a process gap (commit/CI) or a small, mechanical, already-proven-pattern fix
(F-3), consistent with the posture of every prior audit in this trail.
