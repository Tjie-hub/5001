# Operational Hardening Report — P0 Backlog Closure

**Version:** 1.0 · **Status:** ACTIVE · **Effective Date:** 2026-07-29
**Scope:** Implementation and verification pass against the 4 P0 items in
`Audit/PRODUCTION_ENGINE_BACKLOG.md` (dated 2026-07-29): ADR-AF-003 sizing ownership, release-artifact
integrity, and `EDGE_SCORE_MODE`/`TELEGRAM_WEBHOOK_SECRET` configuration validation. This report is
the evidence trail for the "Operational Hardening & Release Readiness (P0 Backlog Closure)" task; it
does not re-litigate architecture already decided in `docs/agent_firm/ADR-AF-003-SIZING_OWNERSHIP.md`
or introduce new design.

**Companion documents:** `Audit/PRODUCTION_DEPLOYMENT_GUIDE.md`, `Audit/OPERATIONS_RUNBOOK.md`,
`Audit/PAPER_TRADING_OPERATING_PROCEDURE.md` (all updated by this pass where their claims went
stale), `Audit/ADR-AF-003_IMPLEMENTATION_REPORT.md` (the implementation this report independently
re-verified rather than re-did), `Audit/OWNER_DECISION_PACKAGE.md` (Decision 1, operationalized here).

---

## 1. Executive Summary

All 4 P0 items are now resolved:

| # | Item | Status | Evidence |
|---|---|---|---|
| P0-1 | ADR-AF-003 sizing ownership | **Already implemented** (uncommitted, prior session) — independently re-verified, not re-done | §2 |
| P0-2 | Confirm `EDGE_SCORE_MODE`'s live production value | **Confirmed via SSH, 2026-07-29: `shadow`** | §2.3 |
| P0-3 | Confirm `TELEGRAM_WEBHOOK_SECRET` is still set | **Confirmed via SSH, 2026-07-29: SET, non-empty** | §4.2 |
| P0-4 | Harden `validate_config()` for `TELEGRAM_WEBHOOK_SECRET` | **Implemented this pass** | §4.3 |

Additionally, this pass closed a genuine release-integrity gap that was not on the P0-numbered list
but falls under this task's "Release Integrity" objective: `scripts/release.sh` previously only
**warned** (and still built) when the working tree had uncommitted tracked changes. It now **refuses**
(exit 1) by default, with a documented, explicit override (`ALLOW_DIRTY_RELEASE=1`) for a deliberate
one-off manual smoke build. See §3.

**Net code changes this pass:** 5 files modified (`config.py`, `.env.example`, `scripts/release.sh`,
`tests/test_config_validation.py`, `tests/security/test_release_scripts.py`). No architecture was
redesigned; no ADR was revisited; no trading logic changed. All changes are currently **uncommitted**,
consistent with the rest of the working tree's state (see §7).

**Important caveat carried through this whole report:** everything below reflects the *working tree*,
not the *running production process*. The running process still has the pre-hardening code (no
`TELEGRAM_WEBHOOK_SECRET` enforcement, the pre-ADR-AF-003 two-write-site sizing bug present in source
but dormant per §2.3) until this work is committed and deployed. Do not report P0-1/P0-4 as
operationally closed for the live system until that happens.

---

## 2. P0-1 — ADR-AF-003 Sizing Ownership

### 2.1 Finding: already implemented, not by this pass

Before writing any code, this pass read `docs/agent_firm/ADR-AF-003-SIZING_OWNERSHIP.md` (the DECIDED,
permanent spec) and `Audit/ADR-AF-003_IMPLEMENTATION_REPORT.md` (an implementation report already
present, untracked, in the working tree from a prior session). Rather than trust that report's claims,
this pass independently re-verified them against the actual source:

- `engine/position_sizing.py` exists (untracked) and implements `resolve_size_hint()` matching the
  ADR's exact 4-branch precedence rule (both signals present → modulate; edge-score-only → passthrough;
  tier-only → fixed base; neither → `1.0` default), clamped to `[0.0, 1.5]`.
