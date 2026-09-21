# Production Watchlist + Walk-Forward + Liquidity Sweep Audit

**Date:** 2026-09-03 · **Branch:** `ops/hardening-2026-07-10`
**Authority:** point-in-time audit record (generated; superseded, never edited)
**Constraint honoured:** no production logic modified, no thresholds changed, no disabled
strategy enabled, no registry gate bypassed, no snapshot deleted, no migration re-run, no
running job killed.

> **Read this first.** The system was rebuilt on 2026-09-02 in response to
> `SIGNAL_PROVENANCE_AUDIT_2026-09-02.md` and the service restarted at **13:55:47 WIB** that
> day. Several premises in the audit brief describe the **pre-rebuild** system and are no
> longer true — notably source tag `P` (premarket → EOD), which was removed. This audit
> reports the system **as it runs now**, and flags where the brief's premise has moved.

---

## 1. EXECUTIVE VERDICT

| Question | Answer |
|---|---|
| What generates live trade signals? | **Nothing on the long side.** The only live signal path is `scan_distribution_signals()` — a SELL/short heuristic. Zero BUY signals since 2026-07-01. |
| Is walk-forward wired to the live scanner? | **Yes, structurally — and it currently admits nothing.** Proven from code and by replay. |
| Is the EOD watchlist research-backed? | **No. Heuristic**, with one evidenced source (`W`) that is currently empty. |
| Is Premarket independent? | **No longer.** Since the 2026-09-02 rebuild it is a revision operator over the frozen EOD plan. |
| What is "liquidity sweep shadow"? | **It does not exist as one thing.** The phrase conflates three unrelated subsystems (§6). |
| Does Liquidity Sweep have proven edge? | **No — the evidence is negative.** §6.4. |

**Three new defects found in this audit**, all in code written on 2026-09-02:

| ID | Severity | Defect |
|---|---|---|
| **P-1** | High | The full rule-parity walk-forward run **failed after 229 minutes** with `database is locked` and discarded all results. |
| **P-2** | High | An **empty published plan leaves no row** in `watchlist_snapshot_log`, so "we published nothing" is indistinguishable from "the job never ran". This is live now: EOD on 2026-09-02 approved 0 names, so today's Premarket will find no base plan. |
| **P-3** | Medium | `Liquidity Sweep` has **no time stop** in `ExitPolicyRegistry` while `distribution` has `hold_days=10`. One shadow position (JSMR) has been open **43 hold-days**. |

---

## 2. ACTUAL PRODUCTION SIGNAL PATH

```
DATA                data/loaders.py::_load_ohlcv_bulk
                    live: raw prices + partial bars | research: final_only + split-adjusted
                          |
RESEARCH / WF       research/walkforward_multi.py::run_walk_forward   [RESEARCH-ONLY]
                    12m train / 3m test, ~16 OOS windows, NO parameter fitting
                    cron Fri 16:05 (bare rule) + Sat 06:00 (production rule)
                          |
WF EDGE             engine/wf_edge.py -> wf_edge (bare) | wf_edge_rule (+rule_id) | wf_rule_study
                          |
REGISTRY            engine/registry_loader.py  <- registry/edge_registry.yaml   [AUTHORITATIVE]
                    0 APPROVED, 1 SHADOW (NR7_BULL v2)
                          |
ADMISSION           engine/admission.py::evaluate                     [AUTHORITATIVE, VETO-ONLY]
                    disabled -> registry -> rule parity -> OOS evidence -> staleness
                    *** 0 admitted, all 877 tickers, all 4 regime bands ***
                          |
LIVE SCANNER        scheduler/scanner.py::scheduled_multi_strategy_scan
                    engine/strategies.py::check_current_entry_signal + weekly MTF gate
                          |  (never reached)
LIQUIDITY           engine/liquidity.py::passes_value_liquidity_gate  [AUTHORITATIVE, VETO-ONLY]
                          |
EDGE / VETO         engine/veto.py (Tier A directional, Tier B statistical)
                    EDGE_SCORE_MODE=shadow -> LOG ONLY, cannot veto today
                          |
AGENT FIRM          engine/agent_firm/ + agent_firm_context.py        [VETO-ONLY]
                          |
ENTRY CONVENTION    engine/entry_convention.py                        [AUTHORITATIVE, VETO-ONLY]
                    refuses any fill on a retrospective basis; live STAGES
                          |
EXECUTION           paper_trade.open_trade -> paper_trades            *** 0 rows ***

SIDE BRANCH (the only live signal source):
scan_distribution_signals()  scheduler/scanner.py:1312
  stockbit_flow composite<=-3 AND verdict BEARISH AND regime!=BULL AND close[-1]<close[-5]
  -> scheduled_signals(SELL)   3,079 ft_signal rows, latest 2026-09-02
  NO wf_edge gate, NO registry check, NO disabled check, NO liquidity filter
```

