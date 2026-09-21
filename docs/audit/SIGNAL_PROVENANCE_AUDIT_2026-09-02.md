# Signal Provenance Audit — Walk-Forward Scanner vs EOD / Premarket

**Date:** 2026-09-02 · **Branch:** `ops/hardening-2026-07-10` @ `9b6e380`
**Authority:** point-in-time audit record (generated; superseded, never edited)
**Scope:** read-only. No production signal logic altered. No production data modified.
**DB inspected:** `data/walkforward.db` (8.5 GB, WAL, read-only URI), `data/research.db`

---

## 0. Headline

The Walk-Forward scanner **has not been able to emit a single BUY signal since 2026-07-01**
(42 trading sessions), and nothing in the system reports this. Every signal the operator has
seen since then came from the EOD and Premarket pipelines, which never consume walk-forward
output at all.

| Measurement | Value |
|---|---|
| Live WF scanner BUY signals, last 42 sessions | **0** (last: 2026-07-01, VKTR / Liquidity Sweep) |
| Tickers with ≥1 admissible strategy | **0 of 877**, across all 4 regime bands |
| APPROVED Edge Registry entries | **0** (1 SHADOW: `NR7_BULL v2`, demoted 2026-08-19 per D-029) |
| Gatekeeper PROMOTE decisions, ever | **0** (5 decisions, all `NR7 Breakout`, all REJECT at `walk_forward`) |
| `paper_trades` rows | **0** |
| Cohorts under forward test | **1 of 3**, and it tracks only the SELL side |

---

## 1. Architecture and data flow

### 1.1 Component locations

The prompt named `engine/walkforward_multi.py`. **That file does not exist.** Walk-forward lives
in `research/walkforward_multi.py` — moved across the research/production boundary in M2, and
production may no longer import it (CI-enforced, `tests/test_architecture_boundary.py`).
**No production code path runs walk-forward.** Production reads only the table it leaves behind.

| Component | Actual path | Side | Role |
|---|---|---|---|
| walkforward_multi | `research/walkforward_multi.py` | research | Rolling OOS backtest + metrics |
| refresh_wf_scores | `research/jobs.py:57` | research | Weekly batch → `wf_scores`, `wf_edge` |
| wf_edge DAO | `engine/wf_edge.py` | fenced | Holds write SQL; only research may call |
| strategies | `engine/strategies.py` (2,662 ln) | shared | `STRATEGY_FUNCS` (backtest) + `_CHECKER_DISPATCH` (live) |
| scanner | `scheduler/scanner.py:1364` | production | `scheduled_multi_strategy_scan()` |
| EOD plan | `scheduler/jobs.py:1202` | production | `run_eod_trade_plan()` 16:40 WIB |
| Premarket | `scheduler/jobs.py:1003` | production | `run_premarket_firm_scan()` 08:35 WIB |
| Forward test | `forward_testing/` | production | Shadow ledger, 18:30 WIB |

### 1.2 Table ownership

| Table | Written by | Read by | Rows | Latest |
|---|---|---|---|---|
| `wf_edge` | `research/jobs.py` via `engine/wf_edge.py` | `scanner._edge_selectable`, `edge_enrich`, `routes/` | 3,869 | 2026-08-28 |
| `scheduled_signals` | `scanner._save_signals_to_db` | `forward_testing` SignalAdapter, dashboards | 11,288 | 2026-09-01 |
| `reversal_watchlist` | `screener/reversal_filter.py` (16:15) | `trade_plan` (R), `unified_watchlist` (REVERSAL) | 150 | 2026-09-01 |
| `daily_screen` | `screener/screener_jobs.py`, `screener/db.py` | `trade_plan` (S, V), `agent_firm_context` | 80,526 | 2026-09-01 |
| `watchlist_premover` | `engine/premover_detector.py` (16:30) | `unified_watchlist` (PREMOVER) | 17,512 | 2026-09-01 |
| `regime_watchlist` | `engine/watchlist.py` (hourly scan) | `unified_watchlist` (BEAR_DIP) | 249 | 2026-09-01 |
| `agent_decisions` | `engine/agent_firm/firm.py` | `trade_plan` (P), dashboards | 2,729 | 2026-09-01 |
| `watchlist_snapshot` | `engine/trade_plan.py::record_snapshot` | `diff_watchlist` (reporting only) | 141 | 2026-09-01 |
| `candidate_watchlist_snapshot` | `engine/watchlist_report.py` | `watchlist_report` diff (reporting only) | 1,017 | 2026-09-01 |

### 1.3 Pipeline A — Walk-Forward → live scanner (Cohort 1)

```
RESEARCH  research/walkforward_multi.py   12m train / 3m test, ~16 windows/ticker
    |                                      cron: Fri 16:05 (deploy/crontab:34)
    v
OOS results   per-window metrics, test-window trades only
    v
wf_edge       pooled trade-weighted expectancy_pct, n_trades >= 20      3,869 rows
    v
strategy admission   adaptive_strategy_selector()   scheduler/scanner.py:892
    |   regime map -> registry_governance() -> _edge_selectable() -> disabled_strategies
    |   *** RESULT TODAY: [] for every ticker, every regime ***
    v
LIVE SCANNER  check_current_entry_signal()          *** never reached ***
    v
signal        scheduled_signals                      *** 0 BUY since 2026-07-01 ***
    v
risk / veto / Agent Firm                             *** never reached ***
    v
execution     paper_trade.open_trade()               *** paper_trades: 0 rows ***

SIDE BRANCH (still live, bypasses all of the above):
scan_distribution_signals()  scheduler/scanner.py:1312
    stockbit_flow composite_score <= -3 AND verdict LIKE '%BEARISH%'
    AND regime != BULL AND close[-1] < close[-5]
    -> scheduled_signals signal_direction='SELL'      10,930 rows, 120 in Sep
    -> forward_testing SignalAdapter -> ft_signal(SHORT) -> ft_shadow_trade
```

### 1.4 Pipeline B — Premarket (Cohort 3)

```
reversal_watchlist(latest)   regime_watchlist(active|promoted)   watchlist_premover(latest)
      REVERSAL                       BEAR_DIP                          PREMOVER
          \                             |                                /
           +----------------------------+-------------------------------+
                                        v
                  build_unified_watchlist()   engine/unified_watchlist.py
                  weighted union, +15 confluence bonus, cap 40 rows
                                        v
                  select_top_liquid_longs(top_n=3)   engine/liquidity.py
                                        v
                  edge_enrich -> veto.apply_vetoes   *** EDGE_SCORE_MODE=shadow: LOG ONLY ***
                                        v
                  build_candidate_context -> Agent Firm evaluate_staged
                                        v
                  record_snapshot(strategy='premarket')      30 rows, 16 dates
```

### 1.5 Pipeline C — EOD (Cohort 2)

```
reversal_watchlist(date,long)  daily_screen(bullish)  daily_screen(vol_ratio>=5)  agent_decisions(premarket,approve,SAME DAY)
         R                            S                       V                            P
          \                           |                       |                           /
           +--------------------------+-----------------------+--------------------------+
                                        v
                  gather_long_candidates()   engine/trade_plan.py:43
                                        v
                  candidate_score()  R:2.0+conv/50  P:2.0+2*conf  S:1.0  V:min(vr/50,1)
                                        v
                  select_top(n=8)
                                        v
                  edge_prescreen (Tier A only)   *** EDGE_SCORE_MODE=shadow: LOG ONLY ***
                                        v
                  Agent Firm -> rank_approved() -> record_snapshot(strategy='eod')
                                                                 111 rows, 18 dates
```

