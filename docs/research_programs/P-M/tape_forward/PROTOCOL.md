# Forward tape record: protocol for testing the journal's tape-reading events (FROZEN)

**Status:** FROZEN 2026-10-15 by D-098 (owner: "Approved"). Fixed-panel control (§4) NOT taken. Nothing
registered; census stays at 612. Changes only by a superseding D-entry.
**Date:** 2026-10-15 · **Origin:** owner "do your recommendation" (broaden the tape-reading monitor; item 2:
turn the recorder into evidence instead of impressions).

## 1. Why a protocol now, before any data is looked at

The jurnal26 monitor (commits `b768fb0`, `32703b1`) records every regular-board trade of the watch and held names
into `tape` (jurnal DB) and fires descriptive events. Every threshold was set on **one morning** (2026-10-15).
If outcomes are read before the definitions and the analysis are frozen, the monitor's events become one more
searched pattern (D-070 §1). This draft freezes them first.

## 2. Frozen definitions (by file hash, jurnal26 at `32703b1`)

| file | sha256 (first 16) | defines |
|---|---|---|
| `tape.py` | `4cd0dfcee3d77ad3` | session read, DIVERGE, SWEEP, tempo, book read |
| `bigplayer_watch.py` | `7bb6f27a2e9a75c6` | ABSORB, CAP, BROKEN, CAP BROKEN, FLIP, ALGO, LOCK, absorber read |
| `limit_watch.py` | `f0d5db2a3b2892b5` | ARB/ARA lock, queue drain, pre-open read |

A changed threshold creates a **new event version**; events of different versions are never pooled. The event log
is the monitor's state file plus `tape`; an event is recorded at the time the monitor saw it (no back-dating).

## 3. Events and outcomes (fixed now)

- **Events (primary set, one test each, no others added later):**
  E1 ABSORB · E2 CAP · E3 close locked at ARB (from the 16:10 verdict or the tape: last regular trade at the ARB price
  with an empty bid) · E4 SWEEP ≥ Rp 250M (sign = side) · E5 DIVERGE (sign = kind).
- **Outcome:** from the **next session's open** to the close of session **t+5**, net of 0.60% round trip, minus the
  same-window equal-weight return of the liquid cross-section (ADV ≥ Rp 5bn). Sign pre-declared: ABSORB, buy
  SWEEP, BULLISH DIVERGE → positive; CAP, sell SWEEP, BEARISH DIVERGE, ARB close-lock → negative.
- **Control (within name):** the same names on days without that event at a key level, same weekday mix.
- **Inference:** clustered by date. Long side only is tradeable on IDX; negative-sign events are recorded as
  avoid/exit information, not as short trades.

## 4. Stated limits (before any outcome)

- **Selection bias:** the recorded universe is the owner's watch list plus holdings, chosen by the owner. Within-name
  controls reduce but do not remove it. Option (owner): add a fixed panel of ~10 liquid names, recorded but not
  alerted, as an unselected control — costs ~60–100 Stockbit pages per run; the token is shared with 5001's screener.
- **Sampling:** 5-minute polls; events are only computed when a name is at a key level (positions always).
- **Data:** Stockbit running trades; broker codes absent intraday; trade times to the second, but an event is
  only seen at the next 5-minute poll.
- **Prior evidence is against several of these:** 5001's shock-absorption rule was dead; flow tests on daily
  aggregates failed (HYP-PM-0003, D-091); ARB pinning predicts continuation (HYP-PM-0008 refused, D-060); buying
  after a ≥15%/10-day drop continued lower (t −4.94).

## 5. When outcomes may be read

No outcome is read until **either** 60 trading sessions of recording **or** ≥ 100 events of a type, whichever is
later for that type. Then a G0: effect floor and 20% minimum power frozen first (D-086 stop rule), power from the
pre-event return distribution only. A type that fails the stop rule is withdrawn uncounted. A type that passes
needs a D-entry and registration (next id at that time) before its G1.

## 6. What can run now without breaking this

A **descriptive** count of ARB close-locks on 5001 daily OHLCV 2021–2026 (how often the next day continues,
flattens or rebounds) is allowed as context: HYP-PM-0008 was refused, so nothing is registered or counted, and the
result cannot be cited as evidence for E3, whose outcome window and sample are different.

**Approval:** owner 2026-10-15, "Approved" (without the §4 fixed-panel option). Recorded as DECISION_LOG D-098.
