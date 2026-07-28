# AF-1 — Failure Contract

**Date:** 2026-07-28
**Status:** these become contractual guarantees under `AGENT_FIRM_GOVERNANCE.md`'s versioning policy
— any future change to the behavior specified below is a MAJOR version change requiring explicit
sign-off, per the Governance document's compatibility policy.
**Method:** every behavior below is verified against `engine/agent_firm/firm.py`'s actual current
implementation, not designed from scratch — AF-1's job is to make existing, working fail-open
behavior into an explicit, permanent guarantee, and to specify the handful of items that aren't yet
pinned down.

---

## 1. Fail-Open (the master guarantee)

**Contract:** `evaluate`/`evaluate_staged` never raises to the caller under normal operation. Every
failure mode below resolves internally to a decision value the caller already knows how to handle
(`degraded`, or an analyst-level `"failed"` `AgentResult` that feeds into a still-produced decision).

This is not a new guarantee — it is `AGENT_FIRM_INTERFACE_SPEC.md` §4 restated as a version-governed
contract per `AGENT_FIRM_GOVERNANCE.md`'s compatibility policy: **introducing a caller-visible
exception path is always a MAJOR change requiring explicit owner sign-off**, because Production
Engine's own fail-open architecture (`run_agent_firm_gate`, `monitor.py`'s exit-veto check, both
independently verified sound in `Audit/PRODUCTION_READINESS_REPORT.md`) is built assuming this holds.

## 2. Provider Unavailable (single or both)

**Verified current behavior:** provider unavailability is handled entirely inside the provider-
routing layer (circuit breaker, quota governor) — by the time an analyst or risk agent's `run()` is
called, it receives either a real response or an internally-caught exception that becomes
`AgentResult(status="failed")`. Confirmed directly: every analyst module (e.g. `agents/technical.py`)
wraps its provider call in `try/except Exception` and returns `status="failed"` rather than
propagating.

**Contract:**
- **Single provider down, failover succeeds:** invisible to the caller — decision proceeds normally,
  `providers_used` reflects the provider that actually served the request.
- **Both providers down:** every analyst's `run()` returns `status="failed"`. The Risk agent's own
  `run()` also fails under the same condition, and `firm.py`'s own logic
  (`if result.status == "failed": decision_str = "degraded"`) is the exact, verified mechanism that
  turns this into a `degraded` `AgentDecision` with `rationale="Agent firm degraded — quant signal
  passed through"`. Confirmed by direct code read, not inferred.

## 3. Malformed LLM Response

**Verified current behavior:** at least one analyst (`technical.py`) explicitly catches
`json.JSONDecodeError` separately from the general `Exception` catch, still resolving to
`AgentResult(status="failed")`.

**Contract:** a malformed/non-parseable LLM response is treated identically to a provider failure —
it becomes a `"failed"` `AgentResult` for that agent, not a caller-visible exception, and not silently
treated as a successful-but-empty result. **AF-2 requirement:** confirm this exception-catching
discipline is consistent across *all* agent modules (`bull`, `bear`, `flow`, `news`, `regime`, `risk`),
not just the one verified here — flagged as a verification task, not assumed uniform.

## 4. Partial Consensus (some analysts succeed, others fail)

**Verified current behavior:** `_run_analysts` runs all four analysts (`technical`, `flow`, `regime`,
`news`) concurrently via `asyncio.gather` — a `"failed"` result from any one of them does not stop
the others or abort the pipeline; all four results (a mix of `"ok"` and `"failed"` is possible) feed
into `bull`/`bear`/`risk` regardless.

**Contract:**
- The pipeline **always** proceeds through bull → bear → risk, regardless of how many analysts
  individually failed, as long as the graph itself doesn't hard-fail (see §2 for the all-fail case).
