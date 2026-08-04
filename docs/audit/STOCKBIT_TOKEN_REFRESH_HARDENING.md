# Stockbit Token Refresh — Reliability Hardening

**Generated:** 2026-07-28 06:20 WIB · **Scope:** authentication reliability only —
`auto_token.py`, `stockbit_fetcher.py::ensure_valid_token()`, and their tests. No changes to
`stockbit_flow` schema, historical data, certification artifacts, ingestion architecture, or the
research pipeline. · **Branch:** `ops/hardening-2026-07-10`

---

## 1. Root Cause Analysis

The complete authentication lifecycle, traced end to end:

| Stage | Where | Behavior |
|---|---|---|
| Token creation | `auto_token.py::auto_refresh()` (Playwright session replay) / `credential_login()` (headless login form) | Both capture a JWT via `_capture_from_page()`'s network-request interceptor |
| Storage | `.stockbit_token` (mode 600, gitignored) | Before this fix: `TOKEN_FILE.write_text(token)` / raw `open(...,"w")` — a single, non-atomic write |
| Expiry calculation | `jwt_expiry()` / `_jwt_iat()` (`auto_token.py:76-95`) | Decodes the JWT payload's `exp`/`iat` claims (Unix timestamps), compares against `time.time()` |
| Refresh scheduling | `deploy/crontab`: `40 8 * * 1-5 ... auto_token.py` | Once daily, 08:40 WIB, pre-market |
| Refresh trigger | `should_skip_refresh()` (`auto_token.py:98-110`, pre-fix) | `if remaining > 6: skip` — **the precise defect, see §1a** |
| Retry logic | None, pre-fix | `auto_refresh()` and `credential_login()` were each tried exactly once |
| Failure handling (proactive refresh) | `main()`, pre-fix | Preserved an old-but-still-valid token, alerted via Telegram, `sys.exit(1)` on total failure — this part was already sound |
| Failure handling (**consumers** — the actual bug) | `stockbit_fetcher.py::ensure_valid_token()` (`:194-201`, pre-fix) | **`if manual_token: ... return None` on an invalid manual token — no fallback attempted at all.** See §1b |

### 1a. Defect 1 — `should_skip_refresh()`'s threshold ignored the downstream deadline

```python
# auto_token.py, pre-fix (auto_token.py:98-110 before this change)
def should_skip_refresh():
    ...
    remaining = jwt_expiry(token)
    if remaining > 6:
        if verify_token(token):
            log(f"Token still fresh ({remaining:.1f}h remaining), skipping refresh")
            return True
    return False
```

`main()` calls this before doing anything else; if it returns `True`, the entire refresh is
skipped for the day. The `6` was never derived from anything — it doesn't correspond to the token
TTL (24h), the refresh cadence (daily, 08:40), or the latest same-day consumer (20:15,
`scheduler/jobs.py::run_broker_flow_fetch`, an 11h35m gap from 08:40).

**Timeline of the actual incident** (all times WIB, from `logs/auto_token.log` /
`logs/cron_auto_token.log`, reproduced verbatim):

```
[2026-07-26 17:31:51] Auto refresh started (headless)          <- off-schedule (Sunday evening)
                                                                     issues a token expiring 2026-07-27 17:31
[2026-07-27 08:40:01] Token still fresh (8.9h remaining), skipping refresh
                                                                     <- remaining=8.9h > old threshold(6h) => SKIPPED
[2026-07-27 17:31:xx] token expires (no proactive check between 12:00 and 18:30)
[2026-07-27 18:30:02] Using manual token
[2026-07-27 18:30:02] ERROR: Manual token invalid
[2026-07-27 18:30:02] ERROR: Could not obtain a valid token
[2026-07-27 18:30:03] EXIT stockbit_flow rc=1
```

