# FWD-PM-TREND-003 — PROTOCOL (DRAFT — REGIME GATE HELPS BUT DOES NOT FULLY RESCUE THE EFFECT; NOT YET REGISTRABLE)

**Status:** DRAFT. **Not registered. No family slot consumed. Not open.**
Third in a sequence: `FWD-PM-TREND-001` (top-80, withdrawn) → `FWD-PM-TREND-002` (broad-liquid
threshold, not recommended standalone — 2025-concentrated, ex-2025 t=1.31) → this document, which
tests the follow-up `002` §6 explicitly proposed and did not build: gate the same Donchian rule
on `HYP-PM-0010`'s own registered regime classifier. **Read §6 on multiplicity before treating
this as independent evidence of anything** — it is not a fresh test, it is the third iteration
of one adaptive sequence on the same underlying signal and data.

**Drafted:** 2026-09-20 · **Spec frozen:** 2026-09-20 v1 (section 2 + `scripts/donchian3_regime.py`, SHA256SUMS)
**In-sample reference run:** 2026-09-20, local settled DB (data through 2026-07-29), output in §1

## 0. What this is, and what it is not

`FWD-PM-TREND-002` found a Donchian 20/10 trend rule on the broad-liquid threshold universe with
a statistically strong full-sample excess that was almost entirely a 2025 phenomenon (ex-2025
t=1.31, not significant) — and offered a coherent, testable explanation: 2025 was IHSG's
strongest trending year in the window (+20.7%), and an unconditional trend rule mechanically
needs a trend to work. `HYP-PM-0010`'s already-registered regime classifier
(slope/efficiency-ratio/participation) exists specifically to detect that condition. This
document tests, directly rather than by inference, whether requiring that classifier to be True
at entry closes the gap.

**It does — partially, not fully.** See §1. This is neither a clean confirmation nor a dead end.

**Construction is otherwise unchanged from `FWD-PM-TREND-002`**: same universe threshold, same
traded-days guard, same Donchian 20/10 entry/exit, same cost basis, same trade-level event-study
design (no daily book, no aggregation denominator, explicit per-ticker sequential scan for
entry/exit pairing rather than a vectorised shift), same dual benchmark, same `cluster_t`. The
regime classifier itself is reproduced verbatim from `forward_regime/scripts/ma.py` and the
frozen definition in `forward_regime/PROTOCOL.md` §2 — not re-derived, not retuned.

## 1. Evidence being pre-registered (IN-SAMPLE, no confirmatory weight)

```
FWD-PM-TREND-003 frozen event study v1 (DRAFT, in-sample reference)
universe : adv20>=Rp1e9 threshold + regime_ok gate, 952 tickers loaded, 378,851 liquid ticker-days, 39,652 liquid+regime-ok ticker-days
trades   : 1,608 raw -> 13 contaminated (excluded) -> 1,595 used; 26 still open at data end (censored, excluded)
          598 distinct tickers, 749 distinct entry dates
          top ticker UNTR = 11 trades (0.7% of total)
          median hold 33d, mean hold 44.4d
vs IHSG  : N=1,595  mean excess +6.67%  cluster-t 4.95
vs EWbook: N=1,595  mean excess +5.39%  cluster-t 4.17
ex-2025 vs IHSG: N=1,131  mean excess +1.98%  cluster-t 2.05

year-by-year (excess vs IHSG, entry-date year):
      size  mean
yr
2021   151  5.84
2022   300  2.15
2023   260 -0.68
2024   289  3.54
2025   464 18.11
2026   131 -1.04

integrity: entry<exit for all trades OK; no hygiene-excluded ticker present OK
```

**Side-by-side with the ungated `FWD-PM-TREND-002`:**

| | 002 (ungated) | 003 (regime-gated) |
|---|---|---|
| trades used | 4,508 | 1,595 (35% of 002's count) |
| vs IHSG, full-sample | +3.55%, t 4.35 | **+6.67%, t 4.95** |
| vs IHSG, ex-2025 | +0.83%, t 1.31 | **+1.98%, t 2.05** |
| 2023 (excess) | −1.89% | −0.68% (improved, still negative) |
| 2026 YTD (excess) | −0.07% | −1.04% (worse) |
| 2025 trade share | 23.6% | 29.1% (more concentrated, not less) |

The regime gate moves the ex-2025 t-stat from noise-level (1.31) to borderline (2.05) — a real,
directionally-correct improvement, consistent with the §0 hypothesis. It does **not** clear this
program's own t>2.5 promotion bar used elsewhere (`FWD-PM-FADE-001` §3,
`FWD-PM-TREND-001`/`002` implicitly), 2023 is still net negative even after gating, and 2026 YTD
got worse, not better. The 2025 trade-share also got MORE concentrated under the gate (29.1% vs
23.6%), which is expected — the classifier is supposed to fire more in a genuinely trending year
— but it means the gate has not diversified the result across years, only sharpened the
signal-to-noise within the years it does fire.

Breadth remains clean: 598 distinct tickers, top name (UNTR) only 0.7% of trades, top-10 tickers
26.2% of total positive excess contribution — not a concentration-by-name problem at any stage of
this sequence.

## 2. Frozen specification

Identical to `FWD-PM-TREND-002` section 2 (universe, traded-days guard, Donchian 20/10
entry/exit, cost, contamination guard, dual benchmark, `cluster_t`), with one added entry
clause:

