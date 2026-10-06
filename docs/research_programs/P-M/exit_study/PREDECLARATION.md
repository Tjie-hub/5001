# PREDECLARATION — exit & position-management practice study on the owner's sniper entry

**Status:** frozen before any outcome is read · **Date:** 2026-10-06 ·
**G0-bis re-freeze:** 2026-10-06 (planner review, before any outcome read — see §3) ·
**Authority:** brief `ZCODE_BRIEF_EXIT_POSITION_STUDY_2026-10-06.md` (fix/telegram-curation @ 551dc99).
**Branch:** `research/exit-study-2026-10` from `origin/research/new-order-2026-09-30` (062999d).
**This is a PRACTICE STUDY, not a hypothesis registration**: exploratory, consumes no family slot,
not filed in FAILURE_REGISTRY; it is predeclared and frozen anyway because choosing the best of
many exit rules is itself a multiple-comparison problem. The sha256 sidecar (`PREDECLARATION.sha256`)
covers THIS file, the driver (`exit_study.py`) and the PIT tests (`test_pit_exit_study.py`) — the
three lines in it are the freeze. Two gates: **G0 = this freeze + a counts-only census** (no
returns computed); **G1 = one run** after owner/planner approval (machine-gated on
`EXIT_STUDY_G1_APPROVED=1`), reading both eras in that one run, then RESULT, VERDICT,
PRACTICE_NOTE, stop. No re-runs with changed settings after seeing results.

## 1. Question

The owner trades a "sniper" entry (buy a support zone in an uptrend with two limit orders, stop
below the zone, target the nearest resistance; historically also averages down and trades swing
lots). Which management rules — stop placement, averaging down vs adding to winners, profit
taking — help or hurt on that entry population? The research program has found no tradeable
entry edge; this study is decision support for the owner's own trading, not an edge claim.

## 2. Data and universe (frozen)

- `research.rulecard.data.load_extended_ohlcv(issuance=True)`, daily OHLCV only; dataset
  fingerprint + git commit recorded through `research/tracking.py` in `CENSUS_G0.json` (and at
  G1 in the RESULT).
- **Owner screen (primary universe):** ADV20 ≥ Rp 10 bn at the signal date, where ADV20 = mean
  of C×V over the last 20 sessions (min_periods 20).
- **Parity universe (report only):** top-150 by 60-session mean turnover (min_periods 40) — the
  earlier studies' universe. It appears in the census counts; arms do NOT run on it.
- **Eras (by signal month):** E1 = 2001-01..2021-09 (discovery), E2 = 2021-10..2026-09
  (confirmation). Both are read in the one G1 run; the recommendation rule requires both.

## 3. E-SN, the sniper population (frozen; re-implemented — no ~/jurnal26 import)

> **G0-bis re-freeze (2026-10-06, planner review, BEFORE any outcome was read — the one
> authorized re-freeze).** The level rules below are superseded so the E-SN levels match
> jurnal26 exactly (`server.py::_levels` with w=5, tol=0.04; `watchlist._sniper`). Four changes:
>
> 1. **Pivots:** 11-bar pivots — 5 bars each side: `H[i] == max(H[i−5..i+5])` and
>    `H[i] > max(H[i−5..i−1])`, lows mirrored — knowable only **5 sessions after forming**
>    (confirmation lag was 2). Window = the last 250 bars before the signal day
>    (confirmed pivots in [s−249, s−5]; left-strict / right-non-strict comparison unchanged,
>    so a plateau still counts once, at its first bar).
> 2. **Zones:** pivot highs AND pivot lows are pooled into ONE list, sorted by price
>    ascending, and grouped: a pivot joins the current group iff p ≤ group[0] × 1.04,
>    where group[0] is the group's lowest price (the anchor — the chain does not slide),
>    else it starts a new group. Each group gives (mean, count, min, max). A group may
>    mix pivot highs and pivot lows.
> 3. **Support zone:** the pooled group with the **highest mean below the close** (mean-based
>    membership and ranking). Zone low = group min; zone max = group max; **zone top =
>    min(max(zone max, zone low + 0.5·ATR14), C[s])**; **stop = zone low − 0.75·ATR14**
>    (formulas unchanged, now computed on group stats).
> 4. **Target:** the **min** of the pooled group with the **lowest mean above the close**;
>    none → the 52-week high; **if target ≤ zone top → the 52-week high** (new guard).
>    E-BRK's resistance target, built on the same pivot machinery, inherits the pooled-group
>    selection anchored on the signal close; its frozen definition is otherwise unchanged
>    (no zone-top guard — its zone top is the entry itself).
>
> Everything else stays as frozen (arms, mechanics, costs, recommendation rule, C-1..C-10).
> The re-frozen artifacts are covered by the regenerated sha256 sidecar; `CENSUS_G0.json` was
> regenerated (counts only) under this code, at git HEAD 8437dc2 (the G0 commit).

