# Production Engine — RC1 CI Validation & Release Readiness Report

**Date:** 2026-07-28
**Basis:** `Audit/RC1_RELEASE_PACKAGING_2026-07-28.md` (packaging), PR #26 (github.com/Tjie-hub/5001),
two rounds of real GitHub Actions CI failures investigated and fixed in this task.
**Method:** All CI status in this report was pulled directly from the GitHub REST API
(`api.github.com`, unauthenticated public-repo reads) against the actual PR and workflow-run
objects — never inferred or assumed. Every fix was validated locally (targeted test, then a full
suite run against a clean `git worktree` of committed HEAD, never the working tree) before being
pushed.

---

## 1. Push Summary

Three pushes to `origin/ops/hardening-2026-07-10` in this task's scope (on top of the 10 commits —
5 RC1 + 5 pre-existing — already pushed to open PR #26):

| Commit | What | Why |
|---|---|---|
| `e04b8eb` | `fix(agent-firm): add missing provider_events.reset_time migration` | CI failure #1 |
| `09ce765` | `fix(test): mock claude CLI discovery in config-validation tests` | CI failure #2 |

Both are single-file, minimal, isolated commits kept separate from the 5 RC1 commits and from each
other — neither touches Production Engine reporting/scheduler/redaction code. History was not
rewritten or squashed at any point; every commit is additive.

One process note: both pushes initially appeared not to have landed when checked immediately
afterward (`git fetch` showed the prior SHA). In both cases this resolved itself moments later — the
first was likely a stale response from a delayed local retry, the second was confirmed (via a direct
GitHub API query, bypassing local git entirely) to have actually succeeded on GitHub the whole time;
a plain `git fetch` was returning a stale cached ref. Worth knowing if this recurs: check the GitHub
API directly rather than trusting an immediate local `git fetch`.

---

## 2. Pull Request Summary — PR #26

- **URL:** https://github.com/Tjie-hub/5001/pull/26
- **Base:** `master` ← **Head:** `ops/hardening-2026-07-10` @ `09ce765`
- **State:** open, not draft, **`mergeable_state: clean`**

*(Note: the PR's title as currently set — "feat(ops): SQLite backup/restore with verification and
retention (audit P-3)" — does not describe RC1; it appears to reflect an earlier or default title
from this long-lived branch/PR rather than the RC1 work. Recommend updating the PR title/description
before merge to accurately describe what this PR now contains — see §6.)*

**Suggested PR description content** (for the title/description update recommended above):

