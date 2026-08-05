# AF-6 — Production Readiness Assessment: Agent Firm Decision Flow → Ranking → Watchlist Generator (v1)

**Date:** 2026-07-29 · **Status:** Assessment only — no code changed, no files modified.
**Scope:** the arc audited across AF-3 (Decision Flow, WP4 implemented), AF-4 (Ranking Engine,
audited complete), AF-5 (Watchlist Generator, audited complete) — Production Engine → Candidate →
Agent Firm Review → Ranking → Watchlist Generator → Publisher. This is **not** a re-certification of
the whole repository; a separate, whole-Production-Engine certification already exists and is cited,
not repeated (`Audit/FINAL_PRODUCTION_READINESS_CERTIFICATION.md`, `Audit/PRODUCTION_ENGINE_RELEASE_CERTIFICATION.md`,
`Audit/FINAL_RELEASE_DECISION.md`).
**Method:** synthesis of AF-3/4/5's own evidence (already independently gathered from source and
tests, not re-derived here) plus a fresh, this-session test run and a targeted search of prior
release-certification documents for an authoritative product-scope definition (§1).

---

## 1. Official Product Definition of the Production Engine

**Answer: Telegram + Dashboard + API, in general — but each individual feature is scoped
independently, and the specific feature this arc built (EOD/Premarket/Watchlist reporting) was
explicitly, deliberately scoped as Telegram-only.**

Two distinct facts, not in tension:

- **At the whole-application level**, CLAUDE.md's own "What This Is" section defines the product as
  "a Flask app... that scans... manages paper trades... fetches intraday flow/orderbook data...
  and sends Telegram alerts" — i.e. the shipped product already includes a Flask dashboard/API
  (`templates/dashboard.html`, `routes/*.py`) *and* Telegram, both already built and already
  RC1-certified (`Audit/RELEASE_READINESS_AUDIT_2026-07-28.md`).
- **At the feature level**, the specific EOD/Premarket/Watchlist capability this arc is about was
  scoped narrower, and by explicit record, not by omission. Found directly in the release-audit
  trail: `Audit/PRODUCTION_ENGINE_IMPLEMENTATION_AUDIT_2026-07-28.md` line 228 states **"Per user's
  instruction, Forward Testing Reporting and the Operations Dashboard are intentionally"**
  [separated], and line 391 names the dashboard explicitly as the one item **"out of scope"** for
  this phase, closing with "Engine is ready to move to the Operations Dashboard / Job History phase
  next, **per your instruction**." CLAUDE.md's own 2026-07-28 amendment log promotes this into
  canonical documentation under the literal heading **"Production Engine Telegram reporting"** — not
  "Telegram + Dashboard reporting."

So the product definition, for *this specific feature*, is **Telegram publication only, by explicit,
recorded, user-directed scope** — not an accidental narrowing discovered by this audit, and not a
gap this arc left behind. The dashboard is real, already exists, already serves other watchlist-shaped
data (AF-5 §2), and is deliberately sequenced as its own, separately-named next milestone.

---

## 2. Is Telegram Publication Sufficient?

**Yes — it satisfies the actual, recorded product requirement for this feature.** AF-5 confirmed
both `build_message()` (EOD) and `_build_premarket_firm_message()` (Premarket) are complete, tested,
and confirmed at live call sites (`scheduler/jobs.py:1111` and `:946`). Per §1's evidence, no
requirement — recorded or implied — calls for this specific feature to also ship a dashboard/API
surface; that was explicitly deferred, not omitted.

---

## 3. Does the Dashboard Consume the Canonical Agent Firm Watchlist?

**No.** AF-5 traced this precisely: `templates/dashboard.html`'s watchlist panel fetches
`/api/dashboard/watchlist` (a deterministic BUY WATCH/AVOID/WAIT classifier, `engine/dashboard.py`,
zero connection to `AgentDecision` or `watchlist_snapshot`) and `/api/dashboard/unified-watchlist`
(a pre-firm merge of reversal/premover/bear-dip sources, also not agent-firm-aware). The
agent-firm-ranked artifact (`watchlist_snapshot`, written by `engine/trade_plan.py::record_snapshot()`)
has no route reading it at all.

---

## 4. Is the Dashboard Difference Intentional, Debt, or Unfinished?

**Intentional product design — confirmed by direct citation, not inferred.** Per §1's evidence
(`Audit/PRODUCTION_ENGINE_IMPLEMENTATION_AUDIT_2026-07-28.md`), the Operations Dashboard was
excluded from this feature's scope **by explicit user instruction**, and the two dashboard watchlist
panels that do exist (`get_watchlist()`, `build_unified_watchlist()`) are older, independent
features that predate this arc and serve genuinely different purposes (AF-5 §2) — they were never
supposed to show the agent-ranked list, so their not doing so is not a defect in them either. Neither
"technical debt" nor "unfinished feature" fits: technical debt implies an accepted shortcut with a
cost; unfinished implies work that was supposed to happen and didn't. Here, the scope was drawn on
purpose and the work on the other side of that line has an already-named home (Operations Dashboard
/ Job History).

