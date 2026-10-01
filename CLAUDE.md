# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Version:** 1.1 · **Status:** FROZEN · **Effective Date:** 2026-07-21
**Amended:** 2026-07-28 — Production Engine Telegram reporting (EOD/Premarket/Forward-Testing v2),
watchlist snapshot/diff infrastructure, scheduler crash-alert rate limiting, and outbound-Telegram
secret redaction added to Architecture/Environment Variables below (RC1 fixes; see
`Audit/PRODUCTION_ENGINE_IMPLEMENTATION_AUDIT_2026-07-28.md` and
`Audit/RELEASE_READINESS_AUDIT_2026-07-28.md` for the full implementation/audit trail this section
promotes into canonical documentation).
**Amended:** 2026-07-29 — **ADR-AF-002 (Agent Firm Tier 1 Context Ownership) is COMPLETE.** Every
Tier 1 context object (technical/flow/regime/news/market/portfolio/risk/execution) is now assembled
by `engine/agent_firm_context.py` and attached to `SignalCandidate` at all five live construction
sites (`scheduler/scanner.py` x2, `scheduler/jobs.py` x2, `monitor.py` x1) before Agent Firm
evaluation; every specialist (`engine/agent_firm/agents/*.py`) consumes only typed candidate fields,
with no raw SQL/data retrieval inside any specialist. See `Audit/ADR-AF-002_CLOSURE_REPORT.md` for
the full WP1-4 implementation/audit/validation trail this section closes out, and
`Audit/ADR-AF-002_HANDOFF_CHECKLIST.md` for the operational handoff. Next Production Engine
milestone: see `Audit/PRODUCTION_ENGINE_NEXT_MILESTONE.md`.
**Amended:** 2026-09-15 — Agent Firm provider hierarchy flipped: **Claude Sonnet is now PRIMARY,
GLM-5.3 Flash (`zai`) is the sole FALLBACK** (`AGENT_FIRM_PROVIDER_ORDER=claude,zai`, `AGENT_FIRM_MODEL=glm-5.3-flash`;
code-level defaults in `engine/agent_firm/config.py` updated to match — `AGENT_FIRM_PROVIDER` now
defaults to `auto`, not single-provider `zai`). No router/circuit-breaker/quota-hold logic changed —
`providers/router.py` already tries `PROVIDER_ORDER` fresh, in order, on every invocation, so this
was a configuration-only change. Applies uniformly to all three Agent Firm call sites (post-close,
premarket, and the intraday exit-veto in `monitor.py`), which all share one router built from this
same config.
**Amended:** 2026-10-01 — NR7_BULL retired (D-066): invariant #10 now has
no grandfathered exception; registry_loader treats RETIRED as a hard admission exclusion.

> This document is the canonical workspace operating manual for Claude sessions in this
> repository. It defines how work should be performed but does not supersede repository source
> code, tests, or canonical governance documents. If conflicts occur, follow the Decision-Making
> Hierarchy defined in this document.

## What This Is

An Indonesian stock market (IDX) algorithmic trading suite: a Flask app (port 5001) that scans
IDX30/LQ45/IDX80 tickers with multiple quantitative strategies, manages paper trades with automatic
SL/TP via an exit kernel, fetches intraday flow/orderbook data from Stockbit, and sends Telegram
alerts. An optional multi-provider LLM "agent firm" (Claude Sonnet primary, GLM-5.3 Flash fallback) reviews
signals before they trigger trades. A separate `research/` subsystem runs walk-forward backtests,
a statistical gatekeeper, and regime analysis against the same data, under a CI-enforced boundary
that keeps research and production code from contaminating each other.

All times are **WIB (Asia/Jakarta, UTC+7)**. IDX market hours: 09:00–15:30 WIB Mon–Fri.

There is a second, unrelated Flask app in this repo: `chart-viewer/` (port 5050, own venv) — a
standalone multi-pane charting backend. It is not wired into `app.py` and has its own
`chart-viewer/README.md`.

---

## Session Contract

At the beginning of every session, Claude shall:

1. Confirm the current branch.
2. Confirm that CLAUDE.md has been read.
3. Identify the task category:
   - Research
   - Production
   - Governance
   - Infrastructure
   - Documentation
