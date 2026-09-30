# D-066 PROPOSAL — retire NR7_BULL from SHADOW · 2026-09-30

**Status:** PROPOSAL — for Owner decision. File only; `registry/edge_registry.yaml` is not
edited here (write boundary). Nothing in `DECISION_LOG.md`, `CENSUS_UPDATE.md`, or any manifest
is touched.

## What's being proposed

`registry/edge_registry.yaml`'s `NR7_BULL` v2 entry (`status: SHADOW`, approved 2026-08-19,
demoted from v1's APPROVED under D-029 for failing the Evidence Model's C3/E5+X3 capital bar)
should move from **SHADOW to RETIRED**.

## Evidence

**P4-1 (`fix/p4-evidence-honesty` 46656f6, 2026-09-30):**
`research/studies/nr7_generalization_study.py`'s `liquid_universe()` filtered the whole 5-year
generalization study by *today's* ADV rather than gating each trade at its own entry date —
look-ahead bias, both toward tickers currently liquid and away from tickers that have since gone
illiquid. Corrected:

| | before (buggy) | after (P4-1) | after (P4-1 + P4-6 liquidity-scaled costs) |
|---|---|---|---|
| T1 pooled exp | +0.099%/trade, N 1337 | −1.150%/trade, N 899 | −1.298%/trade, N 899 |
| T2 chronological CV | **PASS** (retention 0.74) | **FAIL** (retention −1.90) | **FAIL** (retention −2.05) |
| T3 BULL regime | **PASS** (+1.44%) | **FAIL** (−0.35%) | **FAIL** (−0.52%) |
| Decision | DO-NOT-WIDEN | DO-NOT-WIDEN | DO-NOT-WIDEN |

The DECISION was already DO-NOT-WIDEN before correction (T1 never cleared +0.50%), so this isn't
a new failure — but the two signals that DID pass locally (T2's chronological retention, the BULL
regime stratum) were **look-ahead artifacts**, not edge. NR7_BULL's original v1 APPROVED status
(2026-07-04) and its worked "positive edge" framing (`scheduler/scanner.py`'s own comment: "Only
NR7 Breakout showed positive edge") predate this correction and rest in part on evidence that no
longer holds under an honest re-measurement.

**P4-6 (same commit range):** flat 0.10%/leg slippage doesn't scale with the mostly-illiquid
roster NR7 was tested against; liquidity-scaled costs (opt-in, `research/nr7_study.py`) push the
already-failing T1/T3 numbers further negative, not closer to passing.

**Combined with prior evidence already in the registry:** v1→v2's own D-029 demotion already
found NR7_BULL's worked-example score (K3/K4/E3-ish/C1/X2) concludes "No capital" under the
Evidence Model's C3 gate. P4-1/P4-6 remove the one piece of evidence (the generalization study's
local passes) that could have argued for restoring capital status — it now argues the opposite.

## Where NR7 still surfaces (code read, 2026-09-30 — this is why RETIRED, not just "leave it in SHADOW")

SHADOW is not dormant in this codebase. From a direct read of `scheduler/scanner.py`,
`scheduler/jobs.py`, and `engine/strategies.py` on `research/new-order-2026-09-30`:

1. **Scanner dispatch** — `scheduler/scanner.py:807,810`: `'NR7 Breakout'` is present in
   `_REGIME_STRATEGY_MAP['BULL_MODERATE']` and `['BULL_STRONG']`, and is **not** in
   `_DEFAULT_DISABLED` (scanner.py:839) — unlike its sibling `'Inside Bar Breakout'`, which is
   disabled. A comment at scanner.py:802-805 claims "Inside Bar Breakout / NR7 Breakout removed
   2026-07-02 ... no live checker" — **this is stale for NR7**: `engine/strategies.py:1303`
   registers `'NR7 Breakout': lambda ticker, df: check_nr7_signal(df)`, a real live checker
   (`check_nr7_signal`, `engine/strategies.py:936+`). NR7 actively generates live BUY signals
   today.
2. **Telegram** — `scheduler/scanner.py:1559-1571`: a dedicated alert path fires
   `engine.phase5_watch.nr7_signal_alert_msg(ticker, n)` specifically when an NR7 signal clears
   flow confirmation, with its own comment: *"the one approved edge — fires live; the GO/NO-GO
   clock runs on these."* That framing is itself stale (v1's APPROVED status was demoted to
   SHADOW under v2/D-029, 2026-08-19, before this comment's own timestamp) and should be revisited
   regardless of this proposal's outcome.
3. **Scheduler / regime-band watch** — `scheduler/jobs.py:2114-2161`: a daily post-EOD job
   ("Phase 5 ... daily post-EOD regime-band check for the NR7 ... phase5_regime_state") calls
   `approved_universe("NR7 Breakout")` and sends its own loud Telegram alert ("NR7-eligible now:
   N/M") the moment market regime conditions would let NR7 trade.
4. **Paper trade** — no NR7-specific code in `paper_trade.py` (it is strategy-agnostic); any NR7
   signal that clears the checker and scanner dispatch flows into paper trading generically,
   tagged `'NR7 Breakout'`, same as any other live-dispatched strategy.

**Consequence:** a SHADOW-status strategy in this repo still fires live signals, sends live
Telegram alerts framed as "the one approved edge," and runs a dedicated daily watch job — SHADOW
here means "not sized with real capital," not "quiet." Downgrading the registry status without
also addressing scanner.py:802's stale comment and the phase5_watch alert copy would leave
NR7_BULL sending live "approved edge" alerts under a RETIRED registry entry — an inconsistency
worth flagging to whoever implements this proposal, not something this file (a proposal, not a
code change) fixes itself.

## What RETIRED should mean here (for the Owner's decision, not decided here)

Not decided in this proposal — options for the implementer once the Owner signs off:
- Remove `'NR7 Breakout'` from `_REGIME_STRATEGY_MAP` and add it to `_DEFAULT_DISABLED`
  (stops live signal generation and the Telegram alert path that depends on a dispatched signal).
- Retire or gate `scheduler/jobs.py`'s phase5 regime-band watch job separately, since it alerts
  independently of dispatch via `approved_universe("NR7 Breakout")`.
- Correct or remove the stale "one approved edge" framing in `engine/phase5_watch.py`'s alert
  copy regardless of the registry outcome, since it already misrepresents the current (SHADOW,
  pre-this-proposal) status.

## Owner decision requested

Move `NR7_BULL` from SHADOW to RETIRED in `registry/edge_registry.yaml` (new version entry per
the file's own immutability convention — status changes are new versions, not edits to existing
ones), citing P4-1/P4-6 as the evidence this proposal records. Direct the implementer to also
address the three live-surface inconsistencies above so RETIRED is not silently contradicted by
a still-alerting scanner/job/Telegram path.
