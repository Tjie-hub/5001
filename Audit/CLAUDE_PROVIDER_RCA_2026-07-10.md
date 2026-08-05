# Claude Provider Reliability — Root Cause Investigation

**Date:** 2026-07-10 (investigation run 18:55–19:10 WIB)
**Scope:** Why the `claude` CLI provider performed poorly during the 2026-07-10 production failover event.
**Constraint:** Investigation only. No fixes implemented, no code changed.

---

## 1. Executive Summary

The Claude CLI is **not broken**. The failures were **Claude subscription 5-hour usage-window exhaustion** ("session limit"), shared between the firm's headless CLI calls and the user's own interactive Claude Code sessions running at the same time.

Direct, non-circumstantial evidence: every failure-window session transcript in
`~/.claude/projects/-home-tjiesar-10-Projects-idx-walkforward-5001/` ends with the literal assistant message:

> **"You've hit your session limit · resets 1:20pm (Asia/Jakarta)"** (10:06 window)
> **"You've hit your session limit · resets 6:20pm (Asia/Jakarta)"** (14:35 window)

The reset times exactly predict the observed success/failure windows (see §3).

The "exit 1, empty stderr" mystery is an **observability defect in `engine/agent_firm/providers/claude.py`**: on nonzero exit the provider reads only **stderr** (`claude.py:94-100`) and discards **stdout** — but the CLI writes the limit message to stdout. Additionally, the quota regex (`claude.py:23`, matches "usage limit|quota|out of credits") would not match the actual message text "session limit" even if stdout were read. So every quota rejection surfaced as generic `ProviderUnavailable("claude CLI exited 1")`.

Headline numbers (from `provider_events`, corrected from the audit's initial read):

| Metric | Value |
|---|---|
| Actual CLI invocations during incident | 227 (not ~70) |
| Successes | **90** (6 at 10:06 WIB, 84 at 13:35–13:44 WIB) |
| Failures | 137 — all `claude CLI exited 1`, all with empty stderr |
| Circuit-open skips (no CLI spawned) | 476 |
| Timeouts | 0 |

---

## 2. Root Cause Analysis

### Primary cause — Account limitation (Confidence: HIGH)

Claude Code subscriptions meter usage in rolling **5-hour windows** shared across all sessions on the account. On 2026-07-10 the account was simultaneously running:

- heavy interactive Claude Code sessions (the operational-hardening work 09:54–10:06 WIB, then the verification audit from 13:22 WIB), and
- the firm's failover bursts (35–140 requests per burst when ZAI's circuit opened).

Evidence chain:

1. Failure transcripts carry the explicit limit message with reset times (above).
2. **Reset-time alignment** — window ending 1:20pm explains: failures at 10:06 and 11:05, then a fresh window from ~1:20pm giving **84 straight successes 13:35–13:43**, then re-exhaustion at 13:44 with the new message "resets 6:20pm", then failures at 14:35 and 16:40 (both before 6:20pm). Every episode fits one consistent quota schedule.
3. Mid-stream flip at 13:43→13:44 (success→failure with no config/env change) is characteristic of a metered cutoff, not a software defect.
4. Per-call cost is high: real firm calls processed **~35–45k tokens each** (measured from success transcripts: ~10k input + 23–35k cache-creation; prompts embed 60-day OHLCV + wf_scores; user-scope SessionStart hooks inject ~5k tokens of superpowers/claude-mem context into every headless call). The 84-call burst ≈ ~3M tokens in 9 minutes — enough to drain a fresh window in ~23 minutes even without the concurrent interactive session.

### Secondary cause — Provider error-handling configuration (Confidence: HIGH)

Not a cause of failure, but the cause of the *misdiagnosis* ("exit 1, empty stderr"):

- `claude.py:94-100` classifies errors from **stderr only**; stdout (where the CLI puts the limit message / result JSON) is discarded on nonzero exit. All 137 failures therefore collapsed to the same opaque reason string.
- `_QUOTA_PATTERNS` (`claude.py:23`) does not include "session limit", so even correct plumbing would have classified these as `ProviderUnavailable` instead of `ProviderQuotaExceeded`. The router therefore burned 2–4s per attempt rediscovering quota exhaustion every 30s circuit cooldown instead of backing off until the known reset time.