### 1.6 Where they converge

Two places, neither of them walk-forward:

1. **Premarket(D) → EOD(D)**, same calendar day, via source tag `P`. This is the only real
   coupling, and its direction is the reverse of the intended architecture (§5).
2. **`reversal_watchlist`** is read by both (as `R` in EOD, `REVERSAL` in premarket). In practice
   this shared input almost never survives: 29 of 30 premarket snapshot rows came from
   `BEAR_DIP`+`PREMOVER`, sources EOD never reads.

`wf_edge` reaches Pipelines B and C through exactly one function —
`engine/edge_enrich.py::_best_wf_edge` — and that path is inert because `EDGE_SCORE_MODE=shadow`.
**No EOD or Premarket name has ever been filtered by walk-forward evidence in production.**

---

## 2. Walk-Forward mechanism

`run_walk_forward()` splits each ticker's OHLCV into rolling 12-month-train / 3-month-test windows
stepping by 3 months, keeping windows with >60 train bars and >15 test bars (~16 non-overlapping
OOS windows/ticker on the 5-year corpus; observed 14.8–16.0).

**It never fits anything on the training window.** The train slice supplies only a 60-bar indicator
warm-up tail prepended to the test slice; trades with `entry_date < test_start` are then discarded.
Every strategy runs with hard-coded parameters.

> **Terminology finding.** This is *rolling out-of-sample backtesting*, not walk-forward
> optimisation. That is not a defect — a fixed-parameter rolling OOS test is honest — but it
> relocates the leakage risk entirely: it is not inside the loop, it is in how the parameters and
> the strategy roster were chosen *before* the loop ran.

### 2.1 How `wf_edge` is produced (`engine/wf_edge.py:42`)

```
n              = Σ window.total_trades                                 # pooled OOS sample
if n < 20: exclude                                                     # N_MIN_TRADES, no zero-fill
expectancy_pct = Σ(window.avg_pnl_pct × window.total_trades) / n        # trade-weighted POOL
sharpe         = Σ(window.sharpe      × window.total_trades) / n
win_rate       = Σ window.total_winners / n × 100
consistency_pct = % of windows with total_return_pct > 0                # carried, not recomputed
```

`expectancy_pct` = **net-of-cost mean percentage P&L per OOS trade**, pooled across every completed
test window (Σ over trades, not a mean of per-window means). Costs applied on both legs inside each
strategy via `apply_costs()`. Recomputed weekly (Fri 16:05 WIB); live table last written
`2026-08-28 16:05`, run_id `08ff0ca6…`, 2h23m over 959 tickers.

### 2.2 Leakage assessment

| Path | Verdict | Evidence |
|---|---|---|
| Train/test overlap | CLEAN | `[cur, train_end)` / `[train_end, test_end)`; asserted disjoint + ordered by new tests |
| Test-window reuse | CLEAN | step = test_months → OOS windows tile without overlap; each bar scored once |
| Warm-up contamination | CLEAN | filtered by `entry_date >= test_start`; equity rebuilt from kept trades |
| Within-bar look-ahead | CLEAN | NR7 reads bar `i-1`, enters at bar `i` open with `open > prev.high`, SL checked before TP |
| Partial-bar contamination | CLEAN | research loads `final_only=True`; `is_final=0` excluded (Phase 2A item 2.1) |
| Aggregation hygiene | CLEAN | completed windows only; thin cells excluded, never zero-filled |
| **Parameter-selection leakage** | **PRESENT** | frozen constants chosen with whole-corpus visibility; windows are OOS to *execution*, not to *parameter choice* |
| **Strategy-selection leakage** | **PRESENT** | `_DEFAULT_DISABLED` names the 8 strategies "the 2026-07-04 re-baseline proved has NEGATIVE pooled OOS expectancy" — selected by reading the same `wf_edge` the survivors are judged on |
| **Multiplicity uncontrolled** | **PRESENT** | 3,869 cells pass N≥20; admission is a bare `expectancy_pct > 0` per cell. No FDR, no DSR, no family scoping at the gate |
| Survivorship | MITIGATED | WF scores the whole corpus (item 2.4); but the live universe is `idx_tickers`, ~127 days stale |
| Corporate-action basis | MISMATCH | research on split-**adjusted** prices, live scanner on **raw** (`data/loaders.py:77-80`) |

### 2.3 Findings

**L-1 (Critical) — `wf_edge` does not measure the rule the live scanner runs.**
The backtest calls `STRATEGY_FUNCS[name]`. The live scanner calls `check_current_entry_signal()`,
which dispatches to `_CHECKER_DISPATCH[name]` **and then applies a weekly multi-timeframe trend
gate** (`engine/strategies.py:1338`) that no backtest function applies. Nine of eleven live checkers
are subject to it (`_WEEKLY_GATE_BYPASS` exempts only Crash Recovery, Panic Rebound, Liquidity
Sweep). The live signal set is a proper subset of the backtested one, filtered by a rule whose
effect on expectancy has never been measured. `wf_edge` is evidence about a rule that is not the
deployed rule.

**L-2 (Critical) — the live entry price is retrospective.**
`check_nr7_signal` returns `details['price'] = df.iloc[-1]['open']` — today's opening print — and
`scheduled_multi_strategy_scan` passes it straight to `open_trade(ticker, entry_price)`
(`scanner.py:1760, 1807`). The scan runs at 10:05, 11:05, 14:35. At 14:35 you cannot buy at 09:00's
open. The bias is systematically favourable because the signal condition *is* "the open gapped above
the setup bar's high". Latent (no trade has used this path) but must be fixed before any BUY
strategy is re-admitted, or a forward test will measure a fill nobody can get.

**L-3 (Material) — `edge_enrich` attributes the wrong strategy's statistics.**
`_best_wf_edge()` selects `ORDER BY expectancy_pct DESC LIMIT 1` for the ticker — the ticker's
*best* strategy, regardless of which strategy or source produced the candidate. A reversal-watchlist
name is judged against, e.g., a Liquidity Sweep row's `n_trades` / `win_rate` / `expectancy_pct`,
which are exactly the fields Tier B of `engine/veto.py` (`s1`–`s4`) gates on. Inert under
`EDGE_SCORE_MODE=shadow`; becomes a live correctness bug the moment the mode is set to `enforce`.

---

## 3. The live scanner: why nothing fires

Admission chain in `adaptive_strategy_selector()`:

1. `detect_regime(df)` → BULL / BEAR / SIDEWAYS; BULL splits on ADX ≥ 45.
2. `_REGIME_STRATEGY_MAP[band]` → 3–6 candidate names.
3. Counter-trend names (Crash Recovery, Panic Rebound) must clear `registry_governance()` —
   a frozen APPROVED universe containing the ticker.
4. Everything else → `_edge_selectable()`: registry-governed names need APPROVED + ticker in
   universe; a `'SHADOW'` sentinel is excluded outright with no fallback; only genuinely
   unregistered names fall through to the legacy `wf_edge expectancy_pct > 0` query.
5. If nothing selected **and** the band had no counter-trend candidate at all, the broad fallback
   `_edge_selectable(conn, ticker, None)` runs — which is registry-only, so it needs APPROVED.
6. `_get_disabled_strategies()` strips the disabled list; macro-panic / event guards strip the
   momentum family.