4. Verify whether the recommended model matches the task (see Recommended Claude Model).
5. State any repository invariants relevant to the task (see Repository Invariants).
6. Proceed only after this initialization.

If any prerequisite is missing (wrong branch, missing governance corpus, inconsistent registries,
etc.), report it before continuing.

---

## Before Starting Any Task

The checklist below operationalizes Session Contract steps 3–5 (task category, model check,
relevant invariants) into concrete, per-topic actions.

- **Confirm which branch you're on.** Most of what this document describes as "current" — the
  entire Research Governance Corpus (`docs/governance/`, `docs/roadmap/`, `docs/research_os/`,
  `docs/research_programs/`, `docs/Phase_A_Scientific_Foundation/`, plus
  `docs/RESEARCH_MASTER_PLAN.md`) and the operational-hardening work — exists **only** on
  `ops/hardening-2026-07-10`, not on `master` (`docs/roadmap/REPOSITORY_STATUS_NOTE.md`; verified
  there as 82 commits ahead of `master`, 0 behind, as of 2026-07-16). If working from `master`,
  treat the Research Governance Corpus section below as not-yet-present.
- If the task touches `research/`, `engine/registry_loader.py`, or any table listed in
  `RESEARCH_TABLES` (`tests/test_research_data_fence.py`), read **Architecture → Research /
  production separation** and **Repository Invariants** below before writing code.
- If the task is hypothesis-driven research rather than engineering, read
  `docs/research_os/RESEARCH_PROTOCOL.md` §1–2 first, then check the live state in
  `docs/research_programs/HYPOTHESIS_REGISTRY.md` and `FAILURE_REGISTRY.md` before assuming a
  program, family, or hypothesis doesn't already exist.
- Check `docs/roadmap/DECISION_LOG.md` for a decision already on record before proposing a
  governance or architecture change — decisions are amended only by a superseding entry, never a
  silent edit.
- Before touching any shrink-only allowlist or debt ledger (`_ROUTES_DEBT`, `_ROUTES_WRITE_DEBT`,
  `_LIFECYCLE_DEBT`, `_STATUS_DEBT`, a declared multiplicity family), read why the entry exists —
  each carries a dated reason in its source comment or governance record. The default action is to
  shrink it, not add to it.
- Run the relevant test file(s) before reporting work as done (see Testing). Several rules in this
  document are enforced only by tests, and a doc can be stale — the corpus's own `DECISION_LOG` §5
  records cases where a canonical document's status claim was contradicted by the actual
  repository state.

---

## Recommended Claude Model

This repository assumes the operator selects the most appropriate Claude model before starting work.

### Claude Opus
Use for:
- Research governance
- Repository-wide audits
- Architecture review
- Statistical methodology
- Experiment design
- Large refactoring decisions
- Cross-document consistency checks
- Final implementation review

### Claude Sonnet
Use for:
- Day-to-day implementation
- Bug fixes
- Feature development
- Test writing
- Documentation updates
- Small refactoring
- Code review

### Escalation Rule

If a task involves:
- repository-wide reasoning,
- governance decisions,
- architectural trade-offs,
- experiment design,
- or statistical interpretation,

escalate to Claude Opus before implementation.

Otherwise, Claude Sonnet is the default implementation model.

---

## Commands

**Run the app:**
```bash
./start.sh              # production runtime (gunicorn, SECTORS_APP_MODE=shadow) — same path as systemd
./start.sh dev           # Flask dev server fallback
python app.py            # equivalent to `start.sh dev`
```
Production is normally managed by `systemctl --user start idx-walkforward` (see `docs/OPERATIONS.md`),
not run by hand.

**Tests:**
```bash
pytest -q                                                   # full suite (hermetic — builds its own temp SQLite DBs, no fixtures needed)
pytest tests/test_indicators.py::TestCalcAtr::test_returns_series   # single test
pytest tests/agent_firm/test_firm.py -k "test_evaluate"      # by keyword
```
CI (`.github/workflows/test.yml`) runs `python -m pytest -q` on Python 3.12, no other lint/build step configured.

