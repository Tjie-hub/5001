# Alpha Falsification & Candidate-Selection Pass — 2026-09-03

**Scope:** audit handover tasks 1–6 (verify WF evidence, resolve Liquidity Sweep rule
divergence, candidate table, falsification, forward cohort, EOD→Premarket validation).
**Operating principle held throughout:** evidence first, falsification first, no
production promotion, no gate loosening, Liquidity Sweep stays disabled.
**Production impact:** zero. All new code is research-only (`scripts/`), all writes go
to research artifacts (`data/reports/`, `research.db` failure_registry / gate tables)
or nothing. No production file was modified by this pass.

---

## 1. Is the WF research pipeline now trustworthy?

**Mostly yes for the engine, no for the evidence state — and the handover contained one
materially wrong claim.**

### 1.1 What the handover claimed vs what the database shows

| Handover claim | Verified reality |
|---|---|
| "The Sept-2 parity process completed cleanly at 17:00:38" | **False.** Run `62d3d8b7…` (started 13:11:34) **crashed at 17:00:38** with `sqlite3.OperationalError: database is locked` at the final single-transaction save (`logs/wf_parity_2026-09-02.log`, last line). It scored ~937/959 tickers and **persisted nothing**. 17:00:38 is the timestamp of the failure, not of a completion. |
| (implicit) full-universe parity evidence exists | **Only 3 rows exist**: a TFB-only parity run (`664b4697…`, 946 tickers, **0 qualifying rows** — a decisive TFB negative) and a 3-ticker smoke of {conservative, momentum} (`b3d613e1…`/`afcc0137…`, Sept-3 07:29, 6 rows, 0 qualifying). The full-roster parity rerun **has not happened**; the Saturday 06:00 cron slot (`deploy/crontab`) is the next scheduled attempt. |
| Bare wf_edge stats (31,136 LS trades, −0.984%) | **True** — reproduced exactly: `SELECT SUM(n_trades), SUM(expectancy_pct*n_trades)/SUM(n_trades) FROM wf_edge WHERE strategy='Liquidity Sweep'` → 31,136 / −0.9840. Source: bare-study run `08ff0ca6…` (Aug-28 16:05→18:27, 946/959 tickers, 3,869 rows). This evidence is rule-valid for LS only because LS is a weekly-gate bypass strategy (`_WEEKLY_GATE_BYPASS`). |

### 1.2 What is actually persisted (the numbers the handover asked to report)

**Bare OOS study (`wf_edge`, run `08ff0ca6…`, last_computed 2026-08-28, warmup 60,
12m/3m rolling WF, costs baked in at ~0.60% round trip — 0.15% buy + 0.25% sell
commission + 0.10% slippage per side, `engine/exits/costs.py`):**

| strategy | tickers (cells) | OOS trades | trade-wtd expectancy %/trade | win % | exit costs | admission result |
|---|---|---|---|---|---|---|
| NR7 Breakout | 54 | 1,311 | **+1.641** | 55.5 | net of 0.60% RT | **REJECTED** by gatekeeper ×6 (Jul ×5; this pass with full corpus — again `walk_forward`, consistency 48.56% < 50%); registry v2 **SHADOW** (D-029); `rule_parity` evidence created this pass (3/959 thin cells, §4); not PROVEN |
| momentum | 340 | 9,819 | −0.689 | 29.9 | net | policy-disabled |
| vwap_reversion | 854 | 55,667 | −0.864 | 29.1 | net | policy-disabled |
| Liquidity Sweep | 724 | 31,136 | −0.984 | 26.4 | net | policy-disabled (this pass adds parity evidence, §2) |
| ORB | 272 | 7,008 | −0.946 | 37.9 | net | policy-disabled; no live checker routed |
| vol_weighted | 780 | 34,590 | −1.062 | 27.8 | net | policy-disabled |
| Volume Profile POC | 30 | 651 | −1.125 | 25.4 | net | policy-disabled |
| conservative | 797 | 38,655 | −1.128 | 24.9 | net | policy-disabled |
| Inside Bar Breakout | 18 | 406 | −2.309 | 15.6 | net | policy-disabled |