### Ruled out

| Suspect | Verdict | Evidence | Confidence |
|---|---|---|---|
| Claude CLI defect | **Ruled out** | 90 prod successes with identical flags/env; 18/18 success in controlled ladder at concurrency 1–10; stderr empty and exit 0 in all tests | HIGH |
| Concurrency | **Ruled out as failure cause** | Ladder test: 0% failure at N=1,2,5,10; failures in prod occurred also at effective concurrency 1 (circuit half-open single trials) | HIGH |
| Provider Router | **Ruled out** | Dispatch, failover ordering, semaphore(4), breaker (3 fails→OPEN, 30s cooldown, half-open single trial) all behaved per design in the event stream; 0 timeout events | HIGH |
| Operating system | **Ruled out** | ulimit -n 1,048,576; max user processes 29,723; no fork/FD errors; N=10 ran clean at load 6.58 | HIGH |
| Auth/env under systemd | **Ruled out** | 90 successes from the same service env; a clean-env (`env -i`) invocation authenticated fine | HIGH |

---

## 3. Timeline of the Incident (all times WIB = UTC+7)

| Window | ZAI | Claude | Explanation |
|---|---|---|---|
| 10:05–10:09 | 35× 429 → circuit open | 6 successes (29.9s→62.0s, semaphore queue), then 29× exit-1 → circuit open | Window's last quota drops, then exhaustion ("resets 1:20pm") |
| 11:05–11:09 | 35× 429 | 35× exit-1, 0 successes | Still inside exhausted window |
| 13:35–13:44 | 110× 429 | **84 successes** (durations up to 267s = queue wait) | Fresh 5h window from ~13:20; 84 calls ≈ 3M tokens re-exhaust it by 13:43 |
| 14:35–14:37 | 40× 429 | 40× exit-1 | Transcripts: "resets 6:20pm" |
| 16:40–16:41 | 17× 429 | 16× exit-1 | Still before 6:20pm reset |

Note: ZAI's own 429s included code 1308 "Usage limit reached for 5 hour" — **both providers were failing on the same class of 5-hour subscription windows simultaneously**, which is why the system saturated.

---

## 4. Timeline of a Single Claude Request (measured, prod flags, prod cwd, clean env)

| Stage | Time | Source |
|---|---|---|
| Process spawn + Node boot (`claude --version`) | ~0.15s | `/usr/bin/time`, 3 runs |
| CLI init: settings, plugins, SessionStart hooks (superpowers sync hook; Obsidian/Xvfb + antigravity async launchers) | ~3.0s | wall 6.50s − CLI-reported `duration_ms` 3.48s |
| CLI pre-API (session create, context assembly, hook context injection ~5k tokens) | ~1.6s | `duration_ms` − `duration_api_ms` |
| API network + inference (trivial prompt) | 1.8–2.8s | `duration_api_ms` |
| Parse + shutdown | ~0.2s | residual |
| **Total (trivial prompt, idle box)** | **6.5s** | measured |
| **Total (real firm prompt ~40k tokens, prod)** | **15–30s** | first uncontended prod successes: 29.9s, 14.7s, 20.4s |

Failure-path latency (limit rejection): **2–4s** per attempt (from event inter-arrival times) — the CLI boots, starts a session, gets the limit rejection, exits 1.

Resource cost per invocation: ~293MB max RSS, ~5.7s CPU (88% of 6.5s wall) on this 4-thread XPS-13.

---

## 5. Concurrency Analysis (measured 19:05 WIB, prod-identical flags)

