# Production Engine — Release Certification (Final Gate)

**Date:** 2026-07-28
**Basis:** `Audit/PRODUCTION_READINESS_REPORT.md`, `Audit/END_TO_END_VALIDATION_REPORT.md`,
`Audit/SECURITY_REVIEW_REPORT.md`, `Audit/TECHNICAL_DEBT_RELEASE_REVIEW.md` — all produced by this
same certification pass. This document is the synthesis and final decision.
**Mandate:** adversarial — attempt to disprove production readiness, not confirm it. Six parallel
adversarial investigations plus this reviewer's own live, executed verification (not just code
reading) fed into this certification.
**Constraint honored:** no architecture change, no new features, no refactors. Six genuine defects
were found and fixed, each minimal and isolated; every fix is validated and committed.

---

## Executive Summary

This certification found **6 genuine production defects**, fixed and validated all 6, and found
**~18 further genuine, evidenced risks** that were deliberately **not** fixed in this pass — each
because fixing it correctly required either a design/security decision this review cannot make
unilaterally (changing fail-open auth behavior on an already-live system), touched more files than
"minimal and isolated" allows, or required new operational infrastructure rather than a code
correction. Every one of those ~18 is documented with file:line evidence and a required-follow-up
recommendation, not silently accepted.

**None of the 24 total findings (fixed or not) is a regression introduced by RC1's own delivered
work** — the Telegram reporting, crash-alert rate limiting, and redaction fixes already certified in
`Audit/RC1_FINAL_CERTIFICATION_2026-07-28.md` and validated green on real GitHub Actions in
`Audit/RC1_CI_VALIDATION_AND_RELEASE_READINESS_2026-07-28.md`. Everything found in this pass is
pre-existing on this long-lived branch, surfaced only because this is the first time the whole
repository has been adversarially re-examined end-to-end in one certification.

Of the two most severe findings:
- **The `paper_trades` boot-deadlock** (a from-scratch/disaster-recovery deploy would boot once and
  then permanently fail to restart) was reproduced *live* — not inferred from reading code — and is
  now fixed and verified via an actual simulated restart.
- **The `TELEGRAM_WEBHOOK_SECRET` fail-open gap** is real and exploitable if misconfigured, but this
  review deliberately did not silently harden it, because doing so could refuse to boot an
  already-functioning live system if that variable isn't already set there. This is flagged as the
  single most urgent action item, not fixed unilaterally.

---

## Findings, By Phase (full detail in the four linked reports)

| Phase | Report | P0 | P1 | P2 | P3 | Fixed this session |
|---|---|---|---|---|---|---|
| 1–2 Repository audit + operational readiness | `PRODUCTION_READINESS_REPORT.md` | 1 (unfixed: webhook) + 2 (fixed) | ~13 | 5 | 4 | 5 |
| 3 End-to-end validation | `END_TO_END_VALIDATION_REPORT.md` | — | 1 (cron gap, cross-listed) | — | — | 2 (via Phase 1 fixes, executed live) |
| 5 Security review | `SECURITY_REVIEW_REPORT.md` | 1 (webhook) | 5 | 2 | — | 3 |
| 6 Technical debt | `TECHNICAL_DEBT_RELEASE_REVIEW.md` | 0 | 0 | 0 | 0 | 0 (none needed) |

(Totals overlap across reports by design — e.g. the webhook finding and the cron-gap finding are each
discussed in the report most relevant to their phase, cross-referenced rather than duplicated in
full.)

## Fixes Applied and Validated This Session

| Commit | Fix | Evidence basis |
|---|---|---|
| `e30d4f3` | Remove crash-prone redundant `print()` in registry announce | Live-reproduced `UnicodeEncodeError` crash |
| `4826cae` | Create `paper_trades` table in `init_runtime()` | Live-reproduced boot deadlock on simulated restart |
| `0c35d1b` | Fix `STOCKBIT_PASSWORD`→`STOCKBIT_PASS` redaction var name | Direct code/env-var cross-reference |
| `368f6c8` | `worker_exit` `shutdown(wait=True)`, log shutdown errors | APScheduler library source, verified directly |
| `21edd4d` | Route `paper_trade.py` exception prints through the logger | Direct code reading; filter-attachment confirmed |
| `ac2d349` | `.gitignore` `.stockbit_token.lock` | `git check-ignore -v` |

**Validation:** each fix was tested in isolation (targeted pytest runs, all passing), then the full
suite was re-run against a clean `git worktree` of the actual committed HEAD (never the working
tree) after each batch of fixes. Final full-suite result at the true final HEAD (`ac2d349`):

```
16 failed, 1605 passed, 3 skipped in 387.49s (0:06:27)
```

(One fewer failure and one more pass than the immediately-prior intermediate baseline of 17/1604/3 —
the difference is `tests/regime/test_storage.py::test_append_only_rerun_makes_a_new_profile_id`,
which appeared flaky rather than fixed: none of this session's six commits touch anything in
`research/regime`. All 16 remaining failures are the same six categories already independently
traced below.)