**Research jobs**: see `.claude/rules/research-governance.md` (loads automatically when working
under `research/` or `docs/research_*`).

**Manual data operations, release / deploy**: see the `repo-ops` skill.

---

## Environment Variables

Copy `.env.example` to `.env`. `config.py` is the single reader of `.env` — import settings from
there (`from config import DB_PATH, ...`), don't call `os.getenv()` directly in new modules.
Exceptions that intentionally keep their own `os.getenv()`: `app.py` and `scheduler/` (for
`importlib.reload()` compatibility in tests).

Key variables (full list in `.env.example`):

| Variable | Purpose |
|---|---|
| `DB_PATH` | SQLite DB path (default `data/walkforward.db`) |
| `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID` | Alerting — startup refuses to boot without these |
| `AGENT_FIRM_ENABLED`, `AGENT_FIRM_PROVIDER` (`claude`\|`zai`\|`auto`), `AGENT_FIRM_PROVIDER_ORDER` | LLM agent-firm review + provider routing/failover |
| `ZAI_API_KEY` | Z.ai key (agent firm primary provider) |
| `AUTH_MODE` (`off`\|`shadow`\|`enforce`) + `AUTH_TOKEN_ADMIN/OPERATOR/VIEWER/SCHEDULER` | Route auth (see Security below) |
| `EDGE_SCORE_MODE` (`off`\|`shadow`\|`enforce`) | Composite edge-score veto pipeline |
| `SECTORS_APP_MODE` (`shadow`\|`enforce`) | sectors.app overlay — observability only in shadow |
| `SCHEDULER_JOB_ERROR_COOLDOWN_S` | Cooldown (seconds, default 3600) between repeated Telegram alerts for the same crashing scheduler `job_id` — see `EVENT_JOB_ERROR` under Scheduler below |

`config.validate_config()` runs at startup and raises `ConfigError` (listing every problem at once)
if mandatory config is missing — see `config.py` and `docs/OPERATIONS.md`.

Secrets live only in `.env` and `.stockbit_token` (both gitignored, must be mode 600 — startup
validation aborts otherwise). Never read secrets via any path but `config.py`.

---

## Architecture

### Entry point & runtime (`app.py`, `wsgi.py`, `gunicorn.conf.py`)

Flask app registers blueprints from `routes/`, `routes_backtest_multi.py`, and `screener/routes.py`.
`app.init_runtime()` is the single startup path (idempotent table migrations, APScheduler start,
Telegram poller thread) — called from both `python app.py` (`__main__`) and gunicorn's
`post_worker_init` hook, so dev and prod never diverge.

**`gunicorn.conf.py` workers MUST stay 1** — the process embeds APScheduler and owns the SQLite
writer; a second worker would double-run every scheduled job. Guarded by
`tests/test_config_validation.py::test_gunicorn_config_stays_single_worker`. Concurrency comes from
threads (`gthread`, 8 threads), not processes.

### Database (`data/db.py`)

One SQLite file (`data/walkforward.db` by default). `data.db.connect()` is **the one entry point**
for any SQLite connection anywhere in the codebase — it sets `busy_timeout` + WAL, which is the
single fix point for a class of lock bugs this repo hit repeatedly before centralization. Do not
call `sqlite3.connect()` directly in new code.

### Research / production separation (the load-bearing architectural boundary)

This is the most important structural fact about the codebase. Production code (`scheduler/`,
`engine/`, `forward_testing/`, `data/`, `screener/`, `routes/`, plus `app.py`, `monitor.py`,
`paper_trade.py`) and the `research/` package are deliberately isolated, and the isolation is
**CI-enforced by source-scanning tests**, not convention:

- `tests/test_architecture_boundary.py` — production may not `import research`; `research/` may
  not import execution modules (`scheduler`, `monitor`, `paper_trade`, `forward_testing`, `app`).
  A small, explicitly shrink-only allowlist (`_ROUTES_DEBT`, capped at 4 entries) covers
  pre-existing violations in `routes/` — never add to it without also shrinking it.
