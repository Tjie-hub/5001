# HANDOFF G0 — market-stress reversal S1 (HYP-PM-0019 draft, D-075) · 2026-10-08

**Branch:** `research/market-stress-reversal-2026-10` (from hardening `8664856`, new worktree).
**Status:** G0 BUILT and FROZEN — predeclaration, drivers, 9 PIT tests, counts-only census.
**No return after any stress day's close was computed, printed or stored** (day-t returns are
the trigger itself, D-075). **NOT SUBMITTED**: per D-075 ("G0 after D-073's") and the owner's
order, submission waits for HYP-PM-0017's G0 approval. G1 is machine-gated on
`STRESS_G1_APPROVED=1`.

## history_long provenance (D-075 disclosure requirements)

- **Source / builder:** `atr_plan/build_long_db.py` — pre-2021-07-05 rows come from
  `docs/research_programs/P-M/forward_volex/remeasure/work/hist_pre2021.pkl` (yfinance-derived;
  the builder notes it is ALREADY split-adjusted — 187/197 pre-2021 splits show no price jump);
  rows from 2021-07-05 are appended from walkforward `ohlcv` (`is_final=1`). Sampled overlap
  rows are **byte-identical** between the two panels (201/201 on close AND volume) — one vendor
  basis. **`adj_close` ≡ `close` everywhere (0/2,124,338 rows differ):** the builder literally
  sets `adj_close = close`, so the panel carries NO dividend adjustment and returns add the
  dividend back (below).
- **Split/dividend adjustment:** stored closes are split-adjusted to the fetch-time basis
  (stored = as-traded ÷ f_cum; verified: BBCA pre-Oct-2021 closes ≈ 7,290 = raw/5). The CA
  table's `dividend_value` is pre-scaled to the SAME basis (verified arithmetically: AKRA
  2021-08 = 60 = 300/5 for its 2022-01 1:5 split; ASRM 2021-07 = 194/4.2 for its 4.2 bonus), so
  `(close_t + div_t)/close_{t−1} − 1` is a clean total-return construction on both panels, EX
  dates only. **CA coverage starts 2009** — the 10 events of 2007–2008 keep price-only legs and
  are counted (`events.pre2009_events_price_only_legs`).
- **Survivorship:** 929 tickers; **54 have a last bar before 2026-01-01** — delisted/suspended
  names ARE present (e.g. WSKT, DUCK, HOTL, JSKY, LMAS, PURE); the panel is not
  survivorship-clean but retains them, which is what a long event panel needs.
- **Coverage by year:** 2000-03 → **2026-09-24** (E1 ends Sep 24; the overlap window ends
  there too), per-year rows/tickers in `CENSUS_G0.json: provenance.coverage.per_year`. The
  full table is in the census; zero-volume stale bars (19% of pre-2021 rows) were already
  dropped by the builder, so the zero-volume ARB basket exclusion is structural pre-2021.
- **Nominal ADV floor:** the census uses TRUE rupiah ADV20 (`close × f_cum × volume`) —
  stored closes are split-adjusted while volume is as-traded, so the naive product understates
  pre-split ADV by up to the split factor. Both tables reported (`adv_floor`): median liquid
  names/day E1 2007 = **48 true** (40 naive) → the ≥ 30-name floor holds from ~2005; E2 2026 =
  176 (175). Per-EVENT medians: 75 (E1) / 144 (E2) — planner said 70/137 ✓.
- **Earlier VOLEX out-of-sample use (disclosed per D-075):** the same corpus fed the VOLEX
  volatility-exclusion remeasure (`forward_volex/remeasure`), which asked a different question
  (level-dependent exclusion, not stress-day reversal); no arm of this study reuses its
  outputs.

## Panel agreement gate (pre-event; the brief's STOP rule)

- Common flag window 2022-01-24..2026-09-24 (1,114 days compared): E1 flags 28, E2 flags 28,
  union 29, **agree 27, disagree 2 (2023-10-19 E1-only, 2024-06-14 E2-only) → 6.9% ≤ 20% —
  GATE PASSED**, the census proceeded.

## Events and counts (counts only; full tables in CENSUS_G0.json)

- **E1: 113 stress days / 65 episodes / 46 events (2007–2020)** · **E2: 28 days / 17 episodes /
  17 events (2021-07→)** · **pooled 63 events** · halves 46 / 17, neither (2021-H1) 0 ·
  78 later-in-episode stress days (report-only at G1).
- Per year: 2007:4, 2008:6, 2010:2, 2011:4, 2012:1, 2013:4, 2014:3, 2015:6, 2016:1, 2017:1,
  2018:8, 2019:1, 2020:5 | 2022:1, 2023:5, 2024:3, 2025:3, 2026:5 (no 2009, no 2021 events).
- Basket sizes: E1 median **15**, E2 median **28** (22–47). ARB-excluded per event: E1 median
  0, E2 median 1. σ-multiple range (E1 events): −7.59..−2.51.