**Rule-parity study (`wf_edge_rule` / `wf_rule_study`):** strategies whose live path
applies the weekly MTF gate have essentially no rule-parity evidence. TFB is the only
full-coverage parity study ever completed: **946 tickers, 0 qualifying rows** (no cell
reached n≥20 — strong negative). Crash Recovery / Panic Rebound have 0 rows anywhere.

**Regime breakdown:** does not exist for the pooled WF evidence — the Aug-28 bare study
and the failed Sept-2 parity run persist no per-regime split. Regime analysis exists
only in the gatekeeper (family BULL/BEAR/SIDEWAYS per strategy). NR7's July gate
evidence: governing cell BULL (n=349, exp +1.32%), multiplicity PASS (BH/Bonferroni
p≈0.0032), PSR 0.999, DSR WATCH 0.866, holdout retention 0.68 — but window consistency
47.96% **FAIL**. The NR7 manifest itself records `universe_generalization: FAIL
(T1 −0.001%)` and `sideways: REJECTED` on a **4-ticker** frozen universe.

**Admission result (official, `scripts/parity_evidence_report`):** *ADMISSIBLE: none.*
The live scanner correctly produces no BUY signals. Zero APPROVED registry entries;
the only registered strategy (NR7_BULL v2) is SHADOW with 0 forward trades since
2026-07-04.

### 1.3 Pipeline trust assessment

- **Engine/mechanics: trustworthy.** Costs are applied from a single authority
  (`engine/exits/costs.py`); the OOS boundary (entry ≥ test_start, warmup tail is prior
  data only) is correct; aggregation floors thin cells instead of zero-filling; the
  post-crash checkpoint + `_commit_with_retry` fix is in place (exercised by this pass's
  targeted parity run).
- **Evidence state: NOT trustworthy until the full parity rerun completes.** Eight of
  eleven strategies have no rule-parity evidence at all; the admission chain correctly
  refuses them. The pipeline's own parity report is honest about this — the problem is
  the missing compute, not missing logic.
- **Hygiene defects found:** (a) 5 orphaned `RUNNING` rows in `research_runs`
  (crash paths never finalize — including the two `RUNNING` gate-eval-era backtest-cache
  rows); (b) the P-3 repair (`engine/exits/policy.py` hold_days=10) and the entire EOD→
  Premarket rebuild (`engine/watchlist_ledger.py`, `engine/premarket_revision.py`,
  `forward_testing/adapters/watchlist_adapter.py`) are **uncommitted/untracked in git** —
  production runs from the working tree, so a stray checkout would silently revert audit
  repairs. Commit them; (c) **collector parity defect** (found by this pass, §4): the
  gatekeeper's NR7 collector and the wf-refresh engine produce opposite-sign pooled
  expectancy for the same rule (+1.14pp vs −0.18pp on ~6.2k trades each) — likely the
  window-edge trade truncation vs continuous-simulation shape difference. Reconcile
  before tiering any NR7 claim.

---

## 2. Liquidity Sweep rule divergence — resolved (rerun done)

**Authoritative rule:** the forward/shadow definition (`hold_days=10`,
`engine/exits/policy.py`, added 2026-09-03 for P-3) is the rule the system actually
trades, so parity requires the historical study to use the same cap. Entry rules were
already at parity (LS is a weekly-gate bypass; `live_rule_id == research_rule_id`,
`engine/rule_identity.py`); the divergence was exit-only.

**Method:** new research-only harness `scripts/ls_hold10_parity_study.py` replicates the
wf-refresh OOS methodology exactly (same `walk_forward_split` 12m/3m rolling windows,
same 60-bar warmup tail, same entry≥test_start filter, same cost model via the shared
`apply_costs`, same exit kernel `engine.exits.evaluate_exit`) and computes BOTH exit
variants on identical signals. Faithfulness gates: **GATE1** — harness baseline vs
direct `run_strategy()` on smoke tickers: trade-for-trade identical, PASS.
**GATE2** — baseline vs persisted `wf_edge` across 724 tickers: n exact-match 723/724
(the one mismatch is 4 trading sessions of data drift since Aug-28, not harness error),
|Δexp| mean 0.0007pp / max 0.0064pp. (The script's strict-gate printout says "FAIL"
because it requires 100.0% n-match; the residual is data drift and does not affect the
comparison, which is same-data same-signal A/B.)