---

## 5. Any Remaining Blocker to Declaring "Production Engine v1 Complete"?

**No**, for the scope this arc actually covers (Decision Flow WP1-4, Ranking Engine, Watchlist
Generator + Publisher). Evidence, fresh this session:

```
pytest tests/agent_firm/ tests/test_trade_plan.py tests/test_bear_watchlist_ranking.py \
       tests/test_eod_trade_plan_job.py -q --ignore=tests/agent_firm/providers
→ 213 passed, 0 failed
```

This is a superset of AF-3's 164 (Decision Flow, including WP4's new K1/K2 guardrails) and AF-4's 82
(Ranking Engine; the 213 total reflects some overlap removed by combining the invocation, not fewer
tests — every suite AF-3/AF-4 separately confirmed passing is included here). Zero regressions,
zero new failures, zero drift since either prior audit.

**Distinct from, and not overriding**, the separately-scoped whole-Production-Engine certification
already on record (`Audit/FINAL_PRODUCTION_READINESS_CERTIFICATION.md`, dated the same day): that
document independently reached **GO WITH CONDITIONS** for the broader ADR-AF-002/003/004 +
integration + operational-validation workstream, with its own, already-catalogued condition list
(live Ubuntu measurements, two `.env` value confirmations, post-deploy decision-distribution
monitoring). This assessment does not re-litigate that scope; it confirms nothing found in AF-3/4/5
or this session's fresh test run contradicts it or adds a new blocking condition.

---

## 6. Classification of Every Remaining Item

**A. Production blockers — none.**

**B. Operational improvements (carry into deploy/burn-in, not code changes):**
| Item | Source |
|---|---|
| Monitor premarket/EOD/exit-review Agent Firm decision-distribution shift post-deploy | `FINAL_PRODUCTION_READINESS_CERTIFICATION.md` §3/§4 — the one condition every prior certification in that chain has named |
| Monitor K1/K2 guardrail veto rate now that they enforce immediately (not shadow-gated) | AF-3 — this session's own WP4 implemented K1/K2 as directly-enforcing per the literal task spec; worth watching against real traffic since it's the first new deterministic veto path added since launch |
| Capture real Ubuntu host CPU/RSS/disk/DB-growth measurements | `FINAL_PRODUCTION_READINESS_CERTIFICATION.md` §3 — outstanding across multiple phases, SSH access previously declined |
| Confirm live `.env`'s `EDGE_SCORE_MODE` and `TELEGRAM_WEBHOOK_SECRET` values | `FINAL_PRODUCTION_READINESS_CERTIFICATION.md` §3, carried from `RELEASE_CONDITIONS_MATRIX.md` |
| Confirm bear-watchlist's Telegram-less, log-only behavior is still the intended design | AF-4/AF-5 — cites a specific 2026-06-16 decision (commit `89baa33`); worth an explicit re-confirmation, not a silent assumption, before this arc is called permanently closed |
| Fix the Provider-Layer test-collection defect (`_hydrate_quota_holds` import error) | AF-3 — blocks a bare `pytest -q` repo-wide; Provider Layer is out of this arc's scope but the defect affects CI hygiene generally |

**C. UI/Presentation enhancements (optional, not required for v1):**
| Item | Source |
|---|---|
| A dashboard/API route exposing `watchlist_snapshot` (the agent-ranked list) alongside the two existing, unrelated watchlist panels | AF-5 §6/§10 — additive only, would not touch `record_snapshot`/`diff_watchlist`/`build_message` |
| Extending bear-watchlist ranking to the same snapshot/diff/Telegram contract EOD/Premarket already share | AF-4 §7/§9 — contingent on the confirmation in the Operational table above, not a default action |

