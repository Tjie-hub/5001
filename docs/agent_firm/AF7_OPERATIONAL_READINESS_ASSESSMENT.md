# AF-7 — Operational Readiness Assessment

**Date:** 2026-07-29 · **Status:** Assessment only — no code changed, no files modified (one
pre-existing, already-uncommitted defect is *reported*, not fixed, per this task's own rule).
**Scope:** the operational checklist required before declaring the Production Engine (as certified
in AF-6: Decision Flow, Ranking Engine, Watchlist Generator, Telegram Publisher) fully operational —
not code correctness (already assessed in AF-3 through AF-6) but deployment/monitoring/runbook state.

**Headline finding, verified directly from the release tooling's own test suite, not inferred:**
**none of the work certified in AF-3 through AF-6 is committed, and this repository's own release
script already refuses to deploy it as a result.**

```
git status --porcelain | wc -l        → 179 uncommitted paths (code + docs + scratch)
git diff --stat -- engine/agent_firm/firm.py engine/agent_firm/guardrails.py \
                    engine/agent_firm_context.py scheduler/jobs.py scheduler/scanner.py \
                    engine/position_sizing.py engine/agent_firm/providers/governor.py
→ all modified/untracked — none committed
git log -1 --format="%H %ci"          → 197da2c, 2026-07-28 16:39:23 (a docs-only commit)
tests/security/test_release_scripts.py::test_release_refuses_uncommitted_tracked_changes
→ confirms scripts/release.sh exits non-zero and refuses to build a release
   when tracked files are dirty, unless ALLOW_DIRTY_RELEASE=1 is explicitly set
```

Everything AF-3 (WP1-4, K1/K2), AF-4 (Ranking Engine wiring in `scheduler/jobs.py`/`scanner.py`),
and AF-5/AF-6 examined and found "complete and tested" is true **of the local working tree**, not of
the deployed system. The live host — whatever last ran `scripts/release.sh` — is running the commit
at `197da2c` (2026-07-28), which predates ADR-AF-002/003/004's implementation, the Provider Governor,
and this session's own K1/K2 guardrails. `engine/trade_plan.py` (the Ranking/Watchlist Generator core)
*is* already committed and clean — so the EOD/Premarket ranking-and-Telegram pipeline itself has very
likely already been live since the 2026-07-28 RC1 release — but the Tier-1-context wiring that feeds
it (`scheduler/jobs.py`/`scanner.py`, both modified/uncommitted) and everything downstream of it
(K1/K2, the Provider Governor) has not.

This does not contradict AF-6's "GO WITH CONDITIONS" — that assessment was scoped to code readiness,
correctly. It does mean **"operationally ready" and "deployed" are not the same claim**, and this
audit's job is specifically the latter.

---

## 1. Operational Readiness Score

**Weighted assessment across 24 checked items: 9 Complete, 12 Partial, 3 Not Started.**

Score is deliberately **not** expressed as a clean percentage, because one item (deployment itself)
gates most of the others — a numeric average would understate how load-bearing that single item is.
**Effective readiness: code/infrastructure is ~85-90% ready; live-operational readiness is ~35-40%**,
almost entirely because nothing new has been deployed or exercised against the real host yet.

---

## 2. Checklist — Complete / Partial / Missing

### Operational Monitoring

| Item | Status | Evidence |
|---|---|---|
| Decision distribution monitoring | **Partial** | Ready-to-run SQL fully specified, zero new instrumentation needed (`Audit/AF2_POST_DEPLOYMENT_MONITORING_PLAN.md` §3). Not automated/scheduled; never run against live data. |
| K1/K2 veto-rate monitoring | **Partial** | Data is queryable today — `apply_guardrails()`'s override reason embeds `"(K1, threshold 3)"` / `"(K2)"` literally into `agent_decisions.rationale` (`engine/agent_firm/guardrails.py`, this session's WP4). No query for it is written into the monitoring plan yet (plan predates WP4); trivial one-section addition, not a code change. |
| Provider health monitoring | **Complete** | `providers/metrics.py::provider_stats()`, `providers/alerts.py` (session-limit/restored/all-unavailable Telegram alerts), `/api/agent/status` (`routes/backtest.py`), documented query in `docs/OPERATIONS.md` §"Provider failover" |
| Runtime metrics | **Partial** | `duration_s`/`cost_usd`/token counts persisted per decision, zero-new-instrumentation query specified (§6 of the monitoring plan); no unified dashboard; no Prometheus/StatsD (documented, deliberate — CLAUDE.md "Unknown" section) |
| Resource monitoring | **Not Started** | Ubuntu CPU/RSS/disk/DB-growth measurements — repeatedly flagged not collected across every prior operational-validation phase; SSH access previously declined |
| Error reporting | **Complete** | `EVENT_JOB_ERROR` listener + `JobErrorRateLimiter` (scheduler crash alerts), `fail_open_alarm()`, `cron_wrap.sh`'s per-job Telegram alert on nonzero exit — all documented in CLAUDE.md, already committed (this item is not part of the uncommitted set) |