8.9h remaining at 08:40 meant the token would expire at 17:31 — one hour *before* the 18:30
`stockbit_flow` cron and three hours before the 20:15 broker-flow job. The threshold cleared a
token that could not survive the day. This is not merely an edge case triggered by the off-schedule
Sunday refresh — **the old threshold (6h) was unsafe even in the normal case**: at the 08:40 check,
surviving to the 20:15 consumer requires ≥11h35m remaining, and to the 18:30 consumer requires
≥9h50m — both exceed 6h. The normal daily cadence happened to mask this (a token refreshed every
day at 08:40 is ~24h old, i.e. ~0h remaining, at the next day's check, so it always re-refreshed
regardless of the threshold) — the off-schedule refresh is what exposed the latent defect.

**Independent corroboration that 6h was an unexamined convention, not a reasoned value**: the exact
same `warn_hours: float = 6.0` default appears in `engine/pipeline_health.py::token_status()`
(a *different*, alert-only health-check module — see §1c), suggesting "6 hours" was copied as a
plausible-sounding round number rather than derived from the schedule it needed to protect.

### 1b. Defect 2 — the actual failure mode: `ensure_valid_token()`'s manual-token dead end

Defect 1 explains *why the token was allowed to expire*. This defect explains *why an expired token
was actually used to attempt a fetch* — the more direct answer to "identify the precise failure
mode that allowed an expired token to be used":

```python
# stockbit_fetcher.py, pre-fix (:194-201 before this change)
def ensure_valid_token(manual_token=None):
    if manual_token:
        log("Using manual token")
        if verify_token(manual_token):
            return manual_token
        log("ERROR: Manual token invalid")
        return None                      # <-- dead end, no fallback attempted

    token = extract_token_from_chrome()  # <-- fallback machinery below is
    ...                                  #     UNREACHABLE from the branch above
    log("Token invalid/missing — running auto_token refresh...")
    new_token = at.auto_refresh()
    ...
    new_token = at.credential_login()
    ...
```

Every production cron that consumes this token passes it explicitly:

```
# deploy/crontab
50 8 * * 1-5  ... stockbit_fetcher.py --token "$(cat .stockbit_token)"
30 18 * * 1-5 ... stockbit_fetcher.py flow --token "$(cat .stockbit_token)"
```

Because `--token` is always supplied, `ensure_valid_token()` **always** takes the `if manual_token:`
branch. When that token is invalid, the function returns `None` immediately — the `auto_refresh()` /
`credential_login()` fallback that exists nine lines below, and that demonstrably works (it is what
a manual `python3 auto_token.py` run used to recover last night, and what `auto_token.py`'s own
cron already relies on), was **structurally unreachable from the code path every production
consumer actually uses.**