- `tests/test_research_data_fence.py` — a set of tables (`wf_scores`, `wf_edge`, `backtest_cache`,
  `gate_decisions`, `gate_evidence`, `regime_profiles`, `regime_profile_cells`, `hypotheses`,
  `hypothesis_links`, `failure_registry`) are **write-once-by-research-only**: production may read
  them (dashboards) but a source-level SQL scan fails CI if production code writes them. One DAO
  exception (`engine/wf_edge.py` holds the write SQL but only research may call it) and one
  shrink-only route debt entry (`routes/backtest.py`).

If you add a new table that only research should populate, add it to `RESEARCH_TABLES` in that
test. If you're touching `routes/`, check whether the file you're in is already in one of the
debt allowlists before adding a `research` import or write.

### Research → production contract (Edge Registry)

`registry/edge_registry.yaml` + `registry/manifests/*.yaml` is the frozen handoff format: research
promotes a strategy by writing a registry entry (id/version/status/strategy_fn/regimes/universe
artifact); `engine/registry_loader.py` is the **only** production-side reader — it loads once
(cached), validates schema/compatibility, and degrades to `None` (selector falls back to legacy
behavior) on any failure, never crashing the engine. `APPROVED`/`SHADOW` registry states are
receipt-bound to gatekeeper evidence (`_LIFECYCLE_DEBT` is the sole, dated, shrink-only exception —
see the module docstring). `engine/strategy_specs.py` is the single source of truth for which
strategies exist and whether they have a live checker — `engine/strategy_registry/` is dead code
(deleted, left as an empty package by mistake; don't add to it).

### Research package (`research/`)

- `research/tracking.py` — append-only `research_runs` ledger: one row per research batch run
  (run_id, git commit, dataset fingerprint, params, environment provenance, metrics). Rows are
  never updated except to fill in finish fields on the run's own row; history is never rewritten.
- `research/gatekeeper/` — the statistical promotion pipeline (8 stages, REJECT / WATCHLIST /
  PROMOTE decisions, DSR computed from the real scan-distribution). Decisions + evidence persist
  append-only to `gate_decisions` / `gate_evidence`.
- `research/regime/` — hierarchical market regime taxonomy (BULL/BEAR/SIDEWAYS primary +
  declarable vol/liquidity axes); `regime_profiles` is append-only.
- `research/knowledge/` — the hypothesis registry (`hypotheses`, `hypothesis_links`,
  `failure_registry`); status transitions into the promotion track (`FORWARD_TESTING`, `VALIDATED`)
  require a linked gate/forward-test evidence receipt via a `set_status()` gateway — they cannot be
  hand-edited into existence.
- `research/cli.py` — batch jobs that used to run on the production scheduler (wf-refresh,
  backtest-cache, roller); cron-able, never imported by production.
- `docs/RESEARCH_MASTER_PLAN.md` is the **frozen architecture baseline** for this pipeline
  (Phases A–H); change it only via a dated, explicit amendment recorded in that file, never
  silently.
- `docs/research_os/RESEARCH_PROTOCOL.md` is the entry point for the research *methodology* —
  hypothesis lifecycle, gates, evidence tiers. Read it before doing hypothesis-driven research
  work; it is largely orthogonal to day-to-day engineering in this repo.

### Forward testing (`forward_testing/`)

Live-truth tracking for strategies promoted out of research (`ft_*` lifecycle: adapters,
lifecycle state machine, positions, storage). Wired into the nightly scheduler cycle; see
`docs/Forward_Testing_Architecture.md`.

### Scheduler (`scheduler/`)

APScheduler cron jobs (daily signal scan, EOD trade plan, premarket briefing, etc.), re-exporting
its pieces (`scanner`, `utils`) through `scheduler/__init__.py` so `from scheduler import X` keeps
working. Source of truth for cron entries outside APScheduler: `deploy/crontab`, every job wrapped
by `scripts/cron_wrap.sh` (per-job log + Telegram alert on nonzero exit).

**Telegram operational reporting, crash alerting, and secret redaction**: see `scheduler/CLAUDE.md`
(loads automatically when working under `scheduler/`) for the full detail — three daily reports
(EOD Trade Plan, Premarket Shortlist, Forward-Testing Summary), the `_job_sentinel` dedup guard, the
`EVENT_JOB_ERROR` crash-alert listener, and outbound-Telegram secret redaction.

### Security (`security/`)

Route-level RBAC (`viewer` < `operator`/`scheduler` < `admin`), gated by `AUTH_MODE`
(`off`/`shadow`/`enforce`). Every registered route must be classified in
`security/route_policy.py` — `tests/security/test_route_policy.py` fails CI on an unclassified
route (fail-closed: defaults to admin-only). Full detail: `docs/SECURITY.md`.

### Provider failover (`engine/agent_firm/`)

Multi-provider LLM router (Claude Sonnet primary, GLM-5.3 Flash (`zai`) fallback via `AGENT_FIRM_PROVIDER_ORDER`) with
a per-provider circuit breaker and quota-aware routing that holds a session-limited provider out of
rotation until its advertised reset time (see `docs/OPERATIONS.md` "Provider failover"). Every
router decision is persisted to `provider_events`. Both providers share subscription-plan 5-hour
usage windows — the Claude leg's quota is shared with interactive Claude Code use on this account.

---

## Testing

- Test tree mirrors source layout (`tests/engine/`, `tests/gatekeeper/`, `tests/regime/`,
  `tests/security/`, etc., plus flat `tests/test_*.py` for most modules).
- The suite is hermetic (per CI config comment): it builds its own temporary SQLite DBs and never
  touches the gitignored `data/walkforward.db`.
- Architecture is enforced by tests, not just documented: boundary (`test_architecture_boundary.py`),
  write fence (`test_research_data_fence.py`), route classification
  (`security/test_route_policy.py`), single-worker gunicorn config
  (`test_config_validation.py`), cron script existence (`test_cron_contract.py`). When you touch
  anything these cover, run the specific test file, not just a manual check.
- Shrink-only allowlists appear throughout (`_ROUTES_DEBT`, `_ROUTES_WRITE_DEBT`,
  `_LIFECYCLE_DEBT`, `_STATUS_DEBT`): each has its own `test_*_shrinks_only` assertion. Adding to
  one of these is a deliberate, reviewed exception, not a quick fix — prefer fixing the underlying
  violation.
- The source-scan boundary tests (`test_architecture_boundary.py`, `test_db_centralization.py`,
  `test_research_data_fence.py`) compare a file's path against their allowlist as
  `Path.relative_to(ROOT).as_posix()`, not `str(...)` — `str()` uses native path separators, which
  silently broke every allowlist match on Windows (backslash paths never matched the forward-slash
  allowlist entries, making already-documented debt look like fresh CI failures). Fixed 2026-07-28
  (RC1 audit R-1) — keep using `.as_posix()` in any new source-scan test.

---

## Data Integrity

- `research/tracking.py`'s dataset fingerprint identifies the research input exactly (settled
  OHLCV corpus + the `corporate_actions` table that adjusts it) via order-independent per-ticker
  checksums — any research result should be reproducible from its `run_id`'s fingerprint.
  Environment provenance (Python/platform/package versions) is captured automatically and
  fail-soft (never blocks or fails a run on capture error).
