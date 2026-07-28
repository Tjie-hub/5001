# Production Engine — Release Conditions Matrix

**Date:** 2026-07-28
**Basis:** Every finding across `Audit/PRODUCTION_READINESS_REPORT.md`,
`Audit/END_TO_END_VALIDATION_REPORT.md`, `Audit/SECURITY_REVIEW_REPORT.md`,
`Audit/TECHNICAL_DEBT_RELEASE_REVIEW.md`, and `Audit/PRODUCTION_ENGINE_RELEASE_CERTIFICATION.md`.
**Method:** Every "Current status" cell below was re-verified in this pass, not copied forward
unchecked. Several statuses changed materially from the prior certification because this pass
obtained **direct, primary-source evidence from the live production host** (SSH to
`tjiesar@192.168.31.214`, the machine actually running `idx-walkforward.service`) rather than relying
on inference from the Syncthing-synced local checkout — see `Audit/OWNER_DECISION_PACKAGE.md` for the
full evidence trail on the items this changed.

---

## Legend

- **Status:** `FIXED` (committed + validated this certification cycle) · `VERIFIED SAFE TODAY`
  (live-confirmed not currently exploitable/harmful, design gap may remain) · `OPEN` (real,
  unaddressed) · `ACCEPTED DEBT` (bounded, dated, documented — not a defect)
- **Can release before fixing?** Answers "does this block shipping the certified commits" — not
  "should this ever be fixed."

---

## Fixed This Certification Cycle

| ID | Severity | Description | Evidence | Status | Owner decision? | Release before fix? | Recommendation |
|---|---|---|---|---|---|---|---|
| RC-002 | P0 | `paper_trades` never created at `init_runtime()` — fresh/DR deploy boots once then permanently deadlocks | Live-reproduced restart failure; `app.py` | FIXED (`4826cae`) | No | Yes (fixed) | Closed |
| RC-003 | P0 | Redundant `print()` in `announce_registry()` crashes on non-UTF-8 stdout, unprotected in scheduler boot | Live-reproduced `UnicodeEncodeError`; `engine/registry_loader.py` | FIXED (`e30d4f3`) | No | Yes (fixed) | Closed |
| RC-004 | P1 | `STOCKBIT_PASSWORD` vs `STOCKBIT_PASS` name mismatch disabled password redaction | `utils/logging_config.py` vs `auto_token.py:28` | FIXED (`0c35d1b`) | No | Yes (fixed) | Closed |
| RC-005 | P1 | `worker_exit` used `shutdown(wait=False)`, contradicting its own graceful-shutdown claim | APScheduler source; `gunicorn.conf.py` | FIXED (`368f6c8`) | No | Yes (fixed) | Closed |
| RC-006 | P1 | `paper_trade.py` exception-echoing `print()`s bypassed redaction | `paper_trade.py` lines 65/205/641/656 (orig) | FIXED (`21edd4d`) | No | Yes (fixed) | Closed |
| RC-007 | P3 | `.stockbit_token.lock` not gitignored | `git check-ignore -v` | FIXED (`ac2d349`) | No | Yes (fixed) | Closed |

---

## The Mandatory Item — Telegram Webhook

| ID | Severity | Description | Evidence | Status | Owner decision? | Release before fix? | Recommendation |
|---|---|---|---|---|---|---|---|
| RC-001 | P1 (downgraded from P0) | `/telegram/updates` skips its own HMAC check entirely when `TELEGRAM_WEBHOOK_SECRET` is unset — a design fail-open, not enforced by `validate_config()`, absent from `.env.example` | See full analysis below | **VERIFIED SAFE TODAY** | Yes — see Owner Decision Package | **Yes** | Ship as-is; harden `validate_config()` as a scheduled fast-follow, not a release blocker |

**Full analysis (Mandatory Objective 1):**

1. **Is `TELEGRAM_WEBHOOK_SECRET` required?** No — `config.py:27` defaults it to `""`, and
   `routes/telegram.py`'s check (`if TELEGRAM_WEBHOOK_SECRET:`) makes the entire HMAC verification
   conditional on it being set. Nothing in `validate_config()` requires it.
