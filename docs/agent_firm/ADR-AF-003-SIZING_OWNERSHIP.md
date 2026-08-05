# ADR-AF-003 — Sizing Ownership (Resolves Blocker B2)

**Date:** 2026-07-29
**Status:** DECIDED. Permanent, per `AGENT_FIRM_GOVERNANCE.md`'s decision-record discipline.
**Resolves:** `AF2_IMPLEMENTATION_READINESS.md` Blocker B2 — the live, confirmed collision between two
sizing signals writing to the same field.

---

## Evidence: Every Write to `r["agent_size_hint"]`, Traced

| Order | Location | Gate | Condition | Value written | Scope |
|---|---|---|---|---|---|
| 1 | `scanner.py:962` (`run_edge_veto_stage`) | `EDGE_SCORE_MODE` | Only when `mode == 'enforce'` | `keep[r['ticker']]['size_mult']` — `round(edge, 2)` from `engine/edge_score.py::compute_edge()` | Only survivors of `apply_vetoes()`; non-survivors are filtered out of `intersection_results` entirely before reaching step 2 |
| 2 | `scanner.py:1013` (`run_agent_firm_gate`) | `engine.agent_firm.config.is_active()` | Whenever Agent Firm is active **at all** (not gated by its own `enforce` state) | `_size_map.get(r["ticker"], 1.0)` — the LLM's `AgentDecision.size_hint` if approved, **else a blind default of `1.0`** | **Every row in `intersection_results`, unconditionally** |

**Confirmed call order:** `run_edge_veto_stage()` (`scanner.py:1564`) runs strictly before
`run_agent_firm_gate()` (`scanner.py:1569`) in the same pipeline, every scan cycle.

**Overwrite behavior, confirmed by direct read:** step 2's loop (`scanner.py:1012-1013`) iterates over
*every* row in `intersection_results` and *unconditionally* assigns `r["agent_size_hint"]`, with no check
for whether step 1 already wrote a value. When both `EDGE_SCORE_MODE=enforce` and Agent Firm are active
simultaneously:
- If Agent Firm approves the ticker: step 1's deterministic `size_mult` is silently discarded and
  replaced by the LLM's `size_hint`.
- If Agent Firm does not approve the ticker (veto/degraded/bypassed/not evaluated): step 1's
  deterministic `size_mult` is silently discarded and replaced by a blind `1.0` — **discarding a
  computed, validated edge score in favor of a value that encodes no information at all.**

**No precedence rule was ever documented for this collision anywhere in the codebase or the prior AF-1
document set.** This is not a hypothetical risk; it is confirmed, currently-shipped behavior.

---

## Decision

**Exactly one component owns the executable sizing multiplier. Agent Firm never writes `agent_size_hint`
directly, at any pipeline stage, under any mode.**

### The Rule

1. **Production Engine owns executable sizing**, in a single new module: `engine/position_sizing.py`.
   This module's `resolve_size_hint()` function is the **only** code in the entire codebase permitted to
   write a final numeric value into `agent_size_hint`. `scanner.py:962` and `scanner.py:1013`'s current
   direct-write lines are both **removed** and replaced by exactly one call site.
2. **Agent Firm may only recommend qualitative confidence.** The Risk agent's LLM output changes from a
   numeric `size_hint` (0.0-1.5) to a qualitative `size_tier: "reduce"|"normal"|"increase"` — already the
   direction `AF1_REQUIRED_CONTEXT_OBJECTS.md` §5 specified, now made binding rather than merely
   recommended.