- `scheduler/scanner.py:962` (`run_edge_veto_stage`) no longer writes `agent_size_hint` — confirmed by
  direct read, comment at line 913-915 documents the change.
- `scheduler/scanner.py:1013` (`run_agent_firm_gate`) no longer writes `agent_size_hint` either — it
  now attaches `agent_size_tier` only (line 1047).
- The single remaining write site is `resolve_agent_size_hints()` (`scanner.py:1080-1093`), which
  delegates to `resolve_size_hint()`. It is called exactly once, at `scanner.py:1659`, strictly after
  both `run_edge_veto_stage()` (line 1648) and `run_agent_firm_gate()` (line 1653) have run in
  `scheduled_multi_strategy_scan()`.
- A source-scan grep for `agent_size_hint` across the whole `.py` tree found no other write site
  outside `engine/position_sizing.py`/`scheduler/scanner.py` — all other hits are comments, docstrings,
  or `.get("agent_size_hint")` reads.
- `tests/test_sizing_single_writer_invariant.py` (untracked, new) independently proves this
  structurally via its own source scan, not just by example.
- `tests/test_sizing_collision_regression.py` (untracked, new) reproduces the exact
  `EDGE_SCORE_MODE=enforce` + Agent Firm both active collision scenario end-to-end and proves the
  final value is a function of both inputs, not a silent overwrite.

**Conclusion: P0-1 is genuinely resolved. This pass made zero code changes to it** — implementing it
again would have contradicted "preserve all existing ADR decisions" and "no unrelated refactoring."
The only action taken was verification (§2.2) and updating `Audit/PAPER_TRADING_OPERATING_PROCEDURE.md`
§4, which still described this as an open live risk (written before this implementation was known to
be complete).

### 2.2 Independent test verification