- Corporate actions (splits) are applied with gap-verification and double-adjustment protection —
  don't re-adjust already-adjusted OHLCV.
- Backups: nightly `scripts.db_backup` (SQLite online-backup API, WAL-safe) with integrity check +
  row counts before compression, 7 daily + 4 weekly retention. Weekly restore drill
  (`scripts.db_restore`) actually restores and verifies — "a backup is not considered good until
  this has passed" (`docs/OPERATIONS.md`).

---

## Research Governance Corpus

`docs/research_os/`, `docs/governance/`, `docs/roadmap/`, and `docs/research_programs/` together
form the **Institutional Research OS** — an institution-level scientific charter and governance
layer for how trading-strategy research is done here, distinct from (and wrapping) the executed
pipeline in `research/` described above. **This entire corpus exists only on
`ops/hardening-2026-07-10`** — see Before Starting Any Task.

Full detail (Layers/Programs/Stages/Gates, the two master roadmaps, document status levels, the
four registries, research lifecycle, evidence-first philosophy) has moved to
`.claude/rules/research-governance.md`, which loads automatically when working under
`docs/governance/`, `docs/roadmap/`, `docs/research_os/`, `docs/research_programs/`,
`docs/RESEARCH_MASTER_PLAN.md`, `docs/Phase_A_Scientific_Foundation/`, or `research/`.

