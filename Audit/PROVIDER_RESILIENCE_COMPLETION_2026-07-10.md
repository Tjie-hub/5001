# Provider Resilience Enhancement — Completion Report

**Date:** 2026-07-10/11
**Basis:** `Audit/CLAUDE_PROVIDER_RCA_2026-07-10.md` (root cause: shared subscription 5-hour session limits; error classification incomplete; reset info discarded)
**Constraints honored:** no architecture redesign, no SDK/API migration, no Router redesign, no business-logic/strategy/scoring changes, no deployment changes. Backward compatible throughout.

---

## 1. Completed items

| Phase | Deliverable | Status |
|---|---|---|
| 1 | Error classification from **stdout + stderr**, 8+ explicit categories | ✅ |
| 2 | Session-limit detection with reset-time extraction + persistence + `provider_session_limit` events | ✅ |
| 3 | Quota-aware routing: hold until reset, skip retries, automatic resume, coexists with Circuit Breaker | ✅ |
| 4 | Metrics: availability + WHY, next reset, session-limit/skip/fallback counts, circuit state | ✅ |
| 5 | Structured operational logs (`Provider: … | Status: … | Reset: … | Action: …`) | ✅ |
| 6 | Transition-based alerts with dedupe (limit / restored / repeated / all-down) | ✅ |
| 7 | Configurable policies with sensible defaults (7 new `AGENT_FIRM_*` vars) | ✅ |
| 8 | 55 new automated tests, full suite green | ✅ |
| — | Operational documentation updated | ✅ |

## 2. How it works now (behavior delta)

**During the 2026-07-10 incident**, 137 quota rejections surfaced as
`ProviderUnavailable("claude CLI exited 1")` and the Router re-probed the
exhausted provider every 30s circuit cooldown for hours (476 wasted skips,
each real probe burning 2–4s).

