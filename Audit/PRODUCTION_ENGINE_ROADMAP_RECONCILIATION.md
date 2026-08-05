# Production Engine — Roadmap Reconciliation Matrix

**Date:** 2026-07-29
**Purpose:** reconcile every roadmap/planning/certification source touching the Production Engine
and Agent Firm subsystems into one consistent picture, resolve contradictions between them, and
classify every planned milestone and outstanding follow-up item with justifying evidence. No code
was read-only-inspected but not modified as part of producing this document.

---

## Sources Collected

| Source | Date | Nature |
|---|---|---|
| `CLAUDE.md` | v1.1, effective 2026-07-21, amended 2026-07-28 and 2026-07-29 | Living operating manual / current status source |
| `Audit/PRODUCTION_ENGINE_IMPLEMENTATION_AUDIT_2026-07-28.md` | 2026-07-28 | Kickoff audit that scoped the Telegram Reporting v2 ("RC1") work |
| `Audit/RELEASE_READINESS_AUDIT_2026-07-28.md` | 2026-07-28 | First audit of RC1 implementation — found R-1..R-4 |
| `Audit/RC1_CERTIFICATION_REPORT_2026-07-28.md` | 2026-07-28 | Adversarial board review of RC1's fix report — CERTIFIED WITH CONDITIONS (RC1-C1, RC1-C2) |
| `Audit/RC1_CONDITIONS_CLOSURE_REPORT_2026-07-28.md` | 2026-07-28 | Closes RC1-C1 (Windows path normalization) and RC1-C2 (redaction completeness for `auto_token.py`/`stockbit_fetcher.py`) |
| `Audit/RC1_RELEASE_PACKAGING_2026-07-28.md` | 2026-07-28 | Release packaging/commit-scope decisions |
| `Audit/RC1_CI_VALIDATION_AND_RELEASE_READINESS_2026-07-28.md` | 2026-07-28 | Real GitHub Actions CI validation — GO to merge PR #26 |
| `Audit/RC1_FINAL_CERTIFICATION_2026-07-28.md` | 2026-07-28 | Further re-certification (F-1/F-2/F-3) — reaffirms next-phase sequencing |
| `Audit/PRODUCTION_READINESS_REPORT.md` | 2026-07-28 | Phases 1–2 of a **separate, broader**, whole-repository adversarial certification ("Final Gate") |
| `Audit/END_TO_END_VALIDATION_REPORT.md` | 2026-07-28 | Phase 3 of the Final Gate pass |
| `Audit/SECURITY_REVIEW_REPORT.md` | 2026-07-28 | Phase 5 of the Final Gate pass |
| `Audit/TECHNICAL_DEBT_RELEASE_REVIEW.md` | 2026-07-28 | Phase 6 of the Final Gate pass — zero must-resolve debt items |
| `Audit/PRODUCTION_ENGINE_RELEASE_CERTIFICATION.md` | 2026-07-28 | Synthesis of the Final Gate pass — GO WITH CONDITIONS |
| `Audit/OWNER_DECISION_PACKAGE.md` | 2026-07-28 | 4 decisions from the Final Gate pass requiring owner judgment |
| `Audit/RELEASE_CONDITIONS_MATRIX.md` | 2026-07-28 | Full findings ledger from the Final Gate pass |
| `Audit/FINAL_RELEASE_DECISION.md` | 2026-07-28 | Re-evaluation — webhook secret confirmed live via SSH — upgraded to unconditional **GO** |
| `docs/agent_firm/ADR-AF-001-DETERMINISTIC_OWNERSHIP.md` | 2026-07-29 | Decided architecture — canonical-producer disambiguation |
| `docs/agent_firm/ADR-AF-002-CONTEXT_OWNERSHIP.md` | 2026-07-29 | Decided architecture — Tier 1 context assembly ownership |
| `docs/agent_firm/ADR-AF-003-SIZING_OWNERSHIP.md` | 2026-07-29 | Decided architecture — `agent_size_hint` single-writer rule |
| `docs/agent_firm/ADR-AF-004-VERSIONING_CONTRACT.md` | 2026-07-29 | Decided architecture — versioning/compatibility policy |
| `docs/agent_firm/AF2_ARCHITECTURE_CERTIFICATION.md` | 2026-07-29 | Certifies ADR-AF-001..004 collectively resolve Blockers B1–B4; "AF-2 implementation may begin" |
| `docs/agent_firm/AF2_WORK_PACKAGE_SEQUENCE.md` | 2026-07-29 (superseded numbering) | Stale WP0–9 sequencing that does not match what was actually delivered |
| `docs/agent_firm/AGENT_FIRM_MIGRATION_PLAN.md` | 2026-07-28 | What-stays/what-moves plan for an eventual Agent Firm repository split |
| `docs/agent_firm/AGENT_FIRM_IMPLEMENTATION_ROADMAP.md` | 2026-07-28 | AF-1 through AF-7 sequence — repo-extraction readiness, separate from ADR-AF-00x |
| `docs/agent_firm/AGENT_FIRM_GOVERNANCE.md` | 2026-07-28 | Versioning/release/compatibility/deprecation policy; states repo-split timing explicitly |
| `PLAN.md` | 2026-06-04, marked SHIPPED 2026-06-05/09 | Earlier, already-complete "Agent Firm Optimization" initiative (2-stage evaluation) |
| `Audit/AF2_WP1..WP4_*.md`, `Audit/ADR-AF-002_*.md`, `Audit/AF2_PRODUCTION_VALIDATION_REPORT.md` + companions | 2026-07-29 | This closure sequence's own deliverables — ADR-AF-002's implementation/audit/validation trail |

