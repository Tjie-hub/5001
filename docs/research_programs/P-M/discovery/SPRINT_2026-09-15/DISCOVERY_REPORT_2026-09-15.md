# RAPID EDGE DISCOVERY SPRINT — RANKED DISCOVERY REPORT

**Date:** 2026-09-15 · **Program:** P-M · **Stage:** DISCOVERY ONLY
**Status:** No hypothesis registered. No registry entry created or modified. No experiment executed
beyond exploratory scans. Nothing in this report is confirmatory evidence, registered evidence, or
authorization to trade. I7/HYP-PM-0009 was not revisited; C7 and G1 were not re-run or reinterpreted.

**Artifacts:** this directory (`docs/research_programs/P-M/discovery/SPRINT_2026-09-15/`) —
`sprint_lib.py` (harness), `run_daily.py`, `run_broker.py`, `run_intraday.py`, `rank_and_increment.py`,
`cache/ledger_{daily,broker,intraday,e3c,e3grid,all}.json` (every tested construction, 60+ ledger rows).

---

## 1. Data used (existing validated stores; no pipeline changes)

| Source | Store | Coverage | Grain |
|---|---|---|---|
| OHLCV (final) | `data/walkforward.db` `ohlcv` | 2021-07..2026-09-14; canvas 2025-01-02..2026-09-14 (401 sessions, 959 tickers) | ticker-day |
| Retail platform flow (daily) | `stockbit_flow` | 2025-01-02..2026-09-14 (frozen v002 byte-identical on overlap; 2026-08-25 missing → NaN) | ticker-day |
| Broker flow (frozen Dataset B) | `views_v1.sqlite` A–G views | 2025-01-02..2026-08-27, IDX100 roster (broker DM excluded) | ticker-broker-day |
| Minute flow bars (frozen v002) | `stockbit-flow-bars-v002.db` | 2025-01-02..2026-04-27, 77.5M bars; **excl.** fixture 2025-04-14 and integrity zone 2025-08-04..09-17 | ticker-minute |
| Bandar regime labels | `bandar_detector` | 2025-01..2026-09 | ticker-day |

**Sprint-specific exclusions declared ex ante:** PIT liquidity floor (trailing-60-session median traded
value ≥ Rp 1e9, shift(1)); entry-day tradability (stock must trade on t+1); 2026-09-15 pre-open partial
session in production `ohlcv` (585 `is_final=1` rows inserted by the morning fetch **before WIB open** —
flagged to owner as a data defect); minute families additionally restricted to the v002 admitted window.

**Conventions (inherited, not invented):** forward return `hold_k(t) = close(t+1+k)/close(t+1) − 1`
(entry at next close; k=1 ⇒ exit index i+2), split- and dividend-adjusted via the foundation.py
applied-basis detector; trailing-60 PIT z-scores (shift 1); costs = 60bp round-trip sensitivity floor
(40–60bp environment); NW t via erfc convention reported descriptively only — **ranking was never by
p-value** (per sprint charter).

**Sample:** ~123.6K liquid tradable ticker-days (avg 308/day); unconditional base rate hold5 = +0.39%,
hold10 = +0.85%, hold20 = +1.65% (market drifted up in-window; 2026H1 was a drawdown — unconditional
hold5 −1.32% — so subperiod *excess* is the stability lens, not raw sign).

---

## 2. Headline findings

1. **The only economically capturable edge found is a price-event effect: up-move continuation.**
   A single-day gain ≥ +3%, entered at the next close, returned **+1.39% over 5 days, +1.78% over 10,
   +2.08% over 20** (net of the 60bp floor: **+79bp / +118bp / +148bp** per round trip). It is
   parameter-robust (all 6 cells of a declared |ret1|×flow grid positive, 1.05–1.63% h5), positive in
   absolute terms in 3 of 4 half-years and in **excess** over the unconditional base in all four
   (h5 excess ≈ +56 / +136 / +133 / −24bp), and present in **all liquidity terciles** (top-tercile
   h5 +1.06%, net ≈ +46bp — executable names). Breadth: ~16.4K events, 569 tickers, ~33/day.