**D. Future roadmap (already named elsewhere in this repository, no new scope invented here):**
| Item | Source |
|---|---|
| Operations Dashboard / Job History | `Audit/PRODUCTION_ENGINE_NEXT_MILESTONE.md`, `Audit/ADR-AF-002_HANDOFF_CHECKLIST.md` — the standing next milestone; would naturally absorb the C-row dashboard item above if/when it starts |
| Agent Firm repository split (AF-1 through AF-7) | `docs/agent_firm/AGENT_FIRM_IMPLEMENTATION_ROADMAP.md` — sequenced after the dashboard milestone |
| `ConsensusContext.aligned_bullish`-driven confidence-band logic (K4) | Named in `AF1_CONTEXT_OBJECT_CATALOG.md` as a documented-but-not-required extension; K1/K2 (this arc's actual mandate) are done — K4 was never asked for by WP4 and isn't implied by anything audited here |
| 11-item RC1 follow-up list (`validate_config()` hardening, `monitor.py` exception isolation, redaction fixes, `/health` liveness check, release-script fixes, etc.) | `Audit/RELEASE_CONDITIONS_MATRIX.md` via `Audit/PRODUCTION_ENGINE_NEXT_MILESTONE.md` — **pre-existing Production Engine debt, explicitly not part of the Agent Firm/Ranking/Watchlist arc** (that document's own words); still open as of the last verified check, unaffected by anything in this session |

---

## 7. Risk Assessment

| Risk | Severity | Note |
|---|---|---|
| K1/K2 ship enforcing (not shadowed) — first new deterministic veto path since launch | Medium | Matches the user's literal WP4 instruction ("automatically veto"); flagged as a B-row monitoring item, not reversed here — this task is an assessment, not a design change |
| Whole-Production-Engine operational conditions (Ubuntu measurements, `.env` confirmations) remain genuinely unclosed across multiple prior sessions | Medium | Real, acknowledged, unrelated to this arc's own correctness — carried forward from the standing certification, not newly discovered |
| Dashboard/watchlist naming collision (AF-5) could cause a future engineer to "fix" the wrong component | Low, now well-documented | AF-5's inventory table is the mitigation — consult it before touching anything watchlist-named |
| None of this arc's own code (WP4, Ranking Engine, Watchlist Generator) shows any open defect | — | 213/213 passing, fresh this session |

---

## 8. Go / No-Go Decision

# GO WITH CONDITIONS

**Justification:** consistent with, not a departure from, this repository's own established
certification tier for this entire release sequence (`FINAL_PRODUCTION_READINESS_CERTIFICATION.md`:
"not a new tier — the same recommendation every report in this sequence has independently reached").
The Decision Flow (WP1-4, including this session's K1/K2 guardrails), Ranking Engine, and Watchlist
Generator are each complete, tested (213/213 passing, fresh this session), and consistent with their
own recorded scope — including the Telegram-only scoping this assessment confirmed was deliberate,
not accidental. No item found in AF-3, AF-4, AF-5, or this session's own verification rises to
"blocking." Every remaining item is operational (monitor, measure, confirm) or explicitly optional
(UI enhancement, future roadmap) — none require new engineering to declare this arc production-complete.

---

## 8a. Operational Activities Remaining (Go path)

1. **Burn-in monitoring**: watch Agent Firm decision-distribution shift (standing condition) and
   K1/K2 veto rate (new, this session) against real scan-cycle traffic for the first 1-2 weeks.
2. **Deployment validation**: confirm `watchlist_snapshot`'s `CREATE TABLE IF NOT EXISTS` migration
   applies cleanly on the live DB on first post-deploy run (idempotent by construction, per
   `engine/trade_plan.py::ensure_watchlist_snapshot_table`, but worth a first-run confirmation like
   any new table).
3. **Live-host measurement**: capture the outstanding Ubuntu CPU/RSS/disk/DB-growth numbers — overdue
   across multiple prior phases, not blocking, but the largest genuinely open item on record.
4. **Config confirmation**: verify live `.env`'s `EDGE_SCORE_MODE` and `TELEGRAM_WEBHOOK_SECRET`
   values against expectations.
5. **Decision confirmation, not code change**: explicitly re-confirm bear-watchlist's log-only
   design is still wanted, given it's the one asymmetry across the three ranking pipelines.
6. **Housekeeping**: fix the Provider-Layer `_hydrate_quota_holds` test-collection defect so a bare
   `pytest -q` succeeds repo-wide — small, low-risk, unrelated to this arc's correctness.
7. **Documentation**: none blocking; the pre-existing `docs/agent_firm/*.md` planning-corpus
   reconciliation debt (23 files, carried from `FINAL_PRODUCTION_READINESS_CERTIFICATION.md`) remains
   low-priority and unaffected by this arc.

## 8b. Mandatory Engineering Work (No-Go path)

Not applicable — decision is GO.

---

## 9. Recommended Next Milestone After Production

**Operations Dashboard / Job History** — already the standing, independently-named next milestone
(`Audit/PRODUCTION_ENGINE_NEXT_MILESTONE.md`, `Audit/ADR-AF-002_HANDOFF_CHECKLIST.md`,
`FINAL_PRODUCTION_READINESS_CERTIFICATION.md` §3 Future Enhancements) — not a new recommendation
invented by this assessment. Its first version should absorb the one C-row item this arc surfaced
(a dashboard/API route for `watchlist_snapshot`, AF-5) alongside its own already-scoped job-history
content, so the dashboard doesn't need a second pass later to add agent-ranked-watchlist visibility.
After that: the **Agent Firm repository split** (AF-1 through AF-7,
`docs/agent_firm/AGENT_FIRM_IMPLEMENTATION_ROADMAP.md`), unchanged from its existing sequencing.

No work has been started on any of the above; this is the assessment only, as requested.
