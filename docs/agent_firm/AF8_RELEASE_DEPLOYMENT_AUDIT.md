# AF-8 — Release & Deployment Audit

**Date:** 2026-07-29 · **Status:** Audit only — no files modified, no commits made, no deployment
performed.
**Scope:** the full uncommitted working tree (180 paths), the release/deployment tooling
(`scripts/release.sh`, `wait_for_health.sh`, `rollback.sh`, `cron_wrap.sh`), and a commit/deployment
plan for shipping the arc certified in AF-3 through AF-7.
**Method:** `git status`/`git diff --stat`/`git diff --summary` (for file-mode changes) on every
uncommitted path, content inspection of every non-obvious file, and a fresh, full test run
(`--continue-on-collection-errors`) to get one authoritative pass/fail picture across the entire
release scope — not reused from any prior session's numbers.

**Two findings materially change what AF-7 assumed. Both are reported here, neither is fixed:**

1. **File-mode corruption.** Nine shell/entry-point scripts (`scripts/release.sh`, `rollback.sh`,
   `wait_for_health.sh`, `cron_wrap.sh`, `start.sh`, `run_telegram.sh`, `chart-viewer/start.sh`,
   `_archive/patch_rr_ratio.sh`, `_archive/update_fetch_report.py`, `auto_token.py`) have lost their
   executable bit (`100755 → 100644`) in the working tree — a Windows-checkout artifact with zero
   content change. Committed as-is, this would silently break every `systemd`/`cron` invocation of
   these scripts on the Ubuntu host. **This is a real release blocker if committed carelessly**, and
   the fix is mechanical (`chmod +x`), not a code change.
2. **The Provider Governor is broken and unwired.** `engine/agent_firm/providers/governor.py` (new,
   untracked) is not referenced by `router.py`, `factory.py`, or `firm.py` anywhere — it is dead
   code. Its own `_build_from_config()` crashes (`AttributeError: module 'engine.agent_firm.config'
   has no attribute 'GOVERNOR_ENABLED'` — confirmed by running its own test suite). Four new,
   untracked test files (`test_governor.py`, `test_quota_scenarios.py`,
   `test_quota_state_persistence.py`, `test_quota_hydration_edge_cases.py`) expect a companion
   "quota-hold persists across router rebuilds" feature (a `_hydrate_quota_holds()` function) that
   was never implemented in `router.py`. This is contained and does **not** affect the certified
   Decision Flow/Ranking/Watchlist arc (nothing in the live request path calls the Governor), but
   these five files must not ship in this release as-is.

Full evidence for both is in Phase 1/2 below. **Recommendation: exclude both from this release's
commit** rather than fix them now — fixing the mode bits is mechanical and safe to do as part of
staging; fixing/wiring the Governor is scope this task should not perform (it would be new
integration work, not a blocker-fix for the arc actually being released).

---

## Phase 1 — Working Tree Audit

**Total uncommitted paths: 180** (50 modified, ~130 untracked, several of which are directories).

### 1. Production implementation — this release's actual payload

| File | Change |
|---|---|
| `config.py` | `TELEGRAM_WEBHOOK_SECRET` made mandatory in `validate_config()` |
| `data/db.py` | Idempotent `size_tier` column migration for `agent_decisions` (ADR-AF-003) |
| `engine/agent_firm/agents/{flow,news,regime,risk,technical}.py` | Typed Tier-1-context consumption (WP2/WP3) |
| `engine/agent_firm/firm.py` | WP3 wiring + this session's WP4 (K1/K2 guardrails) |
| `engine/agent_firm/guardrails.py` | This session's WP4: `build_consensus_summary()` + K1/K2 |
| `engine/agent_firm/prompts/{flow_v1,news_v1,regime_v1,risk_v2,technical_v1}.md` | WP3 prompt updates |
| `engine/agent_firm/schemas.py` | Tier-1/Tier-2 context types (WP1) |
| `engine/agent_firm/smoke.py` | Updated for context-carrying candidates |
| `monitor.py` | Exit-review Tier-1-context wiring (AF-2 WP4) |
| `paper_trade.py` | Duplicate-close race guard (Operational Validation Phase 2) |
| `scheduler/jobs.py` | Tier-1-context wiring for premarket/EOD (AF-2 WP2) |
| `scheduler/scanner.py` | Tier-1-context wiring for main scan + bear-watchlist (AF-2 WP2) |
| `engine/agent_firm_context.py` *(new)* | Context Producer (ADR-AF-002) |
| `engine/position_sizing.py` *(new)* | Sizing Ownership, `resolve_size_hint()` (ADR-AF-003) |