2. **Does `.env.example` document it?** No — confirmed via direct grep, zero mentions. This is a
   real documentation gap: an operator provisioning a new environment from `.env.example` alone would
   have no way to know this variable exists or matters.
3. **Does startup validate it correctly?** No — `validate_config()` enforces `TELEGRAM_TOKEN` and
   `TELEGRAM_CHAT_ID` (fails startup if missing) but has no equivalent check for
   `TELEGRAM_WEBHOOK_SECRET`.
4. **Does the webhook fail open or fail closed?** **Fails open when unset** — confirmed by direct
   code reading (`routes/telegram.py`): the `if TELEGRAM_WEBHOOK_SECRET:` guard skips
   `hmac.compare_digest(...)` entirely when the var is empty, and the route proceeds to process any
   POST body unconditionally. When set, it correctly performs a constant-time comparison and returns
   403 on mismatch — fails closed and correctly, in that configuration.
5. **Does current behavior match intended security policy?** **Partially.** The *code's* policy is
   "secure if configured, insecure by silent default" — an intentional-looking design (the same
   `if TOKEN_SET:` pattern recurs elsewhere in this codebase for optional hardening), but with no
   safety net if the configuration step is ever skipped. The *actual, currently-running* policy is
   secure, because the secret **is** configured — see below.

**Direct, primary-source confirmation obtained this pass (not present in the prior certification):**
SSH access to the live production host (`tjiesar@192.168.31.214`, per session memory) was used to
check the actual `.env` the running service reads from — not the Windows-side Syncthing copy, the
file itself, on the box, read directly:

```
$ grep -c "^TELEGRAM_WEBHOOK_SECRET=" "/home/tjiesar/10 Projects/idx-walkforward-5001/.env"
1
$ grep -qE "^TELEGRAM_WEBHOOK_SECRET=.+" "..." && echo SET_NONEMPTY
SET_NONEMPTY
```

Confirmed the running service (`idx-walkforward.service`, `loaded active running`) reads from exactly
this file — `/home/tjiesar/idx-walkforward-current/.env` is a symlink to it
(`lrwxrwxrwx ... -> /home/tjiesar/10 Projects/idx-walkforward-5001/.env`). **The value is set and
non-empty on the actual live system, right now.** The webhook is currently fail-**closed** in
practice, despite the code's fail-open design when unconfigured. No secret value was read, printed,
or logged — only key presence was checked, per this task's security posture.

**Verdict: this is not an active exposure. It is a real design gap (no defense-in-depth against a
future deploy silently omitting this variable) that should be hardened, but it does not block this
release.** See `Audit/OWNER_DECISION_PACKAGE.md` for the formal decision trail and recommended
hardening, prepared rather than silently implemented, per this task's explicit instruction.

---

## Remaining Findings — Full Matrix

