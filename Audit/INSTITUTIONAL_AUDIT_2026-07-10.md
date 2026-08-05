# Institutional Production Readiness Audit — 2026-07-10

**Auditor role:** Principal Software Architect (read-only audit; no code modified)
**Scope:** entire repository at `master` @ `5ca318e`, plus the live runtime it drives (app pid 1353, crontab, production DB)
**Evidence baseline:** full test suite executed during audit — **1196 passed in 101s** (hermetic, no live DB needed)

---

## 0. Executive Summary

The system has undergone a genuine and verifiable transformation since the 2026-07-02 audit: a one-kernel exit engine, cost/parity authority, a raw-basis data corpus, CI-enforced research/production separation (import boundary + write fence + registry-driven promotion), DB lock hardening, heartbeat dead-man's-switch, and a well-designed multi-provider LLM abstraction. The *quant-engineering* discipline is now well above hobby grade.

The *operations* layer is not. The production instance is the developer's working tree behind a symlink, served by the Flask development server, with no process supervision, **no database backup for a 3.0 GB single-file SQLite holding every table the business owns**, no authentication on 98 HTTP routes bound to `0.0.0.0`, plaintext credentials in a world-readable `.env`, and two cron jobs that have been failing every scheduled run for weeks because the scripts they call do not exist.

Two live defects were confirmed during the audit itself:

1. The agent firm is **degrading in production right now** (ZAI 429 rate-limits at 08:37–08:39 WIB today) and **cannot fail over to Claude** because production config never enables the router's `auto` mode — the entire failover subsystem shipped on 2026-07-09 is idle.
2. The `provider_events` telemetry table has **zero rows ever written**; the metrics module queries it, so failover/circuit metrics are permanently zero. The write side was never built.

**Verdict: DO NOT DEPLOY (as an institutional system).** As a single-operator research/paper platform it is defensible — no capital is at risk (`paper_trades` open = 0, live long book deliberately empty pending a BULL regime). The conditions to change the verdict are enumerated in §15.

---

## 1. Architecture

**Intended architecture** (per `docs/superpowers/specs/`, esp. `2026-07-07-research-production-separation-design.md` and `2026-07-08-firm-provider-abstraction-design.md`): a production trading engine (scheduler → scanner → gates → firm → signals/shadow positions) that consumes research outputs *only* through a git-versioned Edge Registry; research lives in `research/` and runs off-process via `research.cli` + cron.

**Alignment: largely intact.** The load-bearing boundaries are real and CI-enforced:

- `tests/test_architecture_boundary.py` — production may not import `research/`; research may not import execution. `ALLOWLIST = ∅`, shrink-only. **Verified green.**
- `tests/test_research_data_fence.py` — only `research/` writes `wf_scores`/`wf_edge`/`backtest_cache`; DAO allowlist = `{engine/wf_edge.py}`, shrink-only. **Verified green.**
- `registry/edge_registry.yaml` + frozen artifact + manifest, loaded by `engine/registry_loader.py` with schema/compat validation and fail-open alarms. One APPROVED entry (NR7_BULL v1). Promotion/rollback = git commit. **This is the strongest piece of the architecture.**

**Drift and violations found:**

| # | Violation | Evidence | Severity |
|---|---|---|---|
| A-1 | ~15 orphan top-level modules outside any package boundary (`monitor.py`, `paper_trade.py`, `flow_filter.py`, `news_filter.py`, `stockbit_fetcher.py`, `auto_token.py`, `routes_backtest_multi.py`, …). The boundary tests must enumerate them by hand (`PRODUCTION_FILES` lists 6; the rest are unguarded). | repo root; `tests/test_architecture_boundary.py:15` | High |
| A-2 | Dead code shipped in the production tree: `engine/strategy_registry/` (deliberately unmerged design, per project history, yet present on master), `migrations/applied/` ad-hoc patch scripts, `scheduler/jobs.py.bak`, `scheduler/scanner.py.bak`, `config.py.bak`, `scheduler.py.manual_backup`, 5 template `.bak/.broken` variants in `templates/`. | `ls` of respective dirs | Medium |
| A-3 | Repo-as-workspace: experiment scripts, screenshots, WhatsApp images, logs, and planning docs at root (`TOWR.md`, `TOWR_chart.png`, `WhatsApp_TOWR.jpeg`, `_brpt_engine_test.py`, `backfill_flow_jan_apr.py`, `zai_quota_monitor.sh`, `app.log` 460 KB). Untracked-but-present in the *running production directory*. | `git status`, root `ls` | Medium |
| A-4 | `engine/strategies.py` is a 2,636-line monolith holding all 14 strategy implementations + `STRATEGY_FUNCS` registry. Single highest-churn, highest-risk file in the codebase. | `wc -l` | Medium |
| A-5 | Heavy research-shaped workloads (interactive multi-strategy backtests, `routes/backtest.py`, 1,261 lines) execute **inside the production trading process**, sharing its CPU, its SQLite writer slots, and its GIL with the scheduler. The research/production split moved *jobs* out but not *interactive compute*. | `app.py` blueprint registration; `routes/backtest.py` | High |