2. **Retail/platform flow is NOT incrementally positive on top of that event** — and inside move
   events, *more* agreement between flow and the move predicts **worse** forward returns
   (FM β = −0.35%, t = −3.32 controlling the event flag; within-actives dose β = −0.65%, t = −2.84
   for the volume-spike variant). Down-moves with any *extreme* retail flow (buying the dip or
   capitulating) continue down (−0.38% / −0.43% h5 vs +0.35% for flow-neutral down-moves).
   The flow information content discovered on this canvas is **toxicity/avoidance information**, not
   a long entry signal.
3. **One positively incremental flow variable survived: 5-day flow acceleration** (Δ5d net flow z),
   FM **+0.53% per event, t = +3.09 controlling ret1, ret5z, volume z, and the flow level itself**.
   But its standalone long portfolio is below cost (h5 gross 0.43–0.46%) and it does not separate
   outcomes within move events — it is a **factor-library candidate for combination work**, not a
   capturable signal today.
4. **The entire broker-grain family (Dataset B, IDX100) is economically dead at daily grain**:
   concentration+lean, HHI, bandar "Big Acc" labels, few-sellers, same-broker persistence — all
   KILL (h5 gross 0.01–0.60%, net negative, breadth-limited). Consistent with the C7 null.
5. **Absorption is empirically dead on IDX in this window**: strong buying + muted/negative price
   response (A1, A1b, D1, D5) was flat to strongly negative. Buying weakness does not get rewarded;
   weakness with retail flow present continues down.

---

## 3. Ranked candidates

Ranking: economic magnitude after cost > robustness across time > breadth > parameter stability >
plausibility of execution > incrementality > fragility. NW t shown only as description.