| ID | Severity | Description | Evidence | Status | Owner decision? | Release before fix? | Recommendation |
|---|---|---|---|---|---|---|---|
| RC-008 | P1 | `validate_config()` requires `DB_PATH` to pre-exist as a file — contradicts its own "fresh DB allowed" comment; nothing automates creating it | `config.py`; reproduced live in the prior E2E validation pass | OPEN | Yes — see decision package | Yes | Safe after release (production DB already exists); fix before the *next* fresh/DR deploy is actually attempted |
| RC-009 | P1 | Silent auth-token role downgrade on duplicate token values across roles | `security/auth.py::configured_tokens()` | OPEN, **confirmed dormant** — production `.env` has no `AUTH_MODE` set (defaults to `off`), verified directly on the live host | No | Yes | Safe after release; must resolve before `AUTH_MODE` is ever switched to `enforce`/`shadow` in this environment |
| RC-010 | P1 | `start_scheduler()`'s ~20 `add_job()` calls have no wrapping try/except — one bad registration crashes the whole boot | `scheduler/__init__.py:186-311` | OPEN | No | Yes | Safe after release; recommend as next-milestone hardening (touches ~20 call sites, not a minimal single-pass fix) |
| RC-011 | P1 | No external alert if the process crash-loops at boot (systemd `StartLimitBurst` untuned) | `deploy/idx-walkforward.service` | OPEN | Yes — ops config, not code | Yes | Safe after release; ops-level tuning + a boot-health external check, not a code change |
| RC-012a | P1→Resolved | Backup cron gap (~36h, 2026-07-25/26) | `logs/cron_db_backup.log` | **RESOLVED** — confirmed live: backups resumed and ran cleanly 07-26, 07-27 (`rc=0`, `integrity=ok`, `3229.9MB`, `635.2MB` compressed) | No | Yes | No further action; the underlying dead-man's-switch gap (Finding RC-012b) is the real residual item |
| RC-012b | P1 | No dead-man's-switch for "did this cron job fire at all" (vs. "did it fail after firing") — and the **weekly restore drill specifically has not run since 2026-07-19**, a 9-day gap as of this writing (should have fired 07-26) | `logs/cron_db_restore_drill.log`, confirmed live on the production host | **OPEN, currently active** | Yes — see decision package | Yes (data safety unaffected; backups are current) | Investigate why the restore-drill cron entry specifically stopped firing (the backup entry recovered on its own; the drill entry did not) — recommend running one manual drill this week and checking the crontab/cron daemon state directly |
| RC-013 | P1 | Zero `PRAGMA integrity_check` anywhere in the application startup path | `app.py::init_runtime()` | OPEN | No | Yes | Safe after release; partially mitigated by the nightly backup's own verify step (now confirmed running) |
| RC-014 | P1 | `monitor.py`'s per-trade SL/TP loop has no per-trade exception isolation; caller only logs, never alerts, on failure | `monitor.py:527`, `scheduler/jobs.py:367-372` | OPEN | No | Yes | Safe after release; recommend as next-milestone hardening |
| RC-015 | P1 | Halted/delisted-ticker positions silently stop being monitored, no staleness alert | `monitor.py:203-206` | OPEN | No | Yes | Safe after release; backlog item |
| RC-016 | P1 | `redact_secrets()` structurally cannot redact the live Stockbit bearer JWT (not an env var) | `utils/logging_config.py`; `.stockbit_token` | OPEN | Yes — needs a design decision on how to feed the live token value into redaction | Yes | Safe after release; recommend next-milestone security hardening pass |
| RC-017 | P1 | Truncation happens before redaction at 10+ call sites — a secret straddling the cutoff partially leaks | `scheduler/jobs.py`, `scheduler/reports.py`, `scheduler/__init__.py`, `scheduler/utils.py` | OPEN | No | Yes | Safe after release; coordinated multi-file fix, recommend next milestone |
| RC-018 | P1 | Committed token-write path lacks atomic write / explicit chmod (hardened version exists, uncommitted, deliberately excluded from RC1) | `auto_token.py`/`stockbit_fetcher.py` at HEAD | OPEN | Yes — whether/how to land the deferred hardening commit | Yes | Prioritize as the next commit after this release — the work already exists, just needs review + landing |
| RC-019 | P1 | `cron_wrap.sh`'s raw-`curl` Telegram crash alert bypasses redaction entirely | `scripts/cron_wrap.sh` | OPEN | No | Yes | Safe after release; needs a shell-level redaction equivalent, next milestone |
| RC-020 | P1 | `/health` doesn't verify scheduler liveness — a broken deploy can pass the deploy gate | `app.py:78-103`, `scripts/wait_for_health.sh` | OPEN | No | Yes | Safe after release (heartbeat dead-man's-switch is a ~10min-delayed backstop); next milestone |
| RC-021 | P1 | `scripts/release.sh`'s default `SHARED_PATHS` doesn't match the actual `DB_PATH` default location | `scripts/release.sh` | OPEN — **confirmed non-issue in practice**: live production sets an absolute `DB_PATH` manually (verified directly), avoiding this gap | No | Yes | Safe after release; fix the default anyway so a future operator can't hit it by relying on defaults |
| RC-022 | P1 | Release packaging (`scripts/release.sh`) never exercised end-to-end by CI | `.github/workflows/test.yml` | OPEN | No | Yes | Safe after release; add a CI step next milestone |
| RC-023 | P2 | `redact_secrets()` is exact-value-match only, not pattern-based | `utils/logging_config.py` | ACCEPTED DEBT | No | Yes | Backlog |
| RC-024 | P2 | `metrics.py::provider_stats()` defaults `success_rate=1.0` on zero calls (mitigated by `available`/`circuit_state`) | `engine/agent_firm/providers/metrics.py` | ACCEPTED DEBT | No | Yes | Backlog |
| RC-025 | P2 | `.playwright_state/`'s live session cookies not covered by the secret-permission check | `config.py` | ACCEPTED DEBT | No | Yes | Backlog |
| RC-026 | P2 | No release-directory retention/pruning — unbounded disk growth over time | `scripts/release.sh`/`rollback.sh` | ACCEPTED DEBT | No | Yes | Backlog |
| RC-027 | P2 | No explicit `wal_checkpoint` call — relies on SQLite default auto-checkpoint | `data/db.py` | ACCEPTED DEBT | No | Yes | Backlog; no evidence of actual harm |
| RC-028 | P3 | No `signal.signal()` handler for the `python app.py` dev-mode path | `app.py` | ACCEPTED DEBT | No | Yes | Backlog; production always runs under gunicorn |
| RC-029 | P3 | 13 files with bare `print()` in non-critical CLI/debug-tool paths | Various | ACCEPTED DEBT | No | Yes | Backlog |
| RC-030 | P3 | No disaster-recovery runbook exists | `docs/*.md` | OPEN | No | Yes | Recommend writing one; not urgent given single-operator system |
| RC-031 | P3 | `rollback.sh` falls back to newest release (not older) when no `current` symlink exists at all | `scripts/rollback.sh` | ACCEPTED DEBT | No | Yes | Informational; bootstrap-only edge case, reasonable default |
| RC-032 | P2 (new, found during this closure pass) | `routes/telegram.py`'s webhook `except` block does `print(f"Webhook error: {e}")` — same redaction-bypass pattern as the already-fixed `paper_trade.py` findings, not previously called out by name | `routes/telegram.py` (webhook handler except block) | OPEN | No | Yes | Same fix pattern as RC-006 (route through the module logger) — small, isolated; recommend as an immediate next commit given the precedent already set |

