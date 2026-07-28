# RC1 Certification Report

**Date:** 2026-07-28
**Role:** Independent Release Certification Board review of `Audit/RC1_FIX_REPORT_2026-07-28.md`
(R-1–R-4). Adversarial mandate: attempt to prove RC1 is NOT ready, not to confirm it is.
**Method:** Three independent re-derivation passes against raw evidence (current file contents,
live test runs, package source, `git diff`) — none trusted the prior Fix Report's claims at face
value. Generated, point-in-time record.

---

## Executive Summary

**Overall verdict: NOT unconditionally certified.** Two of the four RC1 fixes (R-1, R-4) are
**incompletely closed** — both in ways verified by direct evidence, not inference. Neither
represents an active production defect today, and both have small, mechanical, already-proven
fixes (the same pattern already applied elsewhere in the same fix). R-2 (rate limiting) and R-3
(documentation) were independently re-verified and hold up under adversarial review, including a
concurrency analysis R-2's own Fix Report did not perform.

**Decision: CERTIFIED WITH CONDITIONS.**

---

## Findings

### Medium — R-1 closure claim is incomplete: a fourth file has the identical bug, currently failing

**Evidence:** `tests/test_config_hygiene.py:49` (`test_dotenv_loaded_only_in_config`) computes
`rel = str(p.relative_to(ROOT))` and compares it against `DOTENV_ALLOWED = {"config.py",
"engine/agent_firm/config.py"}` — the exact same forward-slash-vs-native-separator bug R-1 fixed in
three other files. Re-run live: `pytest tests/test_config_hygiene.py -v` →
`test_dotenv_loaded_only_in_config FAILED`, reporting `['engine\\agent_firm\\config.py']` as an
offender because it never matches the forward-slash allowlist entry on Windows.

**Why it matters:** The RC1 Fix Report states "R-1 — Architecture Boundary: conclusion... Fixed" and
lists three files. This is not the full set — the sweep that found the bug class didn't grep for
every other source-scan test using the same `str(Path.relative_to(...))` allowlist-comparison
pattern. The underlying risk is the same as the original R-1 finding (benign, Windows-only,
non-security) — but the *claim* that R-1 is closed is not accurate as written, and this specific
test is currently red on this branch.

**Required action:** Apply the identical `.as_posix()` fix to `tests/test_config_hygiene.py`'s
`rel` computation. Mechanical, same pattern as the three already-fixed files, low risk.

### Medium — R-4 completeness claim is incomplete: two Telegram senders bypass redaction entirely

**Evidence:** `auto_token.py:74` and `stockbit_fetcher.py:96` each define their own standalone
`send_telegram(msg)` function that builds and posts the Telegram HTTP request directly — neither
imports nor calls `utils.logging_config.redact_secrets` or `utils.telegram.send_telegram`. Verified
by reading every call site in both files (7 total): none currently embeds `str(e)` or other
dynamic/secret-shaped content, so there is no active leak today.

**Why it matters:** R-4's stated objective was "Ensure all **outbound operational alerts** pass
through the existing secret-redaction mechanism." This is verifiably not the case — two alerting
paths exist entirely outside the redaction net. The gap is latent, not active, but it is exactly
the kind of gap this certification's operational-correctness check #3 ("secrets cannot bypass
redaction") is designed to catch, and it did.

**Required action:** Route `auto_token.py::send_telegram` and `stockbit_fetcher.py::send_telegram`
through `redact_secrets()` before posting (or, if consolidating them onto `utils.telegram.send_telegram`
is preferred, that's a slightly larger change — the minimal fix is calling the existing
`redact_secrets()` function, matching the pattern already used in the two files R-4 did fix).

### Low — cosmetic / non-blocking

- `scheduler/__init__.py`'s `JobErrorRateLimiter.should_alert()` returns a hardcoded `0` (not the
  live suppressed count) on its `False` branch. Harmless — the only caller (`_on_job_error`) ignores
  the second value whenever the first is `False` — but is a latent surprise for any future direct
  consumer of the class. No behavior change needed for RC1; worth a one-line comment if touched again.
- No test exercises `JobErrorRateLimiter(cooldown_s=0)` or a negative cooldown. The behavior is
  correct by inspection (rate limiting cleanly disables at 0; verified independently by two of the
  three review passes) — a coverage gap, not a functional bug.
- `docs/OPERATIONS.md`'s opening line still reads "Post-hardening (2026-07-10 ...)" with no updated
  pointer to the 2026-07-28 additions documented later in the same file. Not factually wrong,
  slightly stale as a "last updated" signal. Cosmetic.

### Clean — verified, not just asserted

- **R-1's three named files**: fresh re-run, `tests/test_architecture_boundary.py`,
  `test_db_centralization.py`, `test_research_data_fence.py` → 10/10 passed.
- **R-2 concurrency**: independently analyzed (the Fix Report did not address this). Confirmed
  `gunicorn.conf.py` workers=1/threads=8 (gthread), confirmed APScheduler's `max_instances` defaults
  to 1 in the installed package source, and confirmed no `add_job()` call in `scheduler/__init__.py`
  overrides it. This means the same `job_id` cannot fire `EVENT_JOB_ERROR` concurrently with itself,
  so `JobErrorRateLimiter`'s non-atomic check-then-write can only interleave across *different*
  job_id dict keys, which don't conflict. No exploitable race given this app's actual concurrency
  configuration — a real finding, not a hand-wave, since it depends on a specific, verified
  configuration invariant (`workers=1`, default `max_instances`) rather than assumption.
- **R-3 documentation accuracy**: every checked claim (function/class names, `watchlist_snapshot`
  schema, cron times, `_job_sentinel` schema, env var defaults, version/amendment metadata, cited
  file paths) is an exact match against current code — zero mismatches found.
- **No duplicate implementations, no dead code, no TODOs, no hardcoded secrets** across all 14
  RC1-touched files (production + test). `tests/security/test_secret_hygiene.py` actively scans all
  four production files touched and passes (5/5).
- **Test-diff reproduction**: the RC1-relevant 7-file test set reproduces exactly as claimed (59
  passed / 2 failed, both the pre-existing Windows tempdir-lock issue, unrelated to these changes).

---

## Deferred Work (intentionally outside RC1 scope)

- Operations Dashboard / Job History — the explicitly excluded next phase.
- R-6 (near-duplicate diff-rendering code, EOD vs. Premarket) and R-7 (dedup-guard try/except
  placement asymmetry) from the Release Readiness Audit — style-only, not requested for this pass.
- Environment-only pre-existing failures (missing `langgraph`/`yaml`, Windows-subprocess `.sh`
  incompatibility) — not release-blocking, not in scope.
- The full 1438/56/6 repo-wide baseline was not re-executed end-to-end by this certification pass
  (would require the ~8-minute full run); the RC1-relevant subset was independently reproduced
  instead and matched exactly.

---

## Certification Decision

**2. CERTIFIED WITH CONDITIONS**

Conditions (both small, mechanical, already-proven-pattern fixes — not architectural, not
speculative):

1. Apply the `.as_posix()` fix to `tests/test_config_hygiene.py` (same pattern as R-1's three
   files).
2. Route `auto_token.py::send_telegram` and `stockbit_fetcher.py::send_telegram` through
   `redact_secrets()` (same pattern already used in `utils/telegram.py`/`routes/telegram.py`).

Neither condition reflects an active production defect, a security incident, or an architectural
problem — both are narrow, verified completeness gaps in claims made about R-1 and R-4. R-2 and R-3
are certified without qualification.