| N concurrent | Success | Wall time range | API time | MemAvailable dip | Load (1m) |
|---|---|---|---|---|---|
| 1 | 1/1 | 6.5s | 1.8s | −0.25GB | 1.5 |
| 2 | 2/2 | 7.7s | 1.7–2.0s | −0.42GB | 2.0 |
| 5 | 5/5 | 15.4–17.0s | 1.6–2.6s | −0.81GB | 3.9 |
| 10 | 10/10 | 27.7–30.9s | 1.8–2.8s | −1.07GB | 6.6 |
| 20 | *not executed* | projected 55–60s | — | projected ~2.2GB | — |

- **Failures do NOT increase with concurrency: 0% at every level tested.** stderr was empty (0 bytes) on every run; all exits 0; all stdout valid result JSON.
- Latency scales ~linearly with N while API time stays flat → the bottleneck is **local CPU** (each invocation needs ~5.7s CPU; the host has 4 threads), not the API and not the CLI's process model.
- N=20 was deliberately not executed: 20×293MB against 3.5GB available with swap 83% consumed risks the OOM-killer hitting the live gunicorn worker (440MB RSS, the largest resident process). Projection: it would likely still succeed but at ~55–60s wall, brushing the 75s timeout. Irrelevant to production anyway — the provider semaphore hard-caps at 4 (`AGENT_FIRM_CLAUDE_MAX_CONCURRENT=4`).

---

## 6. Bottleneck & Resource Analysis

1. **Local CPU is the throughput ceiling**: ~5.7s CPU per invocation × 4-thread host ⇒ max sustainable ~0.5–0.7 calls/s regardless of semaphore. During the 13:35 burst the service rate was ~10 calls/min against an arrival burst of ~100 → queue wait grew linearly to **267s** on the last success.
2. **The 75s timeout does not cover semaphore queue wait** (`claude.py:75-85`: timer starts before the semaphore, but `wait_for` wraps only `communicate()`). Consequence: zero timeouts fired despite 267s end-to-end latencies. Not a failure cause; a latency-transparency gap for callers.
3. **Fixed per-call overhead**: ~3s of Node/plugin/hook startup + ~5k tokens of hook-injected context on *every* headless call. At 84 calls that is ~7 minutes of pure startup CPU and ~420k tokens of quota spent on context the firm agents don't need.
4. Memory: linear at ~100–290MB per concurrent instance; no leak observed; no OS limit approached.

---

## 7. Risk Assessment

- **Correlated failure (the big one):** the failover provider shares its quota with the human operator's interactive sessions. Claude capacity disappears precisely on days of heavy interactive use — which are exactly the days incidents get investigated. Failover reliability is therefore anti-correlated with operator activity.
- **Misclassification risk:** quota rejections raised as `ProviderUnavailable` mean the router/breaker treat a hard quota (known reset at 1:20pm) like a transient blip, retrying every 30s cooldown for hours (476 circuit-open skip events).
- **Diagnostic blindness:** stdout discard on exit≠0 means the CLI's self-explanatory error text never reaches logs or `provider_events`.
- **Both-providers-down mode is real:** ZAI and Claude both run on 5-hour subscription windows; 2026-07-10 demonstrated simultaneous exhaustion.

---

## 8. Cause Attribution (ranked)

| Rank | Cause | Probability | Evidence |
|---|---|---|---|
| 1 | **Account limitation** — Claude subscription 5-hour session limit, shared with interactive use | ~90% of failure volume, Confidence HIGH | Literal limit messages in failure transcripts; reset-time alignment across all 5 episodes; mid-stream flip; measured token burn |
| 2 | **Configuration** (provider error handling: stdout discarded, "session limit" unmatched by quota regex; hook-inflated per-call cost) | Contributor/amplifier, Confidence HIGH | Code at `engine/agent_firm/providers/claude.py:23,94-100`; measured 5k-token hook injection; all 137 reasons identical |
| 3 | Provider Router | Not a cause | Event stream shows correct dispatch/breaker/failover; 0 timeouts |
| 4 | Claude CLI | Not a cause | 90 prod successes; 18/18 controlled ladder; 0-byte stderr is CLI convention (errors to stdout), not malfunction |
| 5 | Operating System | Not a cause | Limits ample; N=10 clean |