| # | ID | Definition (exact) | Source | n obs | h5 gross → net(60bp) | Subperiod h5 (25H1/25H2/26H1/26H2) | Status |
|---|---|---|---|---|---|---|---|
| 1 | **UP3 move-event momentum** | `ret1 ≥ +3%`, long next close, hold 5–10d | OHLCV only | 16,391 (569 tk, ~33/day) | **+1.39% → +0.79%** (h10 +1.78% → +1.18%) | +0.78 / +3.18 / +0.13 / +1.73% abs; excess +56/+136/+133/−24bp | **SHORTLIST** |
| 2 | **A5 flow acceleration** | `z60(Σ5d net − Σ5d net prior) ≥ 1.5` | stockbit_flow | 8,352 (z1.5) | +0.46% → −0.14% (standalone) | FM **+0.53%, t=+3.09** vs all controls incl. flow level; unstable standalone | **SHORTLIST (factor-lib)** |
| 3 | A4 flow/ADV magnitude | `net_value/ADV60 ≥ 5%` | stockbit_flow + ohlcv | 32,183 | +0.69% → +0.09% | excess positive **all four** halves (+16/+29/+46/+37bp); FM vs raw flow t=−1.17 | WATCH |
| 4 | Flow-toxicity avoid filter | within `ret1 ≤ −3%`: `|nbz| ≥ 0.5` ⇒ avoid/underweight (spread ≈ −72bp vs neutral) | stockbit_flow | ~10.7K events | −0.40% vs +0.35% (avoided cell vs neutral) | spread −95/+106/−145/−129bp (sign flips 25H2) | WATCH (overlay only) |
| 5 | BL raw flow | `z60(net_value) ≥ 2` | stockbit_flow | 3,839 | +0.56% → −0.04% | unstable | WATCH-low |
| 6 | BL broker lean | `z60(net of top-3-gross brokers) ≥ 2` (IDX100) | Dataset B | 940 | +0.60% → 0.00% | unstable; breadth-limited | WATCH-low |
| 7 | BL volume spike (price/vol twin) | `z60(volume) ≥ 2` | ohlcv | 7,080 | +0.79% → +0.19% | FM vs controls t=−0.89 | WATCH-low (price-only) |
| 8 | E1 volspike+buyflow | `vol_z≥2 & nbz≥1` | stockbit_flow + ohlcv | 2,695 | +1.22% → +0.62% | **anti-incremental** vs volspike twin (β −0.78%, t=−2.87); edge = selection, flow dose hurts | KILL (as flow signal) |
| 9 | E3 bigmove+flow-confirms | `\|ret1\|≥3% & sign(nbz)=sign(ret1)` | stockbit_flow + ohlcv | 13,283 | +1.18% → +0.58% | **anti-incremental** vs bigmove-only (β −0.35%, t=−3.32) — effect is the price event | KILL (as flow signal) |
| 10 | E3c un-chased up-move | `ret1≥+3% & nbz≤0` | stockbit_flow + ohlcv | 3,822 | +1.21% → +0.61% | ≈ identical to chased variant (+1.22%) — flow adds nothing capturable here | KILL (as flow signal) |
| 11 | C1 flow streak | `net>0 on ≥4 of last 5 & nbz>0` | stockbit_flow | 9,246 | +0.67% → +0.07% | FM β **negative** (t=−2.15) | KILL |
| 12 | A1 absorption (4-param grid) | `nbz≥{1.5,2} & \|ret1\|≤{1%,2%}` | stockbit_flow + ohlcv | 463–1,750 | +0.02–0.25% | flat/negative | KILL |
| 13 | A1b absorption-in-dip | `nbz≥{1.5,2} & ret1≤−1%` | stockbit_flow + ohlcv | 368–663 | **−1.42%** | strongly negative | KILL |
| 14 | A2 sell-absorption | `nbz≤−{1.5,2} & ret1≥+1%` | stockbit_flow + ohlcv | 711–1,077 | +0.22–0.68% | below cost / breadth | KILL |
| 15 | A3 bull divergence | `nbz≥{1,1.5} & ret1≤{−3%,−2%}` | stockbit_flow + ohlcv | 471–690 | −1.12% | negative | KILL |
| 16 | B1/B2 concentration + lean | `z60(top3_share or HHI)≥{1,1.5} & z60(top3-broker net)≥1` | Dataset B | 248–506 | +0.01–0.06% | below cost, breadth | KILL |
| 17 | B3 bandar "Big Acc" / "Big Dist" | regime label event (IDX100) | bandar_detector | 6,275 / 7,735 | +0.09% / +0.17% | below cost | KILL |
| 18 | B4 few-sellers | `n_sellers pctrank≤{0.2,0.4} & lean_z≥1` | Dataset B | 74–224 | — | too few obs | KILL |
| 19 | C2 broker persistence | some broker buy-side ≥4/6 sessions, 6d cum ≥ {0.5%, 2%} ADV | Dataset B | ~30.2K | +0.18% | ≈ unconditional (near-always-true condition) | KILL |
| 20 | C3 conc persistence | `top3z≥1 & lean_z≥0` ×3 consecutive | Dataset B | 84 | — | too few obs | KILL |
| 21 | D1/D2/D3 intraday conditionals | red-day late-flow confirm; late-buy muted close; heavy-tape buying | v002 bars | 62–465 | — | too few obs at declared thresholds | KILL |
| 22 | D4 early-flow price-lag | `z60(net by 10:30)≥{1,1.5} & move≤0` | v002 bars | 1,122–2,048 | +0.25–0.28% | below cost; sign flips by half | KILL |
| 23 | D5 red-reversal + flow held | `ret1≤−3% & day net>0 & recovered ≥ half` | v002 bars | 889 | **−3.06%** | strongly negative | KILL |