**After this change:** the same rejection is classified as
`ProviderSessionLimit` (category `session_limit_exceeded`) with the reset
time parsed from the CLI's own message ("resets 6:20pm (Asia/Jakarta)" →
aware datetime, next-occurrence logic). The Router places the provider on a
**quota hold** until reset + 60s buffer (fallback 15 min when no reset
parseable — e.g. Z.ai's 1308; capped at 6h against mis-parses), spawns **no
CLI process** while held, logs one structured WARNING, persists one
`provider_session_limit` event (with `reset_time`) plus `provider_skipped`
events, sends **one** Telegram alert per reset window, and **resumes
automatically**: first request after the hold expires tries the provider;
first success emits `provider_restored` + alert. The Circuit Breaker is
untouched and operates in parallel. Trading-engine behavior is unchanged —
requests fail over exactly as before, just without the futile re-probes.

Off-switch: `AGENT_FIRM_QUOTA_HOLD=false` restores pre-change routing exactly.

## 3. Files modified

Production code (7):
- `engine/agent_firm/providers/classification.py` — **new**: pure classifier; category taxonomy; `parse_session_reset()` (12h→24h, tz via zoneinfo w/ Asia/Jakarta fallback, next-occurrence rollover); result-JSON unwrapping; exception mapping
- `engine/agent_firm/providers/errors.py` — `category` attr on `ProviderException`; new `ProviderSessionLimit(ProviderQuotaExceeded)` (carries `reset_time`), `ProviderAuthFailed`/`ProviderNetworkFailure`/`ProviderUnexpectedError` (subclass `ProviderUnavailable` → all existing `except` sites keep working)
- `engine/agent_firm/providers/claude.py` — failure path now decodes **both** streams and raises the classified exception (regexes moved to classification.py)
- `engine/agent_firm/providers/zai.py` — 429 + "usage limit reached" (code 1308) → `ProviderSessionLimit` (no reset ⇒ fallback hold); plain 429 unchanged
- `engine/agent_firm/providers/events.py` — 3 new event types (`provider_session_limit`, `provider_skipped`, `provider_restored`); `reset_time` field; persister self-heals a pre-change schema (ALTER on first use — no redeploy/migration step needed)
- `engine/agent_firm/providers/router.py` — quota-hold map + `_hold_until()` policy; skip/resume/restore logic; `provider_status()` snapshot (per-provider available/why/hold-until/circuit); structured logs; failure events now carry `[category]` prefix in reason; all-providers-down alert hook. Same class, same constructor signature, same loop — no architecture change
- `engine/agent_firm/providers/alerts.py` — **new**: transition-based alerts, dedupe registry (once per reset window; restored; repeated-exhaustion escalation at threshold; all-down per min-interval); WARNING log always, Telegram best-effort, never raises
- `engine/agent_firm/providers/metrics.py` — `ProviderStats` gains `available`, `unavailable_reason`, `estimated_next_reset`, `session_limit_events`, `quota_skips`, `fallback_count` (all defaulted → backward compatible)
- `engine/agent_firm/config.py` — 7 new env-driven settings (see §6)
- `data/db.py` — `provider_events.reset_time` column (fresh-create + PRAGMA-guarded ALTER, same pattern as existing migrations)

Docs/config:
- `docs/OPERATIONS.md` — new "Session limits & quota-aware routing" section: behavior, SQL to check availability, 4 operator actions, known limitations
- `.env.example` — the 7 new vars with defaults and comments

## 4. Tests added (55 new; TDD — every one watched fail first)

- `test_classification.py` (**new**, 23): reset parsing (pm/am, no-minutes, 12am/12pm, day rollover, unknown tz fallback, absent), category detection incl. the exact incident shape (stdout msg + empty stderr), JSON-wrapped diagnosis, stderr priority, truncation, signal-kill, exception mapping + backward-compat subclassing
- `test_claude_provider.py` (+4): incident shape → `ProviderSessionLimit` w/ reset; auth classified; empty-output → category `unknown`; stdout excerpt in message
- `test_zai_provider.py` (+2): 1308 → session limit (no reset); plain 429 still rate-limited
- `test_event_persistence.py` (+4): reset_time persisted (UTC string); **self-healing ALTER on old schema**; new event types; db.py migration adds column
- `test_config.py` (+3): defaults + env overrides for all new knobs
- `test_alerts.py` (**new**, 7): once-per-reset-window dedupe, new-window re-alert, restored + counter reset, repeated-exhaustion escalation, all-down dedupe, config kill-switch, notifier-failure never raises
- `test_router.py` (+8): hold set on session limit + skip without calling provider; automatic resume after reset; fallback hold boundary (899s held / 901s retried); max-hold cap; `QUOTA_HOLD=false` restores old behavior; breaker coexistence; `provider_status()` explains why; restored alert

## 5. Test results

- Full suite: **1284 passed, 0 failed** (baseline 1229 + 55 new) in 100s.
- End-to-end smoke (real `ClaudeProvider` subprocess + real Router + real SQLite, fake `claude` binary reproducing the incident output): classify ✅, hold-without-spawn ✅ (marker-file proof), auto-recovery ✅, persistence incl. self-healed column ✅, alerts ✅, structured logs ✅.

## 6. New configuration (all optional, defaults active)

| Var | Default | Meaning |
|---|---|---|
| `AGENT_FIRM_QUOTA_HOLD` | `true` | Enable quota-aware holds (false = pre-change behavior) |
| `AGENT_FIRM_QUOTA_RESET_BUFFER` | `60` | Seconds past advertised reset before retrying |
| `AGENT_FIRM_QUOTA_FALLBACK_HOLD` | `900` | Hold when no reset time parseable |
| `AGENT_FIRM_QUOTA_MAX_HOLD` | `21600` | Hard cap on any hold (mis-parse safety) |
| `AGENT_FIRM_QUOTA_ALERTS` | `true` | Telegram alerts for quota transitions |
| `AGENT_FIRM_ALERT_MIN_INTERVAL` | `1800` | Dedupe window for repeatable alerts |
| `AGENT_FIRM_QUOTA_REPEAT_THRESHOLD` | `3` | Limit hits without recovery → escalation alert |

## 7. Operational improvements

- "exit 1, empty stderr" can no longer happen: the diagnosis is captured, categorized, logged, persisted, and alerted.
- An incident like 2026-07-10 now costs **one** CLI probe per provider per window instead of ~137, and produces ~4 alerts instead of silence.
- `provider_status()` + extended `provider_stats()` answer "is claude available, and if not, why and until when" from code or SQL.
- `Unknown` category is reserved for zero-output failures only — it should now be rare, and its rate is measurable (`[unknown]` prefix in provider_failed reasons).

## 8. Remaining limitations (unchanged from RCA, by design)

- Quota is still **shared** with interactive Claude Code sessions — holds route around exhaustion; they cannot create capacity. Structural fix (metered API key) explicitly out of scope.
- Holds are process-local: an app restart forgets them (cost: one re-probe, then re-held).
- Reset parsing covers the observed "resets H:MM(am|pm) (Zone)" phrasing; anything else degrades gracefully to the fallback hold.
- Z.ai never advertises a reset timestamp → always fallback hold (15 min default vs its 5h window; the repeat-escalation alert surfaces chronic cases).
- Alert dedupe state is in-memory (restart may re-send one alert per active condition).

## 9. Deployment status

**No deployment performed** (constraint). Changes are on the working tree
(`ops/hardening-2026-07-10` branch, uncommitted); the running gunicorn
(user-unit `idx-walkforward.service`) still executes the old code. The DB
schema needs no manual step — the writer self-heals and `init_db()` also
adds the column on next start. Activation = commit + restart, at the
operator's discretion.
