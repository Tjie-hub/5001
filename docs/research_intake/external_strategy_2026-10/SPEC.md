# SPEC — EXT-BSJP: IDX retail "beli sore jual pagi" (close → next-morning) · Phase A

**Date:** 2026-10-01 · **Status:** PHASE A SPEC (docs only). **Not registered.** No hypothesis id,
no family slot, no gatekeeper run. **Owner decision 2026-10-01:** proceed with R1 (BSJP) from
`RETAIL_IDX_SURVEY.md`.
**Branch:** `spec/external-strategy-intake` · **Gate to Phase B:** P1 (research-fence cutover) must
have landed; then a Rule Card (`research/rulecard/`, D-055) is frozen from this SPEC before any
outcome is computed.

## 0. Snooping log (what has and has not been looked at)

| Looked at | When | Purpose |
|---|---|---|
| Video claims (win rates, returns) | 2026-10-01 | intake — treated as marketing, §6 |
| **Signal counts only** per variant, local `walkforward.db` snapshot (to 2026-07-29) | 2026-10-01 | power planning, §7 |
| **Any forward (next-open / next-day) return of any event** | **never** | — |

Nothing in this SPEC was chosen after seeing an outcome. Every threshold below is the source's own
number; where the source is ambiguous the SPEC picks a default **before** data and lists the
ambiguity in §9.

## 1. Source of record (verbatim, grep-verifiable)

All in `SOURCE/retail_idx/` (auto-transcripts via NotebookLM; NotebookLM full text has no
timestamps, so references are file + exact string). Quotes below were grep-checked 2026-10-01.

| Var | File | Rules as stated (verbatim Indonesian) |
|---|---|---|
| **a** | `YT_5zoKb511hL8_*` | "harga kemarin ditutup naik lebih dari 5%"; "Open lebih dari SMA 20 and close kurang dari SMA 20"; value "lebih dari Rp1 miliar"; screen "jam 1551 sampai dengan 15.58"; TP "harga beli ditambah 2%" (order booking, next morning); "minus 2% Cut loss" |
| **b** | `YT_Vt0zI0v0Bsk_*` | "kenaikan harga saham hari ini minimal 10%"; "nilai transaksi hari ini minimal 1 miliar"; "beli pucuk"; sell next morning |
| **c** | `YT_yE0qlHaz1ck_*` | "kenaikan baik itu high ataupun close minimal 20%" (DSI: high > previous close × 1,2); "nilai transaksi minimal 10 miliar"; exclude "uma repo tidak dijamin sedang cumdate dividen bad news"; BSJP entry at the close; SL "2% di bawah harga beli" |
| **d** | `YT_gKzpAzVl3Xo_*` (Kokocuan) | "nilai transaksi sebesar 5 miliar 10 miliar"; price "naik dalam beberapa persen tertentu" (unquantified); "maksimal beli tuh tiga saham doang dalam sehari"; "belinya jam 15.50"; "besok paginya jual" |
| e | `YT_Le-wAwIjLHM_*` | AmiBroker "JJS Cetar" fractal-breakout bot — rule not disclosed → **excluded** (§4) |

## 2. Mechanism (hypothesis, not assumption)

**Statement.** Stocks that drew attention today (large up-move, high value) close into the
pre-closing auction with unmet demand; attention-driven retail buying at the next open lifts the
open above the close. BSJP harvests that close → open gap.
**Loser.** Retail buyers who chase at the next open (the BSJP exit sells to them).
**Barrier.** No practical IDX short side; ARA locks ration supply at the limit, pushing unmet
demand into the next session.
**Competing prediction (must be tested, not ignored).** The same attention literature predicts the
open is *overpriced* and reverses intraday — that favours the pure next-open exit (E1) over
holding into the session (E2). And variants a/c buy names already up 5–20%: short-horizon reversal
predicts the opposite sign.

**Literature — tag [M] (from memory, NOT admissible as a prior until verified to [V]):**
- Berkman, Koch, Tuttle & Zhang (2012), "Paying Attention: Overnight Returns and the Hidden Cost
  of Buying at the Open", JFQA — high-attention stocks: high overnight return, intraday reversal.
- Lou, Polk & Skouras (2019), "A tug of war: Overnight versus intraday expected returns", JFE.
- IDX-specific overnight/limit-hit evidence: **none located yet** — Phase A open item §9-Q1.

With no verified IDX literature this is a **Tier N** card (`research/rulecard/card.py`:
t ≥ 3.0 and DSR ≥ 0.95), not Tier R.