- **Open item, not yet a pinned contract:** how much weight a partially-failed analyst set should
  carry in the Risk agent's own verdict is currently left to the Risk agent's own prompt/reasoning,
  not a deterministic rule. This is acceptable for AF-1 (no behavior change), but is named explicitly
  as something `AGENT_FIRM_GOVERNANCE.md`'s deprecation/versioning discipline should track if it's
  ever made deterministic later — that would be a MINOR-or-larger interface-relevant change, not an
  invisible internal tweak, since it changes how much a caller can trust a `"degraded"`-adjacent but
  technically `"approve"`/`"veto"` decision built on partial analyst data.

## 5. Deterministic Guardrails (post-LLM override)

**Verified current behavior:** `apply_guardrails()` runs after the Risk agent's own LLM-derived
decision and can override `approve → veto` on a hard flow contradiction or sub-floor confidence in a
weak regime — deterministic, not LLM-based, and keyed on analyst verdicts rather than the
scale-inconsistent raw `quant_score`.

**Contract:** guardrail overrides are a **permanent part of the decision pipeline**, not an optional
enhancement — a caller must not assume `AgentDecision.decision == "approve"` means "the LLM said
approve"; it means "the LLM said approve and no deterministic guardrail vetoed it." This distinction
matters for anyone building new logic on top of `AgentDecision` — the guardrail layer is exactly
where `AF1_CONTEXT_API.md`'s new `RiskLimits.entries_blocked` check belongs (§6 below), extending an
existing, proven mechanism rather than adding a new one.

## 6. New Contractual Requirement From the Context API (Blocker Closure, Not New Behavior)

**Per `AF1_CONTEXT_API.md`:** once `RiskLimits` is wired in, the guardrail layer must treat
`entries_blocked=True` as an unconditional veto trigger — **this is a new contractual guarantee**,
not a currently-verified existing behavior (today, Agent Firm has no visibility into this flag at
all, confirmed in the Context API document). This is the one place in this Failure Contract where
AF-2 must implement genuinely new logic rather than formalize existing behavior — flagged explicitly
so it isn't mistaken for already-working today.

## 7. Retry Behavior

**Contract (already stated in `AF1_RESPONSIBILITY_MATRIX.md`, restated here for completeness as a
failure-contract item):** Agent Firm owns all retry logic internally; the interface never expects or
requires the caller to retry. A `degraded` decision is not a signal to retry — it is a completed,
final answer for that evaluation cycle. Production Engine must not implement caller-side retry
against `evaluate`/`evaluate_staged`.

## 8. Timeout Behavior

**Status: still an open gap, not resolved by AF-1.** As already named in
`AGENT_FIRM_INTERFACE_SPEC.md` §6, no explicit per-call timeout contract exists today. AF-1 does not
close this gap — it is carried forward as an explicit AF-2 requirement: either (a) Agent Firm commits
to a hard per-`evaluate()` timeout as part of this Failure Contract, with an internal fallback to
`degraded` on timeout (consistent with every other failure mode's resolution above), or (b) the
contract explicitly states "unbounded, caller must impose its own timeout." **AF-2 must make this
choice explicitly — it is the one item in this document intentionally left as a decision for the
next milestone, not an oversight.**

---

## Summary — What Is and Isn't Resolved

| Failure mode | Contract status |
|---|---|
| Fail-open (master guarantee) | **Pinned** — verified existing behavior, now version-governed |
| Single provider down | **Pinned** — verified existing behavior |
| Both providers down → `degraded` | **Pinned** — verified existing behavior |
| Malformed LLM response | **Pinned for `technical.py`; AF-2 must verify uniformity across all agents** |
| Partial consensus proceeds | **Pinned** — verified existing behavior |
| Partial-consensus *weighting* | **Explicitly not pinned** — left to agent reasoning, flagged for future governance if ever made deterministic |
| Guardrail overrides are permanent | **Pinned** — verified existing behavior |
| `RiskLimits.entries_blocked` veto | **New requirement — not yet implemented, AF-2 scope** |
| No caller-side retry | **Pinned** — policy, not existing-behavior-verification |
| Timeout | **Explicitly unresolved — AF-2 must choose (a) or (b) above** |

Everything marked "Pinned" requires zero further owner decision. Everything else is named exactly so
AF-2 knows what's still open, rather than discovering it mid-implementation.
