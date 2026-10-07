# ZCode brief — Task 3: feasibility for mechanisms outside corporate actions (no outcomes) (2026-10-07)

**Category:** Research (P-M), feasibility gate under **D-070**.
**Owner-requested 2026-10-07:** "while waiting, put new task to zcode — goal still finding edge".
**Queue position:** after Task 2 (`ZCODE_BRIEF_STRUCTURAL_EVENTS_FEASIBILITY_2026-10-07.md`). If you're
waiting on the owner's Task 1 G0 approval, do this next.
**Branch:** `research/mechanism-inventory-b-2026-10`, created from `origin/ops/hardening-2026-07-10`
(`a28ec7e` or later, with D-070 filed). New worktree. Push only that branch.

## Why

D-070 closes the daily price-pattern search. A new edge study now needs a **named economic mechanism
accepted in its own D-entry before G0**:
- forced flow
- liquidity provision
- a risk premium
- an institutional or rule constraint

Task 2 covers corporate actions (classes A–F). This task covers the other mechanism classes, so the
owner can choose the next 1–2 predeclared studies from **one ranked list** that spans both tasks.

## Rule 1: NO OUTCOMES (same as Task 2)

- Don't compute, print or store any return, price change or excess return **after an event's
  decision date** (or after a calendar window starts), for any horizon or aggregate.
- Estimate power only from **pre-event** volatility: the daily return SD over the 60 sessions ending
  the day before the decision date.
- **Class M needs its own rule** (below).
- Any field that could leak post-event price information is left out, and the report says so.

## Classes to assess

| # | Class | Mechanism (state one paragraph each) | Data to inventory (read-only; **no fetching**) |
|---|---|---|---|
| G | **Global index rebalances** (MSCI quarterly / semi-annual, FTSE) | passive funds trade on a pre-announced effective date; announcement about 2 weeks ahead | no membership table in the DB. Check `scheduler/scanner.py` (MSCI event-risk window, around line 889) for what dates exist. Scope a public source for announcement and effective dates plus add/delete lists (MSCI and FTSE press releases, IDX news), with an effort estimate |
| H | **IPO lock-up expiry** | pre-IPO holders' shares unlock about 8 months after listing (POJK lock-up rule: verify the exact rule and its start year); predictable supply | listing date, using the first-bar proxy, and how {LC} (D-064) defined "young listing". Check for any IPO-detail source. Survivorship: delisted IPOs |
| I | **Suspension / resumption, special monitoring board (Papan Pemantauan Khusus, full call auction)** | forced exits by funds with liquidity mandates; price discovery after a halt | `suspension_events` (3,189). **First check whether `classification` / `gap_pct` are derived from post-resume prices.** If so they're outcome-tainted and only `last_normal_date` / `resume_date` may be used. Note any board-placement data, or its absence |
| J | **Earnings announcements (PEAD)** | investors under-react to new information | needs point-in-time **filing dates**. Inventory `stockbit_keystats` (snapshot history depth), the yfinance quarterly fundamentals (2,908 observations; filing dates or only period ends?), and `factor_zoo`. If there are no PIT filing dates, mark it infeasible historically and say what forward collection would need |
| K | **Calendar / institutional flow** | turn of month (payroll and pension inflows), quarter- and year-end window dressing by local funds, Ramadan/Lebaran (THR) liquidity, foreign-flow seasonality | `trading_calendar` and the panel. Pooled designs only. **State the multiplicity risk:** calendar effects are the classic data-mining zoo, so propose at most 2 windows, each with an ex-ante mechanism |
| M | **Liquidity provision: pooled cross-sectional short-term reversal** in liquid names (weekly losers bought, monthly rebalance) | the market-maker premium for absorbing order imbalance | this is price-derived, so it's admissible **only** under D-070's mechanism exception. **Map prior coverage first:** FADE {R1} / HYP-PM-0012, BANK {R2} / HYP-PM-0014, `DISCOVERY_2026-08-21_M2x_short_horizon.md`, `factor_zoo`, broad_search v1/v2. Then check D-062 (no correlated registration). If it's covered or correlated, say so and stop on M. **M's no-outcome rule:** report only the count of formation dates, the cross-section size and the pre-formation volatility. No portfolio returns |

Out of scope, with a single note line each:
- broker flow / bandar (exhausted, D-058..D-064)
- insider buys (D-061)
- ownership composition (2 snapshots; forward-collection only)
- dividends (Task 2, class D; also note what `forward_dividend/` already is)

## For each class, report (same structure as Task 2)

1. **Prior coverage.** Search HYPOTHESIS_REGISTRY, FAILURE_REGISTRY, DECISION_LOG and
   `docs/research_programs/`. If the class is already tested or counted, say so; it isn't new.
2. **Point-in-time decision dates.** When the market knew: which field, and what share of events
   have it.
3. **Counts.** Per year; on the liquid universe (ADV20 ≥ Rp 10 bn the day before); 2009..2021-09
   vs 2021-10..2026; overlaps.