3. **`resolve_size_hint()`'s inputs, and how they combine:**
   ```
   resolve_size_hint(
       edge_score: float | None,        # engine/edge_score.py::compute_edge(), when EDGE_SCORE_MODE has run
       size_tier: str | None,           # Agent Firm's qualitative recommendation, when Agent Firm has run
       consensus: ConsensusContext | None,
       execution: ExecutionContext | None,
   ) -> float                            # bounded [0.0, 1.5] by construction
   ```
   **Precedence, stated explicitly and finally:**
   - If `edge_score` is present (i.e., `EDGE_SCORE_MODE` ran and the ticker survived its vetoes) **and**
     `size_tier` is present (i.e., Agent Firm ran and evaluated the same ticker): `edge_score` is the
     base, and `size_tier` **modulates** it within a bounded band (`"reduce"` → multiply by 0.7,
     `"normal"` → unchanged, `"increase"` → multiply by 1.15, then clamp to `[0.0, 1.5]`). Neither signal
     silently discards the other; both are inputs to one deterministic function, not two competing writers.
   - If only `edge_score` is present (Agent Firm inactive, degraded, or vetoed): `resolve_size_hint()`
     returns `edge_score` directly (rounded, clamped).
   - If only `size_tier` is present (`EDGE_SCORE_MODE=off`): `resolve_size_hint()` maps `size_tier` to a
     fixed base value (`"reduce"` → 0.5, `"normal"` → 1.0, `"increase"` → 1.2 — the same numeric bands
     `risk_v2.md` used to hardcode into the LLM's own output, now living in code instead) and returns
     that, clamped.
   - If neither is present: `resolve_size_hint()` returns `1.0` (today's existing default, preserved as
     the fallback, not silently changed).
   - **This function is called exactly once per candidate, after both `run_edge_veto_stage()` and
     `run_agent_firm_gate()` have run**, not once per stage — eliminating the two-write-sites structure
     entirely, not just documenting a winner between them.

**This directly satisfies "no silent overwrite is permitted":** there is exactly one write to
`agent_size_hint` per candidate, performed by one function, with an explicit, tested combination rule for
every input-presence combination — never a second write silently clobbering a first.

---

## Consequences

- `guardrails.py` does **not** own `resolve_size_hint()` — this corrects
  `AF1_REQUIRED_CONTEXT_OBJECTS.md` §5 and `AF1_CONTEXT_API_V2_SPEC.md`'s Tier 3 section, both of which
  placed this function in `engine/agent_firm/guardrails.py`. Per this ADR's binding instruction
  ("Production Engine owns executable sizing"), it moves to `engine/position_sizing.py`, outside
  `engine/agent_firm/` — consistent with ADR-AF-002's ownership-by-file-location principle.
- The Risk agent's prompt (`risk_v2.md`) and schema output change from `size_hint: 0.0-1.5` to
  `size_tier: "reduce"|"normal"|"increase"` — as already specified in `AF1_REQUIRED_CONTEXT_OBJECTS.md`
  §5, now finalized rather than proposed.
- `AgentDecision.size_hint` (the field on Agent Firm's own output type, `schemas.py:50`) is **repurposed**:
  it no longer carries the LLM's raw recommendation (that's `size_tier`, a new field); it carries the
  *final resolved value* `resolve_size_hint()` produced for this candidate, for audit-trail completeness
  in `agent_decisions`. This is a value-source change, not a type or field-presence change, so it remains
  MINOR-compatible per `AGENT_FIRM_GOVERNANCE.md`.

---

## Required Documentation Updates

- `AF1_REQUIRED_CONTEXT_OBJECTS.md` §5 — `resolve_size_hint()`'s owning module corrected from
  `guardrails.py` to `engine/position_sizing.py`; its signature updated to include `edge_score`.
- `AF1_CONTEXT_API_V2_SPEC.md` Tier 3 section — same correction.
- `AF1_CONTEXT_OBJECT_CATALOG.md`'s Tier 3 table — same correction.
- `AF1_REMEDIATION_PLAN.md` WP5, `AF1_IMPLEMENTATION_BACKLOG.md` WP5, `AF2_WORK_PACKAGE_SEQUENCE.md` WP9/
  WP5 — affected-files lists updated to `engine/position_sizing.py` instead of `guardrails.py`; WP5's
  scope expands to include **deleting** `scanner.py:962` and rewriting `scanner.py:1009-1013` into the
  single new call site, not just adding a new function alongside the old two.
- `AF2_IMPLEMENTATION_READINESS.md` Part 3 (Blocker B2), `AF2_RISK_REGISTER.md` R-B2/R-WP5 — marked
  resolved, referencing this ADR; R-WP5's rollback mechanism updates from "single-line revert at
  `scanner.py:1609`" to "revert to the pre-ADR two-write-site behavior via git revert of the
  `engine/position_sizing.py` introduction commit," since the two old write sites are being removed, not
  left dormant.

## Required Implementation Changes (for AF-2, not performed by this ADR)

- Create `engine/position_sizing.py::resolve_size_hint()` per the signature and precedence table above,
  with the boundary-case unit test matrix specified in `AF2_TEST_STRATEGY.md` (now additionally covering
  the `edge_score`-present/`size_tier`-absent and vice versa cases).
- Delete `scanner.py:962`'s direct write; delete `scanner.py:1009-1013`'s direct write; add one call to
  `resolve_size_hint()` after both `run_edge_veto_stage()` and `run_agent_firm_gate()` have completed for
  a given scan cycle, writing `r["agent_size_hint"]` exactly once.
- Update `risk_v2.md`'s output schema and decision framework per the `size_tier` change (already scoped
  in `AF1_PROMPT_CONTEXT_MAPPING.md`).
- The B2 regression test specified in `AF2_TEST_STRATEGY.md` (WP5) — now directly verifiable: assert
  `agent_size_hint` is written exactly once per candidate per scan cycle (e.g., via a call-count
  assertion on `resolve_size_hint()`, or a static check that the two old write sites no longer exist).