| Strategy | Regime map | Registry | wf_edge rows | Disabled? | Checker | Admitted? |
|---|---|---|---|---|---|---|
| NR7 Breakout | BULL_MOD, BULL_STR | **SHADOW** (NR7_BULL v2) | 54 (43 >0) | no | yes | **no** — SHADOW excluded outright |
| Trend Following Breakout | BULL_MOD, BULL_STR | UNREGISTERED | **0** | no | yes | **no** — no wf_edge row exists |
| Crash Recovery | BEAR | UNREGISTERED | 0 | no | yes | **no** — counter-trend needs APPROVED |
| Panic Rebound | BEAR, SIDEWAYS | UNREGISTERED | 0 | no | yes | **no** — counter-trend needs APPROVED |
| Liquidity Sweep | BEAR, SIDEWAYS | UNREGISTERED | 724 (154 >0) | **yes** | yes | **no** — disabled_strategies |
| momentum | BULL_MOD, BULL_STR | UNREGISTERED | 340 (85 >0) | **yes** | yes | **no** — disabled_strategies |
| vol_weighted | BULL_MOD, BULL_STR | UNREGISTERED | 780 (131 >0) | **yes** | yes | **no** — disabled_strategies |
| vwap_reversion | all bands | UNREGISTERED | 854 (135 >0) | **yes** | yes | **no** — disabled_strategies |
| conservative | BULL_STRONG | UNREGISTERED | 797 (83 >0) | **yes** | yes | **no** — disabled_strategies |

**S-1 (Critical) — zero strategies are admissible, for any ticker, in any regime.**
Replaying the exact admission chain against all **877 tickers** in `wf_edge` for all four regime
bands yields **0 tickers with ≥1 admitted strategy** in every band. Not marginal — no candidate
survives any path. The second entry point, `daily_signal_scan()` → `scan_momentum_signals()`, is
independently closed by two gates (`momentum` disabled; `registry_governance("Momentum Following")`
is not a set). Corroborated by the ledger: 358 BUY rows all-time, last 2026-07-01, none in 42
sessions since; `paper_trades` empty. Every gate is doing what it was designed to do — the
composite outcome is a silently dead buy-side with no alarm on it.

**S-2 (Material) — stale `wf_edge` has no defined scanner behaviour.**
`engine/edge_enrich.py` warns at `_WF_STALE_DAYS = 7`. `scanner._edge_selectable` never reads
`last_computed` — a 2019 row is selected like a fresh one. Seven live rows still carry
`last_computed = '2026-06-30 09:21'` with NULL `run_id`, orphaned from the 2026-08-28 refresh.

The only live signal path remaining is `scan_distribution_signals()` — a pure heuristic on
`stockbit_flow` with no `wf_edge` gate, no registry check, no disabled-strategies check, no
liquidity or sector filter, running over the whole universe. It produced 10,930 of the 11,288 rows
in `scheduled_signals`.

---

## 4. EOD assessment

Source tags confirmed exactly as specified. **None is walk-forward derived.**

| Tag | Query | Generator | Statistical basis |
|---|---|---|---|
| **R** | `reversal_watchlist WHERE scan_date=? AND direction='long'` | `screener/reversal_filter.py`, 16:15 | Broker-flow heuristic. No OOS study. |
| **S** | `daily_screen WHERE date=? AND signal='bullish'` | `screener/screener_jobs.py` | Technical screen. No OOS study. |
| **V** | `daily_screen WHERE vol_ratio >= 5.0` | same row as S | Threshold heuristic. Not independent of S. |
| **P** | `agent_decisions WHERE strategy='premarket' AND decision='approve'` | LLM firm, same morning | LLM judgement. No OOS study. |

No EOD source reads `wf_edge`, `wf_scores`, `STRATEGY_FUNCS` or the Edge Registry. The single point
where walk-forward could touch EOD is `edge_prescreen()`, which applies Tier A directional vetoes
only (never the `wf_edge`-based Tier B gates) and is log-only under `EDGE_SCORE_MODE=shadow`.

`candidate_score()` weights (R = 2.0 + conviction/50, P = 2.0 + 2×confidence, S = 1.0,
V = min(vol_ratio/50, 1.0)) have no fitted or validated origin; the docstring justifies them by
argument, which is a reasonable prior, not evidence.

The pool is dominated by the weakest source: **88 of 111** EOD snapshot rows carry `["S","V"]` —
the same `daily_screen` row counted twice — against 3 rows of pure `R`.

---

## 5. Premarket, and the EOD → Premarket architecture

Intended: `EOD plan → EOD snapshot → overnight carry-forward → premarket update → actionable list`.
Implemented: not this.

| # | Question | Finding |
|---|---|---|
| 1 | Does premarket consume the previous EOD snapshot? | **No.** `run_premarket_firm_scan()` contains no read of `watchlist_snapshot`, no `tp.get_snapshot()` call, no reference to `strategy='eod'`. It *writes* that table for its own diff but never reads EOD's rows. |
| 2 | Does it build an independent universe? | **Yes.** `build_unified_watchlist(DB_PATH)` from scratch, then `select_top_liquid_longs(top_n=3)`. |
| 3 | What does EOD have that premarket lacks? | `daily_screen` entirely — tags **S** and **V**, which supply **79% of EOD's approved rows**. Also the `P` tag and EOD's `candidate_score` ordering. |
| 4 | What genuinely new information arrives overnight? | Six jobs land after 16:40: VPIN (18:00), news (17:00 & 08:00), Stockbit screener (17:05), broker_flow (20:15), corporate actions (20:20), OHLCV reconciliation (21:00). Premarket uses only the market risk score and `build_candidate_context`'s per-ticker news / foreign-flow — and only for the 3 names it selected itself. |
| 5 | Which premarket inputs may legitimately override an EOD candidate? | Legitimately: overnight news, reconciled / CA-adjusted prices, settled broker flow, VPIN, market risk tier. **Not** `reversal_watchlist`, `watchlist_premover` or `regime_watchlist` — all three are written at 16:15–16:30, *before* the 16:40 EOD plan. Premarket's entire universe is built from data already on the table when EOD ran. |
| 6 | Can macro/regime remove or downgrade an EOD candidate? | **No.** Two independent reasons: premarket never loads EOD candidates; and the only deterministic macro gate (`apply_vetoes`, whose `EDGE_FLOOR`/`N_MAX` are regime-keyed) is log-only under `EDGE_SCORE_MODE=shadow`. Regime reaches the LLM as context and the Telegram header as text; it cannot mechanically demote anything. |
| 7 | Does premarket introduce new names? | **Almost exclusively.** Across 17 consecutive EOD→premarket transitions, **4 tickers** carried over. 13 of 17 shared **zero** names. |
| 8 | Intentional and empirically justified? | Intentional in the narrow sense (docstring: "informational only… auto-entry stays owned by the 16:30 premover EOD path"), but **no documented rationale and no empirical justification** for the universes being disjoint. No decision-log entry covers it. |
| 9 | Duplicated / conflicting logic? | **Both.** Two independent merge/rank/confluence implementations (`unified_watchlist` vs `trade_plan`), two incompatible source vocabularies, two ranking formulas, both feeding the same LLM firm and the same snapshot table. And the coupling that *does* exist runs backwards. |
| 10 | Does it harm forward testing? | **Yes.** With no carry-forward there is no "EOD prediction" to score against a "premarket revision" — the cohorts are disjoint samples, so premarket's effect on EOD candidates is **unmeasurable by construction**. And `select_top_liquid_longs(top_n=3)` is a severe, unlogged selection step: survivors are recorded, rejects are not, so the cohort is conditioned on an unobservable filter. |