Indicators per stock, all causal (min_periods = full window): MA20/MA50/MA200 = simple means of
close; **ATR14 = 14-session simple mean of TR**, TR = max(H−L, |H−C_prev|, |L−C_prev|);
52-week high = max HIGH over the last 250 sessions.

- **Trend filter on day s:** C > MA50 > MA200; MA200 rising over 20 sessions
  (MA200[s] > MA200[s−20]); C ≤ MA20 + 2·ATR14.
- **Pivots:** [G0 original — superseded by G0-bis note above] 5-bar pivots (2 bars each side)
  over the window [s−249, s−2]. Left neighbors strict (`<`), right neighbors non-strict (`≤`) —
  **a plateau counts once, at its first bar**. A pivot is **knowable only 2 sessions after it
  forms** (its right side must exist) — the confirmation lag is enforced and PIT-tested.
- **Zones:** [G0 original — superseded by G0-bis note above] pivots merged chronologically; a
  pivot joins the first-formed zone whose FIRST pivot it is within 4% of (ties → the nearest
  first-pivot in percentage distance), else opens a new zone. Zone construction uses only the
  pivots in the day's window.
- **Support zone:** [G0 original — superseded by G0-bis note above] among zones whose max
  pivot < C[s], the one with the highest max. Zone low = min member; zone max = max member;
  **zone top = min(max(zone max, zone low + 0.5·ATR14), C[s])**.
  **Stop:** zone low − 0.75·ATR14. **Target:** the resistance zone (pivot-high zones built the
  same way) whose min pivot > C[s] is nearest — the target is that zone's min; none → the
  52-week high.
- **Setup set on day s:** trend filter holds ∧ support zone exists ∧ C[s] ∈ [zone top,
  zone top × 1.10].
- **Fills:** the limit at the zone top is watched sessions s+1..s+20. A fill happens the first
  session with L ≤ order; on a gap through (open ≤ order) the fill is at the open.
- **One setup at a time per stock (eager watch):** the pending order's fill is tested every
  session of its watch. A newer setup **supersedes** a pending unfilled order (the old order's
  fill chances are tested through the replacement day's session — orders stood intraday; the
  watchlist updates after the close). A fill **locks the stock for 60 sessions** — the maximum
  hold across arms, chosen so the fill set is arm-independent and every arm trades the identical
  trades. Setups raised while locked are counted and never enrolled.

## 4. E-RND, the control (frozen)

One matched control per E-SN fill: the same stock on a **random liquid day in the same era as
the matched fill** (seeded `np.random.default_rng(20261006)`, picks drawn in fill-
chronological order; the only requirements are the ADV20 gate at r and a valid next-open bar —
no spacing or ordering constraints beyond era stratification, since all metrics are computed
per era anyway). Entry at the **next open (market — always fills)**. The matched E-SN trade's
own levels are expressed as multiples of ITS signal-day ATR — d_stop = (entry − stop)/ATR_s,
d_tgt = (target − entry)/ATR_s, d_zone = (entry − zone low)/ATR_s — and re-applied with the
control day's ATR: stop = entry − d_stop·ATR_r, target = entry + d_tgt·ATR_r, synthetic zone
low = entry − d_zone·ATR_r (the position arms' geometry). Unmatchable fills (no liquid in-era
day) are counted.

## 5. E-BRK, the second entry (reported only, never recommended)