Ledger note: every row above (plus mirrors, grids and baselines — 60+ entries) is reconstructible from
`cache/ledger_*.json` with its exact definition string. Baselines (momentum, reversal, unconditional)
are included in the ledger for the incrementality comparisons; momentum alone (h5 +0.91% gross) is
dominated by UP3 (+1.39%) on the same canvas.

---

## 4. Top candidates for deeper validation (NOT registered — owner to choose)

### T1 — UP3 move-event continuation (rank 1)

- **Signal:** day-t close-to-close return ≥ +3% (up session), enter next close, hold 5–10 sessions,
  liquid universe (program PIT floor), equal weight. ~33 events/day across 569 tickers over 20 months.
- **Why it might be real:** order-driven market with **no designated market maker** (LC-PM-0006) and
  **auto-rejection bands** that mechanically pause up-moves mid-discovery — public information
  (a large up session) is incorporated slowly over days; the literature card LC-PM-0001 (Chordia &
  Subrahmanyam 2004) documents 1–5d continuation as the permanent component of order flow. The
  effect's presence in the top liquidity tercile (+1.06% h5) argues against pure illiquidity microstructure.
- **What could make it spurious:** (i) right-skewed small-cap lottery payoffs — median event h5 ≈ 0,
  hit rate 47%: the mean is tail-driven and sensitive to a few huge movers; (ii) corporate-action
  misadjustment inflating "up-move + continuation" pairs (splits/dividends patched per-event by a
  ±25% heuristic); (iii) suspension inside the 5-day window freezing stale prices (not excluded here);
  (iv) 2026H2 excess was ≈ −24bp — the effect may decay with regime; (v) overlap with the existing
  production fast-mover screens (this program may already harvest part of it operationally); (vi) it
  is **price-only** — under the sprint's own criterion 6 it is not *flow information*, and it is a
  well-documented effect class, so any registered version must treat prior literature as priors, not as replicated evidence.
- **Evidence required before preregistration:** exact frozen spec (threshold, entry/exit indices per
  the I7 off-by-one convention, liquidity floor, max position count, band-contact handling); power/MDE
  analysis; suspension-window and corporate-action exclusion rules from `suspension_events` /
  `corporate_action_events` applied in-spec; PIT admissibility gates (E-PIT-1..4 style) on the event
  variable; a forward/out-of-sample protocol (the prospective flow-capture window and post-sprint
  sessions are the only clean holdout); a cost model per position size vs top-tercile ADV.
- **Provenance limitations:** canvas is survivorship-tilted (current roster with backfilled history);
  2026-08-25 daily-flow gap (irrelevant to UP3 but relevant to any flow overlay); 2026-09-15 defective
  pre-open `ohlcv` rows await owner cleanup.

### T2 — A5 flow acceleration (rank 2, factor-library)

- **Signal:** z60(Σ5d net_value − prior Σ5d net_value) ≥ 1.5 — the *change* in platform net flow,
  not its level.
- **Why it might be real:** fresh incremental buying (acceleration) is the classic informed-trading
  timing variable; it survives Fama-MacBeth **against its own level** (t=+3.09), which the raw level
  does not (BL-raw-flow FM vs controls is weak). This is the only flow construction on this canvas
  with positive information beyond price, volume, and flow level simultaneously.
- **What could make it spurious:** FM magnitude (+53bp/5d per event) < one-way retail cost reality for
  a standalone book — it only pays inside a combination; the z60 window and 5d differencing are two
  researcher degrees of freedom (only one grid point tested); correlation with the UP3 event (moves
  attract accelerating flow) — the FM controls ret1/ret5z but a joint construction could double-count
  one effect.
- **Evidence required before preregistration:** a pre-declared combination spec (e.g., acceleration
  condition *within* UP3 events or within a liquidity stratum) showing ≥ +50bp incremental h5 vs UP3
  alone with subperiod consistency; window-robustness (at least 3 declared (window, diff) pairs);
  then the same gates as T1.
- **Provenance limitations:** same daily-flow canvas constraints; note freq fields are forbidden as
  denominators (program rule) and were not used.

