# Production Engine — Release Readiness Audit (RC1)

**Date:** 2026-07-28
**Scope:** Entire production pipeline (scheduler, jobs, engine, reporting, forward-testing,
Telegram, config, database, logging, error handling, startup/shutdown, recovery, testing,
documentation). `research/` is out of scope by design (CI-enforced isolation).
**Method:** Three independent adversarial audit passes (functional completeness/integration,
operational reliability, observability/security/documentation) plus direct verification of the
most consequential claim (see Finding R-1). This is a generated, point-in-time record — superseded
by a later audit, never edited in place.
**Posture:** This audit treats the three prior implementation phases (EOD/Premarket/Forward-Testing
reporting, scheduler crash alerting) as suspect, not proven — each was independently re-examined,
not merely re-summarized.

---

## Executive Summary

**No critical defects.** The three implementation phases are functionally complete, tested (68 new
tests, zero regressions across two full-suite runs), and contain no dead code, no TODOs, no
duplicate pipelines that matter, and no race conditions in the new dedup guards. However, this audit
found **one already-merged, CI-failing architecture-boundary violation unrelated to this work**
(R-1) and **two real gaps introduced by this work** (R-2 alert-storm risk, R-3 zero canonical
documentation) that should be resolved, not merely noted, before calling this RC1.

**Recommendation: READY WITH MINOR FIXES.** None of the findings require architecture change,
feature redesign, or new implementation beyond small, scoped fixes — see §5 roadmap.

---

## 1. Findings by severity

### Critical
None found.

### High