---

## Repository Invariants

**Research/production pipeline invariants** (`docs/RESEARCH_MASTER_PLAN.md` §5 — 1–10 carried from
v2, 11–12 added in v3):

| # | Invariant | Enforcement |
|---|---|---|
| 1 | Research and production are separated | CI import-boundary scan (`test_architecture_boundary.py`); physical DB split (R-5) still open |
| 2 | Production never discovers strategies | Discovery lives only in `research/` |
| 3 | Production never optimizes parameters | Optimizer is research-only; production loads frozen params |
| 4 | Production never promotes strategies automatically | Promotion is the human-gated forward-test boundary |
| 5 | Research never deploys automatically | One-way boundary; deploy is a human step |
| 6 | Every experiment is reproducible | Seed + dataset fingerprint + git commit + run_id (`research/tracking.py`) |
| 7 | Every experiment is traceable | `research_runs` spine + Phase E hypothesis↔evidence trace |
| 8 | Every rejected hypothesis is preserved | `failure_registry` table + `FAILURE_REGISTRY.md`, both append-only |
| 9 | Every promoted edge has statistical evidence | Gatekeeper (`research/gatekeeper/`) PROMOTE decision required |
| 10 | Every promoted edge has forward-test evidence | R-10 receipt-bound registry lifecycle (`engine/registry_loader.py`); no remaining exceptions (NR7_BULL retired 2026-10-01, D-066) |
| 11 | No capital-facing status transition without a verifiable evidence receipt | `set_status()` gateway in `research/knowledge`; signed receipts are a Phase H prerequisite, not yet built |
| 12 | Multiplicity families are scoped by data epoch + feature space, **never decayed by wall-clock time** | Gate-config family scoping; any loosening is a versioned, non-retroactive, documented amendment |

**Code-level invariants enforced by CI tests** (see Testing above for the files): production may not
import `research.*`; `research/` may not import execution modules; production may not write to a
research-owned table; every registered route must be classified in `security/route_policy.py`;
gunicorn must run exactly 1 worker; every cron entry in `deploy/crontab` must reference a script
that exists; no hardcoded secret-shaped literal in a production `.py` file.

**Research-governance invariants** (documentary, not code-enforced, but stated as binding rules): a
declared multiplicity family is append-only and monotonic — once a program has an active
registration its family may only be widened via a formal governance amendment, never narrowed
(rules PG-3/PG-6/R7.5, `DECISION_LOG` D-028); a hypothesis is counted in its family from
`REGISTERED` and never leaves, including on failure (rule X8); the Decision Log is corrected only
by a superseding entry, never a silent edit.

---

## Decision-Making Hierarchy

Precedence rules for when repository documents or mechanisms appear to conflict have moved to
`.claude/rules/research-governance.md` (loads automatically under the research-governance paths
listed above) — CI-enforced tests beat document claims, `RESEARCH_MASTER_PLAN.md` v3 wins on frozen
mechanisms, `TAXONOMY_AND_NAMING_STANDARD.md` is the vocabulary authority, and so on through 7 rules.

---

## Coding Conventions

Derived from the codebase as it stands — not aspirational:

- Comments explain **why**, especially guard rails against a specific past incident (e.g.
  `gunicorn.conf.py`'s `workers=1` comment, `data/db.py`'s centralization docstring). Follow that
  pattern rather than restating what the code does.
- Idempotent migrations: table setup functions use `CREATE TABLE IF NOT EXISTS` +
  `PRAGMA table_info` column-presence checks before `ALTER TABLE ADD COLUMN`, so they're safe to
  call on every startup (see `data/db.py::init_agent_firm_tables`, `research/tracking.py`).
  Follow this pattern for any new schema change instead of a separate migration runner.