### Stage table

| Stage | Function | Table | Research/Production | Can veto | Can create |
|---|---|---|---|---|---|
| OHLCV load | `data/loaders.py::_load_ohlcv_bulk` | `ohlcv` | both | no | no |
| Walk-forward | `research/walkforward_multi.py` | — | **research-only** (CI-fenced) | no | no |
| WF edge | `engine/wf_edge.py` | `wf_edge`, `wf_edge_rule`, `wf_rule_study` | research writes / production reads | no | no |
| Registry | `engine/registry_loader.py` | `registry/*.yaml` (file) | **production-authoritative** | **yes** | no |
| Admission | `engine/admission.py::evaluate` | reads `wf_edge*` | **production-authoritative** | **yes** | no |
| Regime map | `scheduler/scanner.py::adaptive_strategy_selector` | — | production | yes | no |
| Live checker | `engine/strategies.py::_CHECKER_DISPATCH` | `ohlcv` | production | no | **yes** |
| Weekly MTF gate | `check_current_entry_signal` | `ohlcv` | production | **yes** | no |
| Liquidity | `engine/liquidity.py` | `ohlcv` | production | **yes** | no |
| Flow confirm | `flow_filter.get_flow_batch` | Stockbit API | production | **yes** | no |
| Edge/veto | `engine/veto.py` | `wf_edge*`, `stockbit_flow` | production, **shadow mode → log only** | not today | no |
| Agent Firm | `engine/agent_firm/firm.py` | `agent_decisions` | production | **yes** | no |
| Entry convention | `engine/entry_convention.py` | — | production | **yes** | no |
| Execution | `paper_trade.open_trade` | `paper_trades` | production | no | **yes** |

**Proof the connection is real, not nominal:** `scheduler/scanner.py::_edge_selectable` delegates
every decision to `engine.admission.evaluate`, which reads `wf_edge` / `wf_edge_rule` directly.
`scripts/scanner_replay.py` re-ran the chain point-in-time over 20 sessions × 150 tickers using only
bars ≤ each date: **0 signals, 0 retrospective fills**, blocking stages
`disabled 7282 · registry 800 · rule_parity 786`.

---

## 3. EOD WATCHLIST LOGIC

`scheduler/jobs.py::run_eod_trade_plan` (16:40 WIB) → `engine/trade_plan.py::gather_long_candidates`.

**The brief's premise is out of date.** Verified against `engine/trade_plan.py` lines 62–105:

| Tag | Source | Origin | Status |
|---|---|---|---|
| **W** | `scheduled_signals` BUY for the date | `scheduler/scanner.py` after full admission | **NEW 2026-09-02.** The only evidenced source. Currently always empty. |
| **R** | `reversal_watchlist` (long) | `screener/reversal_filter.py`, 16:15 | heuristic |
| **S** | `daily_screen` `signal='bullish'` | `screener/screener_jobs.py` | heuristic |
| **V** | `daily_screen` `vol_ratio>=5.0` | same row as S | heuristic, **not independent of S** |
| ~~**P**~~ | ~~`agent_decisions` premarket approve~~ | — | **REMOVED 2026-09-02** (finding A-2: it made the flow premarket(D)→EOD(D)) |

`candidate_score` (`engine/trade_plan.py:184`): `W` **+5.0** · `R` +2.0+conviction/50 ·
`S` +1.0 · `V` +min(vol_ratio/50, 1.0). Weights are hand-set; no fitted or validated origin.
`confluence` = count of distinct source tags. `select_top(n=8)` by
`(candidate_score, conviction, net_value)`. Agent Firm enters after `select_top`, on ≤8 names.

