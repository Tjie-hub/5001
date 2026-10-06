# Practice note — managing your sniper positions (one page, plain language)

*From the exit & position-management study, run once on 2026-10-06 over 3,682 real fills of
your sniper setup (trend + support-zone limit at the zone top), 2001–2026, split into a
discovery era (to Sep-2021) and a confirmation era (Oct-2021–Sep-2026). Every number nets of
0.60% round-trip costs. This is decision support for your own trading, not a claimed edge.*

## 1. Which stop?

**Keep a stop — but for survival, not for return.** No exit variant reliably beat the simplest
rule of all (hold 20 sessions, no stop) on average returns — your current plan (stop below the
zone, target at the resistance) scored t −2.0 in the discovery era and +1.5 in the
confirmation era: neither era clears the pre-agreed bar, so "no reliable difference". BUT:
the simulations without a stop produced unbounded loss tails — under disciplined 1%-risk
sizing the no-stop portfolio went bust twice. The stop converts a small-win/big-loss profile
into a many-small-swings profile (win rate 48% → 55%) without changing the average. **Verdict:
keep the structure stop exactly where it is; expect it to control ruin, not to add return.
Don't switch to a wider 2·ATR stop — same "no reliable difference", same busted portfolio.**

## 2. Average down?

**No.** Adding 50% more at one ATR below entry (same stop) left the win rate exactly where it
was (54.0%), made the worst 5% of trades marginally less bad (−17.4% → −16.0%), and nudged
per-trade expectancy from −0.015R to −0.002R — a cost-averaging artifact that fails the
confirmation-era test (t +1.5 < 2.0). It doubles your exposure exactly when the trade is
going wrong. **Don't adopt it.**

## 3. When to take profit?

**The one change this study recommends: trade swing lots (P4).** The rule: after your core
position closes ≥ entry + 1 ATR, place a limit order for a half-size top-up at entry − 0.5
ATR (a pullback); when it fills, sell that lot at its own entry + 1.5 ATR (or with the core
if the stop/target hits first). This was the only variant out of twelve that beat its
baseline in BOTH eras with the pre-agreed significance (t +4.3 discovery, +3.2 confirmation),
and it did the same on RANDOM entries — meaning it's the trade management that works on these
liquid names (buy the pullback after a thrust, sell the rebound), not the sniper entry
itself. Effect size: per-trade expectancy −0.002R → +0.125R in the discovery era; in the
confirmation era it flips you from slightly negative (−0.04R) to breakeven (+0.004R).

## 4. Change the jurnal26 sniper defaults?

**The zone/stop/target levels: no.** They were re-derived in this study to match your
watchlist code exactly (58 of 61 live setups identical; the 3 that differ are rounding or the
5-bar pivot edge — recorded in VERDICT §Disclosures). **The procedural change to consider is
only the P4 swing-lot overlay above.** If you adopt it, that's a candidate D-entry in your
decision log; the study files nothing itself.

## Honest caveats

The confirmation era (Oct-2021→) is a weak regime for this whole style: your entry beat
random-entry controls strongly in the discovery era (t +4.2) but only weakly since 2021
(t +1.1), and random entries lose money under identical management. Twelve variants were
tested against pre-set thresholds — roughly one threshold in twenty can false-positive by
chance, which is why only the variant that passed in both eras AND on both entry populations
is being recommended. One run; no re-runs; numbers live in `RESULT_20261006T142027Z.json` and
`VERDICT.md` on `research/exit-study-2026-10`.