**A naming collision worth flagging explicitly, not silently smoothed over:** "AF-2" is used in this
corpus for two different things — (a) the second-generation Agent Firm architecture initiative as a
whole (ADR-AF-001 through 004, certified as a set by `AF2_ARCHITECTURE_CERTIFICATION.md`), and (b) the
four work packages this session's predecessor actually executed (WP1–WP4), which implemented **only**
ADR-AF-002 (and, as a side effect of the same code, ADR-AF-001 — see below). These are not the same
scope. This reconciliation treats them as distinct throughout.

---

## Part 1 — Milestone Reconciliation

| Milestone | Source(s) | Classification | Justification |
|---|---|---|---|
| **RC1 — Telegram Reporting v2** (EOD/Premarket/Forward-Testing, watchlist snapshot/diff, crash-alert rate limiting) | `PRODUCTION_ENGINE_IMPLEMENTATION_AUDIT`, `RELEASE_READINESS_AUDIT`, `RC1_CERTIFICATION_REPORT`, `RC1_CONDITIONS_CLOSURE_REPORT`, `RC1_CI_VALIDATION_AND_RELEASE_READINESS`, `RC1_FINAL_CERTIFICATION` | **Completed** | Both certification conditions (RC1-C1, RC1-C2) independently closed with evidence (test runs, new regression suites); CI validated green on real GitHub Actions; `CLAUDE.md`'s 2026-07-28 Amended entry already documents these features as canonical, current architecture — and this closure's own WP1-4 sessions built directly on top of `scheduler/jobs.py::run_premarket_firm_scan()`/`run_eod_trade_plan()`, confirming these features are live in the checked-out code, not merely planned |
| **Production Engine Release Certification ("Final Gate")** — whole-repo adversarial audit | `PRODUCTION_READINESS_REPORT`, `END_TO_END_VALIDATION_REPORT`, `SECURITY_REVIEW_REPORT`, `TECHNICAL_DEBT_RELEASE_REVIEW`, `PRODUCTION_ENGINE_RELEASE_CERTIFICATION`, `FINAL_RELEASE_DECISION` | **Completed** (as its own certification event) | 6 defects found and fixed, committed, validated (zero regressions, full-suite re-run at true HEAD); the one blocking condition (webhook secret) directly confirmed via live SSH in `FINAL_RELEASE_DECISION.md`; verdict upgraded from GO WITH CONDITIONS to unconditional **GO** |
| **ADR-AF-001 — Deterministic Ownership** | `ADR-AF-001-DETERMINISTIC_OWNERSHIP.md`, `AF2_ARCHITECTURE_CERTIFICATION.md` | **Completed** | The decision (canonical producers for regime/technical-direction/catalyst) is implemented by construction — `engine/agent_firm_context.py::build_technical_context()`/`build_regime_context()`/`build_news_context()` wrap `tech_direction()`/`detect_regime()`/`has_catalyst()` exactly as this ADR specifies; delivered as a side effect of ADR-AF-002's own WP1 (Foundation), verified by direct code read this session |
| **ADR-AF-002 — Context Ownership** | Full WP1–WP4 trail + Final Architecture Audit + Production Validation | **Completed** | Independently re-verified across three separate sessions (WP4's own certification, a from-scratch architecture audit, a simulated production validation) — see `Audit/ADR-AF-002_CLOSURE_REPORT.md` for the full trail. Not re-litigated here. |
| **ADR-AF-003 — Sizing Ownership** | `ADR-AF-003-SIZING_OWNERSHIP.md`, `AF2_ARCHITECTURE_CERTIFICATION.md` | **Still required — decided, not implemented** | See Part 3 below — this is the single most significant finding of this reconciliation. Verified this session by direct code read: `engine/position_sizing.py` does not exist; `scheduler/scanner.py:962` and `:1038` both still write `r["agent_size_hint"]` exactly as the ADR's evidence table describes, with no precedence rule between them; the Risk agent does not emit `size_tier` (`grep` for the term in `risk.py`/`risk_v2.md` returns nothing) |
| **ADR-AF-004 — Versioning Contract** | `ADR-AF-004-VERSIONING_CONTRACT.md` | **Completed** | A governance/policy ruling, not a code deliverable — it affirms the existing `AGENT_FIRM_GOVERNANCE.md` rule stands unamended. Self-enforcing by convention; WP1–WP3's own field-addition approach (additive optional `SignalCandidate` fields, no `evaluate()` signature change) already followed exactly this rule, confirming it was adhered to in practice, not just written down |
| **`AF2_WORK_PACKAGE_SEQUENCE.md`'s WP0–WP9 sequencing** | `AF2_WORK_PACKAGE_SEQUENCE.md` | **Superseded / obsolete** | This document's own WP4 = `ConsensusContext`; the actually-delivered WP4 = Integration Completion (a different scope entirely). Its underlying blocker-resolution *content* (B1–B4) was still eventually addressed — just via the four ADRs and the WP1–WP4 sequence actually executed, not via this document's literal plan. The document's sequencing/numbering should not be used for any future planning; its blocker analysis (B1–B4) remains historically accurate context |
| **`docs/agent_firm/AGENT_FIRM_IMPLEMENTATION_ROADMAP.md`'s AF-1 through AF-7** (repo-extraction readiness) | `AGENT_FIRM_IMPLEMENTATION_ROADMAP.md`, `AGENT_FIRM_MIGRATION_PLAN.md`, `AGENT_FIRM_GOVERNANCE.md` | **Still required — not started** | Distinct initiative from ADR-AF-00x (confirmed: this roadmap's own basis documents, `AGENT_FIRM_ARCHITECTURE.md`/`AGENT_FIRM_DEPENDENCY_AUDIT.md`, predate and are separate from the ADR-AF-00x set). No AF-1 data-access layer exists (`firm.py::_persist()` and `analytics.py` both still do raw SQL directly, not through an intermediating layer) — zero of the seven milestones has begun. Explicitly sequenced to start only **after** Operations Dashboard / Job History, per `AGENT_FIRM_GOVERNANCE.md`'s own "Independent Repository Timing" section |
| **Operations Dashboard / Job History** | `PRODUCTION_ENGINE_RELEASE_CERTIFICATION.md`, `FINAL_RELEASE_DECISION.md`, `AGENT_FIRM_GOVERNANCE.md` | **Still required — not started, no design doc** | Named as the standing next milestone in three separate 2026-07-28 documents; searched `docs/` and `Audit/` for any design/spec document scoping it — none found beyond these one-line mentions |
| **`PLAN.md` — "Agent Firm Optimization"** (2-stage evaluation, integration into decision flow) | `PLAN.md` | **Completed (historical)** | Document's own header states "Phase 1/2/3 SHIPPED" with commit hashes, dated 2026-06-05/09 — a fully separate, earlier, already-closed initiative. Confirmed still true: `firm.py::evaluate_staged()`'s 2-stage design (exercised directly in this closure's own Production Validation scenarios) matches this plan's target architecture exactly |

---

## Part 2 — Outstanding Follow-Up Item Reconciliation

The Final Gate certification's 11-item numbered follow-up list (`PRODUCTION_ENGINE_RELEASE_CERTIFICATION.md`
§"Conditions for full GO" item 3, detailed in `PRODUCTION_READINESS_REPORT.md`/`SECURITY_REVIEW_REPORT.md`),
cross-checked against `git log` on every file each item names:

| # | Item | Classification | Evidence |
|---|---|---|---|
| 1 | Harden `validate_config()` for `TELEGRAM_WEBHOOK_SECRET` | **Still required** | `FINAL_RELEASE_DECISION.md` confirms the secret is *currently* set (verified live), so there is no active exploit today — but the code-level enforcement gap itself is unaddressed. `git log config.py` shows no post-07-28 commit touching this |
| 2 | `validate_config()` DB_PATH-must-pre-exist contradiction | **Requires owner decision** (Option A vs. B, per `OWNER_DECISION_PACKAGE.md` Decision 2) — not urgent, no current deploy affected | No commit found addressing either option |
| 3 | Restructure `start_scheduler()`'s ~20 `add_job()` calls for failure isolation | **Still required** | `git log scheduler/__init__.py` shows no post-07-28 commit; this is a real robustness gap (one bad job registration crashes the whole worker boot), unrelated to ADR-AF-002 |
| 4 | Cron dead-man's-switch for backup/restore-drill cadence | **Still required** (operational infrastructure, not a code fix alone) | No evidence of a monitoring addition; the specific 2026-07-19 restore-drill gap itself cannot be confirmed resolved or unresolved without live host access (same caveat the original finding carried) |
| 5 | Land `_write_token_atomic()` hardening (already written, uncommitted) | **Still required** | `git log auto_token.py` shows the most recent commit (2026-07-28) is the reporting feature itself, not this hardening — confirms it remains uncommitted |
| 6 | `monitor.py` per-trade exception isolation + alert | **Still required** | `git log monitor.py` shows no post-07-28 commit; ADR-AF-002's WP4 touched `monitor.py::_agent_confirms_exit()` only for Tier 1 context wiring, confirmed by direct diff review, not this isolation gap |
| 7 | Extend redaction (Stockbit JWT structural gap + truncate-before-redact ordering) | **Partially satisfied, partially still required** | `RC1_CONDITIONS_CLOSURE_REPORT.md` already closed a *related but distinct* redaction gap (RC1-C2: `auto_token.py`/`stockbit_fetcher.py`'s own `send_telegram` now call `redact_secrets()`) — this predates and does not cover the Final Gate pass's later, broader findings (the JWT-can-never-be-redacted structural gap, and the 10+ call sites truncating before redacting). Both remain open |
| 8 | `/health` scheduler-liveness check | **Still required** | No commit found; `scripts/wait_for_health.sh` still gates only on DB connectivity per direct read this session |
| 9 | `scripts/release.sh` `SHARED_PATHS` default mismatch | **Still required** | `git log scripts/release.sh` shows no commit since 2026-07-11 (pre-dates even the RC1 work) |
| 10 | Exercise `scripts/release.sh` end-to-end in CI | **Still required** | `.github/workflows/test.yml` still runs only `pytest -q` per every full-suite run in this closure sequence's own reports |
| 11 | Redact `cron_wrap.sh`'s shell-based Telegram alert | **Still required** | `git log scripts/cron_wrap.sh` shows no commit since 2026-07-10 |

**None of these 11 items is satisfied by ADR-AF-002.** ADR-AF-002's WP1–WP4 touched
`scheduler/jobs.py`, `scheduler/scanner.py`, `monitor.py`, and `engine/agent_firm/` exclusively for
Tier 1 context wiring — confirmed by direct diff/session review, not overlapping with any of the 11
items above in either files touched or problem addressed.

---

## Part 3 — The ADR-AF-003 Finding (Central to This Reconciliation)

`ADR-AF-003-SIZING_OWNERSHIP.md` documents a **confirmed, currently-shipped defect**, not a
hypothetical design gap: `scheduler/scanner.py`'s `run_edge_veto_stage()` (line 962, active only
when `EDGE_SCORE_MODE=enforce`) and `run_agent_firm_gate()` (line 1038, active whenever Agent Firm
is active, unconditionally, for every candidate) both write `r["agent_size_hint"]`, with the second
call unconditionally overwriting the first — silently discarding a computed, validated edge score in
favor of either the LLM's own size hint or a blind default of `1.0` ("a value that encodes no
information at all," in the ADR's own words) whenever both modes are simultaneously active.