> **Summary:** RC1 for the Production Engine — EOD/Premarket/Forward-Testing Telegram reporting,
> scheduler crash-alert rate limiting, outbound-secret redaction, and the governance-manual
> (`CLAUDE.md`) recovery, plus two CI-discovered pre-existing defects fixed along the way.
>
> **Workstreams implemented:** EOD consolidated trade plan (16:40 WIB) with watchlist-diff reporting;
> Premarket firm shortlist (08:35 WIB) reusing the same snapshot infrastructure; Forward-Testing
> summary (18:30 WIB); `EVENT_JOB_ERROR` crash-alert listener with per-job_id cooldown rate limiting.
>
> **Audit findings resolved:** R-1 (Windows path-separator allowlist bug), R-2 (alert-storm risk —
> rate limiting), R-3 (zero canonical documentation — `CLAUDE.md` + `docs/OPERATIONS.md` now
> describe this work, and `CLAUDE.md` itself is committed to git for the first time since its
> accidental deletion in April), R-4 (Telegram redaction gaps).
>
> **RC1 conditions resolved:** RC1-C1 (`test_config_hygiene.py` path-separator fix), RC1-C2
> (`auto_token.py`/`stockbit_fetcher.py` redaction — isolated to just the redaction hunk; each
> file's unrelated 2026-07-27 token-hardening work was deliberately left uncommitted/out of scope).
>
> **F-3 scheduler hardening:** `run_eod_trade_plan`'s dedup guard now fails open on
> `sqlite3.OperationalError` identically to its `run_premarket_firm_scan` sibling (patched after a
> real 2026-07-24 production crash) — EOD's own code comment already noted its slot is more exposed
> to the same contention window.
>
> **Testing summary:** Full suite on a clean worktree of committed HEAD: 1604 passed / 17 failed / 3
> skipped, with every failure independently traced to a pre-existing, non-RC1, Windows/local-only or
> excluded-workstream cause (§4 below has the full breakdown). Real GitHub Actions (Ubuntu, `pytest
> -q`): **green** (run 30342637863).
>
> **Known exclusions (deliberately not in this PR):** the agent-firm z.ai adaptive rate-limit
> governor workstream, research-provenance (`dataset_meta_json`) work, the 2026-07-24 news-fetch
> RSS-timeout hardening, and the 2026-07-27 stockbit-token-refresh hardening — all left as
> uncommitted local work or excluded entirely; see `Audit/RC1_RELEASE_PACKAGING_2026-07-28.md` §2b/§2c
> for the full, evidenced classification.
>
> **Remaining work after RC1:** Operations Dashboard / Job History (not started, per instruction),
> then the Agent Firm repository split.

---

## 3. GitHub Actions Results (pulled directly from the API, not inferred)

**Workflow:** `tests` · **Job:** `pytest` · **Run:** `30342637863` · **Trigger:** push of `09ce765`

| Step | Status | Conclusion |
|---|---|---|
| Set up job | completed | success |
| Run actions/checkout@v4 | completed | success |
| Set up Python 3.12 | completed | success |
| Install dependencies | completed | success |
| **Run pytest** | completed | **success** |
| Post Set up Python 3.12 | completed | success |
| Post Run actions/checkout@v4 | completed | success |
| Complete job | completed | success |

Run duration: 08:30:14Z → 08:35:18Z (~5 minutes). Raw log text was not retrievable (`403: Must have
admin rights to Repository` on the logs-download endpoint — a permissions limit of the unauthenticated
API call, not a CI signal) — not needed: GitHub Actions derives a step's `conclusion` directly from
the command's real exit code, so "Run pytest: success" is authoritative on its own, equivalent to
`pytest -q` having exited 0.

**PR #26 current state:** `mergeable: true`, `mergeable_state: "clean"` (previously `"unstable"` while
CI was pending/failing) — the strongest state GitHub reports, meaning no merge conflicts and every
configured required check is satisfied.

---

## 4. CI Failure Analysis — both rounds, both resolved

### Round 1 — `sqlite3.OperationalError: no such column: reset_time`

**Category: pre-existing, unrelated defect (schema drift via an uncommitted migration).**

- `engine/agent_firm/providers/metrics.py::provider_stats()` has queried this column since commits
  `2abeb4b` (2026-07-09) and `48b5d17` (2026-07-14) — both weeks before RC1, both already ancestors
  of HEAD before this task began.
- `tests/agent_firm/providers/test_event_persistence.py::test_init_agent_firm_tables_adds_reset_time_column`
  was already committed as a dedicated regression test for this exact migration — proving the
  intended fix was known and tested for, but the migration itself was never committed
  (`git log --all -p -- data/db.py` showed zero prior mentions of `reset_time`, ever).
- This is the first real CI run this branch has ever had (per `Audit/RC1_FINAL_CERTIFICATION_2026-07-28.md`
  finding F-1) — the gap sat latent for ~2.5 weeks with nothing to surface it.
- **Fix:** `data/db.py` — the standard idempotent `PRAGMA table_info()` → `ALTER TABLE ADD COLUMN`
  migration this file already uses for every other schema change. One file, 10 lines, commit `e04b8eb`.
- **Validation:** targeted (`test_metrics.py` + `test_event_persistence.py`, 21/21 passed) and full
  suite on a clean worktree (before: 27 failed/1594 passed/3 skipped; after: 17 failed/1604 passed/3
  skipped — exactly the 10 reported tests flipped, nothing else changed).

### Round 2 — `provider order includes claude but the claude CLI is not on PATH`