### 5.1 Carry-forward evidence (every transition in the snapshot history)

| EOD date | n | Premarket date | n | Carried over | New in PM |
|---|---|---|---|---|---|
| 2026-07-30 | 8 | 2026-07-31 | 2 | *none* | 2 |
| 2026-07-31 | 8 | 2026-08-04 | 3 | *none* | 3 |
| 2026-08-04 | 2 | 2026-08-10 | 2 | NTBK | 1 |
| 2026-08-05 | 8 | 2026-08-10 | 2 | *none* | 2 |
| 2026-08-06 | 8 | 2026-08-10 | 2 | *none* | 2 |
| 2026-08-07 | 8 | 2026-08-10 | 2 | *none* | 2 |
| 2026-08-10 | 2 | 2026-08-11 | 3 | *none* | 3 |
| 2026-08-12 | 8 | 2026-08-13 | 3 | MAPI | 2 |
| 2026-08-14 | 2 | 2026-08-18 | 2 | *none* | 2 |
| 2026-08-18 | 8 | 2026-08-19 | 1 | DMAS | 0 |
| 2026-08-19 | 5 | 2026-08-20 | 1 | DMAS | 0 |
| 2026-08-21 | 8 | 2026-08-27 | 1 | *none* | 1 |
| 2026-08-24 | 8 | 2026-08-27 | 1 | JAST | 0 |
| 2026-08-26 | 8 | 2026-08-27 | 1 | *none* | 1 |
| 2026-08-27 | 4 | 2026-08-28 | 2 | *none* | 2 |
| 2026-08-28 | 8 | 2026-08-31 | 2 | *none* | 2 |
| 2026-08-31 | 5 | 2026-09-01 | 2 | *none* | 2 |

Source composition confirms the disjointness is structural: **29 of 30** premarket snapshot rows
carry `["BEAR_DIP","PREMOVER"]`; exactly one carries `["REVERSAL"]`. EOD never reads
`watchlist_premover` or `regime_watchlist`.

### 5.2 Architectural findings

**A-1 (Architectural) — premarket is a second, parallel discovery engine, not an overnight update.**
The intended flow is a *revision* operator: take yesterday's frozen belief, apply only what is
genuinely new, emit an updated belief. What is implemented is a second *generation* operator that
happens to run in the morning, on inputs that were already fully settled before the EOD job ran.
The two engines then share one snapshot table, one LLM firm and one Telegram channel — which makes
them look like stages of one pipeline in the reports, while being independent samples in the data.

**A-2 (Material) — the dependency that does exist runs backwards.**
`gather_long_candidates()` reads `agent_decisions WHERE strategy='premarket' AND decision='approve'`
for the *same* `date_str`, and `candidate_score` gives tag `P` the joint-highest base weight
(2.0 + 2×confidence, up to 4.0). The real flow is premarket(D) → EOD(D), with the LLM's morning
confidence entering the evening ranking as if it were an independent source. 18 of 111 EOD snapshot
rows carry `P`. Under the intended architecture this arrow must be reversed.

### 5.3 On the proposed future model

The redesign is sound and this audit supports it, with three non-optional conditions:

1. **The frozen EOD snapshot must be a real freeze.** `record_snapshot()` is `INSERT OR REPLACE`
   keyed on `(date, strategy, ticker)`; a same-day re-run silently rewrites history (now pinned by
   a characterisation test). Append-only and versioned is a prerequisite, not a refinement.
2. **It must carry a decision price and a rule.** Neither `watchlist_snapshot` nor
   `candidate_watchlist_snapshot` stores an entry price, signal timestamp, or exit rule. Without
   those, "EOD prediction quality" is not computable from the record — outcomes must be
   reconstructed from a separate price table, which is exactly what §7 had to do.
3. **Premarket must record its rejects, not only its survivors.** To measure "did premarket's
   changes improve or worsen outcomes", every EOD candidate must appear in the premarket record
   with a verdict — kept / vetoed / reprioritised, with the reason. Today `top_n=3` discards
   silently.

**Sequencing caveat:** reversing the arrow removes the `P` source from EOD, currently the
joint-highest-weighted tag. That is a change to signal generation and must be made deliberately,
with before/after cohorts kept separate.

---

## 6. Evidence classification (Part 6)

Classified strictly. Positive backtest returns, positive `wf_edge`, passing unit tests and Agent
Firm approval are all excluded as grounds for "proven".

| Pipeline | Class | Grounds |
|---|---|---|
| **WF scanner — BUY side** | **C — plausible, unproven** | Coherent code, clean rolling-OOS geometry, but selection leakage + uncontrolled multiplicity + L-1 rule mismatch. Zero live signals in 42 sessions → zero prospective data. Gatekeeper's only verdict on its only candidate is REJECT. |
| **WF scanner — SELL / distribution** | **D — invalid as an edge claim** | Never backtested, never gated, never registry-governed. It *is* forward-tested: 2,108 closed shadow shorts, mean net **−4.97%**, hit rate 26.2%, mean R **−0.34**. Forward evidence strongly negative for the short direction; run over the whole universe with no liquidity filter, so the cohort is dominated by micro-caps. |
| **EOD watchlist** | **C — plausible, unproven** | No OOS study for R/S/V/P. Weights hand-set. Retrospective reconstruction (§7) shows no edge over IHSG. |
| **Premarket watchlist** | **C — plausible, unproven** | No OOS study for REVERSAL / PREMOVER / BEAR_DIP. Never measured prospectively. Retrospective read is nominally positive but rests on 12 independent date-observations in one five-week regime, no pre-registration, no multiplicity control. |
| **NR7 Breakout (strategy)** | **B — historically studied, not prospective** | 54 tickers, 43 positive, pooled +1.63%/trade over 1,311 OOS trades — the only credible historical signature. But 5/5 gatekeeper runs returned REJECT at `walk_forward`, the registry demoted it APPROVED → SHADOW on 2026-08-19 (D-029), and it has produced **zero live signals ever**. |
| **Agent Firm** | **unmeasured** | 2,729 decisions with confidence values. No study links firm confidence to realised outcome. Its decisions are consumed as a ranking key (EOD tag `P`) without ever having been validated as predictive. |

---

## 7. Retrospective measurement of the existing record

Snapshots store names and dates but no prices, so outcomes were reconstructed: entry at the **next
session's open** after the snapshot date, exit at the close *h* sessions later, both legs through
the production cost model (`engine/exits/costs.py`), benchmarked against IHSG over the identical
window. Prices are the raw (unadjusted) `ohlcv` basis, so a split inside a window would distort a
row.

**This is not a forward test** — it is a look back at frozen name lists with the horizon chosen
after seeing the data. Reported to show what the existing record can and cannot support.