4. **Power.** Median and IQR of pre-event volatility. Minimum detectable mean effect over 5, 10
   and 20 sessions at **t = the current deflation bar**: recompute it from the post-D-070 census
   rather than assuming 3.06. Give both the independent n and the month-clustered n. One line per
   class: "detectable ≥ X% over 10 sessions".
5. **Data gaps.** Source, rough effort, and whether it can be backfilled point-in-time. No fetching.
6. **Mechanism D-entry draft** for each class that passes 1–5. This is the one-paragraph text the
   owner would file before G0: mechanism, direction, why it should survive costs, what would
   falsify it. **Draft only, number `D-0xx`, not filed.**

## Combined ranking (the headline deliverable)

Rank classes A–F (from Task 2's output) and G–M (from this task) together in one table:
- columns: mechanism strength, power, PIT quality, prior coverage, data effort
- a recommended pick of the **top 1–2 for a predeclared G0**, with reasons
- a note on which could share one pooled design

If Task 2 isn't finished yet, rank G–M on their own and say so.

## Deliverables

- `docs/research_programs/P-M/mechanism_inventory_b/FEASIBILITY_B_2026-10-07.md`
- `CENSUS_FEASIBILITY_B.json` (counts and pre-event volatility only)
- the script(s) that produced them: read-only, with a fixed seed if any sampling
- `COMBINED_RANKING.md`
- `HANDOFF.md`, which states explicitly that **no post-event price was read**

Push and STOP. No registration, no D-entry filing, no G0.

## Hard constraints

- **No outcomes** (above).
- **Read-only DB:** `data.db.connect(read_only=True)` or a snapshot. No network fetching.
- **Production:** don't touch it. Production now runs from `ops/hardening` in the production tree, so
  don't check out, commit to or push hardening in that tree. Use your own worktree.
- **Records and logs:** no edits to registries, DECISION_LOG or frozen files. `logs/TELEGRAM_OFF`
  stays. Never print secrets.
- **Code:** research-side only. If you add code under `research/`, run the boundary and fence tests.

---

## Amendment 2026-10-07: prior work found, a new class N added, census flag

The owner asked: "have we considered global conditions (war worsening → energy/commodity stocks) and
seasonal effects (holidays)?"

### 1. Read broad search v2 first; don't redo its probes

`origin/research/broad-search-v2-zcode` (never merged into hardening) already did this work in
`docs/research_programs/P-M/broad_search_v2/`. Read W1_INVENTORY, W2_SOURCE_PROBES and
W3_SCREEN_SKETCHES before anything else. Cite them; don't re-derive them.

| Class | What v2 already found |
|---|---|
| G | **FTSE: yes** (notices API, no auth). **MSCI: no** (registration-gated). IX1 was sketched as a *forward recorder* because its history is too short |
| H | lock-up dates are **blocked**: no free structured source; they live in the prospectus PDFs behind the IDX wall |
| I | already sketched as **TS1**: 359 events, 2022-04 onward only, expected to be underpowered |
| K | **CAL1** turn-of-month is underpowered at the bar unless pooled into one arm (N about 2,400, minimum detectable about 21 bp/day). **CAL2** pre-holiday has N about 250, minimum detectable ≥ 40–50 bp; underpowered alone. The IDX holiday calendar can't be fetched from idx.co.id; it can be derived from corpus session gaps plus timeanddate |
| X1 | the US overnight session → IDX already **ran: FAIL (null)**, t −0.30 |
| X2 | commodity overnight → sector: **coal and CPO have no free source**. Gold, oil, gas and copper do (yfinance, 2000 onward) |

For G, H, I and K, add only what v2 doesn't have:
- the D-070 mechanism paragraph
- the liquid-universe counts, using the hardening DB
- a final rank

### 2. New class N: global commodity and geopolitical conditions → IDX exporter sectors

**Mechanisms to state:**
- **(a) Cash-flow pass-through with slow diffusion.** Commodity prices drive the earnings of IDX
  exporters (coal, oil and gas, gold, nickel, CPO), and local investors under-react over weeks, not
  overnight. X2 tested the overnight version; this class is the weekly/monthly one.
- **(b) Geopolitical-risk premium.** In war or escalation regimes, energy and gold names act as a
  hedge, while importers and consumer names carry the risk.

**Designs to assess (feasibility only):**
- **N1.** A pooled sector tilt. The trailing 4–12-week commodity return (gold, oil, gas, copper,
  nickel proxy) sets the weight of the matching IDX sector book at the next monthly rebalance.
- **N2.** A regime overlay. A geopolitical-risk index decides whether energy and gold names are
  over- or under-weighted.
  - Scope the Caldara–Iacoviello GPR index: free, monthly, back to 1985, published with a lag.
    **State its PIT lag.**
  - Alternatively, an oil-volatility regime.

**Report for N:**
- the sector-to-commodity mapping, using `ticker_sector` (Energy 51 names, Basic Materials 79) at the
  industry level
- how many liquid names map to each commodity, per year
- the number of independent rebalance dates
- power from pre-formation volatility only
- coal/CPO coverage: the BTU equity proxy starts only in 2017-04; name any free coal-index alternative
  (e.g. the Newcastle API2 history) and its effort
- prior coverage: `factor_zoo`, broad_search v1/v2 W1 (X2), and the D-062 correlation with VOLEX
  (energy names are high-volatility)

**No outcomes:** no sector or stock returns after any formation date. You may download commodity and
GPR series (a public, no-auth one-time probe is allowed for N only, and is logged), because those
series are the signal, not the outcome.

### 3. Census and deflation bar: owner decision needed

The hardening corpus uses **N = 276, bar ≈ 3.06** (D-064, D-067). But v2's `recount/RECOUNT_W0` and
`CENSUS_NOTE.md` give **N = 561, bar 3.2745**. That figure is drafted, not ratified.

- In this task, and in Task 1's HANDOFF_G0, report minimum detectable effects and the frozen bar
  **under both**, and say which one the predeclaration freezes.
- Recommend which is correct, with reasons. **Don't** file anything, and don't pick silently.

---

## Amendment 2: class O, opening-auction order imbalance (owner-approved 2026-10-07)

**Mechanism to state:** IDX opens with a pre-opening call auction (08:45–08:59). When orders at
the open are imbalanced, liquidity providers fade the imbalance, so the price reverses after the
open. This is a liquidity-provision mechanism, not a breakout pattern.

**Prior evidence to cite:**
- an early Pacific-Basin study of Indonesian intraday volatility (*Price volatility of Indonesian
  stocks*, PBFJ 1995) found reversals dominate continuations at the open and close
- the US opening-range-breakout literature finds the opposite (momentum): Zarattini–Aziz–Barbon on
  ORB, and Gao–Han–Li–Zhou on intraday momentum
- an independent 2026 replication of ORB found it gross-positive but **net zero**

State which of these applies to IDX, and why.

**Data:** the minute-bar store `data/frozen/stockbit-flow-bars-v002/` (frozen, sha256
`fa7f07b3…`, 2025-01-02 → 2026-04-28, 77.6M rows, on the production host only), plus the live
`stockbit_flow_bars` in production `walkforward.db` for 2026-04-28 onward.

Columns: `bar_time`, `price` (the last trade in the minute, not an OHLC bar), `buy_lot` /
`sell_lot` / `buy_freq` / `sell_freq` / `net_value` / `delta`.

- **Check first:** whether the lot and frequency columns are **cumulative within the day**. A quick
  look suggests so. If they are, derive per-minute flow by differencing.
- **Pre-open auction data:** say whether the auction's indicative price or imbalance exists anywhere
  (the store starts at 09:00). If it doesn't, the imbalance proxy is the first-minute (09:00) signed
  flow and the open-vs-previous-close gap.

**Contamination disclosure (planner, 2026-10-07):** the planner has already read **descriptive**
statistics on the frozen 2025-01 → 2026-04 IDX30 sample:
- the per-15-minute volatility profile
- the share of days whose high or low is set in the first 15 minutes (high 46.7%, low 33.8%,
  either 75.6%)
- the first-15-minute share of the day's range (median 41%)

Those are not directional opening-move → later-return statistics, but the high-vs-low asymmetry
is weakly directional. So:
- treat **2025-01 → 2026-04-28 as SEEN** for class O
- any later O test's confirmation sample is **2026-04-28 → onward** (live DB)
- say how many sessions that gives today, and when it would reach a usable n

**Report for O (feasibility only; no outcomes):**
- **Counts:** sessions and ticker-days per universe (IDX30, LQ45, ADV20 ≥ Rp 10 bn) in the seen
  window and the clean window.
- **Imbalance proxy:** its definition, and the share of ticker-days where it can be computed.
  Inputs (first-minute flow, gap) must be known by 09:01 at the latest.
- **Power:** from pre-09:15 volatility only, i.e. the minute returns before the decision minute.
  Give the smallest detectable mean reversal over 09:15 → 10:00 and 09:15 → close, at the bar,
  under both censuses (276 / 561), with independent n and with n clustered by date.
- **Cost reality:** IDX round-trip fees and tax of about 0.4%, plus the tick size relative to price
  (0.3–1.3% on mid-priced names). Give the share of IDX30 / LQ45 ticker-days where one tick is
  ≤ 0.2% of price.
  - State plainly whether any intraday effect could beat costs.
  - **The preferred framing is execution timing:** the owner's existing entries (sniper limits,
    EOD-plan buys) choosing *when* in the first hour to execute, at no extra round trip. Follow X1's
    overlay logic, while noting that X1 itself came back NULL.
- **Prior coverage:** crypto ORB (port 5002, separate market, not counted); broad_search_v2
  A-OPEN; the D-059 cost model; any `intraday` / `MTF` studies in the registries.
- **A D-070 mechanism D-entry draft** (D-0xx) if O passes the above.

**No outcomes:** no price after the decision minute (09:15 by default; declare it) may be used,
for any ticker-day, in either window. Volatility comes only from minutes before the decision
minute.

Add O to `COMBINED_RANKING.md` next to classes A–N.
