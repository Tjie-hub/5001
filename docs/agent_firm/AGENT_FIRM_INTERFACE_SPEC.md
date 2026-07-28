# Agent Firm — Interface Specification

**Date:** 2026-07-28
**Purpose:** Describe exactly and only what Production Engine requires from Agent Firm — the stable
contract that must survive any future Agent Firm refactor, provider swap, or repository split.
Nothing below describes *how* Agent Firm does anything (no LangGraph, no provider routing, no
circuit-breaker mechanics) — only what Production Engine may depend on. Anything not described here
is Agent Firm's internal business and may change freely without notice to Production Engine.
**Basis:** `AGENT_FIRM_DEPENDENCY_AUDIT.md` §1 — the 5 call sites classified as genuine Public API.

---

## 1. The Interface, In Full

Production Engine requires exactly two operations and one data contract from Agent Firm:

```
evaluate(candidates: list[SignalCandidate]) -> list[AgentDecision]
evaluate_staged(candidates: list[SignalCandidate]) -> list[AgentDecision]
reset_market_ctx() -> None
```

Everything else Production Engine currently reaches into (`config.set_mode()`, `analytics.*`, raw SQL
against `agent_decisions`) is **not** part of this interface — it is scoped out as internal
reach-through in the Dependency Audit and addressed as a blocker in `AGENT_FIRM_ARCHITECTURE.md`.

---

## 2. Data Contract

### Input: `SignalCandidate`

| Field | Type | Required | Meaning |
|---|---|---|---|
| `ticker` | string | yes | The instrument being evaluated |
| `strategy` | string | yes | Which Production Engine strategy/scan produced this candidate |
| `score` | float | yes | The strategy's own quantitative confidence, opaque to Agent Firm |
| `scan_time` | string | yes | When the candidate was generated |
| `regime` | string or absent | no | Market regime label, if the caller has one |
| `flow_verdict` | string or absent | no | Smart-money flow verdict, if available |
| `foreign_score` | float or absent | no | Foreign-flow score, if available |
| `indicators` | object (opaque key-value) | no | Arbitrary additional signal context — Agent Firm may use or ignore any key |

**Invariant:** `SignalCandidate` is a pure value object. Constructing one and passing it to `evaluate`/
`evaluate_staged` has no side effects on the caller's own state.

### Output: `AgentDecision`

| Field | Type | Required | Meaning |
|---|---|---|---|
| `ticker` | string | yes | Echoes the input candidate |
| `strategy` | string | yes | Echoes the input candidate |
| `scan_time` | string | yes | Echoes the input candidate |
| `quant_score` | float | yes | Echoes the input candidate's `score` |
| `decision` | one of `"approve"` \| `"veto"` \| `"bypassed"` \| `"degraded"` | yes | See §3 — the one field every caller must branch on |
| `confidence` | float or absent | no | Present only when `decision == "approve"` in the healthy path — callers must not assume presence |
| `size_hint` | float or absent | no | A position-sizing suggestion; callers that don't use sizing may ignore it entirely |
| `rationale` | string or absent | no | Human-readable explanation, safe to render directly in a report (already redaction-safe by the time it reaches the caller — see §5) |
| `providers_used` | list of strings | yes (may be empty) | Names of the provider(s) that actually served this decision — used today only for a cosmetic "provider_line" in reports, never for control flow |
| `traces`, `tokens_in`, `tokens_out`, `cost_usd`, `duration_s` | various | yes (may be zero/empty) | Cost/observability metadata — **not part of the functional contract**; a caller must never branch behavior on these fields, only display or aggregate them |

**Invariant:** `len(output) == len(input)` in the same order, one `AgentDecision` per submitted
`SignalCandidate`, always — no batching, filtering, or reordering happens inside the interface.

---

## 3. The Decision Lifecycle — The One Enum Every Caller Must Handle

```
approve  — the firm reviewed and approved; signal should proceed to whatever the caller does next
veto     — the firm reviewed and blocked; signal should NOT proceed
bypassed — the firm was disabled or kill-switched at the config level; signal proceeds unevaluated
degraded — the firm attempted review but the attempt itself failed; signal proceeds (fail-open)
```