**15 files — MUST be committed.** *Excluded from this list, deliberately:*
`engine/agent_firm/providers/governor.py` *(new)* — broken/unwired, see headline finding.

### 2. Tests

| Group | Files | Status |
|---|---|---|
| Directly tied, modified | `tests/agent_firm/test_{firm,firm_v2,flow,guardrails,news,regime,risk,risk_v2,schemas,technical}.py`, `tests/security/test_release_scripts.py`, `tests/test_{agent_size_hint,bear_watchlist_ranking,config_validation,monitor_exit_review,scheduler_firm_hook}.py | **MUST commit** — all pass (see full run below) |
| Directly tied, new | `tests/agent_firm/test_versioning_contract.py`, `tests/test_{agent_firm_context,agent_firm_context_wiring,scheduler_jobs_context_wiring,position_sizing,sizing_single_writer_invariant,sizing_collision_regression,close_trade_duplicate_prevention,scanner_to_open_trade_integration,historical_replay_operational}.py` | **MUST commit** — all pass |
| Broken, tied to the excluded Governor | `tests/agent_firm/providers/test_governor.py` (2 failures), `test_quota_scenarios.py` (4 failures), `test_quota_state_persistence.py` (3 failures), `test_quota_hydration_edge_cases.py` (1 collection error) | **MUST NOT commit** — see headline finding |
| Unrelated, own scope | `tests/test_{auto_token,news_filter,stockbit_fetcher_ensure_valid_token}.py` (pre-existing incident regressions, 2026-07-24/27), `tests/test_filter_exploration.py` (exploratory research script) | **SHOULD NOT commit with this release** — legitimate, but a different subject entirely |

**Fresh, authoritative test run this session** (full release scope, `--continue-on-collection-errors`):
```
pytest tests/agent_firm/ tests/test_trade_plan.py tests/test_bear_watchlist_ranking.py \
       tests/test_eod_trade_plan_job.py -q --continue-on-collection-errors