**Before/after (full corpus, 959 tickers, OOS trades only):**

| variant | OOS trades | expectancy %/trade | win % | exit mix | cells n≥20 (tw-exp / positive) |
|---|---|---|---|---|---|
| A — unbounded (research rule, = handover −0.984%) | 33,122 | −1.009 | 26.0 | SL 22,554 / TP 6,306 / EOD 4,262 | 725 cells, −0.983pp, 155 positive (21.4%) |
| B — hold_days=10 (shadow rule) | 40,539 | **−0.998** | 28.3 | SL 24,632 / TIME 7,056 / TP 5,742 / EOD 3,109 | 751 cells, −0.975pp, 143 positive (19.0%) |

**Verdict:** the 10-session cap changes nothing material. Trade-weighted expectancy
improves by ~0.01pp and remains ≈ −1%/trade; positive cells fall from 21.4% to 19.0% of
the floor; per-ticker deltas are a coin flip (458 improved / 399 worsened). The cap
converts doomed trades into earlier TIME exits (median hold 3 sessions) and slightly
increases trade count via re-entry — it does not create an edge.

**Disposition:** the divergence is closed — forward and research now measure the same
rule, and the rule is negative under both. **Liquidity Sweep stays disabled** (unchanged
policy). Worth continuing in shadow? Only until the JSMR position (open 43 sessions,
held under the OLD no-cap policy) is closed by the new TIME exit — that single close
validates the policy mechanics in production. After that the shadow book has no
evidential future: admission blocks new LS signals, so the forward sample is frozen at
4 signals / 3 closed trades (+23%, +18%, −3% — a +0.13%/trade mean on n=3, which is
statistically void and a textbook illustration of why tiny forward samples mean
nothing). Recommendation: retire the LS shadow track after JSMR's TIME exit confirms;
keep the strategy definition and both negative studies on record.

Artifacts: `data/reports/ls_hold10_parity_2026-09-03.{md,csv}`,
`logs/ls_hold10_parity_study.log`.

---

## 3. Candidate table (complete)

Tiers per the handover: POSITIVE OOS / PROMISING / ADMITTED / FORWARD-TESTED / PROVEN.

| strategy | OOS trades | OOS expectancy | win rate | costs | regime stability | admission | verdict |
|---|---|---|---|---|---|---|---|
| NR7 Breakout | 1,311 (54 cells) / **6,183 full pool** | +1.64pp on floor cells / **−0.18pp full pool, 95% CI [−0.37, +0.02]**; gatekeeper collector +1.14pp pooled but consistency FAIL | 55.5% cells / 38.6% pool | net 0.60% RT; −0.25pp more at +0.25% | FAIL: generalization T1, sideways REJECTED, only 2025 positive, 2026 YTD −0.88pp | gate REJECT ×6; SHADOW; parity study 3/959 thin cells (§4) | **POSITIVE OOS (selected cells only) — falsified at strategy level; NOT PROMISING** |
| Liquidity Sweep | 31,136 / 40,539 parity | −0.98pp / −1.00pp | 26.4 / 28.3% | net | n/a (never positive) | disabled (policy) | **negative — dead** |
| momentum | 9,819 | −0.69pp | 29.9% | net | n/a | disabled | negative |
| vwap_reversion | 55,667 | −0.86pp | 29.1% | net | n/a | disabled | negative |
| ORB | 7,008 | −0.95pp | 37.9% | net | n/a | disabled | negative |
| vol_weighted | 34,590 | −1.06pp | 27.8% | net | n/a | disabled | negative |
| Volume Profile POC | 651 | −1.13pp | 25.4% | net | n/a | disabled | negative (thin n) |
| conservative | 38,655 | −1.13pp | 24.9% | net | n/a | disabled | negative |
| Inside Bar Breakout | 406 | −2.31pp | 15.6% | net | n/a | disabled | negative |
| Trend Following Breakout | 0 qualifying (946 tickers, parity rule) | n/a | n/a | net | n/a | blocked (no evidence) | **negative under live rule — dead as configured** |
| Crash Recovery / Panic Rebound / VWMA BP / Swing Trend | 0 rows | n/a | n/a | n/a | n/a | no evidence / not routed | unevaluated — no evidence |
| distribution (SELL path) | 2,133 forward shadow | **−0.05pp** (every month negative, Jun–Sep 2026) | — | net | n/a | forward-tested | **FORWARD-TESTED, negative — dead** |