### Deployment Validation

| Item | Status | Evidence |
|---|---|---|
| Ubuntu deployment verification | **Not Started** | No live-host exercise this session-chain; compounded by the headline finding — there is currently nothing new to verify a deployment of, since `scripts/release.sh` would refuse it |
| Production configuration (.env) | **Partial** | `config.validate_config()` fails closed on missing mandatory config (code-level, tested); two specific live values (`EDGE_SCORE_MODE`, `TELEGRAM_WEBHOOK_SECRET`) unconfirmed against the actual host |
| Secrets verification | **Partial** | `tests/security/test_secret_hygiene.py` (source-level scan, passing) + startup mode-600 enforcement (code-level); live file-permission/value verification not exercised this session |
| Scheduler validation | **Complete (code-level)** | `tests/test_cron_contract.py` — every cron entry wrapped, dead jobs removed, referenced scripts exist, all passing. Live "did it actually fire on schedule" is a post-deploy check, not a code gap |
| Service health | **Partial** | `/health` (`app.py:79`) exists, checks DB connectivity + `last_scan` freshness + event-guard/macro-panic state; used by `scripts/wait_for_health.sh` as deploy gate. Does **not** directly assert APScheduler job-store liveness — the specific, previously-named RC1 follow-up ("/health scheduler-liveness check") remains open |
| Recovery procedures | **Complete (documented + replay-validated)** | Restart-safety, graceful shutdown, reboot recovery all documented with named mechanisms (`Audit/PRODUCTION_OPERATIONAL_VALIDATION_PHASE2.md` §7); validated via historical replay (`tests/test_historical_replay_operational.py`), not a live restart |

### Production Validation

| Item | Status | Evidence |
|---|---|---|
| End-to-end production run | **Not Started (live)** | Never exercised against the real host or real live market data, this entire certification sequence |
| Daily scheduler execution | **Not Started (live)** | Same — code/replay-validated only |
| Telegram delivery | **Complete for already-committed features; untested for WP4** | EOD/Premarket message builders confirmed at live call sites (`scheduler/jobs.py:946`, `:1111`) and — per `engine/trade_plan.py` being clean/committed — very likely already live since the 2026-07-28 release. K1/K2's effect on those messages has never been exercised live, since it isn't deployed |
| Snapshot persistence | **Complete, already deployed** | `engine/trade_plan.py` is committed and clean (confirmed via `git diff --stat`) — this specific mechanism predates and is unaffected by the current uncommitted batch |
| Diff generation | **Complete, already deployed** | Same file, same status |
| Failure recovery | **Complete (documented + replay-tested)** | Same as Recovery procedures above |

### Testing