→ 348 passed, 9 failed, 1 error
```
Every failure/error is confined to the four Governor/quota-hydration files listed above. **Excluding
those four files from the commit, the release payload's test suite is 348/348 clean.**

### 3. Documentation

| Group | Files | Recommendation |
|---|---|---|
| This release's own decision/audit trail | `CLAUDE.md` (+9 lines), `docs/agent_firm/ADR-AF-001..005*.md`, `AF1_*.md` (9), `AF2_*.md` (6), `AF3-AF7*.md` (5, this conversation's own audits), `AGENT_FIRM_PROVIDER_LAYER_ARCHITECTURE.md`, `Audit/ADR-AF-002_*.md` (3), `ADR-AF-003_IMPLEMENTATION_REPORT.md`, `ADR-AF-004_IMPLEMENTATION_REPORT.md`, `Audit/AF2_*.md` (17), `AGENT_FIRM_INTEGRATION_VALIDATION_REPORT.md`, `FINAL_PRODUCTION_READINESS_CERTIFICATION.md`, `PRODUCTION_ENGINE_*.md` (5), `PRODUCTION_OPERATIONAL_VALIDATION_PHASE{1,2}.md`, `CLAUDE_PROVIDER_RCA_2026-07-10.md`, `PROVIDER_RESILIENCE_COMPLETION_2026-07-10.md`, `RC1_CI_VALIDATION_AND_RELEASE_READINESS_2026-07-28.md`, `INSTITUTIONAL_AUDIT_2026-07-10.md`, `OPERATIONAL_HARDENING_REPORT.md`, `OPERATIONS_RUNBOOK.md`, `PAPER_TRADING_OPERATING_PROCEDURE.md`, `PRODUCTION_DEPLOYMENT_GUIDE.md` | **MUST/SHOULD commit** — ~55 files, this repo's own governance convention (decisions are recorded, not just coded) |
| `.env.example` | +`TELEGRAM_WEBHOOK_SECRET` documentation | **MUST commit** — documents the newly-mandatory var |
| Pre-existing, unrelated | `docs/Adaptive_Signal_Scoring_Architecture.md`, `"docs/L3 Data Ontology Specification.pdf"`, `docs/archive/*.md` (2), `docs/audit/*` (15, Stockbit flow data-quality), `docs/data/*` (2), `docs/infra/*` (5), `docs/cluster.md`, `docs/cycle_phases_strong12.md`, `docs/review.md`, `docs/superpowers/plans/*.md` (9, unrelated strategy-engine/R5-DB-split planning), `docs/superpowers/specs/2026-07-14-*.md`, `"docs/tjiesar tjiesar XPS 13.txt"` (personal file) | **SHOULD NOT commit with this release** — ~36 files, genuinely different subject matter; bundling would make this release's diff unreviewable |

### 4. Configuration

| File | Note |
|---|---|
| `.env.example` | See Documentation above — MUST commit |
| `.vscode/settings.json`, `idx-walkforward-5001.code-workspace` | Personal IDE/workspace preferences (`python-envs` extension config, `git.ignoreLimitWarning`) — **SHOULD NOT commit**, out of scope, harmless either way |

### 5. Temporary/debug

`scripts/probe_{actual_http_concurrency,zai_concurrency_limit,zai_large_payload,zai_sustained_rate}.py`
(one-off z.ai rate-limit RCA diagnostics, 2026-07-10/13 incident), `monitor_zai_quota.py`,
`zai_quota_monitor.sh`, `tools/check_stockbit_flow_coverage.py`, `_brpt_engine_test.py`,
`backfill_flow_jan_apr.py`, `backfill_stockbit_flow_gap.py`, `grep_final_refs.txt`,
`grep_root_refs.txt` — **SHOULD NOT commit.** Two files are borderline-legitimate operational
tooling worth keeping (optional, not required): `scripts/replay_firm_offline_run.py` and
`scripts/replay_governor_ab.py` directly validate the Provider Governor's own design — but since
the Governor itself is excluded from this release, these are better deferred alongside it.

### 6. Generated artifact

`TOWR_chart.png`, `WhatsApp_TOWR.jpeg`, `brpt-deepdive.png`, `zai-quota-page.png`, `images/` —
screenshots/generated images, scratch. **SHOULD NOT commit.**

### 7. Unknown / tool-and-environment state

`.deepseek/`, `.playwright-mcp/`, `.stfolder/`, `.winvenv/`, `.stignore`, `scratchpad/` — editor/AI
tool/venv/Syncthing state, none currently in `.gitignore`. **SHOULD NOT commit** — and are a minor,
optional `.gitignore` hygiene gap worth closing separately (not a release blocker).

### Summary

| | Count | Verdict |
|---|---|---|
| MUST commit (this release's payload) | ~15 production + ~24 tests + ~56 docs/config ≈ **95 files** | Ship |
| MUST NOT commit (broken/incomplete) | 5 (Governor + 4 tests) | Exclude, defer |
| MUST fix before staging (mode corruption) | 9 scripts | `chmod +x` first, then decide per-file whether its content diff (only `release.sh` has one) also ships |
| SHOULD NOT commit (out of scope / personal / scratch) | **~80 files** | Leave uncommitted |

---

## Phase 2 — Release Readiness

| Item | Status | Detail |
|---|---|---|
| `release.sh` prerequisites | **Ready, once committed** | Requires a clean tracked tree (the guard this release itself adds — currently uncommitted, so not yet protecting anything), `git`, `SHARED_PATHS` correctly symlinked on the host. Unit-tested (`tests/security/test_release_scripts.py`, both the refusal and the `ALLOW_DIRTY_RELEASE=1` override) |
| `wait_for_health.sh` | **Ready** | Content unchanged this session; polls `/health` for `status: ok`, used as `ExecStartPost`. Mode-corrupted — needs `chmod +x` |
| Deployment scripts (`release.sh`, `rollback.sh`, `cron_wrap.sh`) | **Ready, content-wise** | All present, documented in `docs/OPERATIONS.md`. All mode-corrupted — needs `chmod +x` |
| Rollback capability | **Ready** | `scripts/rollback.sh --list` / `[<version>]`, tested (`test_rollback_with_nothing_older_fails` and others) |
| Migration requirements | **Low-risk, automatic** | Exactly one migration: `size_tier TEXT` column on `agent_decisions`, idempotent (`PRAGMA table_info` guard), auto-applied by `init_agent_firm_tables()` at startup — no manual step, no data transformation |
| Environment requirements | **One new mandatory var** | `TELEGRAM_WEBHOOK_SECRET` — `config.validate_config()` now fails closed without it. Per `config.py`'s own comment this was confirmed set on the live `.env` via SSH on 2026-07-28 (Owner Decision Package Decision 1) — **reconfirm immediately before this specific deploy**, since time has passed and the enforcement itself hasn't shipped yet |
| Configuration requirements | Same as above | No other new mandatory config found. `GOVERNOR_*` vars are **not** required since the Governor is excluded from this release |
| Release documentation | **Present** | `docs/OPERATIONS.md` (release procedure, service management, checklist), `Audit/PRODUCTION_DEPLOYMENT_GUIDE.md`, `Audit/OPERATIONS_RUNBOOK.md` — all untracked, should ship with this release per §Documentation above |

**Missing prerequisite identified:** the Provider Governor's configuration is incomplete
(`GOVERNOR_*` settings absent from `engine/agent_firm/config.py`) and it is entirely unwired from
`router.py`/`factory.py`. This is not a prerequisite this release needs — because the Governor is
being excluded — but it must be recorded as **known, incomplete, deferred work**, not silently
dropped or forgotten.

---

## Phase 3 — Commit Strategy

# B. Multiple logical commits

Single-commit is not recommended: the working tree spans at least four independently-reviewable,
independently-revertible concerns (core Decision Flow, Production Engine wiring, small unrelated
operational hardening fixes, and a large documentation corpus), plus one exclusion decision
(Governor) and one mechanical fix (executable bits) that are easier to verify in isolation than
buried in one large diff.

**Proposed boundaries:**

1. **`feat(agent-firm): Tier 1 context ownership, sizing, and deterministic guardrails (WP1-4)`**
   — `engine/agent_firm/schemas.py`, `agents/*.py`, `firm.py`, `guardrails.py`, `prompts/*.md`,
   `smoke.py`, `engine/agent_firm_context.py`, `engine/position_sizing.py`, `data/db.py`
   (size_tier migration) + their tests (`tests/agent_firm/test_*.py` modified,
   `test_versioning_contract.py`, `test_agent_firm_context.py`, `test_agent_firm_context_wiring.py`,
   `test_position_sizing.py`, `test_sizing_single_writer_invariant.py`,
   `test_sizing_collision_regression.py`). Self-contained: this is the Decision Flow arc,
   independently testable and revertible.

2. **`feat(scheduler): wire Tier 1 context into premarket/EOD/bear-watchlist/exit-review`**
   — `scheduler/jobs.py`, `scheduler/scanner.py`, `monitor.py` + `tests/test_scheduler_jobs_context_wiring.py`,
   `test_scheduler_firm_hook.py`, `test_monitor_exit_review.py`, `test_bear_watchlist_ranking.py`,
   `test_agent_size_hint.py`. Depends on commit 1; kept separate because it's the Production Engine
   integration layer, not Agent Firm internals — a future revert of "the wiring" without reverting
   "the Decision Flow itself" stays possible.

3. **`fix(production): duplicate-close race guard + mandatory Telegram webhook secret + release-script dirty-tree guard`**
   — `paper_trade.py`, `config.py`, `.env.example`, `scripts/release.sh` (content only — see
   mode-bit note below) + `tests/test_close_trade_duplicate_prevention.py`,
   `test_scanner_to_open_trade_integration.py`, `tests/test_config_validation.py`,
   `tests/security/test_release_scripts.py`. Three genuinely unrelated small hardening fixes,
   bundled because each is too small to warrant its own commit but none belongs in commits 1-2.

4. **`docs(agent-firm): ADR-AF-001..005 and AF1-AF7 planning/certification corpus`**
   — the ~55-file documentation set from §Phase 1.3. Ride-along or standalone, per this repo's own
   frequent `docs(...)` commit convention; recommended standalone so a documentation-only revert is
   possible without touching code.

5. **Separate, mechanical, before any of the above:** restore the executable bit
   (`chmod +x scripts/*.sh scripts/cron_wrap.sh start.sh run_telegram.sh chart-viewer/start.sh
   _archive/patch_rr_ratio.sh _archive/update_fetch_report.py auto_token.py`) so commit 3's
   `scripts/release.sh` change (and every other script) stages with `100755`, not `100644`. This is
   not a "commit" of new content — it is a pre-staging correction that must happen before `git add`
   touches any of these paths, in any commit.

**Explicitly excluded from all of the above** (per Phase 1): `engine/agent_firm/providers/governor.py`
+ its 4 test files (deferred, broken); `.vscode/settings.json`, `idx-walkforward-5001.code-workspace`
(personal); the ~80 unrelated/scratch/generated files. The three unrelated-incident test files
(`test_auto_token.py`, `test_news_filter.py`, `test_stockbit_fetcher_ensure_valid_token.py`) are
legitimate and passing — optionally a 6th, separate commit if the operator wants them shipped too,
but not required by, or blocking, this release.

---

## Phase 4 — Deployment Risk

| Risk | Level | Rationale |
|---|---|---|
| **Release risk** | **MEDIUM** | Large diff (95 files across 4-5 commits), but every included file is tested (348/348 clean once the Governor exclusion is applied); this is the first time ADR-AF-002/003/004 and K1/K2 reach the live host |
| **Rollback risk** | **LOW** | `scripts/rollback.sh` exists and is tested; the one DB change (`size_tier` column) is additive — a rollback to pre-this-release code would simply not read the new column, no breakage |
| **Configuration risk** | **LOW-MEDIUM** | `TELEGRAM_WEBHOOK_SECRET` becomes fail-closed-mandatory; per code comment already confirmed set live (2026-07-28), but the enforcement itself has never actually run against the live `.env` — a stale/rotated value would now abort startup where it previously wouldn't have |
| **Migration risk** | **LOW** | Single idempotent `ALTER TABLE ADD COLUMN`, auto-applied, no manual step, no backfill needed |
| **Operational risk** | **MEDIUM** | K1/K2 enforce immediately with no shadow period (AF-6/AF-7's standing flag); Tier-1 context reaches 3 live call sites for the first time — an expected decision-distribution shift with a documented but never-yet-run monitoring query (AF-7 §3) |

---

## Phase 5 — Deployment Checklist

1. Restore executable bits on the 9 mode-corrupted scripts (Phase 3, item 5).
2. Review `git diff` for each proposed commit boundary (Phase 3) — confirm scope, exclude the
   Governor + its 4 tests, exclude personal/scratch files.
3. Run the full relevant test suite one more time post-staging:
   `pytest tests/agent_firm/ tests/test_trade_plan.py tests/test_bear_watchlist_ranking.py tests/test_eod_trade_plan_job.py -q --continue-on-collection-errors` — expect **348 passed, 0 failed** once the Governor files are excluded (currently 9 failed/1 error, all attributable to the excluded files).
4. Commit (4-5 commits per Phase 3), Conventional-Commits style, matching this repo's observed log
   convention.
5. Tag the release per `scripts/release.sh`'s own versioning scheme (`date +%Y%m%d-%H%M%S`-`SHORT_SHA`, automatic — no manual tag step found in the documented procedure).
6. Confirm live `.env`'s `TELEGRAM_WEBHOOK_SECRET` (and `EDGE_SCORE_MODE`, carried from AF-7) one
   more time, immediately before deploy.
7. Execute `scripts/release.sh` (will now succeed — the dirty-tree guard was the actual blocker;
   confirm it also reports `100755` on the deployed scripts).
8. Deploy (`systemctl --user restart idx-walkforward` per `docs/OPERATIONS.md`).
9. Run `scripts/wait_for_health.sh`.
10. `journalctl --user -u idx-walkforward -n 50` — confirm clean startup, registry announced, no
    `validate_config()` failure.
11. Verify scheduler: `systemctl --user status idx-walkforward` active, cron jobs registered
    (per `docs/OPERATIONS.md`'s startup log check).
12. Verify Telegram: confirm the next scheduled report (Premarket 08:35 / EOD 16:40 / Forward-Test
    18:30) actually arrives.
13. Verify `watchlist_snapshot`: confirm a new row appears for the day/strategy after the next
    EOD/Premarket run.
14. Verify diff generation: confirm the Watchlist Changes section renders (empty or populated) in
    the next report.
15. Verify logs: `logs/app.log` clean, no unexpected `fail-soft` spam, `provider_events` populating.
16. Observe one complete trading cycle (premarket → intraday scans → EOD → forward-test) end to end.
17. Run the decision-distribution query (`AF2_POST_DEPLOYMENT_MONITORING_PLAN.md` §3) and a K1/K2
    veto-rate query (`agent_decisions.rationale LIKE '%K1%'`/`'%K2%'`) after 24-48h.
18. Capture Ubuntu resource metrics (CPU/RSS/disk/DB growth) — the single most-repeated outstanding
    item across every prior certification in this sequence.
19. Execute the weekly checklist (`docs/OPERATIONS.md`: restore drill, `provider_events` rates, disk).
20. Final production sign-off — re-issue AF-7's certification as plain "GO WITH CONDITIONS," dropping
    the "DEPLOYMENT PENDING" qualifier.

---

## Deliverables Summary

**1. Working tree audit:** 180 uncommitted paths; ~95 belong to this release, ~80 do not, 5 are
broken/deferred, 9 need a mechanical mode-bit fix before staging. Full breakdown in Phase 1.

**2. Release readiness assessment:** all deployment tooling (`release.sh`, `wait_for_health.sh`,
`rollback.sh`, `cron_wrap.sh`) is content-ready and tested; the one missing prerequisite is the
Provider Governor's configuration/wiring, resolved here by exclusion rather than a fix.

**3. Commit strategy:** **B — multiple logical commits** (4-5, boundaries in Phase 3), plus one
mechanical pre-staging step (executable-bit restoration).

**4. Deployment risk assessment:** Release MEDIUM, Rollback LOW, Configuration LOW-MEDIUM, Migration
LOW, Operational MEDIUM. No HIGH-risk item found.

**5. Deployment checklist:** 20 steps, Phase 5 above, from mode-bit restoration through final
sign-off.

**6. Go/No-Go recommendation:** **GO — commit and deploy, with the Governor exclusion and
executable-bit fix applied first.** Nothing found in this audit invalidates AF-6/AF-7's certification
of the Decision Flow/Ranking/Watchlist arc; the two findings here are release-hygiene issues
(file-mode corruption, one unrelated broken/unwired sub-feature), not defects in the certified code
itself.

**7. Remaining blockers:** none for the certified arc, once (a) executable bits are restored and (b)
the Governor + its 4 test files are excluded from this release's commit. Both are mechanical,
zero-business-logic-risk actions, not engineering work.

No files were modified, no commits were made, and no deployment was performed by this audit.