Every failure in that run was independently traced, in this and the prior RC1 certification passes,
to a pre-existing, non-blocking, environment-only or explicitly-excluded-workstream cause (Windows
`.sh`-subprocess incompatibility, Windows temp-file-handle lock, Node.js path-escaping on Windows,
and the separately-scoped agent-firm-governor/research-provenance workstreams) — zero regressions
introduced by any of the six fixes above.

---

## Required Follow-Up Actions (not release-blocking for the fixes already applied, but must be tracked)

1. **Urgent — confirm `TELEGRAM_WEBHOOK_SECRET` is set in the real production `.env` today.** If it
   is not, the `/telegram/updates` webhook is currently accepting unauthenticated requests. Add
   `validate_config()` enforcement (matching `TELEGRAM_TOKEN`/`TELEGRAM_CHAT_ID`'s existing pattern)
   as an immediate fast-follow once confirmed safe to do so.
2. Fix or accept, with an explicit decision, the `validate_config()` DB_PATH-must-pre-exist
   contradiction (an automated bootstrap step, or relaxing the check).
3. Restructure `start_scheduler()`'s ~20 `add_job()` calls to isolate registration failures
   (currently one bad job registration crashes the whole worker boot).
4. Add a "did this cron job fire at all" dead-man's-switch for the backup/restore-drill cadence
   (real ~36h gap found in production logs, 2026-07-25/26).
5. Commit the existing, already-written `_write_token_atomic()` hardening for
   `auto_token.py`/`stockbit_fetcher.py` (currently uncommitted, deliberately excluded from RC1).
6. Add per-trade exception isolation + an alert to `monitor.py`'s SL/TP evaluation loop.
7. Extend redaction to cover the live Stockbit bearer JWT and fix the truncate-before-redact
   ordering at 10+ call sites (a coordinated, multi-file change — not minimal/isolated enough for
   this pass).
8. Add a scheduler-liveness check to `/health` so a broken deploy can't silently pass the deploy gate.
9. Correct `scripts/release.sh`'s `SHARED_PATHS` default to match the real `DB_PATH` default location.
10. Exercise `scripts/release.sh` end-to-end in CI, not just via unit tests of its logic.
11. Redact `cron_wrap.sh`'s shell-based Telegram crash alert (currently the one outbound path never
    covered by the Python `redact_secrets()` mechanism).

None of these require architecture change; all are additive/corrective within the existing design,
consistent with the posture already established across this repository's audit trail.

---

## Confidence Level

**High** on everything actually fixed and tested this session (each is evidence-backed by a live
reproduction or direct library-source verification, not inference alone). **Medium-high** on the
findings not fixed — every one has concrete file:line evidence, but several (the cron-gap monitoring,
the `/health` scheduler-liveness check, the redaction ordering fix) would benefit from a second,
focused pass rather than being squeezed into this same certification sweep. **Not assessed**: GitHub
Issues content (no access), and a true continuous live-market rehearsal of the full signal→trade
pipeline (would require real credentials/market hours this review doesn't have authorization to use).

---

## Release Status

# GO WITH CONDITIONS

### Exact rationale

**Why not NO GO:** every defect found and fixed this session is validated, isolated, and does not
touch RC1's already-certified reporting/scheduler/redaction work. CI is real and green
(`Audit/RC1_CI_VALIDATION_AND_RELEASE_READINESS_2026-07-28.md`). Nothing found is a regression from
RC1's own delivered scope — everything is pre-existing baggage on a long-lived branch that had never
been adversarially audited end-to-end before this pass, or before this pass's own live execution
testing. A NO GO verdict would be disproportionate to what was actually found: two live-reproduced,
now-fixed defects, and a documented, tracked list of pre-existing risks — not a codebase riddled with
active incidents.

**Why not an unconditional GO:** the `TELEGRAM_WEBHOOK_SECRET` fail-open gap is a real, live,
potentially-exploitable security gap this review chose not to silently patch, precisely because doing
so responsibly requires knowing the real production environment's current configuration — information
this review does not have. Shipping without at least confirming that one fact would be irresponsible
regardless of how solid everything else is. The remaining ~17 P1/P2/P3 items are genuine but bounded
and already prioritized in the required-follow-up list above — none of them, individually or
together, rises to the same urgency as the webhook gap.

### Conditions for full GO

1. Confirm `TELEGRAM_WEBHOOK_SECRET` is set in the real production `.env` (or accept the exposure
   explicitly, with eyes open, if the webhook route is not actually reachable from the public
   internet in the current deployment topology).
2. Merge PR #26 (already CI-green) plus the six fix commits from this certification, tag the
   release, per the already-approved RC1 merge/tag recommendation.
3. Track the remaining 10 required-follow-up items as the next block of scheduled work, ahead of or
   alongside the previously-planned Operations Dashboard / Job History phase.

Only after the conditions above are addressed should the previously-agreed next milestones — the
Operations Dashboard / Job History phase, then the Agent Firm repository split — begin, per this
task's own instruction.