- **POSITIVE OOS:** NR7 Breakout — only on its n≥20 cell subset (§4 kills it).
- **PROMISING:** none.
- **ADMITTED:** none. The admission chain admits nobody, by design and by evidence.
- **FORWARD-TESTED:** distribution (negative, large sample); LS (void, n=3);
  NR7_BULL v2 SHADOW (0 trades since registration).
- **PROVEN:** **nothing. Nothing is close.**

---

## 4. Falsification of the apparent winner (NR7 Breakout)

Full study: `scripts/nr7_falsification_study.py` →
`data/reports/nr7_falsification_2026-09-03.md` (+ per-trade CSV). Harness validated
against persisted `wf_edge` (100% n-match on all 54 cells, |Δexp| ≤ 0.0024pp).

| test | result | kills the candidate? |
|---|---|---|
| Walk-forward window consistency | gatekeeper (Jul-14): 47.96% vs 50% bar — FAIL. Persisted cells: 2/54 with ≥50% consistency (avg 31.2%); trade-active-window consistency 72.2% | Ambiguous alone — the gate already rejected it once |
| Transaction costs | already net of ~0.60% RT; +0.25pp extra frictions → −0.43pp full pool | Contributes |
| Liquidity/turnover | **low-volume tercile −0.72pp vs high-volume −0.25pp**; the strategy loses most where fills are worst and the cost model is most optimistic | Contributes |
| Ticker concentration | top-5 tickers = 25.2% of positive pnl; excluding them, cell-level tw-exp unchanged (+1.64pp — selection effect dominates, see pool test) | No |
| Regime/market state | panic-state trades −0.43pp vs −0.12pp; manifest already records sideways REJECTED, generalization FAIL | Contributes |
| Temporal concentration | only 2025 is positive (+0.95pp); 2022 −1.23, 2023 −1.70, 2026 YTD −0.88 | **Yes** |
| Outlier dependence | drop top 1/5/10 trades: −0.20/−0.23/−0.25pp (mild tail dependence) | No |
| Sample size | floor cells n=20–41 each (thin); full pool 6,183 | Pool test decisive |
| **Rule parity** | bare-rule evidence ≠ live rule (weekly MTF gate not in research); targeted parity study run this pass — see below | Was blocking |
| **Multiple-testing / data-mining** | **decisive:** pooled over ALL 858 tickers producing NR7 trades, expectancy is **−0.1787pp, bootstrap CI [−0.373, +0.016] — includes 0**. The +1.64pp exists only inside the 54 cells that survived the n≥20 aggregation floor; the ~804 excluded tickers average ≈ −0.67pp. 43/54 positive cells vs a 23.1% cross-strategy base rate is the signature of a strategy that only "works" on its own selected residue — and 9 strategies × 959 tickers ≈ 8,600 cells were searched. | **Yes** |