| Cohort | N | Hit | Mean gross | Mean net | Median net | 95% CI (net) | IHSG | Excess CI | PF |
|---|---|---|---|---|---|---|---|---|---|
| EOD · 5 sessions | 73 | 50.7% | +2.47% | +1.86% | +0.24% | [−0.80, +4.74] | +0.86% | [−1.66, +3.93] | 1.59 |
| EOD · 10 sessions | 52 | 38.5% | +0.21% | −0.39% | −1.16% | [−3.78, +3.27] | +1.89% | [−5.50, +1.27] | 0.92 |
| Premarket · 5 sessions | 23 | 73.9% | +8.58% | +7.93% | +5.89% | [+2.98, +13.06] | +1.45% | [+1.44, +12.01] | 6.25 |
| Premarket · 10 sessions | 17 | 52.9% | +5.29% | +4.66% | +3.15% | [−2.05, +12.01] | +2.84% | [−4.72, +9.09] | 2.38 |
| Distribution SHORT (realised) | 2,108 | 26.2% | — | −4.97% | −3.78% | — | — | — | ≪1 |

### Why the premarket number must not be believed yet

- **Effective sample size is 12, not 23.** 23 observations from 12 distinct dates and 16 distinct
  tickers, with DMAS appearing 4× and WIRG 3× on consecutive days — overlapping holding windows on
  the same position, counted as independent draws.
- **Collapsing to one observation per date changes EOD entirely.** Mean of per-date means:
  premarket **+11.85%** (sd 12.98% over 12 dates), EOD **−0.40%**. EOD's apparent +1.86% is an
  artifact of averaging across a few large winners on days with many candidates.
- **One regime, five weeks.** Every observation falls in 2026-07-30 → 2026-08-21, IHSG rising
  throughout.
- **Multiplicity.** Four cohort×horizon cells from one dataset, no correction, horizons not
  pre-registered.
- **Conditioned on an unobservable filter.** Only the 3 liquidity survivors, then only firm-approved
  names, reach the snapshot. Rejects are unrecorded.

Under the Research OS evidence model this is class K3 observational at best, and rule R2 applies:
a test that could not have refuted the hypothesis carries zero evidential weight. Twelve
date-observations in a single rising regime could not have refuted it.

---

## 8. Forward test — what exists, what is missing

`forward_testing/` is already a competent, information-boundary-preserving recorder. Extend it,
don't replace it.

| Required field | Status | Where |
|---|---|---|
| signal_date · ticker · strategy · direction | present | `ft_signal` |
| entry_price · planned entry · exit_rule | present | `ft_shadow_position`; rule via `ExitPolicyRegistry` |
| return_gross · return_net · estimated_cost | present | `pnl_pct` is net; `raw_entry_price` allows gross recovery |
| MFE · MAE · holding_period · R multiple | present | `ft_shadow_trade` |
| Entry strictly after signal bar | **enforced** | `resolver.next_open(ticker, signal_date)`; verified 0/2,111 violations |
| Costs on both legs | **enforced** | `apply_costs` at open and close; new test asserts a flat round trip loses |
| Duplicate handling | deterministic | `UNIQUE(signal_date, ticker, strategy, track)`; ingest idempotent |
| raw_signal_score / conviction | partial | `ft_signal.conviction` holds `flow_score` only |
| wf_edge at signal time | **missing** | no column; would have to be re-derived from a mutable table |
| strategy_version · config_hash | **missing** | `ft_strategy_version` is **empty**; both columns NULL on every row |
| market_regime at signal time | **missing** | not captured |
| source_tags · confluence | **missing** | EOD/premarket not ingested at all |
| Agent Firm decision · confidence · veto | **missing** | lives in `agent_decisions`, unlinked to `ft_signal` |
| Append-only guarantee | **missing** | no trigger; `watchlist_snapshot` is explicitly `INSERT OR REPLACE` |

**F-1 (Critical) — two of the three cohorts are not forward-tested at all.**
`SignalAdapter.ingest()` reads exactly one source table: `scheduled_signals`. EOD and Premarket
write to `watchlist_snapshot`, which nothing in `forward_testing/` reads. The only pipeline
currently producing signals the operator acts on is the only one with no forward-test ledger —
while the ledger that does run is fed exclusively by a heuristic short signal nobody trades.

### 8.1 Recommended design (NOT implemented — see §10)

Smallest correct change: a second adapter alongside `SignalAdapter`, reusing the existing
`ft_signal` / `ft_shadow_position` / `ft_shadow_trade` machinery unchanged.

```
# forward_testing/adapters/watchlist_adapter.py  (proposed)
WatchlistAdapter.ingest(run_date)
    reads   watchlist_snapshot WHERE strategy IN ('eod','premarket')
    writes  ft_signal(track='SHADOW', strategy='eod'|'premarket',
                      direction='LONG', source_table='watchlist_snapshot')
    plus    ft_signal_meta(signal_id, source_tags, confluence,
                           agent_decision_id, agent_confidence,
                           veto_reason, market_regime, wf_edge_snapshot,
                           strategy_version, config_hash)      # new, append-only

# Cohort 4 baselines — same adapter, cohort='baseline'
    IHSG buy-and-hold over each cohort's exact holding window
    equal-weight liquid universe (the select_top_liquid_longs input set)
    N random tickers drawn from that same universe, seeded and recorded
```

Two schema changes carry the append-only requirement: an `ft_signal_meta` table written once per
signal with no UPDATE path, and `BEFORE UPDATE` / `BEFORE DELETE` triggers on it that raise.
Cohorts stay separated by `ft_signal.strategy` and must never be pooled.

### 8.2 Statistical discipline for the evaluation period

- Report N, hit rate, mean/median gross and net, PF, expectancy, sd, Sharpe-like statistic, max
  drawdown, MFE/MAE, top/bottom decile — **per cohort**, never merged.
- Report the **per-date** statistic alongside the per-signal one. §7 shows they can have opposite
  signs.
- Bootstrap CIs blocked **by date**, not by signal — overlapping holds on the same name are not
  independent draws.
- Pre-register the horizon and the decision rule before the window opens; state the multiple-testing
  family explicitly (cohorts × horizons × strategies × regimes).
- Any tuning during the window contaminates it: close the cohort, record why, open a new one
  (mirrors `docs/RESEARCH_MASTER_PLAN.md` §3.2e).

---

## 9. Tests executed

**Full suite: 2,804 passed, 2 failed, 6m09s.** Both failures are `tests/test_news_filter.py`
(`module 'news_filter' has no attribute 'requests'`) — a pre-existing test defect that reproduces
when the file is run alone, unrelated to signal architecture, already on record from 2026-09-01.

Targeted runs, all green:
- `test_walkforward_metrics · test_walkforward_registry · test_edge_selector · test_adaptive_strategy · test_registry_lifecycle · test_trade_plan · test_unified_watchlist · test_strategy_specs · test_architecture_boundary · test_research_data_fence` → **128 passed**
- `tests/forward_testing/ · test_wf_edge · test_veto · test_edge_enrich · test_premarket_firm_scan · test_eod_trade_plan_job · test_t7_wf_edge_fallback_fix` → **239 passed**

### New: `tests/test_signal_architecture_audit.py` — 22 passed

The only file added. No production code modified. Several are deliberately *characterisation*
tests: they pin behaviour the audit found questionable, so changing it becomes a visible,
intentional edit rather than silent drift.