## 2. Layering

There is no Presentation → API → Application → Domain → Infrastructure layering, and no pretense of one. The actual shape is: **one Flask process = UI templates + 98 JSON routes + APScheduler + domain engine + direct SQLite access**, with route handlers frequently embedding SQL directly (e.g. `app.py:/metrics`, `routes/*.py`).

Dependency-direction violations of note:

- **Infrastructure ↔ domain inversion:** `data/db.py` (infrastructure) imports `forward_testing.storage.db` inside `init_db()` (domain/persistence of a higher layer) — acknowledged in-code as a cycle-avoidance lazy import, i.e. the cycle exists conceptually.
- **Scheduler as god-layer:** `scheduler/__init__.py` re-exports ~30 symbols from scanner/jobs/reports/utils, so anything can (and does) reach anything through `scheduler`.
- **Routes → engine → DB** is direct everywhere; there is no application-service seam where a REST API could later attach without dragging Flask along.

This is a known, tolerated state for a single-operator system, but it is the main reason API readiness (§7) scores low.

## 3. Hidden Coupling & Duplication

| Finding | Evidence | Severity |
|---|---|---|
| **118 raw `sqlite3.connect()` call sites** remain outside tests. The Phase-3C "centralization" guard (`tests/test_db_centralization.py`) protects only 12 enumerated hot modules; the other ~35 modules (engine/risk_alert, smc_flow, delta_flow, sectors_app_filter, dashboard, routes/*, screener/*, …) can silently regress to no-timeout/no-WAL connections — the exact defect class behind six historical lock incidents. | `grep -c`, guard test | High |
| **Duplicated configuration.** `config.py` declares itself the single env authority, yet `app.py`, `scheduler/__init__.py`, `scheduler/scanner.py`, `data/db.py` each re-read `os.getenv` independently, and the machine-specific default `DB_PATH` (`/home/tjiesar/10 Projects/...`) is duplicated in ≥4 modules (10 hardcoded absolute-path occurrences). | grep | High |
| **Duplicated scheduler domains.** APScheduler (in-process, ~40 jobs) + user crontab (9 lines) coordinate only through comments ("18:30, after APScheduler 16:05 run finishes (~16:25); avoids DB lock conflict"). No shared calendar, no mutual visibility, and the crontab uses *both* path spellings of the project dir. | `scheduler/__init__.py`, `crontab -l` | High |
| **Duplicated route surfaces.** Two screener modules (`screener/routes.py` + `routes/screener.py`), two backtest modules (`routes/backtest.py` + root `routes_backtest_multi.py`). | imports in `app.py` | Medium |
| **Duplicated/stray state.** Six zero-byte orphan DB files (`flow.db`, `idx_data.db`, `data/idx_lite.db`, `data/paper_trade.db`, `data/trades.db`, `data/db.sqlite3`) from earlier code generations — landmines for a misconfigured `DB_PATH`. Duplicate index `idx_ohlcv_ticker` + `idx_ohlcv_raw_ticker` (both on `ohlcv(ticker)`). | `ls`, `PRAGMA index_list` | Medium |
| Module-global mutable caches as shared state: `scanner._macro_panic_cache`, `firm._market_ctx` (correctness depends on callers remembering `reset_market_ctx()`), `registry_loader._cache`. Documented, test-poisonable, single-process-only assumptions. | source | Medium |
| No circular imports detected at package level (lazy imports are used to break the two known potential cycles). | — | — |

## 4. Production Safety

**Can it run unattended every trading day?** It *does*, but on a narrow margin. Confirmed strengths: heartbeat every 5 min + external crontab watchdog (`scripts/check_scheduler_heartbeat.py`, verified firing every 10 min); token-expiry pre-alerts; OHLCV coverage monitor; fail-open alarms to Telegram (`engine/fail_open_alarm.py`); per-day job sentinels (`_job_sentinel` dedup); holiday skip; WAL + 30 s busy timeout on hot paths.

**Confirmed live failures and gaps:**

| # | Finding | Evidence | Impact |
|---|---|---|---|
| P-1 | **LLM failover is configured OFF in production.** `.env` sets no `AGENT_FIRM_PROVIDER`, so `PROVIDER_MODE` defaults to `"zai"` and `_validate()` returns a single-provider router. Today 08:37–08:39 WIB the ZAI endpoint returned 429s; agents recorded errors and the Risk node emitted `degraded` pass-throughs. **174 `degraded` vs 3 `veto` decisions since 07-07.** The Claude failover path, circuit breaker chain, and daily-cap logic merged on 07-09 have never executed in production. | `agent_firm/config.py:45`, `factory._validate`, `agent_traces` rows 2026-07-10 01:37–01:39 UTC | The firm gate degrades to flow-gate fallback exactly when markets are busiest; the flagship resilience feature is dormant. |
| P-2 | **`provider_events` is written by no one.** `log_provider_event()` emits only to Python logging; the DB table (created + indexed in `data/db.py`) has **0 rows ever**, while `providers/metrics.py` queries it for failover/circuit stats. Additionally, failed-call traces persist `provider=''`, so per-provider failure attribution in `agent_traces` is broken too. | table count = 0; `events.py:31`; error traces with empty provider | Provider observability is fictional: any ops review of failover behavior reads all-zeros. |
| P-3 | **No database backup.** `data/walkforward.db` is 3.0 GB and holds all 53 tables (signals, shadow positions, research scores, telemetry, 11.7 M flow bars). The only backup is `walkforward.db.bak_20260427_193503` — 75 MB, from April, 40× smaller than current. No dump job, no snapshot, no offsite copy, no restore drill. | `ls -la data/` | Single disk event = total, unrecoverable loss of the business's entire state and 5-year data corpus. **This alone justifies the verdict.** |
| P-4 | **Two cron jobs have failed every run for weeks.** `sectors_fetcher.py` (daily 19:00) and `audit_signals.py` (daily 16:00) do not exist in the tree; logs show unbroken `No such file or directory`. Whatever consumed `sectors_*` tables is silently stale, and no alert fires on cron failure. | `logs/sectors_fetcher.log`, `logs/audit_signals.log` | Silent data staleness + proof that cron failures are invisible. |
| P-5 | **No process supervision.** `app.py` runs under the **Flask/Werkzeug development server** (`app.run`), parented to init, started manually via `start.sh`. A crash stops trading until a human notices the heartbeat alarm and manually restarts. No systemd unit, no restart policy, no graceful shutdown of APScheduler or the Telegram poller thread. | `ps`, `app.py:192` | SPOF; dev server is explicitly not for production (single-process, no worker recovery). |
| P-6 | **Production = dev working tree.** `/home/tjiesar/idx-walkforward-5001` is a symlink to the dev directory. Any uncommitted edit, checkout, or agent experiment lands in the live engine at next import/restart; `git status` in prod shows deleted docs + 25 untracked files. No build, no release artifact, no immutable deploy. | `readlink`, `git status` | Deploys are unreviewable; rollback target undefined. |
| P-7 | Missing retry/backoff at the provider layer: a 429 storm burns all providers' breaker slots in seconds (30 s cooldown, no jitter/backoff, no honor of `Retry-After`). Network fetch jobs (`stockbit_fetcher`, news) similarly rely on next-cron-slot semantics rather than explicit retries. | `circuit_breaker.py`, jobs | Medium |
| P-8 | `/metrics` scans `ohlcv` (1.04 M rows) with `WHERE date=?` — no date index exists (only ticker/UNIQUE); `scheduled_signals` (6.9 k rows) has **no indexes at all** and is queried by `date(scan_time)` (unindexable expression). Cheap today; a per-15s Prometheus scrape would hammer the writer's DB. | `PRAGMA index_list` | Low-Med |
| P-9 | Resource leak surface: request handlers spawn untracked daemon threads (`routes/screener.py:171,620`; `screener/routes.py:44`) with no concurrency cap — N concurrent HTTP calls = N heavy scans inside the trading process. | grep | Medium |

## 5. Research vs Production Separation

**Verdict: the strongest subsystem.** Three mutually reinforcing, CI-tested fences (import boundary, write fence, DB-connect hygiene) with shrink-only allowlists; research jobs off the production scheduler (crontab `research.cli` — verified installed); production selection reads the frozen registry artifact, not live `wf_edge`.

Remaining softness (all known/deferred, none silent):

- Production still *reads* `wf_scores`/`wf_edge` directly in ~10 sites (blacklist, quality gate, edge veto) — the deferred "reader retirement". Until then, a research recompute mid-session changes live gating inputs without a promotion commit. **Medium.**
- Research and production share one physical DB file and one machine; a runaway research backfill can still lock/starve production I/O (mitigated by WAL + compute-then-write, not eliminated). **Medium.**
- Interactive backtest routes run in the production process (A-5). **High**, already counted.

## 6. Provider Layer

**Design quality: high.** Small `Protocol` interface; self-registering provider registry; factory validates config and fails loud; router owns ordering/failover; per-provider circuit breaker with a correct single-trial HALF_OPEN using cooperative-scheduling atomicity; Claude daily-call quota; shared fence-stripping; typed `ProviderResponse` with cost/latency; pydantic event schema. Extensible: adding a provider = one module + `@register` + config name.

**Defects/improvements:**

1. **P-1/P-2 above** — failover dormant in prod; events not persisted. Fix = write `log_provider_event` through to `provider_events` (the table and indexes already exist) and set `AGENT_FIRM_PROVIDER=auto` in prod. *(≤1 day total.)*
2. Claude provider shells out to a developer CLI (`claude -p …`) — couples production trading to an interactive tool's PATH, login state, subscription quota, and output format; `cost_usd=0.0` makes the daily **spend** cap blind to Claude usage (only the call-count cap applies). Acceptable as bridge; document as such and prefer the API SDK for institutional use. *(2–3 days.)*
3. No backoff/`Retry-After` handling distinct from breaker cooldown (P-7). *(1 day.)*
4. Failed traces persist `provider=''` → metrics can't attribute failures (P-2 corollary). *(0.5 day.)*
5. `router.health()` awaits providers sequentially and is unused by any liveness surface — `/health` doesn't include the firm. *(0.5 day.)*

## 7. API Readiness

**Not ready for an institutional REST layer.** Missing, exactly:

1. **Authentication/authorization — none of the 98 routes have any** (no API key, no session auth; grep confirms zero auth constructs). Blocking.
2. No versioning (`/api/...` unversioned, mixed with page routes), no OpenAPI/schema, no consistent error envelope (handlers return ad-hoc shapes; some 500 via bare exception).
3. No request validation layer (query params parsed by hand per handler).
4. No pagination conventions on list endpoints; some return unbounded table dumps.
5. Long-running work triggered by fire-and-forget daemon threads with no job-status resource (P-9) — an API contract needs a jobs endpoint.
6. No rate limiting; the API shares a process with the trading scheduler (A-5), so an API consumer can degrade trading.

## 8. Frontend Readiness

The server-rendered shell (base.html/shell.css/shell.js, unified nav) is serviceable for a single operator. For independent frontend development the backend contract is **not stable**: undocumented and unversioned JSON shapes, five dead template variants committed, and page routes intermixed with data routes. Blocking issues = §7 items 2–4 plus a documented contract per endpoint.

## 9. Database

- **Schema:** 53 tables in one SQLite file; sensible UNIQUE natural keys on the big tables (`ohlcv(ticker,date)`, `stockbit_flow_bars(ticker,trade_date,bar_time)`); `is_final`/calendar/corporate-actions raw-basis design (Phase 2A) is genuinely good.
- **Indexes:** 25 explicit; gaps: no `ohlcv(date)` index (P-8), `scheduled_signals` unindexed, one duplicate index pair to drop. Archived copies (`ohlcv_pre_raw_rebuild`, `wf_*_pre_2b`) ride inside the production file, inflating the 3 GB and every future backup.
- **Migrations:** no framework and no version table. Schema evolution = idempotent `CREATE IF NOT EXISTS` + `PRAGMA table_info` ALTER blocks scattered across ≥4 init functions (`data/db.py`, `data/market_schema.py`, `screener/db.py`, `forward_testing/storage/schema.py`), plus a graveyard of applied patch scripts. Works forward-only on one machine; unreproducible elsewhere; no down-migrations. **High.**
- **Scalability:** WAL mode, single writer. 11.7 M flow-bar rows growing ~50–100 k/week is fine for SQLite *reads*, but the system's own history (6 lock bugs) shows write contention is the binding constraint. No retention policy on any hot table.
- **Backward compatibility:** additive-only ALTERs — acceptable.
- **Backups: none (P-3). Critical.**

## 10. Testing

- **1196 tests, all passing in 101 s, hermetic, CI-enforced on push/PR (ubuntu, py3.12, 15-min timeout).** For a system this size that is genuinely strong, and the guard-test pattern (boundary/fence/hygiene as source-scan tests) is best-practice.
- **No coverage measurement** (no pytest-cov configured), so "coverage %" is unknown; treat the following as the critical untested map:
  - `auto_token.py` (Playwright Stockbit login — the single most operationally fragile artifact) — untested.
  - Telegram poller loop and webhook path — untested end-to-end.
  - `routes/backtest.py` (1,261 lines) and `routes_backtest_multi.py` — thin/no route tests.
  - **The provider-events persistence contract** — a test asserting `provider_events` receives rows would have caught P-2.
  - **A config-parity test asserting prod `.env` exercises the router in `auto` mode** (or at minimum a startup log/alarm when failover is disabled) would have caught P-1.
  - Concurrency: nothing simulates scheduler-vs-HTTP write contention, the historical #1 incident class.
  - Frontend JS: untested entirely.

## 11. Technical Debt Register

| Sev | Item | Effort | Priority |
|---|---|---|---|
| **Critical** | P-3 No DB backup/restore for the 3 GB single-file store | 1–2 d (nightly `sqlite3 .backup` + offsite sync + quarterly restore drill) | 1 |
| **Critical** | P-1 Failover dormant: prod config + startup alarm when router is single-provider | 0.5 d | 2 |
| **Critical** | P-5/P-6 Supervised, release-based runtime: systemd unit (restart=always) + gunicorn + deploy-from-tag instead of symlinked working tree | 2–3 d | 3 |
| **High** | P-2 Persist provider events; fix `provider=''` failure attribution | 1 d | 4 |
| **High** | §7-1 Authentication on all routes (even a static bearer token) + stop binding 0.0.0.0 unauthenticated | 1–2 d | 5 |
| **High** | P-4 Cron hygiene: delete/repair dead entries; alert on nonzero cron exit (wrapper) | 0.5 d | 6 |
| **High** | Migration framework (even a hand-rolled `schema_version` table + ordered scripts) | 2–3 d | 7 |
| **High** | Extend DB-connect guard to all modules (118 raw sites → `data.db.connect`) | 2–3 d | 8 |
| **High** | Config unification: one `config.py`, kill 10 hardcoded absolute paths | 1–2 d | 9 |
| **High** | A-5 Move interactive backtests out of the trading process (worker or queue) | 3–5 d | 10 |
| **Medium** | Retention/archive policy for flow bars + drop `*_pre_*` archive tables from the live file | 1 d | 11 |
| **Medium** | Repo hygiene: purge .bak/.broken/dead code/binaries; enforce via CI lint | 1 d | 12 |
| **Medium** | Split `engine/strategies.py` along the existing `STRATEGY_FUNCS` seam | 2–3 d | 13 |
| **Medium** | Provider backoff/Retry-After; Claude SDK migration; spend cap covering Claude | 2–3 d | 14 |
| **Medium** | print()→logger in scheduler (93 prints; stdout currently goes to a socket, not the rotating JSON log) | 1 d | 15 |
| **Low** | Index gaps + duplicate index; `/metrics` query cost | 0.5 d | 16 |
| **Low** | Coverage tooling (pytest-cov) + coverage floor in CI | 0.5 d | 17 |

## 12. Scalability

| Dimension | Verdict |
|---|---|
| 100 symbols | **Ready** — already scans ~972 tickers 5×/day. |
| 500 symbols | **Ready with care** — batch fetch + WAL hold; watch flow-bar growth and per-scan LLM spend. |
| 1000 symbols | **Marginal** — single-writer SQLite + in-process scheduler + 11.7 M-row table + per-ticker Python loops; needs retention policy, read replicas or a client/server DB, and worker separation (A-5) first. |
| Multiple exchanges | **Not ready** — IDX/Stockbit/WIB assumptions are hardcoded through fetcher, token lifecycle, calendars, tick rules. Structural work. |
| Multiple brokers | **Not ready** — no execution/broker abstraction exists at all (paper only). |
| Multiple LLM providers | **Ready** — the one dimension explicitly engineered for; registry+factory make a third provider a one-module change. |

## 13. Security

| Finding | Evidence | Severity |
|---|---|---|
| No authentication on any of 98 routes; app binds `0.0.0.0:5001`. Anyone on the LAN can read positions/signals and trigger heavy scans. | `app.py:192`, grep | **Critical (institutional) / High (home LAN)** |
| Plaintext credentials in `.env` mode 664 (world-readable, group-writable): Stockbit user/pass, Telegram token, Tavily + LLM API keys. `.stockbit_token` also 664. No secret manager, no rotation story (JWT rotates daily by necessity, not design). | `ls -la`, key names | High |
| Positives: parameterized SQL throughout (no injection patterns found); no `shell=True`; subprocess uses arg-vectors (`claude`, `git rev-parse`) with timeouts; security headers middleware; Telegram webhook secret supported; `.env`/DBs properly gitignored (verified: no secrets in git). | greps, `git ls-files` | — |
| `FLASK_SECRET_KEY` falls back to `os.urandom` per boot (sessions/CSRF invalidate on restart). | `app.py:29` | Low |
| Claude CLI as a prod dependency inherits whatever auth/session the developer account has — a privilege-boundary smell for an institutional posture. | `providers/claude.py` | Medium |

## 14. Deployment & Rollback

**Deployable today? No — not to any machine but this one.** Blockers, exhaustively: (1) 10 hardcoded `/home/tjiesar/...` paths; (2) no container/unit file/Procfile of any kind; (3) dev-server runtime; (4) prod-dir symlink to working tree; (5) crontab as unmanaged out-of-repo config referencing two path spellings and two missing scripts; (6) 3 GB DB with no provisioning/restore path; (7) `.env` handcrafted, drifted from `.env.example` (still on deprecated `DEEPSEEK_*` names — the fallback shim is what saves it).

**Rollback:** code rollback = manual `git checkout` + manual restart (unversioned, untested); **edge rollback = git revert of the registry — genuinely good**; data rollback = impossible (no backups); config rollback = nothing (env + crontab live outside git).

## 15. Final Verdict

| Dimension | Score |
|---|---|
| Architecture | **7.5/10** — registry-driven separation and the provider layer are institutional-grade designs; orphan modules, monolith strategies file, and research compute inside the trading process hold it back. |
| Code Quality | **7/10** — disciplined, well-commented, guard-tested; marred by dead code, print-logging, and duplication. |
| Production Readiness | **3.5/10** — dev server, no supervision, no backups, dormant failover, dead crons. |
| Maintainability | **6.5/10** — excellent tests and specs; config sprawl and repo clutter tax every change. |
| Scalability | **5/10** — fine at current scale; SQLite single-writer and hardcoded IDX assumptions cap it. |
| Observability | **5/10** — JSON logs, heartbeat watchdog, fail-open alarms are real; provider metrics fictional, stdout prints lost, no cron alerting, no dashboards. |
| Operational Risk | **3.5/10** (10 = well-controlled) — an unsupervised process writing to an unbacked-up 3 GB single file, operated from a live working tree. |
| **Overall Institutional Score** | **5/10** |

### DO NOT DEPLOY — as an institutional system

**Justification:** Institutional deployment requires that the platform survive the loss of any one disk, process, provider, or operator, and that what runs in production be a reviewed, reproducible artifact. Today none of these hold: the only copy of all business state is one unbacked-up SQLite file (P-3); the runtime is an unsupervised Flask dev server started by hand from the developer's working tree (P-5/P-6); the LLM resilience layer is configured off and was observed degrading in production during this audit (P-1) with its telemetry table empty (P-2); and the HTTP surface is unauthenticated on all interfaces (§13). These are operational failures, not quant failures — the research discipline (registry promotion, CI fences, exit-kernel parity, honest empty book) is ahead of many professional shops.

**Conditions to re-grade to GO WITH CONDITIONS** (≈ 2 weeks of focused work): items 1–6 of the debt register — backups with a restore drill, failover enabled + startup alarm, systemd + gunicorn + tag-based deploys, provider-event persistence, route authentication, cron hygiene. With those closed, the remaining debt (migrations, config unification, worker separation) is compatible with a supervised paper-trading deployment while the frozen GO/NO-GO evaluation window (N≥15, ≥+0.5%/trade, 6 months from 2026-07-08) runs its course.

**Context for the verdict's stakes:** the engine currently manages **zero live capital** (empty long book by design, awaiting a BULL regime; 0 open paper trades). The verdict therefore blocks nothing today — it defines the gate that must be passed *before* the first rupiah of institutional capital is exposed.

---
*Method note: all findings verified against the current implementation (code reads, greps, live DB queries in read-only mode, process/crontab inspection, full test-suite execution). No code was modified. Prior audits were used only for comparison after independent verification.*
