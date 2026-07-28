# Production Engine — RC1 Fix Report

**Date:** 2026-07-28
**Basis:** `Audit/RELEASE_READINESS_AUDIT_2026-07-28.md` (recommendation: READY WITH MINOR FIXES).
This report closes the four approved findings (R-1–R-4) from that audit. Generated, point-in-time
record — superseded rather than edited if a later pass finds more.
**Constraints honored:** no architecture redesign, no new trading features, no Operations Dashboard
work (deferred to its own phase per instruction).

---

## 1. R-1 — Architecture Boundary: conclusion

**Not an architecture regression. Not intentional-but-undocumented debt. A test-implementation bug.**

Investigation (in order, per the audit's decision tree — "do not guess"):

1. Verified via `git diff --stat HEAD -- routes/backtest.py routes/portfolio.py routes/screener.py
   tests/test_architecture_boundary.py` that these files carry **zero uncommitted diff** — the
   failure is against committed code, not WIP.
2. Read `tests/test_architecture_boundary.py`'s `_ROUTES_DEBT` allowlist directly: it **already
   contains** `routes/backtest.py`, `routes/screener.py`, `routes/portfolio.py` with a dated comment
   explaining they're known, accepted debt from when the scan was widened to `routes/`. The
   architecture's own policy already says these imports are allowed.
3. Grepped the three files for the actual `research.*` imports (`research.walkforward_multi`,
   `research.optimizer`, `research.backtest_roller`, `research.portfolio_backtest`,
   `research.fastmover_study`) — confirmed real, matching exactly what the allowlist comment
   describes (backtest UI, optimizer endpoints, fastmover study trigger). Not a false match.
4. Reproduced the failure directly: `Path.relative_to(ROOT)` converted to `str()` yields
   `'routes\\backtest.py'` on Windows, which never equals the allowlist's `'routes/backtest.py'`
   (forward slash) — so the allowlist-skip (`if rel in ALLOWLIST: continue`) silently never fires on
   Windows, and every already-accepted debt entry gets reported as a fresh violation. The identical
   bug pattern was independently confirmed in `test_research_data_fence.py` (`DAO_ALLOWLIST`,
   `_ROUTES_WRITE_DEBT`) and `test_db_centralization.py` (`ALLOWLIST = {"data/db.py"}` — the wrapper
   module's own authorized `sqlite3.connect()` call was being flagged against itself).

**Conclusion: the implementation (routes/ importing research/, exactly as much as already
allowlisted) is correct; the boundary *test* was incorrect** — cross-platform-unsafe path
comparison, not a policy bug. Fixed by switching `rel = str(p.relative_to(ROOT))` to
`rel = p.relative_to(ROOT).as_posix()` in all three affected assertions across the three test files.
Zero production code changed; zero allowlist entries added, removed, or otherwise touched.

**No owner decision was required** — this was an objectively verifiable, mechanically fixable test
bug, not a judgment call about the architecture.

---

## 2. R-2 — Scheduler Error Rate Limiting: what shipped

`scheduler/__init__.py` gained `JobErrorRateLimiter`, a per-`job_id` cooldown gate consulted by
`_make_job_error_listener` before calling `send_telegram`:

- **First-failure visibility preserved**: a `job_id` with no prior alert always alerts immediately.
- **Configurable cooldown**: `SCHEDULER_JOB_ERROR_COOLDOWN_S` env var (scheduler/ is one of
  CLAUDE.md's documented `os.getenv()` exceptions), default 3600s; also overridable per-instance
  for tests. Repeats of the same `job_id` inside the cooldown window are logged
  (`[scheduler] job <id> failed (alert on cooldown)`) but not sent to Telegram.
- **No duplicate Telegram spam**: a job crashing on every tick (the audit's concrete example,
  `scheduled_multi_strategy_scan`, 5×/day) now sends exactly one alert per cooldown window instead
  of one per crash.
- **Low memory overhead**: two dicts (`_last_alert`, `_suppressed`) bounded by the number of
  *distinct* `job_id`s ever seen (~20 for this scheduler) — never grows with event volume, verified
  by a test hammering the same `job_id` 1000 times and asserting dict size stays at 1.
- **Deterministic behavior**: the clock is injectable (`clock=` param); all tests use a manually
  advanced fake clock, no real `sleep`/wall-clock timing.
- **Scheduler behavior unchanged**: only whether an alert is *sent* is gated — no change to job
  execution, retries, `max_instances`, or any other scheduling semantics.
- When the cooldown expires and an alert fires again, it now reports how many failures were
  suppressed in between (`format_job_error_alert(..., suppressed=N)` →
  "+N more failures suppressed since last alert"), so a quieted repeat doesn't look identical to a
  first-time failure.

---

## 3. R-3 — Canonical Documentation: what shipped

Promoted from `Audit/PRODUCTION_ENGINE_IMPLEMENTATION_AUDIT_2026-07-28.md` (a point-in-time record)
into the two canonical documents CLAUDE.md itself designates:

- **`CLAUDE.md`**: bumped to Version 1.1 with a dated `**Amended:**` line (kept the original FROZEN
  metadata + Effective Date, per this repo's pattern of dated, explicit amendments rather than
  silent edits). Extended the `### Scheduler (`scheduler/`)` architecture section with the three
  Telegram reports, the `watchlist_snapshot` table, the `_job_sentinel` dedup pattern, the
  `EVENT_JOB_ERROR` crash-alert + rate-limiter, and the Telegram redaction reuse. Added
  `SCHEDULER_JOB_ERROR_COOLDOWN_S` to the Environment Variables table. Added a Testing-section note
  documenting the R-1 `.as_posix()` fix so it isn't silently reverted by a future edit.
- **`docs/OPERATIONS.md`**: new "## Telegram operational reporting" section (job/time/content table
  for all three reports, the shared snapshot/diff + dedup-guard mechanisms, the crash-alert
  rate-limiter with its SQL-caveat note that job-run history still isn't queryable — explicitly
  scoping what the next Operations Dashboard phase needs to cover). Extended "## Logging" with the
  redaction-reuse note. Extended the daily "## Operational checklist" with two new items (checking
  for suppressed-count job-error alerts; confirming all three daily reports actually arrived).

The audit files remain as historical/point-in-time records (per this repo's own documented
convention for such files) — they are no longer the *only* source, which was the finding.

---

## 4. R-4 — Telegram Redaction: what shipped

`utils/logging_config.py`'s `SecretRedactionFilter` logic was extracted into a standalone
`redact_secrets(text: str) -> str` function (same `_SECRET_VARS` list, same ≥8-char/comma-split
rule, byte-identical masking behavior) — the filter now delegates to it instead of duplicating the
loop. Both outbound Telegram paths now call it before sending:

- `utils/telegram.py::send_telegram` — the central alerting function used by every job in
  `scheduler/jobs.py`, including all three new reports and the `EVENT_JOB_ERROR` alert.
- `routes/telegram.py::send_telegram_reply` — the bot-command-reply path, included for "all
  outbound operational alerts" completeness even though it wasn't the primary driver of R-4.

No second redaction implementation was written — one function, two callers, matching the
constraint.

---

## 5. Files modified

| File | Change |
|---|---|
| `tests/test_architecture_boundary.py` | `.as_posix()` fix (2 call sites) — R-1 |
| `tests/test_db_centralization.py` | `.as_posix()` fix (1 call site) — R-1 |
| `tests/test_research_data_fence.py` | `.as_posix()` fix (2 call sites) — R-1 |
| `scheduler/__init__.py` | `JobErrorRateLimiter`, cooldown env var, listener wiring — R-2 |
| `.env.example` | documented `SCHEDULER_JOB_ERROR_COOLDOWN_S` — R-2 |
| `CLAUDE.md` | Scheduler architecture section, env var table, Testing note, version bump — R-3 |
| `docs/OPERATIONS.md` | new Telegram reporting section, Logging note, checklist items — R-3 |
| `utils/logging_config.py` | extracted `redact_secrets()`, filter now delegates to it — R-4 |
| `utils/telegram.py` | `send_telegram` now redacts before posting — R-4 |
| `routes/telegram.py` | `send_telegram_reply` now redacts before posting — R-4 |

## 6. Tests added or updated

- `tests/test_scheduler_job_error_alert.py` — 13 new tests: `JobErrorRateLimiter` unit tests (first
  failure alerts, cooldown suppression, resume-with-suppressed-count, per-job_id independence,
  bounded memory, default cooldown value) + listener-integration tests (repeated failures → one
  Telegram send; resurfacing with suppressed count; first failure still immediate).
- `tests/test_telegram_util.py` — 2 new tests (`send_telegram` redacts a configured secret; ignores
  values under the 8-char floor).
- `tests/test_logging_config.py` — 6 new tests (`redact_secrets()` unit tests + `SecretRedactionFilter`
  delegation tests — this filter had no direct test before this pass).
- `tests/test_routes_telegram_redaction.py` — new file, 3 tests for `send_telegram_reply`
  (redacts, leaves clean text alone, still skips the placeholder token).
- No test was modified in a way that changes its assertions — R-1's fix only changed *how* `rel` is
  computed, not what any test checks for.

## 7. Validation

- Targeted re-run (`test_architecture_boundary.py`, `test_db_centralization.py`,
  `test_research_data_fence.py`, `test_scheduler_job_error_alert.py`, `test_telegram_util.py`,
  `test_logging_config.py`, `test_routes_telegram_redaction.py`, `test_trade_plan.py`,
  `test_premarket_firm_scan.py`, `tests/forward_testing/`): 252 passed, 3 failed — all 3 are the
  same pre-existing Windows-only environment gaps already documented (tempdir file-lock on log
  rotation cleanup; missing `langgraph` package) — zero regressions.
- Full suite, before vs. after, diffed with `Compare-Object`: **exactly** the 4 R-1 boundary/fence
  cases disappeared from the failing set; **nothing else changed** (no new failures, no other
  fixes). 1438 passed / 56 failed / 6 errors (was 1410 / 60 / 6) — the +28 passed is the new test
  coverage from R-2/R-4.
- No duplicate Telegram alerts: covered by the new rate-limiter integration tests (§6) and
  unchanged by the existing `_job_sentinel` dedup-guard tests for the three daily reports.
- Documentation updated: confirmed by direct read-back of the edited `CLAUDE.md`/`docs/OPERATIONS.md`
  sections (not just "trust the diff").

---

## 8. Remaining work before RC1

None of R-1–R-4 has open follow-up. What's left is exactly what the Release Readiness Audit already
scoped as out-of-band from these fixes:

- **Operations Dashboard / Job History** — the one planned workstream this task explicitly excluded.
  Per the audit's R-5 finding (reaffirmed, unchanged by this pass): job failures are durably logged
  (`logs/app.log`) but not queryable as "which jobs ran today and which didn't" without log-grep —
  scope the dashboard to a persisted job-run ledger (`ft_run`/`ft_run_log`'s pattern is a proven
  template) + a route/UI over it, not a rebuild of crash-alerting (already closed).
- Two Medium items from the audit were **not** in scope for this pass and remain open by design
  (not blocking, not requested here): R-6 (near-duplicate diff-rendering code between EOD/Premarket
  — a refactor-for-DRY, explicitly out of scope per "do not refactor for style alone") and R-7
  (the forward-test dedup-guard's stylistic try/except placement asymmetry — already verified
  correct, just asymmetric).
- R-9 (environment-only pre-existing test failures — missing `langgraph`/`yaml`, Windows-subprocess
  `.sh` incompatibility) remains, as expected — these are local dev-venv artifacts, not
  release-blocking, and out of scope for a fix here.