**Live evidence, 2026-09-02 16:40:** `93 candidates, top 8 vetted, 0 approved`. Tier-A pre-screen
logged `5/8 survive; vetoed=[ASBI, ARTO, PDES d2:bearish_tech]` — **log only**, `EDGE_SCORE_MODE=shadow`.

### Does `watchlist_snapshot` influence decisions?

**No — confirmed reporting-only.** `record_snapshot` writes; the only readers are `diff_watchlist`
(Telegram sections), `get_snapshot`/`list_snapshot_*` (API v1 endpoints), and the forward-test
adapter. Nothing reads it back into candidate generation or ranking. **One exception introduced
2026-09-02:** `watchlist_snapshot_log` (the append-only ledger) IS read by
`run_premarket_firm_scan` as its base plan — so the **ledger** is decision-bearing while the
**projection** remains reporting-only.

---

## 4. PREMARKET WATCHLIST LOGIC

**The brief describes the pre-rebuild behaviour.** Verified against `scheduler/jobs.py:1106–1182`:

```
watchlist_snapshot_log(strategy='eod', latest date < today)      <- THE BASE PLAN
        |
engine/premarket_revision.py::revise()
   overnight-only evidence: corporate_action_events | suspension_events |
   news_mentions | broker_flow (settled) | vpin_scores | market risk tier
        -> RETAIN / REMOVE / UPGRADE / DOWNGRADE / ADD, each with reason + evidence
        |
select_top_liquid_longs()  -- every drop now recorded as a REMOVE decision
        |
Agent Firm (vetting only)
        |
watchlist_revision (append-only) + watchlist_snapshot_log(strategy='premarket')
```

`build_unified_watchlist()` is still imported, but **only inside the discovery-adds branch**, gated
by `PREMARKET_ALLOW_DISCOVERY_ADDS` (default **false**). Even when enabled, a discovery name is
refused unless it carries genuinely new overnight evidence — because `reversal_watchlist`,
`watchlist_premover` and `regime_watchlist` are all written at 16:15–16:30, *before* the 16:40 EOD
job, so a name found there is the same evening's data re-read.

**Proven from DB writes:** end-to-end on an isolated copy of 2026-09-01 production data,
carry-forward was **8/8 (100%)** with recorded RETAIN reasons. The pre-rebuild baseline was
**4 tickers across 17 consecutive transitions**, 13 of which shared none.

**But it is not working in production today** — see defect P-2 (§9).

---

## 5. SHOULD PREMARKET INHERIT EOD?

**Yes — and it already does.** The architecture proposed in the brief is what was implemented on
2026-09-02. Assessment against the brief's criteria:

| Criterion | Before | Now |
|---|---|---|
| Duplicate logic | Two merge/rank/confluence implementations, two source vocabularies | One generator (EOD), one revision operator |
| Signal drift | 4 shared tickers in 17 transitions | 8/8 carry-forward measured |
| Reproducibility | snapshot `INSERT OR REPLACE`, silently rewritable | append-only revision-numbered ledger |
| Auditability | no price, no rule, no strategy attribution | decision price + basis + entry rule + strategy + OOS evidence + revision reason |
| Leakage risk | premarket(D) → EOD(D) via tag `P` | arrow reversed; only post-16:40 data may revise |
| Overnight handling | premarket read 16:15–16:30 tables (nothing new) | six genuinely-post-EOD sources |
| Turnover | ~100% churn | RETAIN is the default; every change carries a reason |
| False additions | unbounded | discovery adds off by default, evidence-gated when on |
| False removals | silent `top_n=3` discard | every drop is a recorded REMOVE |
| Operational complexity | two engines, one channel | one engine + one operator; **more** moving parts, but each is inspectable |

**Residual concern:** the revision operator's thresholds (`FOREIGN_NET_MATERIAL = Rp 1bn`,
`RISK_OFF_TIERS`, `VPIN_TOXIC_LABELS`) are **hand-set and unvalidated** — the same class of
heuristic the audit criticised elsewhere. They are conservative (they only remove or downgrade) and
every decision is recorded, so their effect is measurable once the window accumulates. **NOT PROVEN.**

---