**Verified this session, not assumed:**
- `engine/position_sizing.py` (the ADR's prescribed single-writer module) does not exist.
- Both write sites (`scanner.py:962`, `:1038`) are still present, unchanged, in the current checkout.
- The Risk agent does not emit `size_tier` (grep across `risk.py`/`risk_v2.md`: zero matches).
- `EDGE_SCORE_MODE` defaults to `"off"` (`config.py:34`) — meaning the *collision* specifically
  requires an operator to have set `EDGE_SCORE_MODE=enforce` in the live `.env`. **This session has
  no live-host access and cannot confirm whether that is the current production setting** — the same
  category of caveat `FINAL_RELEASE_DECISION.md` itself applied to the webhook secret before
  resolving it via direct SSH. This is flagged as a verification gap, not asserted either way.
- Independent of that specific collision's live severity: the architecture decision itself (route all
  executable sizing through one function) is dated 2026-07-29 — **after** every 2026-07-28 document
  that named "Operations Dashboard / Job History" as the standing next milestone. Those documents
  could not have accounted for a defect that hadn't been identified yet.

**Classification: still required — decided, unimplemented, evidenced as a live code-level defect.**
This is the highest-severity unresolved item found across this entire reconciliation, and materially
informs the next-milestone recommendation in `Audit/PRODUCTION_ENGINE_NEXT_EXECUTION_PLAN.md`.