| Item | Status | Evidence |
|---|---|---|
| Operational smoke tests | **Partial** | `engine/agent_firm/smoke.py` exists — manual, real-provider probe with a `_MAX_DURATION_S` budget — but is manual-only, not scheduled, and has not been run against this session's K1/K2 changes |
| Deployment verification | **Partial** | `scripts/wait_for_health.sh` + `scripts/release.sh` + `scripts/rollback.sh` all exist, documented, and code-tested (`tests/security/test_release_scripts.py` — itself currently modified/uncommitted, see §9); never run end-to-end against the live host this session-chain |
| Production checklist | **Complete (as a document)** | `docs/OPERATIONS.md` §"Operational checklist" — daily/weekly/post-deploy checklist, thorough. Whether it has been executed live is unverified from this vantage point |
| Runbook completeness | **Complete** | `docs/OPERATIONS.md` covers runtime architecture, release procedure, service management, startup validation, auth/audit trail, backup/restore, provider failover, cron, Telegram reporting, logging, operational checklist — no missing section found |

---

## 3. Remaining Operational Tasks (minimal work to close each item)

**#1, blocks nearly everything else — not a code change, a deployment action:**
Commit the certified, tested working-tree changes (WP1-4 Decision Flow, K1/K2 guardrails, Ranking
Engine's Tier-1-context wiring, Provider Governor, position sizing) and run `scripts/release.sh`.
Nothing else in "Deployment Validation" or "Production Validation" can move past Partial/Not-Started
until this happens — the release script itself enforces this by refusing a dirty tree. **This is
flagged as the required next action, not performed by this assessment** (a multi-file commit +
deploy is a consequential, visible action outside this task's "assessment only" mandate).

**Everything else, in the order they become checkable:**

| Task | Type | Effort |
|---|---|---|
| Commit + deploy (see above) | Deployment | — (operator action) |
| Run `scripts/wait_for_health.sh` + `docs/OPERATIONS.md`'s "After any deploy" checklist | Deployment validation | Minutes, already scripted |
| Confirm live `.env`'s `EDGE_SCORE_MODE`/`TELEGRAM_WEBHOOK_SECRET` | Configuration | Minutes, read-only check |
| Add a K1/K2 section to `AF2_POST_DEPLOYMENT_MONITORING_PLAN.md` §7, mirroring §3's existing SQL pattern (`rationale LIKE '%K1%'` / `'%K2%'` over `agent_decisions`) | Documentation | Small, no code |
| Run `engine/agent_firm/smoke.py` post-deploy to confirm K1/K2 behave against real providers | Testing | Minutes, existing tool |
| Execute the daily/weekly operational checklist for at least one full cycle (08:35 premarket → 16:40 EOD → 18:30 forward-test) | Production validation | 1 day, no new tooling |
| Run the decision-distribution and (extended) veto-rate queries after 24-48h of live traffic | Monitoring | Minutes, existing SQL |
| Capture Ubuntu CPU/RSS/disk/DB-growth numbers | Resource monitoring | Requires SSH access — previously declined; needs to be granted or explicitly re-scoped |
| Consider (not mandatory) extending `/health` to assert APScheduler job-store liveness directly, not just via `last_scan` freshness | Small code change | The one item in this whole list that is a genuine code change candidate — explicitly **not implemented here**, flagged as an operational improvement for a separate, small, reviewed change |

---

## 4. Risk Assessment

| Risk | Severity | Note |
|---|---|---|
| **Everything certified GO in AF-3 through AF-6 is certified-in-repo, not certified-in-production** | **High, but procedural not architectural** | The fix is deployment, not engineering — the code itself has no open defect. Risk is entirely about sequencing: declaring "fully operational" before this step would be inaccurate. |
| `tests/security/test_release_scripts.py` is itself part of the uncommitted batch | Medium | It's the test that *proves* `scripts/release.sh`'s dirty-tree guard works — review it alongside everything else before committing, not as an afterthought; it's release-safety-critical, not incidental. |
| K1/K2 (this session's new deterministic vetoes) will be exercised against real production traffic for the first time upon deploy, with no shadow period | Medium | Already flagged in AF-6 §7 B-row; unchanged here — monitor veto rate closely in the first days after deploy. |
| Ubuntu resource measurements remain the single most-repeated "not done" item across every certification in this entire sequence (AF-6, `FINAL_PRODUCTION_READINESS_CERTIFICATION.md`, multiple prior phases) | Medium | Genuinely blocked on access, not on effort or planning — needs an explicit access decision, not another audit finding it again. |
| `/health`'s scheduler-liveness gap (RC1's named, still-open item) means a stalled-but-alive APScheduler could pass health checks | Low-Medium | Mitigated today by `last_scan` freshness as a proxy and the separate heartbeat watchdog (`logs/heartbeat_check.log`, in the daily checklist) — not zero coverage, just not a direct assertion. |

---

## 5. Production Launch Recommendation

**Do not declare "Production Engine — Fully Operational" yet. The code is ready; the deployment is
not.**

This is not a reversal of AF-6's "GO WITH CONDITIONS" — that verdict was correctly scoped to code
correctness and remains valid. This assessment adds the operational dimension AF-6 explicitly
deferred: launch readiness requires the code to actually be running where it matters. Recommended
sequencing: **commit → deploy → execute the post-deploy checklist → THEN declare fully operational**,
not skip straight to the declaration on the strength of local test results.

---

## 6. Final Certification Level

# GO WITH CONDITIONS — DEPLOYMENT PENDING

Distinct from a plain "GO WITH CONDITIONS": every condition in AF-6's list is still valid and
unchanged, but this tier adds that the single largest condition of all — **the code has to actually
ship** — was not previously stated in those terms. Once committed, deployed, and the checklist in §3
is worked through, this certification should be re-issued as a plain "GO WITH CONDITIONS" (matching
the rest of this repository's established tier), with the deployment-pending caveat dropped.

---

## 7. Recommended Execution Order

1. **Review the full uncommitted diff as a deliberate commit** (or a small number of logically
   grouped commits) — 179 changed paths span WP1-4, the Provider Governor, position sizing, Ranking
   Engine wiring, and this session's own K1/K2 work; confirm scope and message per this repo's
   Conventional-Commits convention before committing.
2. **Deploy** via `scripts/release.sh` (will now succeed — the dirty-tree guard was the actual
   blocker) → `scripts/wait_for_health.sh`.
3. **Execute `docs/OPERATIONS.md`'s "After any deploy" checklist** (already written, just needs
   running): `journalctl` clean-startup check, full test suite green.
4. **Confirm live `.env` values** (`EDGE_SCORE_MODE`, `TELEGRAM_WEBHOOK_SECRET`).
5. **Run `engine/agent_firm/smoke.py`** against the live, deployed K1/K2 behavior.
6. **Observe one full daily cycle** (08:35 premarket → 16:40 EOD → 18:30 forward-test) — confirm
   Telegram delivery, `watchlist_snapshot` writes, and diff sections render correctly against real
   traffic for the first time.
7. **Run the decision-distribution and extended veto-rate queries** (§3 task list) after 24-48h.
8. **Capture Ubuntu resource measurements** once access allows.
9. **Execute the weekly checklist** (restore drill, `provider_events` rates, disk usage).
10. **Re-issue certification as plain "GO WITH CONDITIONS"**, dropping the deployment-pending
    caveat, once steps 1-9 are done.

No work has been started on any of the above; this is the assessment only, as requested. The one
uncommitted defect referenced throughout (nothing is deployed) is *reported*, not fixed, consistent
with "no code changes unless a genuine operational blocker is discovered" — this is exactly that
kind of blocker, and the fix is an operator action (commit + deploy), not a code change this task
should make unilaterally.