## 3. Formal rules (frozen defaults)

Daily bars from `ohlcv` (`is_final=1`), split-adjusted per `corporate_actions` (existing
double-adjustment protection). Day *t* = signal/entry day, *t+1* = next trading day
(`trading_calendar`).

**Common definitions**
- `value_t` = close_t × volume_t (Rp). The DB has no traded-value column; this is an approximation
  (true value uses each trade's price) — §8.
- `ret_t` = close_t / close_{t-1} − 1.

**Event filters (per variant)**

| Var | Filter on day *t* (all must hold) |
|---|---|
| a | close_{t-1}/close_{t-2} − 1 > 5% **and** open_t > SMA20_t **and** close_t < SMA20_t (SMA20 of close, incl. day *t*, needs 20 bars) **and** value_t > Rp1B |
| b | ret_t ≥ 10% **and** value_t ≥ Rp1B |
| c | high_t ≥ 1.2 × close_{t-1} **and** value_t ≥ Rp10B **and** no dividend ex-date at *t+1* |
| d | ret_t > 0 **and** Rp5B ≤ value_t ≤ Rp10B; then **at most 3 names per day**, ranked by ret_t descending (the source gives no ranking; this default is fixed here, §9-Q3) |

**Entry fill (close-auction model — NOT the repo's P3 next-open default).** BSJP enters in the
pre-closing call auction, so the fill is close_t. The P3 convention (fill at next session's open)
exists for *intraday-decided* live signals and does not describe this strategy; using it would
erase the very return being tested.
- **Unfillable entry:** if close_t is at the ARA limit (close_t ≥ ARA(close_{t-1}) rounded down to
  the tick grid), the closing auction had no offer → **no trade** (P4-2 fillability authority,
  `engine/exits/price_limits.py`, applied to the *entry*). Expected to bind hard on b and c.
- Decision at 15:50 uses intraday information that daily bars only know at the close; the SPEC
  accepts filters on day-*t* close as the ~15:50 state (look-ahead of ≤10 minutes) and flags it §8.

**Exit models (both pre-declared; E1 is primary)**
- **E1 (primary) — "jual pagi":** sell at open_{t+1}. Pure overnight return. Unfillable if
  open_{t+1} is ARB-locked (no bid) → hold to close_{t+1} (conservative).
- **E2 — order-book TP/SL (variants a, c as stated):** TP at entry × 1.02, SL at entry × 0.98,
  evaluated on bar *t+1*: if open_{t+1} ≥ TP → fill at open; if open ≤ SL → fill at open; else if
  high ≥ TP and low ≤ SL in the same bar → **SL first** (daily bars cannot order them; pessimistic);
  else TP or SL if touched; else exit at close_{t+1}.
- **Success** = realized net P&L > 0. The sources' "success = intraday high ≥ +2%" definition is
  **not** used (it counts touches, not fills).

**Costs.** Round-trip 0.60% (D-059 cost authority) **plus** P4-6 liquidity-scaled slippage by
ADV as-of *t* (P4-1 as-of discipline). Gross results are reported but never used for a decision.

## 4. Multiplicity family (declared now, append-only from registration)

Family **EXT-BSJP** = {a, b, c, d} × {E1, E2} = **8 cells**. e is excluded (rule undisclosed).
DSR trial count = 8 from the first run. Per D-028 / PG-3 the family may only be widened by a
governance amendment, never narrowed; a dropped cell still counts.

## 5. Estimand and decision

- **Primary (per cell):** mean **net** return per trade. Events cluster by date (many names on the
  same day share market moves) → standard errors **clustered by trade date** (or day-level
  portfolio: equal-weight the day's trades, then NW t on the daily series — Phase B picks one in
  the Rule Card before running; default = day-level portfolio, NW lag 5).
- **Benchmark/null:** the unconditional close → next-open return of the same universe on the same
  dates (removes market-wide overnight drift).
- **Hurdle (Tier N):** t ≥ 3.0 on net, DSR ≥ 0.95 at trials = 8, and positive net in ≥ 4 of the 5
  calendar years. Out-of-sample: the last 12 months of data held out and evaluated once.
- **Regime breakdown** reported (BULL/BEAR/SIDEWAYS, `research/regime/`), never used to rescue a
  failed cell (NR7 lesson).

## 6. Claimed performance — unverified marketing

| Var | Claim | Why it is not evidence |
|---|---|---|
| a | 13/16 = 81% win, one December | n = 16, one month, success = high ≥ +2% |
| c | 43/45 = 96% win, one month | success = **high** > 2% (touch, not fill); top gainers at ARA unfillable at close |
| d | ~70% win, 1–2% gross/trade, 5–25%/month | self-reported, no sample, gross of costs |

## 7. Data-requirements check (local snapshot, signal counts only)

Local `data/walkforward.db` (Windows mirror; canonical production DB is longer): `ohlcv` final bars
2021-07-05 → 2026-07-29, 959 tickers, 1,055,598 rows.

**Signal counts (no outcomes computed), before the ARA-entry exclusion:**

| Var | 2021H2 | 2022 | 2023 | 2024 | 2025 | 2026H1 | Total |
|---|---|---|---|---|---|---|---|
| a | 155 | 309 | 282 | 239 | 421 | 394 | **1,800** |
| b | 1,367 | 2,008 | 1,615 | 1,685 | 3,491 | 2,203 | **12,369** |
| c | 670 | 889 | 658 | 599 | 1,684 | 1,124 | **5,624** |
| d (pre-cap proxy) | 2,149 | 4,046 | 4,320 | 4,029 | 4,948 | 3,118 | 22,610 (≤ 3/day after cap) |

Effective n is the number of **distinct trade dates** (≤ 1,216 in this snapshot), not events — power must be
planned on the day-level series (Phase B, from a planning σ that does not use these events'
outcomes).

| Requirement | Available? |
|---|---|
| OHLC + volume daily, split-adjusted | **yes** (`ohlcv`, `corporate_actions` split) |
| Dividend ex-dates (variant c exclusion; E1 across ex-date) | **yes** (`corporate_actions` dividend, 2,069 rows) |
| Trading calendar / suspensions | **yes** (`trading_calendar`, `suspension_events`) |
| Traded value | **approx only** (close × volume) |
| ARA/ARB band per date | **partly** — `price_limits.py` encodes the 2023 symmetric table only; 2021–2023 rules differed (§9-Q2) |
| UMA flags, "efek tidak dijamin", repo status (variant c exclusions) | **no** |
| Special-monitoring-board / full-call-auction membership | **no** — material: those stocks' "close" is a periodic-auction price |
| Delisted/inactive names (survivorship) | **weak** — only 14/959 flagged inactive (P4-7) |
| 15:50 intraday state, 09:00–09:30 next-morning path | **no** (stockbit_flow_bars coverage too thin) — daily-bar proxies used |

## 8. Known model gaps (documented, not silent)

1. Day-*t* close used as the 15:50 decision state (≤ 10-min look-ahead into the closing auction).
2. Traded value approximated by close × volume.
3. E2 intrabar ordering unknowable from daily bars → pessimistic SL-first.
4. Variant c's UMA / not-guaranteed / bad-news exclusions not implementable → c is tested without
   them; this is a deviation from the source and is reported as such.
5. Survivorship: universe built from currently-listed names (P4-7 open).
6. Special-board stocks not excluded (no data) — risk of fake fills at auction prints.

## 9. Open questions for the Owner (answer before the Rule Card freezes)

- **Q1.** Verify the [M] literature (§2) to [V] and search for IDX overnight / limit-hit studies.
  If none, Tier N stands.
- **Q2.** Historical ARA/ARB regimes 2021-07 → 2026: which BEI rule applied on each date? The
  entry-unfillable test needs the per-date ARA. Default if unanswered: tier table as in
  `price_limits.py` for all dates (ARA side), flagged as an approximation.
- **Q3.** Variant d's "naik dalam beberapa persen tertentu" is unquantified. Default fixed here:
  ret_t > 0, top-3 by ret_t. Alternative would be a new cell (widens the family).
- **Q4.** Do we want the data for special-board/UMA exclusions acquired before Phase B (cleaner c)
  or test as specified with the gaps in §8?
- **Q5.** Universe: all listed (as the videos screen) — default — or liquid preset
  (`liquid_idx_v1`)? Changing it later counts as a new cell.

## 10. Boundaries

- Phase B runs only in `research/` against the research fence; results go to the gatekeeper as a
  hypothesis. **Nothing is added to `engine/` or the scanner** unless a PROMOTE decision and a
  forward test exist (invariants 4, 9, 10).
- No `docs/research_programs/P-M/**` file is touched; this is not a P-M hypothesis.
- If the family fails, it is filed in `FAILURE_REGISTRY` with all 8 cells — including the ones
  that looked best.