---

## Technical Debt — Accepted, Bounded (from `TECHNICAL_DEBT_RELEASE_REVIEW.md`)

| ID | Item | Status |
|---|---|---|
| RC-D1 | `_ROUTES_DEBT` (4 entries, shrink-only, CI-enforced) | ACCEPTED DEBT |
| RC-D2 | `_ROUTES_WRITE_DEBT` (1 entry, shrink-only) | ACCEPTED DEBT |
| RC-D3 | `_LIFECYCLE_DEBT` (`NR7_BULL`, dated 2026-07-04) | ACCEPTED DEBT |
| RC-D4 | `_STATUS_DEBT` (research-scope, out of this review) | ACCEPTED DEBT |
| RC-D5 | Provider-hold state process-local (documented tradeoff, kill switch exists) | ACCEPTED DEBT |
| RC-D6 | Conditional `pytest.skip()` calls, all data-availability-gated | ACCEPTED DEBT |
| RC-D7 | `engine/strategy_registry/` fully deleted (better than docs state) | ACCEPTED DEBT (doc wording only) |

**Zero must-resolve technical debt items** — see Phase 3 below for the per-item release/hotfix/
milestone/backlog recommendation.

---

## Summary Counts

- **Fixed this cycle:** 6 (RC-002 through RC-007)
- **Verified safe today, design gap remains:** 1 (RC-001, the mandatory item)
- **Open, release-safe (all explicitly answered "Yes" to "release before fixing"):** 18
- **Accepted debt (bounded, dated, no action required for release):** 14 (7 P2/P3 code findings + 7
  technical-debt inventory items)
- **Blocking this release:** **0**