This also explains a second, smaller bug: the Telegram alert this branch sends —
`"❌ Flow Fetch GAGAL\nToken tidak ditemukan/expired. Auto-login juga gagal."` ("auto-login *also*
failed") — was **false**. Auto-login was never attempted on this path; the message text was
evidently written for the other (unreachable, in practice) branch and never updated. Fixed as a
side effect of closing the dead end (the message is now only ever sent after auto-refresh and
credential-login have both genuinely been tried).

### 1c. The monitoring layer worked; nothing automatic followed from it

For completeness — this is not a defect, but a materially relevant fact for judging severity: an
existing, separate job (`scheduler/jobs.py::run_token_health_check`, added for the 2026-07-04
incident) runs at 08:20 and 12:00 WIB and **did** correctly detect the problem in advance:

```
logs/app.log:9871  [12:00] Token health ALERT: expiring (5.5h left)
```

A Telegram warning was sent 5.5 hours before expiry. It required a human to see it and run
`python3 auto_token.py` manually; nobody did before 17:31. This is why the fix in this document is
a **code-level, automatic** fallback (§3) rather than a better alert — an alert that depends on a
human noticing it within a several-hour window is not a fix for a scheduled, unattended cron.

---

## 2. Timing Audit

| Question | Finding |
|---|---|
| How is expiry determined? | `exp` claim in the JWT payload (Unix timestamp), decoded by `jwt_expiry()`/`_jwt_iat()`. Sourced from Stockbit's own token, not computed locally — correct, no drift risk from this project's side. |
| Timezone handling | All *comparisons* (`jwt_expiry`, `_jwt_iat`, `should_skip_refresh`, the new margin logic) use `time.time()` (Unix epoch) — timezone-agnostic and correct. Only `log()`'s timestamps and the crontab's schedule are WIB-local (naive `datetime.now()`), which is fine for a single-host deployment (`gunicorn.conf.py` workers=1; the cron alert itself names one host, `tjiesar-XPS-13-9343`) but is an implicit assumption worth stating rather than silently relying on. |
| Clock skew assumptions | None existed pre-fix — a token claiming an implausible remaining time (e.g. from a host clock jump) would have been trusted blindly. **Added**: `should_skip_refresh()` now treats `remaining > 48h` (impossible for a 24h-TTL token) as a skew/corruption signal and forces a real check instead of skipping (test: `test_does_not_skip_on_implausible_remaining_clock_skew`). |
| Scheduler frequency | `auto_token` cron: once/day (08:40). `stockbit_ohlcv`: once/day (08:50). `stockbit_flow`: once/day (18:30). APScheduler `run_broker_flow_fetch`: once/day (20:15). Single daily refresh cadence against a 24h TTL leaves little slack — this is *why* the margin must be generous (§3), not a reason to add more refresh crons (out of scope: scheduling cadence is ingestion architecture). |
| Race conditions | Pre-fix: **none guarded against.** A manual `auto_token.py` run (as performed during the 2026-07-27 incident response) racing the 08:40 cron would launch two Playwright instances against the same `.playwright_state` persistent-context directory concurrently — unsafe for Chromium's profile locks — and could interleave two token-file writes. **Fixed**: `_refresh_lock()` (§3), non-blocking `flock`. |

---

## 3. Hardened Refresh Logic — What Changed

All changes are in `auto_token.py` and `stockbit_fetcher.py::ensure_valid_token()`. No other files
were modified (see the git diff, deliverable 5).

| Requirement | Implementation |
|---|---|
| Refresh well before expiry, never wait until the last minute | `should_skip_refresh(margin_hours=REFRESH_MARGIN_HOURS)`, default **14h** (comfortably exceeds the measured 11h35m worst-case gap to the 20:15 consumer). Replaces the unexamined flat `6h`. |
| Configurable refresh margin | `STOCKBIT_TOKEN_REFRESH_MARGIN_HOURS` env var (default 14.0); also `STOCKBIT_TOKEN_REFRESH_MAX_RETRIES` (default 2) and `STOCKBIT_TOKEN_REFRESH_BACKOFF_BASE_S` (default 5). |
| Retry on transient failures + exponential backoff | `_retry_with_backoff()`, applied to `auto_refresh()` (the session-replay path, safe to retry). `credential_login()` is deliberately **not** auto-retried — a failure there is more likely a hard failure (bad password, CAPTCHA) where blind retries risk tripping additional bot-detection/lockout; this matches the existing code's own stated caution about avoiding suspicious request patterns. |
| Preserve existing token if refresh fails | `_old_token_still_safe()` (extracted from previously-inline logic, now independently tested) — keeps the current token if it's still valid and under 20h old, rather than treating a failed refresh as a hard failure. |
| Atomic token replacement | `_write_token_atomic()` — temp file (`mkstemp` in the same directory) + `os.chmod(0o600)` + `os.replace()`. A crash mid-write can never leave a truncated token on disk; readers always see a complete old or complete new token. Used by every write site in both files. |
| Prevent concurrent refreshes | `_refresh_lock()` — non-blocking `fcntl.flock` on `.stockbit_token.lock`. A second concurrent invocation observes the lock held, logs, and returns cleanly (exit 0 — not treated as a failure, since "someone else is already refreshing" is a normal, idempotent outcome). |
| Idempotent behavior | Two back-to-back `main()` calls: the first refreshes and writes; the second sees a fresh token via `should_skip_refresh()` and no-ops. Verified by `test_idempotent_repeated_execution_does_not_double_refresh`. |

---

## 4. Fail-Safe Behavior

Unchanged in spirit, hardened in mechanism:

- Total refresh failure (`auto_refresh()` exhausted its retries **and** `credential_login()` also
  failed, **and** the old token is no longer safe) → structured log line
  (`REFRESH_FAILED old_token_still_safe=False action=manual_intervention_required`, grep-able),
  the existing human-readable Telegram alert with manual-recovery instructions, and `sys.exit(1)` —
  unchanged, still fails loudly rather than continuing silently.
- If the old token *is* still valid, it is kept and used — never silently replaced with nothing,
  never corrupted (`_write_token_atomic` guarantees this even under a crash).
- `ensure_valid_token()` (the consumer-side fix): an invalid manual token now falls through to the
  same two-stage fallback instead of returning `None` outright — but if *both* stages genuinely
  fail, it still returns `None` (never fabricates a token, never retries forever) and the caller's
  existing `sys.exit(1)` + Telegram-alert behavior in `_run_flow_cmd()`/`main()` is preserved
  unchanged.

---

## 5. Scheduler Validation — Every Auth-Dependent Scheduled Task

| Task | Schedule | Token path | Validates before use? | Auto-refreshes on failure? | Status |
|---|---|---|---|---|---|
| `auto_token` (cron) | 08:40 daily | is the refresh itself | n/a | n/a | **Hardened this task** (§3) |
| `stockbit_ohlcv` (cron) | 08:50 daily | `stockbit_fetcher.py main()` → `ensure_valid_token(manual_token)` | Yes | **Yes, now** (was: no) | **Fixed** |
| `stockbit_flow` (cron) | 18:30 daily | `_run_flow_cmd()` → `ensure_valid_token(manual_token)` | Yes | **Yes, now** (was: no) | **Fixed — this is the cron that failed in the incident** |
| `run_token_health_check` (APScheduler) | 08:20, 12:00 | reads file directly, classifies via `token_status()` | Yes (observability only) | No — alert-only by design | Working as designed (§1c); confirmed it fired correctly during the incident |
| `run_broker_flow_fetch` (APScheduler) | 20:15 | `extract_token_from_chrome()` + `verify_token()` | Yes | **No** — alerts and returns on failure, no fallback attempted | **Not fixed — out of scope.** Same class of gap as the fixed bug, but this is a scheduler-orchestration entry point (`scheduler/jobs.py`), and `broker_flow` has been separately non-functional since 2026-07-22 for unrelated reasons (see prior session). Flagged as a residual risk (§6), not silently patched. |
| `run_flow_fetch` (APScheduler, 9×/day 09:30–16:05) | via `flow_filter.main()` → `_load_token()` | **No verification at all** — reads the file and uses it blindly; a bad fetch just returns empty results per ticker, not a hard error | No | **Not fixed — out of scope** (`flow_filter.py`, `scheduler/jobs.py` = ingestion architecture). Residual risk (§6). |
| `check_keystats_freshness` (`scheduler/scanner.py::_load_stockbit_token`) | called from scan jobs | Reads file, checks 3-segment JWT *shape* only — not expiry, not a live verify | No | No | **Not fixed — out of scope**, lower-impact (keystats freshness heuristic, not the core flow pipeline). Residual risk (§6). |

**Confirms/refutes "no task begins with an expired token"**: for the two crons directly implicated
in the incident (`stockbit_ohlcv`, `stockbit_flow`) — **now confirmed true**, they self-heal via
the fixed `ensure_valid_token()`. For the three APScheduler-registered jobs above — **not yet
true**; each can still begin with (or silently limp along on) an expired/invalid token. This is
disclosed, not glossed over.

---

## 6. Residual Risks (not eliminated by this task, by explicit scope decision)

1. **`run_broker_flow_fetch`, `run_flow_fetch`, and `scanner._load_stockbit_token`** do not route
   through the now-hardened `ensure_valid_token()`. They would need to be changed to close this
   gap, and doing so touches `scheduler/jobs.py` / `scheduler/scanner.py` / `flow_filter.py` —
   explicitly out of scope per this task's constraints (ingestion architecture). Recommended
   follow-up, not performed here.
2. **`credential_login()` has no retry** (deliberately, §3) — a transient failure there (rather than
   a hard failure like a bad password or CAPTCHA) would not self-heal within the same run. The next
   day's 08:40 cron would retry it fresh, so recovery is bounded to at most ~24h, backstopped by the
   unchanged Telegram alert.
3. **Single-host assumption.** Locking (`_refresh_lock`) and atomic writes protect against
   concurrent *processes on the same host*; they do not protect against two different hosts sharing
   the same `.stockbit_token` file (e.g. over a network mount) — not a configuration this deployment
   uses (`gunicorn.conf.py` already assumes single-host, single-worker), so not hardened against.
4. **Browser-state growth.** `check_state_size()`'s `⚠ Browser state is NNNMB (limit=500MB)` warning
   has been firing on every run for over a week (608MB → 643MB, `logs/cron_auto_token.log`),
   unrelated to this incident but a plausible contributor to *future* headless-Playwright
   flakiness. Not addressed here (would mean recreating the persistent browser profile — an
   operational action, not a code hardening, and risks invalidating the current session).
5. **6h→14h margin is a considered default, not a proof.** It is derived from the *currently
   documented* schedule (08:40 check, 20:15 last consumer). If either schedule changes materially
   in `deploy/crontab`/`scheduler/__init__.py` without updating `STOCKBIT_TOKEN_REFRESH_MARGIN_HOURS`,
   the same class of bug could reopen with a different margin. This coupling is inherent to keeping
   auth logic decoupled from scheduler internals (a deliberate scope boundary, not an oversight) —
   documented here so a future schedule change is a known trigger to re-check this value.

---

## 7. Test Results

```
$ venv/bin/python3 -m pytest tests/test_auto_token.py tests/test_stockbit_fetcher_ensure_valid_token.py -q
30 passed in 0.83s

$ venv/bin/python3 -m pytest -q     # full suite
<see deliverable 3 / final summary for the exact count>
```

30 new tests across the two scenarios below (mapped to the 9 requested scenarios):

| Requested scenario | Test(s) |
|---|---|
| Normal refresh | `test_normal_refresh_writes_fresh_token` |
| Refresh near expiry | `test_skips_when_remaining_exceeds_margin`, `test_does_not_skip_within_margin_the_2026_07_27_regression` |
| Expired token | `test_does_not_skip_when_already_expired`, `test_expired_token_triggers_refresh` |
| Refresh failure | `test_total_refresh_failure_preserves_old_token_and_alerts`, `test_total_refresh_failure_with_no_safe_fallback_exits_nonzero_and_alerts` |
| Temporary network failure | `test_retry_with_backoff_succeeds_after_transient_failures`, `test_transient_auto_refresh_failure_recovers_via_retry` |
| Scheduler restart | `test_idempotent_repeated_execution_does_not_double_refresh` |
| Multiple concurrent refresh attempts | `test_refresh_lock_blocks_a_second_concurrent_acquire`, `test_concurrent_invocation_finds_lock_held_and_exits_cleanly` |
| Clock skew | `test_does_not_skip_on_implausible_remaining_clock_skew` |
| Idempotent repeated execution | `test_idempotent_repeated_execution_does_not_double_refresh`, `test_refresh_lock_is_released_after_context_exits` |

Plus atomic-write safety (`test_write_token_atomic_*`, 3 tests), the manual-token fallback fix
(`tests/test_stockbit_fetcher_ensure_valid_token.py`, 5 tests), and supporting unit coverage for
`_retry_with_backoff` / `_old_token_still_safe` (9 tests).

---

## Summary

**Root cause (both parts required for the 2026-07-27 outage):**
1. `should_skip_refresh()`'s flat 6h threshold didn't account for the gap to the day's last token
   consumer, so an off-schedule token issuance was wrongly treated as "fresh enough."
2. `ensure_valid_token()` discarded all fallback/self-healing logic whenever a manual `--token` was
   supplied and invalid — which is unconditionally true for every production cron.

Both are fixed at the code level, with tests pinning the exact regression. The token-expiration
failure mode that caused the 2026-07-27 outage is eliminated for the two crons that were actually
implicated (`stockbit_ohlcv`, `stockbit_flow`). It is **not** eliminated for three other,
lower-traffic, out-of-scope auth call sites (§5, §6) — those remain a documented residual risk by
deliberate scope decision, not an oversight.