## 6. LIQUIDITY SWEEP SHADOW — EXACT STATUS

### 6.1 The term conflates three unrelated subsystems

Exhaustive search (`grep -rn -iE "liquidity.?sweep|sweep|shadow|turnover|traded.?value|ADV"` over
`engine scheduler forward_testing data routes screener tests docs`, excluding `.git`,
`__pycache__`, `venv`, `node_modules`, `.worktrees`) returns **no single "liquidity sweep shadow"
component**. What exists:

| # | Thing | What it actually is |
|---|---|---|
| 1 | **"Liquidity Sweep"** | A **trading strategy** — SMC PDH/PDL trap detection + broker-flow confirmation. Nothing to do with liquidity filtering. |
| 2 | **Liquidity gate** | `engine/liquidity.py` — ADV (lots) and value-base turnover filters. A genuine live gate. |
| 3 | **"Shadow"** | Three distinct meanings: registry lifecycle status `SHADOW`; forward-test track `SHADOW`; and `off\|shadow\|enforce` feature flags. |

The only real intersection: **the Liquidity Sweep strategy currently sits in the forward-test
SHADOW track.** That is what "liquidity sweep shadow" corresponds to.

### 6.2 Exact implementation

| | |
|---|---|
| Detection | `engine/smc.py::detect_liquidity_sweep` |
| Input | `ohlcv` OHLC only |
| Thresholds | wick beyond level ≥ **30%** of bar range; close back inside the level; PDH/PDL and (default on) PWH/PWL |
| Flow confirmation | `engine/smc_flow.py::confirm_sweep_flow` |
| Flow input | `stockbit_flow.composite_score` for the date; falls back to intraday `session_delta_stats` |
| Flow threshold | `composite_score > 0`, else `session delta >= 0`; **no data → `confirmed: True` (passthrough)** |
| Backtest fn | `engine/strategies.py::strategy_liquidity_sweep_flow` |
| Live checker | `engine/strategies.py::check_sweep_flow_signal` — requires the bullish sweep to be on the **current** bar |
| Exit policy | `ExitPolicyRegistry`: `sl_mult=1.0, tp_mult=2.5, min_rr=2.5` — **no `hold_days`, no trail** |
| Registry | **UNREGISTERED** |
| Rule parity | **holds** — in `_WEEKLY_GATE_BYPASS`, so live rule == researched rule |
| Live status | in `disabled_strategies` (`paper_config`), therefore **blocked at admission stage `disabled`** |

### 6.3 Classification

| Question | Answer |
|---|---|
| Runs in production? | Only as a **forward-test SHADOW cohort**. Its checker is never called live (admission blocks it first). |
| Only logs? | No — it produces `ft_signal` rows and simulated positions. |
| Can veto? | **No.** |
| Can modify ranking? | **No.** |
| In Agent Firm context? | **No** — `agent_firm_context.py` and `schemas.py` contain no sweep/liquidity/ADV/turnover field. |
| Persisted? | Yes: `ft_signal`, `ft_shadow_position`, `ft_shadow_trade`. |
| Historical performance measured? | Yes — `data/reports/sweep_validation_2026-06-24.md`. |
| Shadow vs live comparable? | **No.** It has never traded live (`paper_trades` empty; 7 BUY signals in `scheduled_signals`, all 2026-06-29..07-01, none executed). |

> **CLASSIFICATION: SHADOW ONLY.**
> It shadows **its own hypothetical execution** — signals from `check_sweep_flow_signal` filled at
> the next session's open and exited by the shared kernel — not any live decision. There is no live
> counterpart to compare against.
>
> The **liquidity gate** (`engine/liquidity.py`) is a separate thing and is a **LIVE GATE**:
> `passes_value_liquidity_gate` (Rp 5bn 30-day avg turnover) runs per-ticker inside
> `scheduled_multi_strategy_scan`, and `select_top_liquid_longs` runs in premarket. Both can veto.

### 6.4 Does it have proven edge? **No — the evidence is negative.**

**(a) Structural backtest, price-only, full history** (`sweep_validation_2026-06-24.md`): 15 LQ45
names, **12 of 15 negative**; Sharpe from −2.51 to +0.50; only AMRT/MDKA/ANTM positive.