### T3 — A4 flow/ADV magnitude (rank 3)

- **Signal:** |day net_value| ratio to ADV60 ≥ 5% (buy side), hold 5–10.
- **Case:** the only candidate with positive h5 **excess in all four half-years** — remarkably stable,
  if modest (+16/+29/+46/+37bp). Fails strict incrementality vs raw flow level (FM t=−1.17): most of
  its information is already in flow z. Could still be preferred operationally because a
  value-to-ADV normalization is capacity-aware and PIT-robust.
- **Spuriousness risks:** ADV estimate from `close×volume` on low-priced names; zero-volume days
  inside the trailing window; overlap with A5 (same underlying flow).
- **Before preregistration:** show it adds anything over BL-raw-flow and A5 in one combined FM; if
  not, fold it into the A5/T2 work and drop.

### T4 — Flow-toxicity avoid filter (rank 4, overlay only)

- **Content:** within down-move events (ret1 ≤ −3%), *any* extreme retail flow state (nbz ≥ +0.5
  chasing, or ≤ −0.5 capitulating) precedes continued weakness (−0.38%/−0.43% h5) vs flow-neutral
  down-moves (+0.35%): a ~72bp avoid-spread. This is the honest home of the failed absorption
  hypothesis (A1b: −1.42%, D5: −3.06% — buying weakness with flow "support" is systematically punished).
- **Use:** as an entry veto for dip/reversal logic elsewhere in the estate — **not** a standalone long signal.
- **Spuriousness risks:** the avoid-spread flips sign in 2025H2 (+106bp) — 3-of-4 halves negative only;
  regime dependence likely.
- **Before preregistration:** would need to be registered as a *filter amendment* to an existing
  registered strategy spec, never as a standalone hypothesis; requires out-of-sample confirmation of
  the spread sign.

### T5 — Broker lean z2 (rank 6; the only live broker thread)

- **Content:** net of the **top-3-gross brokers** z≥2 (IDX100): h5 +0.60% on 940 obs. Everything else
  broker-grain (concentration, HHI, bandar labels, persistence) is dead at daily grain — a durable
  negative result that, together with C7, says aggregate broker-flow structure on IDX100 does not
  clear costs at T+1..T+20.
- **Before preregistration:** likely none — breadth-limited and unstable; recommend leaving dormant
  unless the prospective intraday capture (Dataset C path) revives the broker thread at finer grain.

---

## 5. Explicit discoveries about *what does not work* (negative results, for the registry of ideas)

- All-broker net is identically zero at ticker-day level (store invariant) — any "broker_net" signal
  must be defined on a broker *subset* (top-k lean was used here).
- `bandar_topK_accdist` numeric columns are empty in `v_b_concentration` (vendor labels as text);
  the usable form is the categorical regime label, which carries no edge at daily grain.
- Absorption (flow into weakness) is anti-predictive on IDX in 2025–2026 across daily and intraday
  constructions — five independent constructions, five kills.
- Flow confirmation of moves is anti-incremental within events (chase toxicity), stable enough to be
  useful as a veto, not as an entry.

---

## 6. Sprint discipline statement

Every construction tested is logged with its exact definition in `cache/ledger_*.json` (60+ rows,
including all killed and mirror variants). Grids were declared before running; no threshold was
iterated post hoc; no p-value was used as a selection criterion; no registered artifact was modified;
no experiment was launched; no hypothesis was registered. Per the sprint charter: **STOP.**
The shortlist above is handed to the owner for a deliberate choice of the next candidate.

```json
{
  "sprint": "DISCOVERY-PM-2026-09-15",
  "candidates_logged": 60,
  "shortlist": ["UP3-move-event-momentum", "A5-flow-acceleration-factor", "A4-flow-over-ADV", "flow-toxicity-avoid-filter", "broker-lean-z2"],
  "registration_actions": "none",
  "next_action": "owner review"
}
```
