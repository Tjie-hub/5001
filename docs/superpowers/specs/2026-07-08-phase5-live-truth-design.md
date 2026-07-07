# Phase 5 — "Live Truth" Design Spec

**Date:** 2026-07-08
**Status:** design approved, pending spec review
**Context:** Phases 1–3 remediation complete; Phase 4 research closed (only NR7_BULL has
edge, registry-governed since M1). `paper_trades` has **zero rows ever** — nothing the
system "knows" has been proven against real execution. Phase 5 bridges that gap.

## Objective

Prove the one approved edge (NR7_BULL, backtest +1.18%/trade net in BULL) works
**end-to-end live**, then accumulate realized-vs-backtest evidence to a pre-registered
GO/NO-GO capital decision. Active work is small (a drill + instrumentation + a tracker);
the phase then runs passively as the market supplies BULL regimes.

## Why a fire drill first

The NR7 signal→trade path crosses **seven serial gates that have never fired together**:
registry universe → BULL_MODERATE/STRONG regime map → `check_nr7_signal` → flow gate →
edge veto stage → agent firm gate → `check_trend=='UPTREND'` → `open_trade` → monitor
kernel exits. Audit C-1's lesson is that unexercised paths fail silently. Waiting for a
real BULL signal to discover a disconnect would waste the rarest resource we have
(NR7 fires ~15–25×/year).

## Deliverable 1 — Fire drill: durable e2e test

`tests/test_nr7_live_pipeline_e2e.py` — permanent suite member (C-1 regression guard).

**Fixture:** a temp DB with one synthetic ticker (e.g. `DRILL`) + `IHSG`, crafted to pass
every gate *honestly* (no gate is stubbed out):
- ~250-bar uptrend such that `detect_regime` → `BULL` with ADX in the MODERATE band;
- an NR7 setup on the decision bar: narrowest 7-day range, then breakout close above the
  NR7 high with a volume spike (per `strategy_nr7_breakout` / `check_nr7_signal` logic);
- price shape satisfying `check_trend` → `UPTREND`;
- a **test registry** (tmp-path `edge_registry.yaml` + artifact) whose frozen universe
  contains `DRILL`, loaded via `engine.registry_loader` with `_reset_cache()` isolation;
- `wf_edge`/config tables minimally populated as the scan requires.

**Mock boundary — network seams ONLY:**
- flow batch fetch → returns a confirmed score above threshold;
- agent firm → inactive (or explicit approve) via its config;
- Telegram → captured list;
- keystats/news/sector externals → neutral fallbacks (their gates already fail open by design).

**Real code under test:** regime detection + ADX sub-banding, `check_nr7_signal`, the
flow/edge/firm gate code paths, `check_trend`, `open_trade` (lot sizing off actual stop
distance, aggregate cap), signal persistence, then the monitor pass over subsequent
fixture bars driving a kernel exit and `close_trade` net P&L.

**Assertions:**
1. A `paper_trades` row exists with `strategy='NR7 Breakout'` and ticker `DRILL`.
2. Lots × stop-distance ≈ configured risk (sizing contract, audit C-2).
3. After appending exit-triggering bars and running the monitor: trade closed with an
   exit reason from the kernel taxonomy and **net** P&L consistent with the cost model
   (0.60% round trip).
4. Telegram capture includes the trade-open notification path (proving alert wiring).

If the real pipeline cannot be driven through the actual scan entrypoint without
unreasonable stubbing, the test may drive the documented stage functions in scan order
(selector → checker → gates → auto-trade block → monitor) — but each stage must be the
*production function*, never a reimplementation. Preference: the real scan entrypoint.

## Deliverable 2 — First-signal instrumentation (production, tiny)

- **BULL-watch (daily, state-change only):** after the EOD scan, compute the regime band
  for the 35 governed tickers; Telegram only when a name **enters or leaves** an
  NR7-eligible band: `🟢 PHASE 5: <ticker> entered BULL_MODERATE — NR7 eligible (N/35
  now eligible)`. State persisted (small table or file) so no daily spam.
- **Signal alert:** when a saved BUY signal's strategies include `NR7 Breakout`, send a
  distinctive `🎯 PHASE 5: NR7 live signal #<n> — <ticker>` Telegram. Counter from
  `scheduled_signals`.
- Both are additive lines beside existing jobs — no gate/threshold changes.

## Deliverable 3 — GO/NO-GO tracker (research-side)

`research/studies/phase5_tracker.py` — on-demand CLI (research reads the production
ledger; the architecture's allowed direction). Reports for `strategy='NR7 Breakout'`
paper trades: N closed, realized **net** expectancy %/trade, win rate, avg win/loss,
exit-reason mix, and the verdict under the pre-registered rule. Prints backtest
reference (+1.18%, N=346, 54% win) alongside.

## Pre-registered GO/NO-GO rule (frozen here — no post-hoc adjustment)

| Condition | Verdict |
|---|---|
| N ≥ 15 closed AND realized net expectancy ≥ **+0.50%/trade** | **GO** — deploy small real capital |
| N ≥ 15 closed AND realized net expectancy ≤ **0.00%** | **NO-GO** — edge did not survive live fills |
| N ≥ 15, between 0 and +0.50% | **EXTEND** — observe 10 more closed trades, re-evaluate once |
| < 15 closed after **6 months** (from first SHADOW-eligible day, 2026-07-08) | decide on available evidence with explicit low-N caveat |

Reference: backtest +1.18%/trade net (N=346, BULL). The +0.50% bar deliberately allows
~half the backtest edge to be lost to real-world friction before GO.

## Success criteria / definition of done (active part)

- e2e drill green in the suite and in CI; proves a paper trade opens, manages, closes.
- BULL-watch + signal alert live in production (deployed, verified in log).
- Tracker runs against the prod DB and prints the (currently N=0) status + rule.
- Memory updated with the frozen rule + start date.

## Out of scope

- Real-money order routing/brokerage integration (that is *after* GO).
- Dashboards; any change to NR7 logic, thresholds, regimes, or universe.
- Forcing signals (no regime-gate loosening to "speed up" Phase 5 — the wait is the test).