**(b) Walk-forward, `wf_edge`** — its rule already has parity, so this IS rule-valid evidence:

| | |
|---|---|
| Tickers with n ≥ 20 | 724 |
| Positive | 154 (21.3%), mean of positives +1.430% |
| Cross-ticker mean | **−0.935%** (median −1.095%) |
| **Trade-weighted over 31,136 pooled OOS trades** | **−0.984%** |

The 154 positives are the right tail of a decisively negative distribution, from 3,869 cells searched
with no multiplicity control.

**(c) Forward test** — N = 3 closed:

| Ticker | signal | entry | exit | net | R | hold | reason |
|---|---|---|---|---|---|---|---|
| STAA | 07-01 | 07-02 | 07-06 | −3.27% | −1.12 | 3 | SL |
| VKTR | 07-01 | 07-02 | 07-13 | +23.41% | +2.46 | 7 | TP |
| RMKE | 07-01 | 07-02 | 07-15 | +18.24% | +2.44 | 9 | TP |
| JSMR | 06-30 | 07-01 | — | — | — | **43** | **still OPEN** |

Mean +12.8% on **N=3, one week, one regime, with a fourth trade unresolved**. Under the
pre-registered stopping rule (no read before 60 sessions) this is **zero evidential weight**.

**Verdict: NOT PROVEN — and the two adequately-powered tests are both negative.** Keeping it in
`disabled_strategies` is correct.

---

## 7. WALK-FORWARD → PRODUCTION CONNECTION

**Verified from the system, not the status text.**

| Claim in brief | Verified state |
|---|---|
| job still running | **NO — dead.** pid 811925 exited. |
| ~959 tickers, ~850 processed | Reached **950/959, 937 scored, 0 compute errors** |
| writing `wf_edge_rule`, `wf_rule_study` | **Wrote neither.** |

**Defect P-1.** `research_runs` row `62d3d8b71a00`: started 13:11:34, finished 17:00:38,
**229.1 min, status ERROR, `database is locked`**. Traceback terminates in
`engine/wf_edge.py:85 save_wf_edge_rule`. The job computes for ~4h with no open transaction, then
writes every ticker in one transaction; `data/db.py` sets `busy_timeout=30000` (30s), which a
contended 8.5 GB WAL database under concurrent backfill exceeded. **~4 hours of correct computation
was discarded.** No data corruption — `wf_edge` (3,869) and `wf_scores` (13,244) are untouched.

**What survived:** the targeted run `664b4697` — `Trend Following Breakout`, 29 min, **946/959
tickers, 0 qualifying rows, 0 errors** — committed successfully and is recorded in `wf_rule_study`.

**Is the data consumed by production?** Yes, proven: `engine/admission.py::_wf_row` reads
`wf_edge_rule` when live rule ≠ researched rule, and `rule_researched()` reads `wf_rule_study`.
Current contents: `wf_edge_rule` 7 rows (smoke test only), `wf_rule_study` 1 row (TFB).

---

## 8. PROVEN VS HEURISTIC COMPONENTS

