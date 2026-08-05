# ADR-AF-004 (Versioning Contract) — Implementation Report

**Date:** 2026-07-29
**Basis:** `docs/agent_firm/ADR-AF-004-VERSIONING_CONTRACT.md` (Status: DECIDED, permanent) — read
in full and treated as the single source of truth, per this task's instruction.

---

## Executive Summary

ADR-AF-004 resolves Blocker B4: whether adding Tier 1 context (ADR-AF-002) to the Agent Firm's
evaluation call is a MAJOR change (a new `evaluate()` parameter) or MINOR (new optional
`SignalCandidate` fields). The decision affirms `AGENT_FIRM_GOVERNANCE.md`'s existing,
already-stricter rule for `evaluate`/`evaluate_staged`/`reset_market_ctx` signatures (any
signature change, even additive/optional, is MAJOR) without amendment, and classifies the actual
migration as MINOR because it never touches those signatures at all — Tier 1 context and
ADR-AF-003's `size_tier` both live on `SignalCandidate`/`AgentDecision` as new optional fields
instead.

**This ADR's own "Required Implementation Changes" section names exactly three items — all three
were already fully implemented by the ADR-AF-002 (WP1-4) and ADR-AF-003 sessions that preceded this
one.** This implementation pass is therefore primarily a **verification and permanent-regression-
guard** exercise, not new feature work: every requirement was independently re-confirmed against the
current codebase (not assumed from prior session memory), and the one gap found — no automated test
previously locked in the signature-stability guarantee this ADR's entire classification rests on —
is closed with a new, dedicated test suite. Two minor, pre-existing deviations between the ADR's
illustrative prose and the actual implemented code were found and are documented below, with
justification for why they do not block or contradict the ADR's decision.

---

## Files Modified

| File | Nature of change |
|---|---|
| `tests/agent_firm/test_versioning_contract.py` | **New.** The only file this session adds or modifies. Automated, permanent enforcement of ADR-AF-004's central claim: exact signature snapshots for `evaluate`/`evaluate_async`/`evaluate_staged`/`evaluate_staged_async`/`reset_market_ctx`, a failure-path test proving the signature is closed (rejects unexpected kwargs), an end-to-end backward-compatibility test using a pre-ADR-AF-002-shaped `SignalCandidate`, and direct regression tests for Blocker B4 (Tier 1 fields and `size_tier` must live on the data classes, never as `evaluate()`/`risk.run()` parameters) |

**No other file was modified.** All three items in ADR-AF-004's "Required Implementation Changes"
section were verified, by direct code read this session (not recalled from a prior session), to
already be satisfied:

1. `SignalCandidate` already carries all eight Tier 1 optional fields (`technical`, `flow`,
   `regime_context`, `news`, `market`, `portfolio`, `risk_limits`, `execution`) — delivered by the
   ADR-AF-002 work package sequence.
2. `AgentDecision` already carries `size_tier` (optional), and `size_hint`'s docstring already
   documents its repurposed meaning per ADR-AF-003 — delivered by the ADR-AF-003 implementation
   session; re-read this session and confirmed current.
3. `evaluate`, `evaluate_staged`, `evaluate_async`, `evaluate_staged_async`, and `reset_market_ctx`
   in `engine/agent_firm/firm.py` all have exactly the same parameter lists they had before any of
   this work began (`(candidates, client=None)` for the four evaluate-family functions; zero
   parameters for `reset_market_ctx`) — verified by direct `inspect.signature()` introspection this
   session, not by reading the diff history.

No code change was needed to satisfy any of these three items — they were already correct.

---

## Detailed Implementation Notes

### What this session actually did

Given the three required implementation changes were already satisfied, this session's substantive
work was:

1. **Read ADR-AF-004 in full** (not just the portion read in a prior session) to identify every
   requirement precisely, including the "Consequences" and "Required Documentation Updates"
   sections.
2. **Independently re-verified each of the three "Required Implementation Changes"** against the
   current repository state via direct file reads and `inspect.signature()` calls — not assumed from
   the fact that prior sessions claimed to have done this work.
3. **Identified two deviations** between the ADR's illustrative prose and the actual implemented
   code (documented in full below) and determined neither blocks or contradicts the ADR's actual
   decision.