---

## Part 4 — Owner-Decision Items (Restated, Status Re-Verified)

From `Audit/OWNER_DECISION_PACKAGE.md`, cross-checked against `git log` this session:

| Decision | Recommended option | Status |
|---|---|---|
| 1. Webhook hardening | Option B (`validate_config()` enforcement) | **Not actioned** — same item as follow-up #1 above |
| 2. DB_PATH bootstrap | Option A (relax check) or B (provisioning step) | **Not actioned**, not urgent |
| 3. Restore-drill cron gap | Manual drill now + investigate root cause | **Cannot verify from repository state** — an operational action that may or may not leave a commit trace; requires operator confirmation |
| 4. Token-write hardening timing | Land as very next commit after release | **Not actioned** — contradicts its own "very next commit" recommendation, since no commit followed |

---

## Part 5 — Contradictions Found and Resolved

1. **"11 required follow-up items" vs. the more granular ~15–18 findings in the Phase 1/2/5 reports.**
   Not a contradiction — the certification's own synthesis explicitly deduplicates/consolidates
   overlapping findings (e.g., the webhook item appears in both Production Readiness and Security
   Review by design, "cross-referenced rather than duplicated"). Resolved by treating the 11-item
   numbered list as the canonical, actionable synthesis, with the phase reports as supporting detail.
2. **RC1-C2's redaction fix vs. the Final Gate pass's later redaction findings.** Not a contradiction
   — two different certification passes, at two different points in scope-broadening, found two
   different (related but distinct) redaction gaps. RC1-C2 (narrower, RC1-delta-scoped) closed before
   the Final Gate pass (whole-repository-scoped) ran and found more. Resolved by treating both as
   accurate for their own scope and stated explicitly in Part 2 above (item 7).
3. **`AF2_WORK_PACKAGE_SEQUENCE.md`'s WP4 (`ConsensusContext`) vs. the actually-delivered WP4
   (Integration Completion).** A genuine planning-document staleness, not a live contradiction in the
   system itself — resolved by this reconciliation's Part 1 classification (`AF2_WORK_PACKAGE_SEQUENCE.md`
   superseded/obsolete) and consistent with this closure sequence's own prior sessions reaching the
   same conclusion independently.
4. **"Do not implement new Agent Firm features" (this session's constraint) vs. ADR-AF-003 being an
   Agent-Firm-adjacent gap.** Not a contradiction — ADR-AF-003 is scored in Part 3 as a **defect fix**
   (removing a silent overwrite, not adding new capability), consistent with every prior certification
   in this trail treating bug fixes as distinct from feature work. This reconciliation recommends it be
   prioritized; it does not implement it.
5. **Whether `CLAUDE.md` or `docs/agent_firm/*.md` is the "current status source."** Per this task's
   own instruction, `CLAUDE.md` is treated as authoritative — and no evidence found this session
   contradicts that: `CLAUDE.md`'s 2026-07-29 amendment accurately states ADR-AF-002 is complete, and
   nothing in `docs/agent_firm/*.md` disputes that specific claim (the staleness found there is about
   *sequencing/numbering*, not about whether ADR-AF-002 itself is done).