- Planner cross-check (brief: "reproduce, don't trust"): planner 105 days / 63 episodes on the
  long panel vs mine 141 days / 65 episodes (E1 full history); planner 32 days / 21 episodes on
  the 5001 panel vs mine 28 / 17. The deltas are the frozen conventions the planner did not
  apply: true-ADV (split-corrected) liquidity, the 35% bad-print guard, the E2 split-day guard,
  and σ needing 120 defined days (2021-H2 starts late). **Pooled n = 63 matches the planner's
  episode count exactly, by coincidence of the same forces in opposite directions.**

## 15:49 pre-close agreement (prices only; 2025+ stress and near-miss days)

- **5 agree / 2 disagree over 7 days** (71%). Both misses are "1549 NOT flagged, close flagged"
  on borderline days (close multiple −2.507 and −2.555; rm_1549 −0.042/−0.047 vs thresholds
  ≈ −0.049/−0.048): a trader at 15:49 misses the marginal stress days, never a deep one.
  Zero false-positives at 15:49. 21 member-days had no 15:49 print; the same 35% bad-print
  guard as day-t returns is applied (one corrupted 2025-03-21 print without it gave a +26.8%
  "market" move). Pass condition 3 (next-day entry) covers the case where they cannot know.

## Power (pre-event dispersion only; bar = 3.2954)

- E1: median member daily σ 3.66%, stress multiplier 0.434 → σ_5 = 3.55%, **MDE 1.73%** at
  n = 46. E2: σ 4.70%, multiplier 0.308 → σ_5 = 3.24%, **MDE 2.59%** at n = 17. Pooled at
  n = 63 with σ_5 ≈ 3.4%: **MDE ≈ 1.4%** — the planner's 0.8–1.3% approximation was mildly
  optimistic; a reversal of ~1.5%+ per event is detectable.

## The bar and its N

- **Expected N = 604, bar 3.2954** (exact `bar_v2.e_max_abs_z(604)` = 3.295375);
  **N = 605, bar 3.2959** (exact 3.295896) applies only if HYP-PM-0018 (D-074, tender offers)
  registers before this one — its G0 is "NOT NOW" per the owner.
- **Which:** 604. At freeze, HYP-PM-0017's G0 is frozen (branch
  `research/dividend-clientele-2026-10`, pushed) and registers at the owner's approval — the
  submission gate for this study; D-074 has no G0. The final N is re-verified at submission and
  again at G1 against `CENSUS_G0.json: census.ledger_rows_counted` (595 D-071 components + 2
  exploratory arms of 2026-10-08 + HYP-PM-0017's 2 arms + this arm).
- **Conflict note (brief vs D-entry, D-entry wins, already owner-corrected):** the brief's
  "ledger 601 + 1 = 602 if frozen today" reading is superseded by the same task order that
  fixed D-073's G0 at 603 — the census ledger counts previously-frozen G0 arms once their
  studies are at the gate ahead of this one. No other conflicts: the brief's counts were
  reproduced within convention drift (above), and nothing in the brief contradicted D-075.

## Snapshots (pinned; G1 re-hashes both BEFORE any outcome)

- walkforward `a2d7e675e5c66387446b888287ebbe7cef563b278c48f1518a88c797bc4bbc47`
  (dataset fingerprint `9c26e0df2fdd4e4bec378ff9d38b4d4ccbbdeaa9a6176ca71b3fdb955f137c03`,
  max date 2026-10-07) — the SAME snapshot the dividend G0 pinned.
- history_long `7d298068fbc5633277ef0c032ed0257f935c9ef902068b16daa75ac0ba5e5714`
  (both under `/home/tjiesar/scratch/g0_snapshots_2026-10-08/`, quick_check ok).

## D-059 cost source (frozen)

`docs/research_programs/P-M/cost_liquidity/cost_by_adv.py` @ commit **7e039ee**
("docs(P-M): D-058/D-059 -- universe screen and cost-by-liquidity; T1 is friction"), formula
frozen: 0.50% fees + (½s_entry + ½s_exit) + 2·σ_d·√(Q/ADV20); s = Abdi-Ranaldo (2017) spread
over the 21 sessions ending t−1, floored at one IDX tick; σ_d = the member's daily-return SD
over 60 sessions before t; **Q = Rp 100m** (D-059's primary size); ADV20 = the true-rupiah ADV.

## Runtime estimate for G1

Census (both panels, flags, agreement, 15:49): **4.0 min**. G1 adds 63 × s1_event assemblies
(β regressions, ARD costs, decile books, horizons, controls — all per-event loops over ≤ 300
names): estimated **10–20 minutes** single-threaded, well inside one session. The RESULT
schema is proven by `g1_run.py --synthetic` on the fixture market (no real outcomes touched).

## Governance

Read-only DBs (mode=ro) on the pinned snapshots; no network; HYPOTHESIS_REGISTRY /
FAILURE_REGISTRY / DECISION_LOG untouched; `~/jurnal26`, production, the 5001 service and
`ops/hardening` beyond the branch point untouched; `logs/TELEGRAM_OFF` untouched; no secrets
printed. Boundary + fence tests pass. All SQL is inline-literal and parameterized (Mimosa
scanned). **Built, frozen, pushed — NOT submitted: the owner's gate (HYP-PM-0017 approval)
comes first.**

*— ZCode, 2026-10-08*