| Group | Assertion | Kind |
|---|---|---|
| Walk-forward | train ∩ test = ∅ for every window | invariant |
| Walk-forward | max(train.date) < min(test.date) for every window | invariant |
| Walk-forward | test windows never overlap across windows | invariant |
| Walk-forward | a window's trade count never exceeds its own test bars (warm-up excluded) | invariant |
| wf_edge | expectancy is the trade-weighted pool, provably not the mean of window means | invariant |
| wf_edge | n < 20 excluded, never zero-filled | invariant |
| Scanner | negative and zero expectancy never selected | invariant |
| Scanner | missing wf_edge row → empty selection | invariant |
| Scanner | SHADOW never falls back to legacy wf_edge, on either code path | invariant |
| Scanner | every non-disabled strategy in the regime map has a live checker | invariant |
| Scanner | **stale wf_edge (2019) is still selected** | characterisation |
| Watchlist | EOD (R/S/V/P) and premarket (REVERSAL/PREMOVER/BEAR_DIP) vocabularies are disjoint | invariant |
| Watchlist | **premarket does not read the EOD snapshot** | characterisation |
| Watchlist | **EOD reads same-day premarket approvals (arrow runs backwards)** | characterisation |
| Watchlist | snapshot round-trip preserves rank and sources exactly | invariant |
| Watchlist | **a same-day re-run silently overwrites a recorded snapshot** | characterisation |
| Watchlist | **snapshot schema carries no price, timestamp or exit rule** | characterisation |
| Forward test | fill is taken from the next open after signal_date | invariant |
| Forward test | live DB: 0 of 2,111 closed trades entered on/before the signal bar | data check |
| Forward test | costs worsen both legs; a flat round trip loses money | invariant |

---

## 10. Database evidence

All inspection read-only (`file:…?mode=ro`). No production data modified. A full
`PRAGMA integrity_check` was **not** attempted: it has timed out previously on the 8.5 GB WAL file,
and a broker-flow backfill was writing concurrently.

| Measurement | Value |
|---|---|
| `wf_edge` rows / distinct tickers | 3,869 / 877 |
| `wf_edge` by strategy | vwap_reversion 854 · conservative 797 · vol_weighted 780 · Liquidity Sweep 724 · momentum 340 · ORB 272 · **NR7 Breakout 54** · Volume Profile POC 30 · Inside Bar Breakout 18 |
| Positive expectancy | 691 of 3,869 rows (17.9%). Only NR7 Breakout is net positive: mean **+1.63%**, 43/54 tickers positive, 1,311 pooled OOS trades. Every other strategy has a negative mean (−0.72% to −2.32%). |
| `last_computed` | 3,862 rows @ 2026-08-28 16:05 (run_id `08ff0ca6…`) · **7 orphaned rows @ 2026-06-30 09:21, run_id NULL** |
| `wf_scores` | 13,244 rows, all @ 2026-08-28 16:05 |
| Scanner strategies admitted | **0**, across 877 tickers × 4 regime bands |
| `scheduled_signals` | 11,288 total — **358 BUY** (last 2026-07-01), **10,930 SELL** (120 in Sep). No BUY row has ever carried NR7 Breakout. |
| `paper_trades` | **0 rows** |
| EOD snapshots | 111 rows over 18 dates (2026-07-30 → 2026-09-01) |
| Premarket snapshots | 30 rows over 16 dates (2026-07-30 → 2026-09-01) |
| Pre-firm candidate snapshots | 1,017 rows over 14 dates (2026-08-10 →) |
| Forward test | 3,033 `ft_signal` · 2,582 positions (2,111 closed / 471 open) · 2,111 closed trades. Strategies: distribution 3,029, Liquidity Sweep 4. `ft_strategy_version` **empty**. Runs: 43, all OK, latest 2026-09-01 18:30. |
| Exit reasons (closed) | TIME 1,377 · TRAIL 731 · TP 2 · SL 1 — **65% of round trips end on the clock, not on a level** |
| Research ledger (`data/research.db`) | Tier-1 DB split is live. 58 `research_runs` (35 backtest-cache, 9 wf-refresh, 7 roller, 5 gate-eval). **5 `gate_decisions`, all NR7 Breakout, all REJECT at `walk_forward`**, latest 2026-07-14. 40 `gate_evidence`. `hypotheses` / `hypothesis_links` / `failure_registry`: **0 rows each**. |
| Registry | `registry @9b6e380: 0 approved, 1 shadow, 0 skipped, 1 debt, 0 unverified` |

**Is there enough history to evaluate anything?** For the WF scanner BUY side: no — N = 0. For EOD
and Premarket: 18 and 16 snapshot dates, ~12 with measurable outcomes each; enough to detect a very
large effect, nowhere near enough to detect a realistic one. Only the distribution-short cohort has
a decisive sample, and its verdict is negative.

---

## 11. Final verdict

| Pipeline | Logic correct? | OOS validated? | Forward tested? | Leakage found? | Status |
|---|---|---|---|---|---|
| **Walk-Forward Scanner** | Internally consistent, but dead | Rolling OOS run; gate says REJECT | **No** — 0 BUY signals in 42 sessions | **Yes** — selection, multiplicity, L-1, L-2 | **C** — plausible, unproven, non-operational |
| **EOD Watchlist** | Yes | **No** — no OOS study for R/S/V/P | **No** — not ingested by `forward_testing` | No look-ahead; A-2 backward dependency | **C** — plausible, unproven |
| **Premarket Watchlist** | Coherent, but architecturally wrong | **No** — no OOS study for any source | **No** — not ingested by `forward_testing` | Selection bias via unlogged `top_n=3` | **C** — plausible, unproven |

### The eight questions

**1. What is the actual Walk-Forward scanner?**
A weekly *research* batch (`research/walkforward_multi.py`, cron Friday) that backtests 14
fixed-parameter strategies over rolling 12m-train / 3m-test windows and writes one pooled OOS
expectancy row per (ticker, strategy) into `wf_edge`. There is no fitting step — the training window
supplies only an indicator warm-up tail — so it is rolling out-of-sample backtesting, not
walk-forward optimisation. The *live* component is `scheduled_multi_strategy_scan()`, which reads
`wf_edge` only as an admission filter and generates signals from a separate set of live checker
functions.

**2. Is EOD generated by Walk-Forward?**
No. All four sources (R, S, V, P) come from the reversal filter, the daily technical screen, a
volume-ratio threshold on that same screen row, and the LLM firm's morning approvals. None reads
`wf_edge`, `wf_scores`, `STRATEGY_FUNCS`, or the Edge Registry.

**3. Is Premarket generated by Walk-Forward?**
No. Its three sources are the reversal watchlist, the premover detector and the bear dip-scout
watchlist. It also never consumes the EOD snapshot: it is an independent discovery engine running in
the morning on inputs already settled by 16:30 the previous day.

**4. Which signals have actual statistical evidence?**
One, and it is negative: the distribution SELL signal, with 2,108 closed cost-adjusted shadow shorts
averaging −4.97% per trade at a 26.2% hit rate. As a directional short it does not work. On the long
side, nothing has prospective evidence. NR7 Breakout has the strongest historical signature (1,311
pooled OOS trades, +1.63%/trade, 43/54 tickers positive) but the gatekeeper rejected it 5 times out
of 5 at the `walk_forward` stage and it has never fired live.

**5. Which signals are currently only hypotheses?**
All of the long side: every EOD source, every premarket source, every strategy in `STRATEGY_FUNCS`,
the `candidate_score` and `unified_watchlist` weightings, the confluence bonus, and every Agent Firm
decision. None has a prospective, pre-registered, cost-adjusted measurement.