| Component | Code | Data | Historical/OOS evidence | Production influence | Classification |
|---|---|---|---|---|---|
| `reversal_watchlist` (R) | `screener/reversal_filter.py` | broker flow | none found | EOD candidate + score | **HEURISTIC** |
| `daily_screen` bullish (S) | `screener/screener_jobs.py` | OHLCV/technicals | none found | EOD candidate + score | **HEURISTIC** |
| volume mover (V) | same row as S | `daily_screen.vol_ratio` | none; threshold 5.0 hand-set | EOD score | **HEURISTIC** (not independent of S) |
| premover | `engine/premover_detector.py` | intraday | none found | premarket discovery, **off by default** | **HEURISTIC** |
| bear dip | `engine/watchlist.py` | OHLCV + RSI | none found | premarket discovery, **off by default** | **HEURISTIC** |
| liquidity filter | `engine/liquidity.py` | `ohlcv` | none — thresholds hand-set | **LIVE GATE**, can veto | **HEURISTIC** but decision-bearing |
| Liquidity Sweep (shadow) | `smc.py`+`smc_flow.py`+`strategies.py` | OHLCV + `stockbit_flow` | **negative**: structural 12/15 losing; WF trade-weighted **−0.984%** | none (disabled) | **HEURISTIC, refuted** |
| Agent Firm | `engine/agent_firm/` | context objects | none linking confidence → outcome | **can veto**, sets ranking | **HEURISTIC** |
| `wf_edge` | `engine/wf_edge.py` | `ohlcv` (adjusted) | rolling OOS, costs applied | admission input | **PARTIALLY VALIDATED** — measures the *bare* rule, valid only for the 3 bypass strategies |
| `wf_edge_rule` | same | same | rolling OOS under the **production** rule | admission input | **PARTIALLY VALIDATED** — correct by construction, but nearly empty (P-1) |
| registry | `engine/registry_loader.py` | YAML + manifests | receipt-bound (R-10) | **can veto** | **PROVEN mechanism**, 0 APPROVED entries |
| edge/veto | `engine/veto.py` | `wf_edge*`, flow | thresholds hand-set | **shadow mode → cannot veto** | **HEURISTIC / REPORTING ONLY today** |
| `watchlist_snapshot` | `engine/trade_plan.py` | — | n/a | none | **REPORTING ONLY** |
| `watchlist_snapshot_log` | `engine/watchlist_ledger.py` | — | n/a | **base plan for premarket** | decision-bearing |

**No component is PROVEN / OOS VALIDATED with live production influence.** The one strategy whose
OOS signature is positive (NR7 Breakout, trade-weighted +1.641% over 1,311 trades) is registry
SHADOW, fails rule parity, and was rejected by the gatekeeper 5/5.

---

## 9. CURRENT RISKS / DUPLICATION

| ID | Risk | Evidence |
|---|---|---|
| **P-1** | 4h research runs can be silently discarded by a 30s lock timeout | `research_runs` `62d3d8b71a00` ERROR |
| **P-2** | An empty plan is unrecorded, so premarket cannot find a base plan | `watchlist_snapshot_log` 0 rows; `latest_date_before(eod,'2026-09-03')` → `None`; EOD 2026-09-02 approved 0 |
| **P-3** | `Liquidity Sweep` has no time stop; `distribution` does | JSMR open 43 hold-days vs max 7 for 500 distribution positions |
| R-4 | Revision thresholds unvalidated | `FOREIGN_NET_MATERIAL` etc. hand-set — **NOT PROVEN** |
| R-5 | `EDGE_SCORE_MODE=shadow` means every statistical veto is inert | confirmed in `.env` and in the 2026-09-02 EOD log |
| R-6 | 501 open shadow positions, one unbounded — open-set survivorship distorts cohort stats | `ft_shadow_position` |
| R-7 | S and V fire on the same `daily_screen` row but score additively | `trade_plan.py:81–84` |
| R-8 | `confirm_sweep_flow` returns `confirmed: True` on missing data | `smc_flow.py` passthrough |
| R-9 | `test_db_centralization` failing from concurrent edits (not this work) | `engine/platform_info.py`, `engine/ticker_detail.py` |

**Duplication: largely resolved.** The two parallel generators were collapsed on 2026-09-02. What
remains is `build_unified_watchlist` retained as an optional, default-off discovery source.

---

## 10. FORWARD TEST PROTOCOL

The infrastructure exists (`engine/forward_window.py`, opened 2026-09-02, one window per cohort,
append-only, config-hash contamination detection). Protocol:

**EOD (16:40)** — freeze into `watchlist_snapshot_log`: candidate universe, source tags, confluence,
`candidate_score`, attributing strategy + `rule_id` + `admission_path`, OOS evidence as of that
moment, decision price + basis, entry rule, Agent Firm decision + confidence. *Must include the
empty case (P-2).*

**Overnight** — permitted information only: `corporate_action_events`, `suspension_events`,
`news_mentions`, settled `broker_flow`, `vpin_scores`, reconciled OHLCV, market risk tier. All land
after 16:40 per `scheduler/__init__.py`. Explicitly excluded: `reversal_watchlist`,
`watchlist_premover`, `regime_watchlist` (written 16:15–16:30, pre-EOD).

**Premarket (08:35)** — revise, record every RETAIN/REMOVE/UPGRADE/DOWNGRADE/ADD with reason and
evidence into `watchlist_revision`, freeze into `watchlist_snapshot_log(premarket)`.