---

## 9. Alternatives Comparison (estimate only — no migration performed)

| Option | Expected reliability | Trade-offs |
|---|---|---|
| **Current CLI (subscription)** | High *when quota available*; hard-fails correlated with interactive usage; ~3s + ~5k tokens overhead per call | $0 marginal cost; quota shared with operator; opaque errors unless stdout parsed |
| **Claude Agent SDK (subscription auth)** | Same quota ceiling as CLI (same account window); removes per-call process boot (~3s) and can drop hook injection | Engineering effort; does not fix the root cause |
| **Claude API (metered key)** | Highest: dedicated rate limits independent of the operator's interactive sessions; no local process/CPU bottleneck; structured 429s with retry-after | Per-token cost (real firm calls ≈ 40k tokens ⇒ roughly $0.10–0.15/call at Sonnet API pricing, ~$10–15 per 100-call burst); needs spend controls |

---

## 10. Final Recommendation

**OPTIMIZE CURRENT CLI.**

Justification from measured evidence:

- The CLI itself was 100% reliable at every tested concurrency and 90/90 successful in production whenever quota existed — there is no CLI defect to migrate away from, so MIGRATE TO SDK/API is not justified by *reliability of the mechanism*.
- KEEP CURRENT CLI as-is is not acceptable either: measurement shows concrete, quota-relevant waste (≈5k injected hook tokens + ~3s startup per call) and an error-handling path that provably discarded the diagnosis for all 137 failures.
- DO MORE INVESTIGATION is unnecessary: the root cause is identified with direct evidence, not inference.

Optimization targets identified by this investigation (for a future, separately-approved change — **not implemented here**): read stdout on nonzero exit and add "session limit" to the quota patterns so the router can back off until the stated reset time; strip user-scope hooks/context from headless firm calls (e.g. a dedicated minimal settings file) to cut per-call quota burn ~10–15%; consider counting semaphore queue wait against a deadline so burst callers see honest latency.

**Caveat (explicit):** optimization extends but cannot eliminate the shared-quota ceiling. If firm call volume grows, or correlated operator/failover exhaustion is deemed unacceptable for capital decisions, the structural fix is a metered API key for the firm (isolating its capacity from interactive use) — that is a cost/business decision, flagged but not chosen, because at current volumes a fresh 5-hour window demonstrably absorbed an entire 84-call burst.

---

## Appendix — Evidence Inventory

- `data/walkforward.db :: provider_events` — 1,613 events 02:48–09:41 UTC; per-episode breakdown in §3.
- Failure transcripts (limit message): e.g. `~/.claude/projects/-home-tjiesar-10-Projects-idx-walkforward-5001/0baf62db-*.jsonl` (10:06 window), `124a7555-*.jsonl`, `151897f5-*.jsonl` (14:35 window).
- Success transcripts with token usage: `11ab55e0-*.jsonl` (10.8k in / 23.5k cache-create), `3ea12adf-*.jsonl` (9.7k / 34.9k).
- Controlled ladder raw data: session scratchpad `conc/results.txt` + per-run stdout/stderr captures.
- Code inspected: `engine/agent_firm/providers/{claude,router,events,factory,circuit_breaker}.py`, `engine/agent_firm/config.py`.
- Host: XPS-13-9343, 4 threads, 8GB RAM, claude CLI 2.1.206, `ulimit -n` 1,048,576.

### Side findings (out of scope, flagged for the user)

1. **Stale system-level unit `idx-walkforward-5001.service` is in `failed` state** (exit-code, restart-limited, since 09:54 WIB) and still `enabled`. Production is actually served by the *user-level* `idx-walkforward.service` (gunicorn, healthy, port 5001 → HTTP 200). The dead system unit points at the same symlink path and will keep flapping/confusing monitoring; consider disabling it.
2. Swap is 83% consumed (723MB free of 4GB) on the production host.
3. `agent_traces` today: 66 rows attributed `claude` vs 90 successes — attribution now works but is not 1:1 with provider successes.