4. **Wrote a new, dedicated test suite** that did not previously exist: no test anywhere in the
   repository directly asserted the exact parameter lists of `evaluate`/`evaluate_staged`/
   `reset_market_ctx`, which is the specific, falsifiable technical claim this ADR's MINOR
   classification depends on. Existing tests (`tests/agent_firm/test_schemas.py`) covered
   field-level backward compatibility (new optional fields default to `None`) but not
   signature-level stability of the functions themselves — a real, previously-unguarded gap,
   now closed.

### Why no source code change was required

ADR-AF-004 is explicit that its "Required Implementation Changes" section describes work "for AF-2,
not performed by this ADR" — i.e., the ADR is a decision *about* an implementation that either
already happened or was about to happen in the same work package sequence, not a trigger for new
implementation on its own. Since that implementation (ADR-AF-002's Tier 1 fields, ADR-AF-003's
`size_tier`) was completed and independently certified in the immediately preceding sessions of this
same sequence, there was no remaining code change for this ADR to require. This is consistent with
the task's own instruction to "implement only those required changes" — implementing something
already correctly implemented would be exactly the kind of unrelated/speculative work the
constraints prohibit.

---

## Intentional Deviations (documented, not invented solutions to a blocking conflict)

Per this task's instruction to stop and document rather than invent a solution when the ADR is
internally inconsistent — neither of the two items below rises to that level (both are traceable,
justified, and were correct engineering decisions made during the original ADR-AF-002/003
implementation, not new choices made in this session), but both are real discrepancies between the
ADR's written text and the actual code, and are recorded explicitly rather than silently passed over.

### Deviation 1 — `SignalCandidate.regime_context`, not `.regime`

ADR-AF-004's own text (line 39) describes the new field as `.regime: RegimeContext | None`. The
actual implemented field name is `regime_context`.

**Why this is not a blocking inconsistency requiring implementation to stop:** `SignalCandidate`
already had a **pre-existing, unrelated field literally named `regime`** (`Optional[str]`, the
legacy quant-pipeline regime tag — e.g. `"BULL"`, set directly by scanner.py/jobs.py callers,
consumed by `_candidate_summary()` helpers across every specialist agent) **before ADR-AF-002's Tier
1 work began.** A Pydantic model cannot have two fields sharing one name with different types —
literally implementing the ADR's prose (`regime: RegimeContext | None`) would collide with, and
break, this already-existing, still-actively-used field. Naming the new field `regime_context`
instead was the only way to add the new `RegimeContext` object without deleting or renaming the
pre-existing `regime: Optional[str]` field, which this task's own "preserve existing behavior unless
the ADR explicitly changes it" instruction forbids doing anyway (the ADR never mentions removing or
renaming the legacy `regime` field). This is a documented imprecision in the ADR's illustrative
prose relative to the schema as it already stood, not a defect in the implementation, and not
something this session's constraints permit "fixing" by renaming the working field to match the
prose (that would be the actual violation — breaking a tested, working field to chase a document's
casual mention).

### Deviation 2 — `AgentDecision.size_tier: Optional[Literal["reduce", "normal", "increase"]]`, not `Optional[str]`

ADR-AF-004's text (line 91) describes the new field as `size_tier: Optional[str] = None`. The actual
implemented type (per ADR-AF-003, verified unchanged this session) is the more specific
`Optional[Literal["reduce", "normal", "increase"]]`.

**Why this is not a blocking inconsistency:** a `Literal` of three string values is a strict
subtype of `str` — every valid `size_tier` value satisfies "is a string." The more specific type adds
input validation (already exercised by `test_agent_decision_rejects_invalid_size_tier`, from the
ADR-AF-003 session) that a bare `Optional[str]` would not provide, without changing the field's
presence, optionality, or serialized JSON shape (still a plain string or `null` on the wire) — the
MINOR-classification logic ADR-AF-004 cares about (new optional field, zero impact on existing
callers) is identical either way. This reads as the ADR's prose using `str` loosely to mean
"a qualitative string enum," not as a literal type mandate in tension with better, already-tested
engineering.

**Neither deviation contradicts ADR-AF-004's actual decision** (the MINOR classification, and the
"no `evaluate()` signature change" requirement) — both are documented here for the record, per this
task's own instruction, rather than silently left for a future reader to rediscover.