- Lazy imports are used deliberately to avoid import cycles or to keep the research/production
  boundary enforceable by static scan (e.g. `from research import jobs` inside a function body in
  `research/cli.py`) — don't "clean up" a lazy import into a top-level one without checking why it
  was lazy.
- Fail-soft vs fail-closed is chosen deliberately per surface: environment/provenance capture,
  registry loading, and metrics degrade to sentinels/`None` and log rather than crash; startup
  config validation and `AUTH_MODE=enforce` fail closed. Match the existing posture of the code
  you're editing rather than defaulting to one style everywhere.
- Dataclasses with a `name` field acting as a canonical key (`StrategySpec`) are the pattern for
  "single source of truth" registries — consistency between the registry and its consumers is
  itself asserted by a test (`tests/test_strategy_specs.py`).

---

## Commit Guidelines

Observed convention from `git log` on this repo (not enforced by tooling, but consistently
followed): Conventional-Commits-style subject lines, `type(scope): description`, e.g.
`feat(tracking): capture runtime environment provenance in research_runs`,
`docs(governance): D-024 -- Phase A exit gate; GO WITH CONDITIONS`,
`test(knowledge): fence hypotheses/hypothesis_links/failure_registry`. Scopes are typically a
package or subsystem name (`tracking`, `governance`, `knowledge`, `P-A`/`P-M` for research
programs). Match this style for new commits.

---

## Things Contributors Must Never Do

(Each of these is backed by a comment, test, or incident record in the codebase — not a generic
rule.)

- Never call `sqlite3.connect()` directly outside `data/db.py` — go through
  `data.db.connect()`/`get_db()` (lock-hardening lives in exactly one place; repeated lock bugs
  before centralization).
- Never raise gunicorn `workers` above 1 without first moving the scheduler out of the web process
  (`gunicorn.conf.py` docstring; `test_gunicorn_config_stays_single_worker`).
- Never import `research.*` from production code (`scheduler/`, `engine/`, `forward_testing/`,
  `data/`, `screener/`, most of `routes/`, `app.py`, `monitor.py`, `paper_trade.py`), and never
  import execution modules from `research/` — `test_architecture_boundary.py` fails CI.
- Never write to a research-owned table (`wf_scores`, `wf_edge`, `backtest_cache`,
  `gate_decisions`, `gate_evidence`, `regime_profiles`, `regime_profile_cells`, `hypotheses`,
  `hypothesis_links`, `failure_registry`) from production code — `test_research_data_fence.py`
  fails CI.
- Never add a new route without classifying it in `security/route_policy.py` — unclassified routes
  default to admin-only and CI fails (`tests/security/test_route_policy.py`).
- Never put secrets in source or commit `.env`/`.stockbit_token` — both are gitignored and startup
  validation aborts if either is group/world-readable; `tests/security/test_secret_hygiene.py`
  scans for hardcoded secret-shaped literals.
- Never add to a `_*_DEBT`/`_*_ALLOWLIST` shrink-only set without also shrinking it elsewhere — its
  paired test asserts the set only shrinks.