**6. What needs to be frozen before forward testing?**
Six things: (a) the strategy roster and `disabled_strategies`; (b) the registry file and its hash;
(c) `candidate_score`, `PREMOVER_FLOOR`, `CONFLUENCE_BONUS`, `BEAR_BASE`, `MAX_ROWS` and
`select_top_liquid_longs`'s `top_n`; (d) `EDGE_SCORE_MODE` and the `veto.py` thresholds; (e) the
agent-firm prompt and model routing, versioned; (f) the exit policy and cost model.
Two things must be **fixed** first because they are defects rather than settings: the retrospective
open-price fill (L-2), and — before `EDGE_SCORE_MODE=enforce` — the wrong-strategy attribution in
`_best_wf_edge` (L-3). And `ft_strategy_version` must actually be populated; a forward test whose
`strategy_version_id` is NULL on every row cannot prove what rule it measured.

**7. Minimum observations before judging the system?**
Count independent **dates**, not signals — §7 shows the two diverge sharply. With a per-date sd
around 8–13%, detecting a +1%/trade edge at 80% power needs roughly 400–600 independent
date-observations, which is not a realistic target at 2–8 signals a day. A workable staged rule:
**60 trading days** (~3 months) for a first read that can only rule out a large negative;
**125 days** (~6 months, matching the existing Phase 5 timebox) and **N ≥ 100 signals per cohort**
as the first defensible GO/NO-GO point; and a full result only once the sample spans **at least two
market regimes** — the current data is entirely one rising five-week stretch. Fix the horizon and
the decision rule before the window opens.

**8. Are we trading a proven edge, or one that still needs prospective confirmation?**
Neither, precisely: we are not currently trading anything at all through the Walk-Forward path.
`paper_trades` is empty, no BUY signal has been generated in 42 trading sessions, and zero
strategies are admissible on any of 877 tickers. What the operator sees each day is the EOD and
Premarket Telegram reports — produced by heuristic screens and LLM judgement, with no out-of-sample
validation and no prospective measurement. If those are being acted on manually, that is
discretionary trading on an unvalidated shortlist, which may be a reasonable thing to do, but it is
not a proven edge; the system's own gatekeeper has never issued a single PROMOTE decision.

---

## 12. Code changes, and how to reproduce

### Changes made

One file added: `tests/test_signal_architecture_audit.py` (22 tests, all passing).
**No production code was modified. No production data was modified.** Per the operating rule, the
defects found (L-1, L-2, L-3, S-1, S-2, F-1, A-1, A-2) are reported, not fixed — L-2 and L-3 are the
two that warrant a fix before anything is re-admitted or `EDGE_SCORE_MODE` is advanced.

### Reproduce

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && source venv/bin/activate

# 1 — registry admission state (0 approved, 1 shadow)
python -c "from engine.registry_loader import startup_summary; print(startup_summary())"

# 2 — the core finding: strategies admissible across every ticker and regime
python - <<'EOF'
import sqlite3
from scheduler.scanner import (_edge_selectable, _REGIME_STRATEGY_MAP,
                               _COUNTER_TREND_BOOK, _get_disabled_strategies)
from engine.registry_loader import registry_governance
conn = sqlite3.connect("file:data/walkforward.db?mode=ro", uri=True, timeout=30)
disabled = _get_disabled_strategies()
tickers = [r[0] for r in conn.execute("SELECT DISTINCT ticker FROM wf_edge")]
for band, cands in _REGIME_STRATEGY_MAP.items():
    ct_c = [c for c in cands if c in _COUNTER_TREND_BOOK]
    wf_c = [c for c in cands if c not in _COUNTER_TREND_BOOK]
    hits = 0
    for t in tickers:
        ct  = [c for c in ct_c if isinstance(registry_governance(c), set)
                                 and t in registry_governance(c)]
        sel = _edge_selectable(conn, t, wf_c) if wf_c else []
        if not sel and not ct_c:
            sel = _edge_selectable(conn, t, None)
        if [s for s in sel + ct if s not in disabled]:
            hits += 1
    print(f"{band:15s} {hits}/{len(tickers)} tickers with >=1 admitted strategy")
EOF

# 3 — signal ledger: BUY died 2026-07-01
sqlite3 -readonly data/walkforward.db \
  "SELECT signal_direction, COUNT(*), MAX(substr(scan_time,1,10)) \
   FROM scheduled_signals GROUP BY 1;" \
  "SELECT COUNT(*) FROM paper_trades;"

# 4 — wf_edge distribution by strategy
sqlite3 -readonly data/walkforward.db \
  "SELECT strategy, COUNT(*), SUM(expectancy_pct>0), ROUND(AVG(expectancy_pct),3), \
          SUM(n_trades), MAX(last_computed) \
   FROM wf_edge GROUP BY 1 ORDER BY 4 DESC;"

# 5 — gatekeeper history (Tier-1 research DB)
sqlite3 -readonly data/research.db \
  "SELECT strategy_fn, final_state, failing_stage, decided_at FROM gate_decisions;"

# 6 — EOD -> premarket carry-forward
sqlite3 -readonly data/walkforward.db \
  "SELECT date, strategy, GROUP_CONCAT(ticker) FROM watchlist_snapshot \
   GROUP BY 1,2 ORDER BY 1;"

# 7 — realised forward-test results
sqlite3 -readonly data/walkforward.db \
  "SELECT strategy, COUNT(*), ROUND(AVG(pnl_pct),4), \
          ROUND(AVG(pnl_pct>0)*100,1), ROUND(AVG(r_multiple),3) \
   FROM ft_shadow_trade GROUP BY 1;"

# 8 — tests
python -m pytest -q tests/test_signal_architecture_audit.py
python -m pytest -q tests/forward_testing tests/test_wf_edge.py tests/test_veto.py \
  tests/test_edge_selector.py tests/test_adaptive_strategy.py \
  tests/test_registry_lifecycle.py tests/test_trade_plan.py \
  tests/test_unified_watchlist.py tests/test_walkforward_metrics.py