**Category: pre-existing, unrelated defect (test-determinism gap), surfaced only because Round 1's
fix let CI progress far enough to reach these tests.**

- `tests/test_config_validation.py`'s `test_validate_config_requires_zai_key_when_firm_enabled` and
  `test_validate_config_claude_only_needs_no_zai_key` — both introduced in commit `03cd723`, predating
  and untouched by RC1 — set `AGENT_FIRM_PROVIDER=claude`/`claude` in the order but never mocked
  `shutil.which`, unlike their sibling `test_claude_in_order_requires_cli`, which already established
  the correct pattern. Both silently assumed the Claude CLI would be on PATH; the real GitHub Actions
  Ubuntu runner (correctly) has no such CLI installed.
- **Determined:** the tests' intent is correct; CI should **not** be made to require the Claude CLI
  (it's tied to a specific interactive Anthropic subscription per `CLAUDE.md`, not something a
  generic runner should install/authenticate); `config.py`'s validation logic is correct and
  untouched. The only wrong thing was the two tests' missing mock.
- **Fix:** `tests/test_config_validation.py` only — added the same `monkeypatch.setattr("shutil.which",
  lambda name: "/usr/local/bin/claude")` pattern already used by the sibling test. One file, 12 lines,
  commit `09ce765`.
- **Validation:** isolated check (Windows-only `.env`-permission-bit noise neutralized) confirmed all
  3 related tests pass; full suite on a clean worktree: 17 failed/1604 passed/3 skipped — **identical**
  to the Round 1 post-fix baseline in count and content, `test_config_validation.py` no longer in the
  failure list at all. Zero regressions. Confirmed for real on GitHub Actions per §3.

### Remaining 17 local failures — traced, not hand-waved, and confirmed non-blocking

Every one of these matches a category independently identified as pre-existing/environment-only in
earlier certification passes, well before this PR-26 investigation, and none appear in the actual
GitHub Actions run (which is green):

| Failing test(s) | Cause | Category |
|---|---|---|
| `test_release_scripts.py` (6), `test_cron_contract.py` (3) | Windows-subprocess incompatibility invoking `.sh` scripts | Environment (Windows-only) |
| `test_logging_config.py::TestSetupLogging` (2) | Windows temp-file-handle lock on rotating log handler teardown | Environment (Windows-only) |
| `test_value_format.py` (4) | Node.js `require()` path-escaping breaks on Windows backslash paths | Environment (Windows-only) |
| `test_storage.py` (regime), `test_experiment_tracking.py` | Research/regime and research-provenance workstreams, explicitly out of RC1 scope | Excluded workstream |

None of these are RC1 regressions; none touch Production Engine reporting/scheduler/redaction code.

---

## 5. Final Merge / No-Merge Recommendation

# GO

CI is green on the real GitHub Actions run against the actual pushed commit (`09ce765`), the PR is
`mergeable_state: clean`, and every failure this investigation found — both rounds — was a
**pre-existing, non-RC1 defect** exposed only because this is the branch's first real CI run, not a
regression introduced by the Production Engine work. Both fixes were minimal, evidence-backed,
isolated to their own commits, and validated before and after push.

**Recommended actions:**
1. Update PR #26's title/description (currently stale — see §2) before merging, so the merge commit
   accurately reflects what RC1 actually contains.
2. **Merge PR #26** into `master` (standard merge, not squash, to preserve the 12-commit logical
   structure: 5 RC1 + 5 pre-existing + 2 CI fixes).
3. **Tag the release**, e.g. `git tag -a rc1-2026-07-28 -m "Production Engine RC1"` on the merge
   commit, then push the tag.
4. Only after merge + tag: begin the **Operations Dashboard / Job History** phase, then the **Agent
   Firm repository split** — both remain correctly scoped and unaffected by anything in this report.

---

## 6. Deliverables Index

1. Push summary — §1.
2. Pull Request summary — §2.
3. GitHub Actions results — §3.
4. CI failure analysis — §4 (both rounds, root cause, fix, validation).
5. Final Merge/No-Merge recommendation — §5: **GO**.
6. This report.