| | |
|---|---|
| regime gate (added vs 002) | entry additionally requires, evaluated on data through `t-1` (lagged one session, no look-ahead — reused verbatim from `forward_regime/PROTOCOL.md` §2): `ema20(t-1)/ema20(t-11) − 1 > +0.02` (slope) **and** Kaufman `ER(20) = \|close(t-1)-close(t-21)\| / Σ\|Δclose\|(20) >= 0.30` (efficiency) **and** fraction of the last 20 closes above `ema20` `>= 0.70` (participation) |
| entry (full) | Donchian-20 breakout **and** liquid-universe gate **and** regime gate, all three simultaneously true |
| exit | unchanged from 002 — Donchian-10 channel low, **not** gated by regime or liquidity (a position holds to its channel exit even if the regime later turns off, matching both parent specs' "gates entries only" convention) |

Frozen implementation: `scripts/donchian3_regime.py` (sha256 in `scripts/SHA256SUMS.txt`).

## 3. Endpoint and decision rule — not specified

Deliberately not written. §6 explains why this document is not ready to specify a forward-test
endpoint yet, whatever the in-sample numbers show.

## 4. Expectations, stated in advance

If a future draft carries this forward, the declared expectation should be anchored to the
**ex-2025** read here (+1.98%, t 2.05), not the full-sample read (+6.67%, t 4.95) — the same
discipline `FWD-PM-TREND-002` §4 already applied, now doubly warranted since the full-sample
number is even MORE 2025-weighted after gating (29.1% of trades vs 23.6%), not less.

## 5. Open questions this document raises but does not answer

1. Is the residual 2023 shortfall (−0.68%, still negative after gating) a sign the classifier's
   thresholds (0.02 / 0.30 / 0.70) need their own tuning, or is it simply evidence that even
   genuinely-trending-by-this-definition conditions do not guarantee a positive channel-breakout
   result in every case? Retuning thresholds on the same in-sample data to fix 2023 specifically
   would be a fourth iteration of in-sample search on the same data — flagged, not done.
2. `HYP-PM-0010`'s own entry rule only fires on **episode onset** (first session regime turns
   True after being False) — this draft fires on **every session** the regime is True, a
   materially looser condition. Restricting to episode-onset-only entries is a natural, different
   test and was not run here.
3. 2026 YTD got worse under the gate (−1.04% vs −0.07% ungated) despite IHSG falling 30.3% that
   year — worth understanding before treating the gate as a strict improvement rather than a
   full-sample-weighted one.

## 6. Multiplicity — read this before using any number above

**This is not an independent test.** It is the third step of one adaptive sequence:
`FWD-PM-TREND-001` failed on its own construction bugs → `002` was built in direct response and
failed on 2025-concentration → `003` was built in direct response to `002`'s specific failure
mode, using a classifier that was itself chosen because it was already registered and already
known to exist for exactly this purpose. Each step is well-motivated and each construction is
honestly reported, but a reader who only sees `003`'s numbers without this context would
over-credit them. If any future draft in this line is proposed for registration, the multiplicity
accounting must treat `001`, `002`, and `003` as ONE family of related trials on the same
signal and data — not three independently-earned data points — and the effective search space
includes the informal "what would fix 002" reasoning in §0 of this document, which is itself a
form of researcher degrees of freedom even though no parameter here was literally re-fit to the
data. **No family slot is consumed by this draft; none should be claimed for it without that
accounting being done explicitly by whoever proposes registration.**

## 7. Registration elements (program §5.2 checklist) — not completed

Deliberately omitted. Completing this table would imply a registration recommendation this
document does not make (§3, §6).

## 8. Limitations, stated rather than buried

1. Same split-hygiene caveat as `002`: the exclusion list was audited under top-80 membership
   only; this universe has not had its own dedicated audit.
2. The regime classifier reduces the sample to 749 distinct entry dates (vs 1,090 in `002`) —
   any future power/MDE calculation must use this smaller effective cluster count, not `002`'s.
3. §5.2 (episode-onset vs every-session-true entries) is a real, unresolved design choice that
   changes what "the regime gate" even means; this draft picked the looser interpretation without
   testing the stricter one.
4. Close-fill convention (both legs), 0.60% flat round-trip cost, no slippage beyond that —
   unchanged from `001`/`002`.
5. One 5.1-year window, one market, and (per §6) not a fresh sample even within that window —
   this document's own existence was informed by `002`'s result on the same data.

## 9. Provenance

- Data: local settled DB `data/walkforward.db`, `ohlcv.is_final=1`, data through 2026-07-29.
- Spec script: `scripts/donchian3_regime.py` · SHA256SUMS: `scripts/SHA256SUMS.txt`
- Predecessors: `../forward_trend/PROTOCOL_DRAFT.md` (`FWD-PM-TREND-001`, withdrawn),
  `../forward_trend2/PROTOCOL_DRAFT.md` (`FWD-PM-TREND-002`, not recommended standalone — this
  document is its §6 follow-up, built as proposed there).
- Regime classifier source: `../forward_regime/scripts/ma.py` (formulas reproduced verbatim,
  not re-derived) and `../forward_regime/PROTOCOL.md` §2 (frozen definition, registered
  `HYP-PM-0010`).
- Session record: reviewer-directed build, 2026-09-20, direct continuation of the same session
  that withdrew `FWD-PM-TREND-001` and drafted `FWD-PM-TREND-002`.