python -m pytest -q     # full suite: 2804 pass, 2 pre-existing news_filter failures
```

---

*Read-only audit. DISCOVERY / VALIDATION / PRODUCTION / FORWARD TEST kept separate; no forward
result was allowed to feed back into strategy logic. No production signal logic altered.*

---

# ADDENDUM — Remediation, 2026-09-02

*Appended, not merged: every finding above stands as the record of what was
found. This section records what was changed in response.*

## Status of each finding

| # | Finding | Status | Mechanism |
|---|---|---|---|
| **S-1** | Zero strategies admissible, silently | **Diagnosed + surfaced** (not "fixed" — see below) | `engine/admission.py` (single ordered authority, reason per verdict); scan-time diagnostic; once-a-day Telegram alert; `scripts/admission_report.py` |
| **S-2** | Stale `wf_edge` had no defined scanner behaviour | **CLOSED** | `admission.WF_EDGE_MAX_AGE_DAYS = 14` (two weekly refresh cycles) |
| **L-1** | `wf_edge` measures a different rule than production runs | **CLOSED** | `engine/rule_identity.py`; admission refuses a strategy whose live rule ≠ the researched rule; manifest `rule_id:` is the declared remedy |
| **L-2** | Live entry price was retrospective | **CLOSED** | `engine/entry_convention.py`; NR7 declares `price_basis`; the scanner stages instead of filling |
| **L-3** | `wf_edge` stats laundered across strategies | **CLOSED** | `edge_enrich.wf_edge_for(conn, ticker, strategy)`; no "best row" fallback; unattributed ⇒ no stats ⇒ Tier B `s1` drops it |
| **F-1** | EOD/Premarket not forward-tested | **CLOSED** | `forward_testing/adapters/watchlist_adapter.py`; `ft_signal_meta` (append-only) |
| **A-1** | Premarket was a parallel discovery engine | **CLOSED** | `engine/premarket_revision.py`; premarket consumes the frozen EOD plan |
| **A-2** | Dependency ran premarket(D) → EOD(D) | **CLOSED** | source tag `P` removed; new evidenced tag `W` (validated walk-forward signals) added |
| — | Snapshots silently rewritable, no price/rule | **CLOSED** | `engine/watchlist_ledger.py`: `watchlist_snapshot_log` + `watchlist_revision`, both `BEFORE UPDATE/DELETE ... RAISE(ABORT)` |

## Why S-1 is "surfaced", not "fixed"

The deadlock is **not** a configuration accident, and it was not unblocked:

- `NR7_BULL v2` is `SHADOW` by a dated owner decision (D-029, 2026-08-19) on the
  Evidence Model's C3 bar. Reversing it would be overriding a governance
  decision to manufacture signals.
- The gatekeeper's only five decisions are all `NR7 Breakout` → **REJECT at
  `walk_forward`**. No strategy has ever passed.
- `Trend Following Breakout`, `Swing Trend`, `VWMA Breakout Pullback`,
  `Crash Recovery` and `Panic Rebound` produce **fewer than 20 pooled OOS trades
  on every one of 877 tickers** — verified against `wf_scores`, where all 14
  strategies *are* scored across 946 tickers. They are too rare to support an
  edge claim, not broken.
- The remaining five are in `disabled_strategies` because the 2026-07-04
  re-baseline measured them negative.

Per the operating rule, zero signals is preserved and reported. What changed is
that it is now **impossible for this state to be silent**.

### Selection effect worth recording

`NR7 Breakout`'s mean per-window return in `wf_scores` is **−0.026%** across 946
tickers, while its `wf_edge` mean is **+1.63%** across 54. The difference is the
`n ≥ 20` filter: `wf_edge` conditions on tickers where NR7 traded often enough to
qualify. The positive figure is a statement about a selected subset, not about
the strategy over the universe. This does not invalidate the gate (a thin sample
genuinely cannot support a claim) but it must not be read as "NR7 makes +1.63%".

## Files changed

**New production modules**

| File | Purpose |
|---|---|
| `engine/entry_convention.py` | Single authority on when/at what price a signal may be filled (L-2) |
| `engine/rule_identity.py` | `rule_id` for live vs researched gate sets; parity check (L-1) |
| `engine/admission.py` | Ordered admission authority with a reason per verdict (S-1, S-2, L-1) |
| `engine/watchlist_ledger.py` | Append-only `watchlist_snapshot_log` + `watchlist_revision` |
| `engine/premarket_revision.py` | Premarket as a revision operator over the frozen EOD plan (A-1) |
| `forward_testing/adapters/watchlist_adapter.py` | EOD/Premarket cohorts into the FT ledger + `ft_signal_meta` (F-1) |
| `scripts/admission_report.py` | Replay the real admission chain and print why |
| `scripts/scanner_replay.py` | Point-in-time replay of the live signal path |

**Modified**

| File | Change |
|---|---|
| `engine/edge_enrich.py` | `_best_wf_edge` → `wf_edge_for(conn, ticker, strategy)`; no cross-strategy fallback (L-3) |
| `engine/strategies.py` | NR7 declares `price_basis=session_open`, `entry_rule=NEXT_SESSION_OPEN` (L-2) |
| `engine/strategy_specs.py` | `ensure_entry_price` stamps `price_basis` + `entry_rule` on every signal |
| `engine/trade_plan.py` | Source `P` removed, source `W` added; `attach_provenance()`; `record_snapshot` writes the ledger; `candidate_score` tolerant of missing heuristic keys |
| `engine/registry_loader.py` | Attaches `manifest_data` to entries so admission can read the declared `rule_id` |
| `scheduler/scanner.py` | `_edge_selectable` delegates to `engine.admission`; verdict recording; admission diagnostic + daily alert; fills routed through `entry_convention` |
| `scheduler/jobs.py` | `run_premarket_firm_scan` rebuilt as a revision operator; EOD stamps provenance; FT cycle ingests watchlists |

**Schema (all idempotent `CREATE TABLE IF NOT EXISTS` + `CREATE TRIGGER IF NOT EXISTS`, per the repo's migration convention — no migration runner)**

- `watchlist_snapshot_log`, `watchlist_revision` (append-only, trigger-enforced)
- `ft_signal_meta` (append-only, trigger-enforced)

## Validation performed

| Check | Result |
|---|---|
| Targeted architecture tests | pass |
| Full suite | **2,888 passed, 3 failed** — 2 pre-existing `news_filter` isolation defects, 1 `test_db_centralization` caused by concurrent edits to `engine/platform_info.py` / `engine/ticker_detail.py` (not part of this work) |
| Historical replay of the real admission chain | `scripts/admission_report.py` — 0 admitted across 4 regime bands; blocking totals `disabled 2000 · oos_evidence 600 · rule_parity 400 · registry 400` |
| Point-in-time forward replay (20 sessions × 150 tickers) | `scripts/scanner_replay.py` — **0 signals**, 0 retrospective fills; stages `disabled 7282 · registry 800 · rule_parity 786` |
| Any BUY traceable to a validated strategy + OOS evidence | No BUY produced. Positive path proven by `tests/test_nr7_live_pipeline_e2e.py` (APPROVED + in-universe + declared `rule_id` ⇒ admitted end-to-end) |
| Zero BUYs preserved when evidence is absent | Confirmed by both replays |
| EOD → Premarket provenance and revision | End-to-end on an isolated copy of production data: 117 real candidates → 8 published → **8/8 (100%) carried into premarket** with recorded RETAIN reasons (baseline: 4 tickers across 17 transitions). Risk-off `CRITICAL` correctly removes all 8 |
| Forward-testing captures the actionable path | Both cohorts ingested (`eod` 8, `premarket` 8), 16 `ft_signal_meta` rows, `entry_rule` uniformly `NEXT_SESSION_OPEN`, **0 rows on a retrospective basis**, re-ingest adds 0 |
| Append-only enforcement | `UPDATE`/`DELETE` on `watchlist_snapshot_log`, `watchlist_revision`, `ft_signal_meta` all raise |
| Production data | Untouched. All inspection read-only or against `scratchpad/e2e.db` |

## Remaining blockers

1. **No strategy passes OOS validation.** Zero admissible pairs. Until a
   gatekeeper `PROMOTE` exists and the owner promotes a registry entry to
   `APPROVED`, the engine correctly produces no BUY signal.
2. **Rule parity is unresolved for every gated strategy.** The remedy is a
   deliberate choice: re-run the walk-forward with the weekly MTF gate applied
   and record the resulting `rule_id` in the manifest, or remove the gate from
   production. Both are owner decisions, not engineering defaults.
3. **`ft_strategy_version` is still empty**; `strategy_version_id` is NULL on
   every `ft_signal`. `ft_signal_meta.rule_id` now carries the equivalent
   identity for watchlist cohorts, but the scanner cohort still lacks it.
4. **`engine/platform_info.py` / `engine/ticker_detail.py`** introduce raw
   `sqlite3.connect()` in production scope and fail
   `tests/test_db_centralization.py`. Owned by whoever is editing them.
5. **Cohort evidence is still nil.** The ledger starts empty; the first
   measurable forward-test window begins with the next EOD publication.