- Never apply a wall-clock decay to research multiplicity/trial counts — explicitly prohibited as
  a "data-snooping amnesia knob" (`docs/RESEARCH_MASTER_PLAN.md` invariant #12); multiplicity
  families are scoped by data epoch + feature space instead.
- Never retroactively change a REJECTED gatekeeper decision or an in-flight forward test's rule
  mid-test — both are treated as forms of snooping (Research Master Plan §3.1c, §3.2e).
- Never narrow or split a declared multiplicity family once it has an active hypothesis
  registration — it may only be widened via a formal governance amendment (rules PG-3/PG-6/R7.5,
  `docs/roadmap/DECISION_LOG.md` D-028); the only other remedy is terminating the program and
  starting a new family from zero, forfeiting every survivor.
- Never silently edit an entry in `docs/roadmap/DECISION_LOG.md`, `HYPOTHESIS_REGISTRY.md`, or
  `FAILURE_REGISTRY.md` — all three are append-only in spirit; a change is a new, dated, superseding
  entry, never an edit to the old one.
- Never treat a document under `docs/governance/`, `docs/roadmap/`, `docs/research_os/`,
  `docs/research_programs/`, or `docs/RESEARCH_MASTER_PLAN.md` as present when working from
  `master` — the entire corpus exists only on `ops/hardening-2026-07-10`
  (`docs/roadmap/REPOSITORY_STATUS_NOTE.md`).
- Never file a WITHDRAWN/RETIRED/DECAYED/SUPERSEDED hypothesis outcome as FAILED, or vice versa —
  the corpus explicitly treats conflating them as corrupting the institution's own failure-mode
  self-diagnostic (`docs/research_os/HYPOTHESIS_LIFECYCLE.md` §3.1).

---

## Repository Terminology

| Term | Meaning |
|---|---|
| WIB | Asia/Jakarta, UTC+7 — all scheduling/timestamps in this repo |
| Agent firm | The LLM-based signal-review pipeline (`engine/agent_firm/`) |
| Edge Registry | `registry/edge_registry.yaml` — the research→production strategy handoff contract |
| Gatekeeper | `research/gatekeeper/` — the statistical promotion pipeline (REJECT/WATCHLIST/PROMOTE) |
| DSR | Deflated Sharpe Ratio — computed from the real scan-Sharpe distribution in the gatekeeper |
| wf_scores / wf_edge | Research-owned, write-fenced tables holding walk-forward strategy scores |
| Shadow mode | A feature runs and logs/observes but never blocks or changes behavior (`AUTH_MODE`, `EDGE_SCORE_MODE`, `SECTORS_APP_MODE` all share this pattern) |
| Enforce mode | The same feature actually blocks/changes behavior |
| Research Master Plan | `docs/RESEARCH_MASTER_PLAN.md` — frozen architecture baseline for the research pipeline, Phases A–H |
| Research Protocol | `docs/research_os/RESEARCH_PROTOCOL.md` — the research methodology entry point (separate from this file) |
| Research OS | The institutional governance layer (`docs/research_os/`, `docs/governance/`, `docs/roadmap/`, `docs/research_programs/`) that wraps the Research Master Plan v3 pipeline |
| Layer (L0–L8) | An architecture stratum of the Research OS — "what the system is made of" (`docs/governance/TAXONOMY_AND_NAMING_STANDARD.md`) |
| Program (P0–P6) | A research track — "what is being researched"; P0 = the delivered v3 Edge Pipeline, P-M/P-A the two active 2026-07 programs |
| Stage (S1–S10) / Gate (G1–G4) | Pipeline steps a hypothesis moves through, and the institutional approval checkpoints between them |
| Hypothesis Registry / Failure Registry | `docs/research_programs/HYPOTHESIS_REGISTRY.md` / `FAILURE_REGISTRY.md` — append-only indexes of every hypothesis and every falsified/failed one, distinct from the code-level Edge Registry |
| Evidence class (K1–K7) / tier (E0–E7) / confidence (C0–C4) / reproducibility (X0–X4) | The four independent axes `docs/research_os/EVIDENCE_MODEL.md` scores a claim on; a class ceiling caps the tier no matter how much evidence accumulates |
| REGISTERED / VALIDATED / FAILED / VOID | Frozen-era hypothesis lifecycle states (`docs/research_os/HYPOTHESIS_LIFECYCLE.md`) — WITHDRAWN/RETIRED/DECAYED/SUPERSEDED are terminal but explicitly *not* failures |

---

## Unknown (not inferred from repository)

- Whether there is a linter/formatter convention (no `.flake8`, `ruff.toml`, `pyproject.toml`
  lint config, or pre-commit config was found) — CI runs only `pytest -q`.
- Whether type checking (mypy/pyright) is used anywhere — no config found.
- The intended relationship between `docs/RESEARCH_MASTER_PLAN.md` (frozen v3, code-facing) and
  the broader `docs/governance/` / `docs/research_os/` corpus (extensive, in-flight institutional
  research governance) beyond what `docs/governance/RESEARCH_OS_RECONCILIATION.md` states — that
  document should be treated as authoritative over any summary here if the two ever seem to
  disagree.
- PR review process / required approvers — no `CODEOWNERS` or PR template was found.