**Open** — `ShadowPositionManager` fills at `resolver.next_open(ticker, signal_date)`. Verified:
0 of 2,111 closed trades entered on or before their signal bar.

**Measure per cohort, never pooled:** next-open→next-close return, MFE, MAE, hit rate, expectancy,
turnover, EOD↔Premarket agreement, additions/removals, slippage sensitivity, liquidity impact.
Report the **per-date** statistic alongside per-signal; bootstrap **blocked by date**.

**Stopping rule** (already frozen in `ft_window.decision_rule`): no read < 60 sessions; no GO/NO-GO
< 125 sessions AND < 100 signals; GO needs per-date mean excess over IHSG positive with 95% CI
excluding zero; Bonferroni α = 0.0167 across 3 cohorts.

### Liquidity Sweep shadow forward test (Part 6 of the brief)

It already runs and must **not** be given any influence. Required additions: record the sweep
measurement itself (`sweep_type`, `level_price`, `wick_pct`, flow `source`/`score`/`confirmed`, the
0.30 wick threshold, PASS/FAIL) — none is currently persisted. Horizon from the strategy's own exit
policy: TP at 2.5×ATR, SL at 1.0×ATR ⇒ **10 sessions** with MFE/MAE, plus next-session and 3-day
returns. **Fix P-3 first**: without a time stop the cohort has no bounded horizon (JSMR, 43 days).

---

## 11. RECOMMENDED ARCHITECTURE

Keep the 2026-09-02 architecture. Ordered work, none implemented:

1. **Fix P-2** (blocking) — record an explicit empty-plan row, or a `PUBLISHED` event row, so
   `latest_date_before` finds it.
2. **Fix P-1** (blocking research) — chunk the write per ticker with commit, and raise
   `busy_timeout` for long research writes; re-run `wf-parity`.
3. **Fix P-3** — give `Liquidity Sweep` an explicit `hold_days`, matching its backtest.
4. Persist sweep measurements for the shadow forward test.
5. Leave `EDGE_SCORE_MODE=shadow` until the window produces a read.
6. Leave `disabled_strategies` untouched.

---

## 12. CODE CHANGES REQUIRED — NOT IMPLEMENTED

| # | File | Change | Why |
|---|---|---|---|
| C-1 | `engine/watchlist_ledger.py` | `append_snapshot` must leave a queryable trace for an empty plan | P-2 |
| C-2 | `research/jobs.py`, `data/db.py` | chunked commits + longer `busy_timeout` for research writes | P-1 |
| C-3 | `engine/exits/policy.py` | `Liquidity Sweep` → explicit `hold_days` | P-3 |
| C-4 | `forward_testing/adapters/signal_adapter.py` | persist sweep measurement fields | Part 6 |
| C-5 | `engine/premarket_revision.py` | move hand-set thresholds into the frozen window config | R-4 |
| C-6 | `engine/trade_plan.py` | make S/V non-additive or document why not | R-7 |

## 13. TESTS REQUIRED

T-1 empty plan is retrievable and `latest_date_before` finds it · T-2 research write survives a
held write lock · T-3 every `ExitPolicy` bounds holding period or documents why not · T-4 sweep
measurement persisted with signal · T-5 revision thresholds appear in the frozen window hash ·
T-6 shadow cohort cannot influence candidate selection, Agent Firm, execution, sizing or risk ·
T-7 `wf_edge_rule` never consulted for a bypass strategy and vice versa.

## 14. ACCEPTANCE CRITERIA

1. `run_eod_trade_plan` with 0 approvals leaves a retrievable record; next premarket finds it.
2. `wf-parity` completes and writes `wf_rule_study` for all 11 gated strategies.
3. No `ft_shadow_position` open beyond its policy's bounded horizon.
4. Every Liquidity Sweep shadow signal carries its sweep measurement and threshold.
5. `scripts/parity_evidence_report` runs clean; any PASS is separated from policy gates.
6. Forward windows remain `OPEN` with unchanged config hashes, or roll with recorded reasons.
7. Full suite green except the two known `news_filter` isolation failures.
8. `paper_trades` remains empty until a strategy is deliberately promoted.