**Invariant:** exactly one of these four values is always present on every returned `AgentDecision`.
A caller that only checks `decision == "approve"` before proceeding, and treats everything else as
"don't proceed," is **wrong** for `bypassed` and `degraded` — both of those mean "the firm did not
block this, proceed as if unevaluated," matching the existing fail-open design documented in
`CLAUDE.md`'s Architecture section. Callers must branch on all four values explicitly, or at minimum
treat `{approve, bypassed, degraded}` as "proceed" and `{veto}` as the sole "do not proceed" case.

---

## 4. Failure Behavior

**The interface never raises to the caller under normal operation.** Every documented failure mode
inside Agent Firm — a provider being unavailable, both providers being down simultaneously, a
malformed LLM response, a timeout — resolves internally to a `degraded` decision, not an exception.
This is verified, not assumed: `Audit/PRODUCTION_READINESS_REPORT.md`'s "Verified Clean" section
independently confirmed `run_agent_firm_gate`'s (the scheduler-side caller of this interface) fail-
open design is exemplary specifically because it never needs to catch an exception from this call —
the interface itself already degrades.

**What this means for a caller:** wrapping `evaluate`/`evaluate_staged` in a try/except is defensive
best practice, but the interface's own contract is that it should never need it. A caller that *does*
see an exception propagate from this interface should treat that as an Agent Firm defect report, not
expected behavior to design around.

---

## 5. What The Caller May Assume Is Already Handled (and must not re-implement)

- **Redaction:** by the time `rationale` or any other string field reaches the caller, it has already
  passed through whatever secrets might have been in play during evaluation — the caller does not
  need to (and should not) apply its own secret-scrubbing to these fields before rendering them in a
  Telegram report. (Note: this assumption is about *content* fields returned from evaluation, not
  about the general Agent Firm logging pipeline — see the Dependency Audit's finding on Agent Firm's
  own logging/redaction independence, which is a separate, still-open item.)
- **Cost/rate governance:** a caller does not need to implement its own request throttling, daily
  spend caps, or provider selection — these are entirely internal to the interface and invisible to
  the caller except through timing (see §6).
- **Retry:** the caller does not need to retry a `degraded` decision — Agent Firm's internal retry/
  failover logic (if any) has already run by the time the interface returns. A caller receiving
  `degraded` should treat that candidate as "not reviewed this cycle," not "retry me."

## 6. Timeout Behavior

**Not currently bounded by an explicit contract.** No documented, caller-facing timeout guarantee
exists today — `gunicorn.conf.py`'s `timeout = 300` bounds the *whole HTTP worker request* where
relevant, and APScheduler jobs calling this interface have no per-call timeout of their own. This is
named here as a gap in the *interface's* stability guarantee (not a defect in current behavior) —
any future Agent Firm version should either (a) document a hard per-`evaluate()` timeout as part of
this spec, or (b) explicitly declare "unbounded, caller must impose its own timeout" as the contract.
Until one of those is chosen, callers should not assume any particular latency ceiling.

---

## 7. What Is Explicitly Out of Scope for This Interface

The following are used by Production Engine today (see Dependency Audit §1) but are **not** part of
the stable interface, and Agent Firm should feel free to change them without a version bump under
this spec:
- `engine.agent_firm.config`'s module-level functions (`get_enabled`, `set_mode`, etc.) — internal
  configuration surface, currently reached into directly by `routes/backtest.py`.
- `engine.agent_firm.analytics.*` — internal reporting functions, currently called directly by
  `routes/backtest.py`'s `/api/agent/audit`.
- Direct SQL reads of `agent_decisions`/`agent_traces` from `scheduler/scanner.py` and
  `routes/backtest.py` — these should be replaced by a proper query function (or removed) before
  Agent Firm can version its schema independently.
- Any test-layer package-attribute monkeypatching (`import engine.agent_firm as _pkg; monkeypatch.setattr(_pkg, "firm", ...)`)
  — an artifact of the current lazy-import pattern, not a contract.

Closing these four gaps is exactly `AGENT_FIRM_ARCHITECTURE.md`'s blocker list.