Close above the 20-day high: C[s] > max(HIGH over [s−20, s−1]); ADV20 gate; entry at the next
open; the same 60-session lock. Stop = entry − 2·ATR14; target = nearest resistance-zone low
above C[s] (same pivot machinery, no trend filter required), else the 52-week high; synthetic
zone low = entry − 1·ATR14 (position-arm geometry). E-BRK carries no structure zone, so its
"structure stop" is defined as the 2·ATR stop (X1 ≡ X2 for E-BRK except the resistance target).

## 6. Arms (frozen; 12 per entry population)

**Exit arms** (single full-size entry at the zone top — P0 geometry):

| Arm | Rule (implementation conventions in §7) |
|---|---|
| X0 | Hold 20 sessions, no stop (baseline) |
| X1 | Structure stop (zone low − 0.75 ATR) + target at the nearest resistance (the owner's plan); max 60 sessions |
| X2 | Fixed stop 2·ATR + target 3·ATR; max 60 sessions |
| X3 | Structure stop + chandelier trail (highest close − 3·ATR); max 60 sessions; no fixed target |
| X4 | Structure stop + exit on the first close below MA20 (at that close); max 60 sessions; no fixed target |
| X5 | Time stop: exit at session 10's close unless that close ≥ entry + 1·ATR; then as X1 |
| X6 | No stop, target at resistance, max 60 sessions |

**Position arms** (exit rule X1):

| Arm | Rule |
|---|---|
| P0 | Single entry, full size at the zone top (baseline) |
| P1 | Split entry: half at the zone top, half at the zone low (the owner's two limits); the unfilled half cancels 20 sessions after the SETUP day; a position exit cancels any pending leg |
| P2 | Average down: full at the zone top, then +50% at entry − 1·ATR (only if that level is above the stop) if hit before the stop; same stop for the whole position |
| P3 | Pyramid: full at the zone top, then +50% **at the close** of the first session with close ≥ entry + 1·ATR; stop for the whole position unchanged |
| P4 | Swing lot: core at the zone top; after a close ≥ entry + 1·ATR, a top-up of 50% at entry − 0.5·ATR (limit, from the next session); the top-up sells at its own entry + 1.5·ATR or exits with the core |

## 7. Mechanics (frozen)

- **Same-day precedence (conservative):** (1) the stop — intraday at the stop price, on a gap
  through at the open; if a day's range contains both stop and target, **the stop first**;
  (2) pending limit leg fills (gap through → open); (3) the target — at the limit, gap through
  → open; (4) close-based events (P3 add, P4 arming, X4 exit, X5 time stop — at that close);
  (5) the chandelier trail updates from each close for subsequent days (the trail on day k uses
  closes strictly before k, anchored on the entry price). A stop on the entry day itself is
  possible (conservative).
- **Max hold:** exit at the close of session 60 (X0: session 20). A trade still open at the
  panel's end force-exits at the last close (reason `eos`, counted).
- **Costs:** 0.15% × total buy notional + 0.25% × total sell notional (the owner's broker) +
  0.20% slippage allowance × total buy notional (anchored per round trip on what was put on).
  0.60% RT on the P0 single-fill trade, per the brief.
- **Risk normalization:** every trade is reported as net % = net P/L ÷ total buy notional, and
  as an **R multiple = net P/L ÷ ((first fill − stop) × first-fill units)** (initial risk to
  the structure stop). MAE over [first fill, exit]: worst (lowest) low, in % of first fill and
  in R units.

## 8. Metrics, per entry population × arm × era (frozen)

n, mean and median net %, expectancy in R, win rate, average win / average loss, mean holding
sessions, the MAE decile distribution, the exit-reason mix, the year-by-year table (mandatory),
and an **equal-risk portfolio**: 1% of current equity risked per trade (shares =
0.01·equity ÷ (entry − stop)), at most 10 concurrent, the next signal skipped when full, daily
mark-to-market on closes, costs on the portfolio's own fills → CAGR (250 trading sessions per
year), max drawdown, worst rolling 250-session return. **E-SN vs E-RND** paired per arm
(matched controls) answers whether the sniper entry itself adds anything.

## 9. Recommendation rule (frozen at G0)

An arm is **recommended over its baseline** (X0 for exits, P0 for positions) only if, in BOTH
E1 and E2: expectancy in R is higher, with a paired difference t ≥ 2.0 on matched trades
(paired on (ticker, signal day)), AND its portfolio max drawdown is not worse by more than 20%
relative. An arm is **flagged harmful** if it is worse (lower expectancy) in both eras with
t ≤ −2.0. Everything else is **no reliable difference**. **P2 gets the specific question:**
does it raise expectancy or only the win rate, with a fatter loss tail — reported as its effect
on the worst 5% of trades (mean of the worst-5% net%s vs P0's), beside win rate and expectancy.

**Multiplicity honesty:** 10 non-baseline arms × 2 entry populations (E-SN, E-RND) × 2 eras are
paired comparisons; at t ≥ 2 roughly one in twenty thresholds false-positives. The study is
exploratory by declared design; the both-eras requirement, the drawdown guard and the E-RND
control are the discipline, and the output is advice to the owner, not a registered claim.

## 10. Census at G0 (counts only — no returns)

`CENSUS_G0.json`: per universe (owner screen, parity) and per era — E-SN setups set, fills,
expired orders, superseded orders, setups-while-locked, out-of-window signals (the corpus now
reaches past 2026-09; **era membership is by SIGNAL month and signals after 2026-09 are counted,
never enrolled**, per the brief's era definition), stocks with fills; E-RND matches (tagged by
the matched fill's signal month) and unmatched; E-BRK signals (also capped at 2026-09); per-year
fill/signal counts. The four setup outcome counters reconcile exactly against setups per era.
No P/L, no returns, no performance numbers of any kind are computed at G0.

## 11. PIT tests (G0 gate; read no outcomes)

`test_pit_exit_study.py`, 25 tests on synthetic data only: pivot **5-session** confirmation
lag and plateau-once; **pooled pivot grouping** (4% chain anchored on each group's lowest
price, highs and lows together) and the jurnal26 support/target selection with the
zone-top fallback; **setup truncation identity** (levels at day k
bit-identical on the truncated panel, sampled across a synthetic 420-bar panel, ≥3 setups
exercised); limit/stop/target fill mechanics with gap rules; the stop-first precedence; X0/X3/
X4/X5 exit mechanics incl. the trail's strictly-past closes; P1/P2/P3/P4 leg rules; cost and R
arithmetic against a hand-computed trade; the eager entry state machine (supersede, fill lock,
while-locked rejection); seeded determinism of E-RND; era split; portfolio sizing/cap outputs;
the G1 gate refusal; and an end-to-end `evaluate()` smoke on a synthetic panel (no real
outcomes, nothing written). Architecture boundary tests pass on the branch (3/3).

## 12. Conventions beyond the brief's silence (declared; object at approval if not)

| id | convention |
|----|------------|
| C-1 | Fill lock after a fill = 60 sessions (arm-independent), so all arms trade the identical fill set; the census is therefore arm-independent |
| C-2 | Eager watch: the pending order's fill is tested every session; a superseding setup takes over after the old order's same-session fill chance |
| C-3 | E-RND enters at the next open (market); its levels derive from the matched trade's own levels in signal-day ATR units; the control day is any liquid day in the matched fill's ERA (era stratification replaces spacing rules — the initial spacing-constrained version matched only 1,332/3,644 fills, mostly starving E1, and was replaced BEFORE the freeze; the census committed at G0 is the post-amendment run) |
| C-4 | E-BRK structure stop = 2·ATR (no zone exists); resistance target anchored on the signal close |
| C-5 | X3/X4 have no fixed target (the brief lists none); X5's session-10 exit is at that close |
| C-6 | Slippage allowance anchored on total buy notional; net % divides by total buy notional; R divides by first-fill risk |
| C-7 | Panel-end open trades force-exit at the last close (`eos`), counted |
| C-8 | Portfolio year = 250 trading sessions (CAGR and the worst-12-month window) |
| C-9 | ATR14 = simple 14-session mean of TR (not Wilder's smoothing) — the corpus's established convention |
| C-10 | Signals end 2 sessions before the panel's last bar (a next-open bar must exist); the census/G1 signal horizon is the panel edge minus that guard |

Nothing else deviates from the brief. Any change to this file, the driver or the tests after
approval invalidates the freeze and re-opens G0.