**R-1 — `routes/backtest.py`, `routes/portfolio.py`, `routes/screener.py` import `research/` on
committed HEAD; `test_architecture_boundary.py::test_production_does_not_import_research` and two
`test_research_data_fence.py` cases currently fail against committed code, not uncommitted WIP.**
Verified directly: `git diff --stat HEAD -- routes/backtest.py routes/portfolio.py
routes/screener.py tests/test_architecture_boundary.py` returns empty — these files are byte-for-byte
what's already merged. `git log` shows why it was never caught: `d935600 test(boundary): widen
research-boundary + write-fence scans to routes/` only recently added `routes/` to the scanned
scope; an earlier commit (`124bce2`) had emptied the debt allowlist on the assumption production
imported zero research. The violation predates all three implementation phases in this
conversation — nothing in EOD/Premarket/Forward-Testing reporting touches these files — but it
means **`pytest -q` does not currently pass cleanly on committed HEAD**, independent of this work.
Per `CLAUDE.md`'s own Decision-Making Hierarchy ("a CI-enforced test is ground truth over any
document's claim"), this is a live, merged violation of Invariant #1 (research/production
separation), not a documentation staleness issue. **Not fixed here** — per this audit's
"do not implement unless critical" constraint, and because the right fix (revert the import, or
re-admit these three files to `_ROUTES_DEBT`/`_ROUTES_WRITE_DEBT` with a dated justification) is a
judgment call for whoever owns that boundary, not something to silently patch mid-audit.

**R-2 — `EVENT_JOB_ERROR` listener has no rate-limiting, cooldown, or dedup; concrete alert-storm
path exists.** `scheduler/__init__.py`'s new crash-alert listener (Phase 1) sends one Telegram
message per uncaught exception, unconditionally. `scheduled_multi_strategy_scan`
(`scheduler/scanner.py:1204`, runs 5×/day) has no top-level try/except around its body — a
persistent bug there (e.g. a broken downstream call) fires 5 identical Telegram alerts/day
indefinitely; `daily_signal_scan` (1×/day) has the same exposure at lower frequency. This directly
contradicts the discipline the codebase already applies elsewhere — the provider-failover system
(`docs/OPERATIONS.md` "Provider failover") explicitly dedupes alerts per reset window specifically
to avoid this failure mode. Most other jobs already swallow their own exceptions internally and
never reach this listener, so the blast radius is these two scanner entry points, not all ~20 jobs
— but "one alert per hour per job_id" (or similar) is a cheap, scoped fix and should land before
RC1, both to prevent operator alert fatigue and to keep the new alerting mechanism trustworthy.

**R-3 — Zero mention of any Phase 1–3 feature in canonical documentation.** `CLAUDE.md` and
`docs/OPERATIONS.md` have no reference to `watchlist_snapshot`, `EVENT_JOB_ERROR`,
`forward_testing.reporting`, or the three new/modified Telegram reports. Everything exists only in
`Audit/PRODUCTION_ENGINE_IMPLEMENTATION_AUDIT_2026-07-28.md`, which is explicitly a generated,
point-in-time record by its own header — not the canonical operations manual `CLAUDE.md` designates
itself to be. A future engineer reading `CLAUDE.md`'s Architecture/Scheduler section today would not
learn any of these three reports or the crash-alert listener exist. This is a documentation-vs-
implementation mismatch squarely inside this audit's own mandate ("ensure implementation matches
documentation").

### Medium

**R-4 — Telegram alert bodies bypass the existing secret-redaction filter.**
`utils/logging_config.py`'s `SecretRedactionFilter` is attached to logging handlers only, not to
`send_telegram()`. `format_job_error_alert` sends `str(exception)[:300]` straight to Telegram with
no redaction pass — if an exception message ever embeds a token/URL fragment, it ships unredacted to
Telegram while the equivalent log line would have been masked. Not new (every pre-existing
`send_telegram(f"...{str(e)[:200]}...")` call in `scheduler/jobs.py` has the same latent gap) — the
new listener just adds one more instance of an already-unaddressed pattern.

**R-5 — No persisted, queryable job-run history — confirms the Operations Dashboard is still
genuinely needed, but narrower than it might sound.** Job failures *are* durably captured today (the
root-logger rotating JSON handler in `utils/logging_config.py` captures APScheduler's own
executor-level exception logging independent of the new listener), so a failure is not "gone forever"
if a Telegram message is missed. What's actually missing is **queryability**: no table or route
answers "which jobs ran today and which didn't" without log-grep/jq. Scope the next phase precisely
to (a) a persisted job-run ledger and (b) a route/UI over it — the crash-*alerting* half of
observability is already closed by Phase 1.

**R-6 — Near-duplicate diff-rendering code between EOD and Premarket reporting.**
`engine/trade_plan.py::_build_diff_section` and `scheduler/jobs.py::_build_premarket_diff_sections`
independently implement similar added/removed/rank-delta/confidence-delta rendering (~35 lines
each) because the two specs asked for genuinely different message shapes (one combined section vs.
five separate ones). Not a bug — both are tested and correct — but a third reporting surface would
likely copy-paste a third variant. Worth a shared "render one change-list section" helper if a
fourth report is ever added; not urgent for RC1.

**R-7 — Dedup-guard placement inconsistency (stylistic).** `run_forward_test_cycle`'s
`_job_sentinel` check sits inside its own try/except; EOD/premarket's sit outside theirs. Verified
intentional and correct (forward_test_cycle's contract is "never raise on any error"), but the
asymmetry is worth a one-line comment for the next engineer rather than being self-evident.

### Low

**R-8 — Full orphan-module sweep not independently re-verified this round** (relied on a prior
sweep from Phase 1 that found only the already-known-dead `engine/strategy_registry/` package). No
evidence of a new orphan, but flagged as "checked via reliance on prior finding," not "freshly
re-verified," in the interest of precision.

**R-9 — Pre-existing, environment/branch-wide test failures unrelated to any of this work.** The
full suite carries 60 failed + 6 errors both before and after all three implementation phases
(byte-identical failing-test set, confirmed by `Compare-Object` diff across full runs). Root causes
already isolated in the Phase 1 report: missing `langgraph`/`yaml` packages and Windows-subprocess
incompatibility with `.sh` scripts in this local dev venv (environment-only, would likely pass on
the real Linux CI runner), plus the R-1 boundary violation and an empty `engine/agent_firm/providers`
registry issue (both **not** environment artifacts — see R-1). Not blocking this audit's
recommendation on its own, but relevant context: this branch's test suite is not fully green
independent of anything audited here.

---

## 2. What was checked and found clean (explicitly, per the adversarial-audit brief)

- No TODO/FIXME/XXX/HACK/`NotImplementedError`/disabled (`if False:`) code anywhere in
  `scheduler/`, `engine/`, `forward_testing/`, `routes/`, `screener/`, `app.py`, `monitor.py`,
  `paper_trade.py`.
- Every new symbol from all three phases has a verified call site — none orphaned.
- All three `_job_sentinel` dedup guards are single-`INSERT`-on-a-`PRIMARY KEY` — atomic given
  `data/db.py`'s `busy_timeout=30000` + WAL; no check-then-insert TOCTOU gap.
- `gunicorn.conf.py` enforces `workers=1`; `post_worker_init`/`worker_exit` start and shut down the
  scheduler exactly once per worker process — no double-registration path for the new listener, no
  double-started `BackgroundScheduler`.
- No duplicate-Telegram-send path found for any of the three new/modified send sites.
- `forward_testing/reporting.py` never holds a connection open across its multi-query assembly —
  compliant with the module's own stated short-lived-connection discipline.
- APScheduler's default `max_instances=1` (never overridden in `scheduler/__init__.py`) already
  prevents same-job-id overlap in-process.
- No hardcoded secret-shaped literal in any of the four new/modified files;
  `tests/security/test_secret_hygiene.py` actively scans all of them (none excluded).
- No research-governance invariant violated by the new production tables (`watchlist_snapshot`,
  `ft_shadow_*` are correctly *not* in `RESEARCH_TABLES` — they're production-owned, not
  research-owned); the frozen governance corpus is untouched by any of this work.

---

## 3. Recommended fixes before RC1

| # | Fix | Effort | Owner decision needed? |
|---|---|---|---|
| 1 | Rate-limit/dedup `EVENT_JOB_ERROR` alerts (e.g. one per job_id per hour) | Small | No — mechanical |
| 2 | Document Phases 1–3 in `CLAUDE.md` (Architecture/Scheduler) and `docs/OPERATIONS.md` | Small | No — mechanical |
| 3 | Resolve the `routes/backtest.py`/`routes/portfolio.py`/`routes/screener.py` research-import violation (R-1) — fix the imports, or re-admit to `_ROUTES_DEBT`/`_ROUTES_WRITE_DEBT` with a dated reason | Small–Medium | **Yes** — requires deciding whether the import is intentional debt or a defect |
| 4 | Add a redaction pass (or drop to a generic "see logs" message) for exception text sent to Telegram | Small | No — mechanical, but pick a policy |

None of these require architecture change or new features — all are additive/corrective within the
existing design.

---

## 4. Recommendation

**READY WITH MINOR FIXES.**

Not "NOT READY": no critical defect exists, core functionality (three Telegram reports + crash
alerting) is implemented, tested, and verified regression-free. Not an unconditional "READY FOR
RC1" either: R-1 is a live CI-ground-truth failure on committed code that RC1 shouldn't ship past
silently, and R-2/R-3 are real, cheap-to-fix gaps in the very features this effort just built.

---

## 5. Final implementation roadmap to RC1

1. Apply fixes #1, #2, #4 from §3 (mechanical, no owner decision required).
2. Get an owner decision on fix #3 (R-1) and apply it.
3. Re-run the full suite; confirm the failing-test set shrinks by exactly the R-1 cases (the
   environment-only failures in R-9 will remain until run on the real Linux CI runner — expected,
   not a blocker).
4. Proceed to the previously-scoped **Operations Dashboard / Job History** phase, narrowed per R-5:
   a persisted, queryable per-job run ledger (started/finished/status/error, likely reusing the
   `ft_run`/`ft_run_log` pattern already proven in `forward_testing/`) plus a route/UI over it —
   not a rebuild of crash-alerting, which Phase 1 already closed.