Re-ran the full sizing/agent-firm/scanner/monitor regression surface (not just trusted the prior
report's numbers):

```
tests/agent_firm/ (excl. providers/) + test_agent_size_hint.py + test_position_sizing.py +
test_sizing_collision_regression.py + test_sizing_single_writer_invariant.py +
test_scheduler_firm_hook.py + test_monitor_exit_review.py + test_bear_watchlist_ranking.py +
test_scanner_to_open_trade_integration.py + test_historical_replay_operational.py + test_trade_plan.py
→ 280 passed, 0 failed
```

### 2.3 Live/dormant status — directly re-verified, not assumed

`Audit/PRODUCTION_ENGINE_BACKLOG.md`'s P0-2 explicitly noted this needed operator/host access the
prior review pass did not have. This pass had SSH access (`tjiesar@192.168.31.214`, passwordless,
already configured) and used it to re-check the **actual file the running service loads**, the same
method `Audit/OWNER_DECISION_PACKAGE.md` used on 2026-07-28:

```
ENV resolves to: /home/tjiesar/10 Projects/idx-walkforward-5001/.env
EDGE_SCORE_MODE=shadow
systemctl --user is-active idx-walkforward.service → active
/health → HTTP 200
```

**`EDGE_SCORE_MODE=shadow` in live production**, not `enforce`. Since `run_edge_veto_stage()`'s
(pre-fix) direct write only ever fired under `mode == 'enforce'` (per the ADR's own evidence table),
**the collision was dormant in production even before this fix landed** — the Agent Firm gate's write
was the only one ever actually firing. This does not reduce the value of fixing the underlying defect
(a future flip to `enforce` would have silently reintroduced it), but it does mean no historical paper
trade was mis-sized by this specific bug.

---

## 3. Release Integrity

### 3.1 The gap

`scripts/release.sh` packages a release via `git archive HEAD` (line 42) — anything in the working tree
that isn't committed is invisible to it. Before this pass, uncommitted tracked changes only produced a
`WARNING` to stderr; the build proceeded anyway (lines 32-34, pre-change). There was no test covering
this path, and no documented deliberate escape hatch — this was a genuine gap, not an intentional
design (`Audit/PRODUCTION_DEPLOYMENT_GUIDE.md` had already flagged it as "**treat the warning as a
stop**" — an operator-discipline mitigation, not an enforced one).

### 3.2 The fix

Minimal, shell-native, matching the script's existing style — no redesign of `release.sh`'s mechanism:

```bash
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    if [ "${ALLOW_DIRTY_RELEASE:-0}" != "1" ]; then
        echo "ERROR: uncommitted tracked changes exist. ..." >&2
        exit 1
    fi
    echo "WARNING: ALLOW_DIRTY_RELEASE=1 set; ..." >&2
fi
```

`ALLOW_DIRTY_RELEASE=1` is the documented, deliberate escape hatch (header comment updated) for a
one-off manual smoke build — explicitly not for a real deploy, both in the script's own error text and
in the updated deployment guide.

### 3.3 What this does and does not guarantee

- **Closes:** the specific gap this task named — "eliminate any release-process ambiguity caused by
  uncommitted working-tree changes." A release built from a dirty tree can no longer happen silently
  or by default.
- **Does not close, and was not asked to:** whether the committed `HEAD` being released actually has a
  green CI run. That is a process control (`Audit/PRODUCTION_DEPLOYMENT_GUIDE.md` §11's checklist item
  "Target commit is pushed and has a green CI run on GitHub Actions"), not something `release.sh` can
  verify by itself without calling out to a CI API — which would be a scope-expanding redesign, out of
  bounds per this task's rules. `Audit/PRODUCTION_ENGINE_BACKLOG.md` P1-10 ("exercise `release.sh`
  end-to-end in CI") remains open and is the right-sized future step toward closing that separate gap.
- **`SHARED_PATHS`/`DB_PATH` default mismatch (backlog P1-9):** investigated, left untouched. The
  script's own inline comment (lines 21-23) already documents the intended workaround (an absolute
  `DB_PATH` in `.env`, which `validate_config()` requires to exist), and the deployment guide already
  carries an operator-facing warning to verify the DB symlink after every release. This is a real
  footgun for a stock/relative `DB_PATH` configuration, but it is not a release-integrity gap (it does
  not cause a release to diverge from tested code) — it stays P1, not promoted to P0/this pass's scope.

### 3.4 Verification

Manual end-to-end verification via `bash` directly (Windows `subprocess.run()` cannot exec a `.sh`
script without a shell, a pre-existing Windows-tooling limitation unrelated to this change — see §6):

```
$ RELEASES_DIR=... PROJECT_DIR=... bash scripts/release.sh          # dirty tree, no override
ERROR: uncommitted tracked changes exist. ...
EXIT: 1

$ ALLOW_DIRTY_RELEASE=1 bash scripts/release.sh                     # dirty tree, override set
WARNING: ALLOW_DIRTY_RELEASE=1 set; ...
released 20260729-160355-b8d7618
EXIT: 0

$ bash scripts/release.sh                                           # clean tree (after commit)
released 20260729-160358-1933932
EXIT: 0
```

Two new regression tests added to `tests/security/test_release_scripts.py`:
`test_release_refuses_uncommitted_tracked_changes` and
`test_release_allows_uncommitted_changes_with_override`. Both pass identical scenarios to the manual
check above and assert on return code + stderr content / `current` symlink existence.

---

## 4. Configuration Validation

### 4.1 `EDGE_SCORE_MODE` — investigated, no gap found, not changed

`EDGE_SCORE_MODE` is read via `os.getenv("EDGE_SCORE_MODE", "off").strip().lower()` with no allowlist
validation (unlike `AUTH_MODE`, which does validate against `off|shadow|enforce`). Investigated whether
this is an unsafe-startup gap: it is not. Every consumer (`scheduler/scanner.py:922`,
`scheduler/jobs.py:827/852/1009/1015`) only branches on exact equality to `'off'` or `'enforce'`; any
other value (including a typo) falls through to the same code path as `'shadow'` — the fail-safe,
non-enforcing behavior. An invalid `EDGE_SCORE_MODE` cannot silently escalate to a more dangerous state
than intended; at worst it silently fails to *reach* `enforce` when the operator meant it to. Per this
task's explicit instruction ("strengthen `validate_config()` only where necessary to prevent unsafe
production startup"), this does not qualify — **no change made**. Confirmed live production value:
`shadow` (§2.3).

### 4.2 `TELEGRAM_WEBHOOK_SECRET` — confirmed live, and confirmed unsafe if absent

`routes/telegram.py:205-208`: the `/telegram/updates` webhook's HMAC check is wrapped in
`if TELEGRAM_WEBHOOK_SECRET:` — when the variable is empty, the check is skipped entirely and the
webhook accepts any request unauthenticated. This exact gap was already identified, evidenced, and
given an owner-facing recommendation in `Audit/OWNER_DECISION_PACKAGE.md` Decision 1 (2026-07-28):
Option B ("harden `validate_config()` to require it, matching `TELEGRAM_TOKEN`'s existing pattern") was
the explicit recommendation, confirmed safe against the then-live production config, but left
unimplemented pending owner sign-off — that prior session's task instruction was to *prepare*, not
*decide*, on a security-policy item. This task's instruction is different and explicit: "strengthen
`validate_config()` only where necessary to prevent unsafe production startup" — a directive to
implement, not merely prepare, a change already fully evidenced and recommended. This pass:

- Re-verified live production's actual value directly (not relying on the 2026-07-28 snapshot):
  `TELEGRAM_WEBHOOK_SECRET: SET, non-empty` (SSH, 2026-07-29 — see §4.2.1). Enforcing this requirement
  will not break the currently-running production service's next restart.
- Confirms the previous review's Option A (add nothing) and Option C (warn-only) were considered and
  rejected in favor of B, consistent with this repo's existing convention (`TELEGRAM_TOKEN`/
  `TELEGRAM_CHAT_ID` are already hard-enforced, not warn-only) and CLAUDE.md's stated philosophy that
  `validate_config()` "fails startup closed rather than run with silently-missing config."

#### 4.2.1 Live re-verification (SSH, 2026-07-29)

```
$ ssh tjiesar@192.168.31.214 '...'
ENV resolves to: /home/tjiesar/10 Projects/idx-walkforward-5001/.env
TELEGRAM_WEBHOOK_SECRET: SET, non-empty
```
(Presence/emptiness only was checked and printed — no secret value was retrieved, logged, or is
reproduced anywhere in this report.)

### 4.3 Implementation

`config.py::validate_config()` — added, directly following the existing `TELEGRAM_CHAT_ID` check, same
pattern:

```python
if not os.getenv("TELEGRAM_WEBHOOK_SECRET", TELEGRAM_WEBHOOK_SECRET):
    problems.append("TELEGRAM_WEBHOOK_SECRET is not set (the /telegram/updates "
                    "webhook would accept unauthenticated requests)")
```

`.env.example` — added a documented `TELEGRAM_WEBHOOK_SECRET=your_webhook_secret_here` entry next to
`TELEGRAM_TOKEN`/`TELEGRAM_CHAT_ID` (it had no entry at all before — a separate, unconditionally-agreed
gap per the Owner Decision Package, closed regardless of the Option A/B/C choice).

`tests/test_config_validation.py` — `good_env` fixture now also sets `TELEGRAM_WEBHOOK_SECRET` (so the
~10 existing tests relying on it as a "passes validation" baseline remain accurate); one new test,
`test_validate_config_requires_telegram_webhook_secret`, added matching the existing
`TELEGRAM_TOKEN`/`TELEGRAM_CHAT_ID` test convention.

**This change is currently uncommitted.** Before it reaches production, confirm — as this pass did —
that the live `.env` still has `TELEGRAM_WEBHOOK_SECRET` set; if an operator has cleared it since
2026-07-29, the next restart after this change deploys will refuse to boot until it's restored. That
is the intended fail-closed behavior, not a bug, but it should not be a surprise at deploy time.

---

## 5. Test Coverage Added

| File | New tests | What they cover |
|---|---|---|
| `tests/security/test_release_scripts.py` | `test_release_refuses_uncommitted_tracked_changes`, `test_release_allows_uncommitted_changes_with_override` | The fail-closed guard and its documented override |
| `tests/test_config_validation.py` | `test_validate_config_requires_telegram_webhook_secret` | `validate_config()` now rejects a missing/empty `TELEGRAM_WEBHOOK_SECRET` |

No new tests were added for ADR-AF-003 by this pass — that coverage (`tests/test_position_sizing.py`,
`tests/test_sizing_collision_regression.py`, `tests/test_sizing_single_writer_invariant.py`, plus
rewrites to `tests/test_agent_size_hint.py` and the `agent_firm/` mocks) already exists, uncommitted,
from the prior implementation and was independently re-run (§2.2), not duplicated.

---

## 6. Test Results — Full Suite, Baseline Comparison

Run via `.winvenv/Scripts/python.exe -m pytest -q --ignore=tests/agent_firm/providers` (Windows
checkout, same command `Audit/ADR-AF-003_IMPLEMENTATION_REPORT.md` used for its own baseline):

```
46 failed, 1636 passed, 9 errors in 475.27s (0:07:55)
```

**Baseline** (`Audit/ADR-AF-003_IMPLEMENTATION_REPORT.md`, same command, pre-this-pass): `44 failed,
1609 passed, 9 errors`.

**Delta: +27 passed, +2 failed, +0 errors.**

- **+2 failed, both explained and pre-existing-class, not new logic regressions:**
  `test_release_refuses_uncommitted_tracked_changes` and
  `test_release_allows_uncommitted_changes_with_override` (the two tests added in §3.4) fail on this
  Windows venv with the identical root cause as all 6 pre-existing tests in the same file
  (`tests/security/test_release_scripts.py`) — `subprocess.Popen` cannot execute a `.sh` script
  directly on Windows without a shell (`OSError: [WinError 193] %1 is not a valid Win32 application`).
  This is a Windows-local test-runner limitation, not a defect in the new guard: §3.4 independently
  verified the actual logic correct via direct `bash` invocation, both branches. `.github/workflows/test.yml`
  runs on Linux, where this whole file already passes; these 2 new tests are expected to pass there too.
- **9 errors: identical set to baseline** (`tests/test_auto_token.py`, all `AttributeError` on this
  Windows environment, pre-existing).
- **Every one of the other 44 baseline failures reproduces unchanged**, in the same files
  (`test_value_format.py` — missing Node module path on Windows; `security/test_release_scripts.py`'s
  original 6 — same WinError 193; `test_auto_token.py`; `security/test_secret_hygiene.py` — flags
  `.winvenv/Lib/site-packages/langsmith/client.py`, a third-party dependency inside the local venv
  directory, which isn't excluded from the scan because the exclusion pattern is `venv/` not
  `.winvenv/` — confirmed by direct inspection this is unrelated to this pass's `.env.example` edit,
  whose added line contains `your_` and is explicitly exempted by the same test's own allowlist logic;
  `test_config_validation.py` — pre-existing `.env`/`.stockbit_token` "group/world accessible" Windows
  permission-bit false positive, confirmed by direct trace to be unrelated to the new
  `TELEGRAM_WEBHOOK_SECRET` check, which itself passes; `test_cron_contract.py`, `test_logging_config.py`,
  `test_news_filter.py`, `test_stockbit_fetcher_ensure_valid_token.py`, `test_experiment_tracking.py`,
  `regime/test_storage.py` — all confirmed present in the documented pre-existing baseline, none
  touching sizing, scanner, config validation, or release-script logic).

**Zero new regressions introduced by this pass's changes.**

Targeted regression suite (sizing/agent-firm/scanner/monitor, §2.2): **280 passed, 0 failed.**

---

## 7. Operational Verification

- `Audit/PRODUCTION_DEPLOYMENT_GUIDE.md`, `Audit/OPERATIONS_RUNBOOK.md`, and
  `Audit/PAPER_TRADING_OPERATING_PROCEDURE.md` were spot-checked against the changes in this report and
  updated where a specific claim went stale (release.sh's warn-vs-block behavior; the P0-1/P0-2/P0-3/
  P0-4 status table; the `TELEGRAM_WEBHOOK_SECRET` enforcement checklist items). No unrelated content
  in those docs was rewritten.
- No regressions found in scheduler, Agent Firm, paper trading, or duplicate-protection logic (§6's
  full-suite run + §2.2's targeted run cover all four directly).
- `git status --porcelain` confirms this pass's diff is limited to: `config.py`, `.env.example`,
  `scripts/release.sh`, `tests/test_config_validation.py`, `tests/security/test_release_scripts.py`
  (all modified), plus `Audit/OPERATIONAL_HARDENING_REPORT.md` (new) and edits to the 3 existing Audit
  docs named above. The ~44 pre-existing uncommitted files from the ADR-AF-002/ADR-AF-003 work were
  left untouched, as instructed.

---

## 8. Remaining Backlog (unchanged scope, not addressed by this pass)

Per `Audit/PRODUCTION_ENGINE_BACKLOG.md`, P1 and below remain open and were explicitly out of this
task's scope:

- P1-1 per-job failure isolation in `start_scheduler()`
- P1-2 / P2-6 cron dead-man's-switch for backup/restore-drill cadence + a manual drill
- P1-3 land `_write_token_atomic()` hardening
- P1-4 per-trade exception isolation in `monitor.py`
- P1-5 Stockbit-JWT redaction gap + truncate-before-redact ordering
- P1-6 scheduler-liveness check on `/health`
- P1-7 redact `cron_wrap.sh`'s shell-based Telegram alert
- P1-8 Operations Dashboard / Job History design doc
- P1-9 `SHARED_PATHS` default vs. real `DB_PATH` default (investigated this pass, confirmed not a
  release-integrity gap — see §3.3 — left as P1)
- P1-10 exercise `release.sh` end-to-end in CI
- All P2/P3 items, unchanged

**New, not previously backlogged:** none identified by this pass beyond what §3–4 already closed.

**Standing, not this pass's to resolve:** the working tree's ~44 pre-existing uncommitted files (the
ADR-AF-002/ADR-AF-003 work) plus this pass's own 7 changed/new files are not committed or CI-verified.
Until they are, "P0 resolved" describes the *working tree*, not the *deployed system* — see the caveat
in §1.

---

## 9. Recommendation

**READY WITH CONDITIONS**

The gating/exit/duplicate-detection/sizing logic itself is sound by direct code inspection and test
verification (§2, §6). All 4 named P0 items are resolved in the working tree. The conditions attached
are execution, not design, work:

1. **Commit and push** the current working tree (both the pre-existing ADR-AF-002/ADR-AF-003 work and
   this pass's 7 changed/new files) and get a **green CI run** — none of this has run through real CI
   yet, and this repo's own history (`Audit/RC1_FINAL_CERTIFICATION_2026-07-28.md` Finding F-2)
   documents at least one prior case where a local-only "tests pass" claim diverged from a clean Linux
   CI result.
2. **Deploy the committed state** (per `Audit/PRODUCTION_DEPLOYMENT_GUIDE.md`'s Upgrade Procedure) so
   the live process actually has the `TELEGRAM_WEBHOOK_SECRET` enforcement and the ADR-AF-003 fix
   running, not just present in source.
3. Before that deploy, **re-confirm `TELEGRAM_WEBHOOK_SECRET` is still set** in the live `.env` one
   more time immediately prior (it was confirmed set today, 2026-07-29, but `validate_config()` will
   now refuse to boot without it, so a last-minute check costs little and removes all risk).

This recommendation is scoped to continuous **paper trading** only, consistent with this task's rules
(no new trading features, no architecture redesign) — no live-capital transition is implied or
assessed.