---

## Test Coverage Added

All in `tests/agent_firm/test_versioning_contract.py`:

| Category | Tests |
|---|---|
| **Normal behavior** | Exact parameter-list snapshot for `evaluate`, `evaluate_async`, `evaluate_staged`, `evaluate_staged_async` (parametrized, 4 tests); `reset_market_ctx`'s zero-argument signature; `client`'s default-`None`/optional status |
| **Boundary condition** | A `SignalCandidate` constructed with exactly the pre-ADR-AF-002 field set (no Tier 1 context, no size_tier-adjacent anything) evaluated end-to-end through `evaluate_async()` with zero call-site changes — the direct, executable proof of the ADR's central backward-compatibility claim |
| **Failure path** | `evaluate()`/`reset_market_ctx()` both raise `TypeError` on an unexpected keyword argument — proving the signature is closed, not silently `**kwargs`-permissive (which would let a future MAJOR change hide inside what looks like a compatible call) |
| **Regression case for the issue the ADR resolves (Blocker B4)** | Two tests asserting the eight Tier 1 fields and `size_tier` are reachable only via `SignalCandidate.model_fields`/`AgentDecision.model_fields`, and are disjoint from `evaluate()`/`evaluate_staged()`/`risk.run()`'s own parameter sets — the executable form of "this migration is designed not to need the MAJOR rule" |

11 new tests total.

---

## Test Results

Run via the Windows checkout's `.winvenv` interpreter (`DB_PATH=data/walkforward.db
AGENT_FIRM_ENABLED=true TAVILY_API_KEY= .winvenv/Scripts/python.exe -m pytest ...`).

| Suite | Result |
|---|---|
| `tests/agent_firm/test_firm.py` + `tests/agent_firm/test_versioning_contract.py` (new) | **15 passed, 0 failed** |
| Full Agent-Firm/scanner/sizing/context-wiring surface (14 files, including every file touched across the ADR-AF-002/003/004 sequence) | **344 passed, 0 failed** — exactly the prior 333-test baseline (post-ADR-AF-003) plus these 11 new tests |
| Full repository suite (`pytest -q --ignore=tests/agent_firm/providers`) | **1620 passed, 44 failed, 9 errors** — **identical 44-failed/9-error set** to every prior baseline in this sequence (`test_value_format.py`, `security/test_release_scripts.py`, `test_auto_token.py`, `security/test_secret_hygiene.py`, `test_config_validation.py`, `test_cron_contract.py`, `test_logging_config.py`, `test_news_filter.py`, `test_stockbit_fetcher_ensure_valid_token.py`, `test_experiment_tracking.py`, `regime/test_storage.py` — all pre-existing Windows-local-tooling artifacts, none touching Agent Firm/versioning code); **+11 passed** vs. the prior baseline of 1609, exactly the 11 new tests this change adds |

---

## Regression Analysis

**Zero regressions.** The full-suite delta (1609 → 1620 passed, 44 failed / 9 errors unchanged in
both count and identity) is accounted for exactly by the 11 new tests added — no pre-existing test's
outcome changed, and no new failure category appeared. This is consistent with the fact that no
production code was modified this session: the only file changed is a new, additive test file.

---

## Remaining Follow-Up Items (outside this ADR's scope)

- **`AF1_CONTEXT_API.md`'s "Open Item for AF-2" section** — ADR-AF-004's own "Required Documentation
  Updates" asks for a one-line pointer to this ADR as the superseding resolution. Not performed this
  session, consistent with every prior session in this sequence's explicit, established deferral of
  `docs/agent_firm/*.md` planning-corpus reconciliation (first flagged in the ADR-AF-002 WP2 report,
  re-confirmed in the WP4 and final-audit sessions) — this is a documentation-only, non-blocking
  change to a large, already-known-stale planning corpus, not a code requirement.
- **The two documented deviations above** (`regime_context` vs. `.regime`; `Literal[...]` vs. `str`)
  are not "follow-up work" in the sense of something that needs fixing — they are correct as
  implemented. Listed here only so a future reader auditing ADR-AF-004 against the codebase does not
  mistake them for an unaddressed gap.
- No other follow-up items were identified. This ADR's scope is fully closed.