**Fresh gatekeeper re-evaluation (this pass, decision `decided_at` 2026-09-03):**
**REJECT — failing stage `walk_forward` again**, now with the full corpus (n_overall
6,164, 1,044 windows vs July's 221): consistency 48.56% < 50% (507 profitable windows).
All other stages pass — BULL governing cell exp +1.14%, CI [0.75, 1.53] (bar 0.50),
multiplicity p≈8.1e-9, PSR ≈1.0, DSR 0.856 WATCH, holdout retention 1.64. Same verdict
as all five July runs, at twice the data volume.

**New defect surfaced by this re-evaluation — collector parity:** the gatekeeper's
NR7 collector (`research.studies.nr7_generalization_study.collect_trades_for_ticker`)
pools the same rule at **+1.14%** (n=6,164) while the wf-refresh engine path
(`strategy_nr7_breakout` per extended window — the evidence source behind `wf_edge`,
reproduced trade-exactly by the validated falsification harness) pools at **−0.18%**
(n=6,183). Same rule_id, opposite sign. The likely mechanism is simulation-shape, not
signal rules: the wf path truncates positions at each 3-month window edge (EOD exits)
and resets position sequencing per window, while the gatekeeper collector runs one
continuous full-history position stream. This is a research-artifact rule-identity
defect (two "authoritative" NR7 trade sets disagree on the sign of the pooled edge)
and must be reconciled before any NR7 claim is tiered — under **both** paths NR7 is
non-admissible today, so no promotion risk is created by leaving the fix to the owner.

**NR7 verdict: falsified as a strategy-level edge.** What remains is a per-cell
selection artifact concentrated in illiquid small caps (TIRT, MDRN, PACK…) in one
calendar year. This independently confirms the institution's own earlier decisions:
the gatekeeper's five REJECTs, D-029's demotion ("No capital — C3 requires E5+X3; the
claim has neither"), and the v1 generalization FAIL on a 4-ticker universe. NR7_BULL v2
SHADOW should stay exactly where it is (it has produced 0 forward trades since
2026-07-04 — nothing to even measure).

**Rule-parity rerun for NR7 (this pass):** targeted `wf-parity --strategies
"NR7 Breakout"` (run `2597066b…`, 11:09:44→11:27:42, config `39045def0ebfd58b`,
gates weekly_mtf_trend, warmup 160, 959 tickers / 946 scored, 0 errors) — the first
full-corpus parity run completed under the post-crash checkpoint mechanism
(959/959 checkpoints persisted, 0 abandoned; P-1 fix validated at scale).
**Result: 3 of 959 tickers qualify** under `NR7 Breakout@weekly_mtf_trend#dcbd1d87d31d`:

| ticker | exp %/trade | win % | consistency | n | sharpe |
|---|---|---|---|---|---|
| LAND | +1.936 | 57.1 | 31.2% | 21 | 1.37 |
| LAPD | +3.593 | 66.7 | 25.0% | 27 | 2.96 |
| TAMA | +0.814 | 56.0 | 31.2% | 25 | 0.79 |

The weekly gate does not broaden the edge — it narrows 54 bare-rule cells to 3, each
thin (21–27 trades over ~5y), each with consistency far below the 50% bar. A 0.3%
qualifying rate after a ~8,600-cell historical search is indistinguishable from
multiplicity noise. **No parity evidence of a tradeable NR7 edge under the live rule.**

Production-safety note: these 3 fresh `wf_edge_rule` rows would now pass NR7's
evidence/parity/freshness admission stages per-ticker — but admission stage 2 refuses
the registry's SHADOW entry outright (T7), so **no live behavior changes** from this
run. The layered defense held; nothing was enabled.

---

## 5. Clean forward-test cohort

**Empty.** No candidate survives the existing gates, so nothing new enters forward
testing. What the forward book contains today:

- `distribution` shadow cohort — legacy, large, **negative** (−0.05%/trade over 2,133
  closed trades). Recommendation: record the verdict (done, failure_registry) and wind
  down; it is consuming compute to re-confirm a known negative.
- LS shadow — 4 signals / 3 closed (+0.13%/trade, void), 1 open (JSMR) that will TIME-
  exit under the new policy. Retire after that close.
- NR7_BULL v2 SHADOW — 0 trades since 2026-07-04. No evidence is accruing; either feed
  it through the new watchlist forward adapter (starting tonight) or acknowledge it is
  dormant.
- **Rejected candidates persisted** (selection-bias measurement):
  `research.db.failure_registry` — Liquidity Sweep (both-rule negative, ref
  `4c2f5932…`), distribution (forward negative, ref `4e833d8b…`), and NR7 Breakout
  (falsified at strategy level + parity study 3/959 thin cells — see below), source
  `alpha-falsification-2026-09-03`. Strategy-level negatives for the disabled roster
  are already enforced by `paper_config.disabled_strategies` and need no duplicate
  record.
- The rebuilt EOD→Premarket forward cohorts (`eod` / `premarket`, kept deliberately
  separate in `ft_signal_meta` with `revision_action`/`revision_reason_code` join keys)
  begin ingesting at tonight's 18:30 cycle — that is the forward cohort machinery going
  forward.

Every hypothetical trade persistence requirement (strategy, ticker, entry, exit, hold,
liquidity condition, costs, regime, signal timestamp, outcome) maps 1:1 onto the
existing `ft_signal` / `ft_signal_meta` / `ft_shadow_position` / `ft_shadow_trade`
schema — no new tables are needed; the gap was sample, not plumbing.

---

## 6. EOD → Premarket validation

**Architecture: verified end-to-end in code; production execution has not started yet.**

- EOD published plan: `eod_trade_plan` 16:40 WIB → `watchlist_snapshot_log` (append-only,
  BEFORE UPDATE/DELETE triggers) + `watchlist_publication` (records EMPTY_PLAN) +
  `watchlist_snapshot` projection. Sources now R (reversal) / S (screen) / V (volume) /
  W (walk-forward signals, weight 5.0); the backwards P→EOD coupling was removed (A-2).
- Premarket carry-forward: 08:35 job reads `base_plan(date, 'eod')` via
  `latest_date_before` (never same-day), aborts on BASE_MISSING, revises only on
  post-16:40 evidence (corp actions, suspensions, market-risk RED/CRITICAL, VPIN
  extreme, foreign-flow ±1e9, overnight news), records every action to
  `watchlist_revision`, discovery ADDs gated behind `PREMARKET_ALLOW_DISCOVERY_ADDS`
  (default off). Publication returns to the same three tables with `strategy='premarket'`.
- Outcome leg: `WatchlistAdapter` ingests both cohorts into `ft_*` at 18:30 with
  per-row revision attribution — the revised-vs-untouched-EOD comparison is a join on
  `ft_signal_meta.revision_action`, deliberately never pooled.
- **Why no outcome measurement yet:** the rebuild's code finalized 07:22 today and the
  app restarted 09:02; every premarket row currently in `watchlist_snapshot` (sources
  `["BEAR_DIP","PREMOVER"]`) is the OLD discovery-panel flow, and
  `watchlist_snapshot_log`/`watchlist_publication`/`watchlist_revision`/`ft_signal_meta`
  are all empty. The first production run of the new flow is **today 16:40** (EOD),
  tomorrow 08:35 (premarket revision), 18:30 (outcome ingest). Measuring whether
  revisions improve outcomes becomes possible after ~20+ sessions accumulate; the
  measurement itself still needs to be written (no study/report does the cohort join
  yet — recommended follow-up, see §8).

---

## 7. Answers to the eight audit questions

1. **Is the WF research pipeline now trustworthy?** The engine is (costs, OOS boundary,
   aggregation, crash-resilient persistence all verified). The evidence base is not yet:
   the Sept-2 full parity run was silently lost (the handover mis-recorded its crash as
   a completion), and 8 of 11 strategies lack rule-parity evidence. Until the Saturday
   cron (or a manual rerun) completes the full parity pass, "no admission" is the only
   defensible output — which is exactly what the system produces.
2. **Which strategies have credible OOS evidence?** None that establishes an edge.
   NR7's positive cells are a selection artifact (wf-path full pool −0.18pp, CI
   includes 0). The gatekeeper collector's +1.14% pooled figure does not rescue it:
   its own pre-registered gate rejects on consistency (48.56% < 50%), the wf-path pool
   is negative, the gated-rule parity study qualifies 3/959 thin cells, and the two
   paths disagree on sign (collector-parity defect, §4). TFB is decisively negative
   under its live rule (0 qualifying cells in 946 tickers).
3. **Which survive admission?** None. ADMITABLE = none is the correct current state.
4. **Which fail and why?** All nine bare-study strategies have negative pooled OOS
   expectancy after costs (−0.69pp to −2.31pp). NR7 additionally fails consistency,
   generalization, regime stability, liquidity, and multiple-testing. LS is negative
   under both exit rules. distribution is forward-negative.
5. **Is Liquidity Sweep worth continuing in shadow?** Only until the JSMR TIME exit
   validates the new hold_days=10 policy in production. Thereafter no: admission blocks
   new signals, the sample is frozen at n=3, and both rules now have historical parity
   evidence at ≈ −1%/trade. Keep disabled; retire the shadow track after the JSMR close.
6. **What is the clean forward-test cohort?** Empty of new entrants. Existing book:
   distribution (negative — wind down), LS (void — retire after JSMR), NR7_BULL v2
   SHADOW (dormant). The eod/premarket watchlist cohorts start accruing tonight.
7. **What evidence threshold before controlled paper/live deployment?** The institution
   already has the right bar — hold it. Per `docs/research_os/EVIDENCE_MODEL.md`:
   gatekeeper PROMOTE (8 stages incl. CI > 0.50% promotion bar, BH+Bonferroni, PSR,
   DSR, WF consistency ≥ 50%, holdout retention) → forward test inside an ex-ante
   timebox (min_n=15, go_exp ≥ 0.50%) → capital only at C3 = E5 + X3 (severe
   pre-registered OOS + friction + regime stability + independent reproduction). Note
   honestly: LIM6/EV-9 make C3 structurally unreachable for a single-researcher
   operation — the realistic ceiling is controlled paper (forward) evidence, not capital.
   Do not lower the bar to fit; record the ceiling.
8. **Single highest-value next experiment?** **Let the rebuilt EOD→Premarket→forward
   loop run for ~20 sessions, then run the cohort-comparison study** (revised vs
   untouched-EOD vs W-source-only on `ft_signal_meta` × `ft_shadow_trade`). It is the
   only live experiment that (a) exercises the new admission-gated pipeline end to end,
   (b) measures whether human/macro revision adds or destroys value, and (c) accumulates
   the K6-class forward evidence the Evidence Model requires — with zero promotion risk.
   Secondary (cheap, do it anyway): complete the full-roster `wf-parity` rerun so the
   Saturday cron starts from a healthy checkpoint state.

---

## 8. Artifacts produced by this pass

| artifact | purpose |
|---|---|
| `scripts/ls_hold10_parity_study.py` + `data/reports/ls_hold10_parity_2026-09-03.{md,csv}` + `logs/ls_hold10_parity_study.log` | LS exit-rule parity A/B (validated harness) |
| `scripts/nr7_falsification_study.py` + `data/reports/nr7_falsification_2026-09-03.md` + `data/reports/nr7_oos_trades_2026-09-03.csv` + `logs/nr7_falsification_study.log` | NR7 falsification (validated against wf_edge) |
| `scripts/record_alpha_falsification_rejections.py` + `research.db.failure_registry` rows | selection-bias ledger |
| targeted `wf-parity` run for NR7 (`logs/wf_parity_nr7_2026-09-03.log`, run `2597066b…`, config `39045def0ebfd58b`) | missing rule-parity evidence — 3/959 qualifying cells |
| gatekeeper re-eval for NR7 (`data/reports/nr7_gate_eval_2026-09-03.md`, fresh `gate_decisions`/`gate_evidence` rows) | current-evidence verdict: REJECT (`walk_forward` 48.56%) |
| this report | audit record |

**No production code changed. No gates loosened. Nothing promoted. Liquidity Sweep
disabled throughout.**
