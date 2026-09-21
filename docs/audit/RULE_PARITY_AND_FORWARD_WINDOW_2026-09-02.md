# Rule Parity, Canonical Strategy Version, and the Clean Forward-Test Window

**Date:** 2026-09-02 · **Branch:** `ops/hardening-2026-07-10`
**Authority:** point-in-time research record (generated; superseded, never edited)
**Predecessor:** `docs/audit/SIGNAL_PROVENANCE_AUDIT_2026-09-02.md` (audit + remediation addendum)
**Scope:** closes remaining blockers 2, 3 and 5 from that addendum. No gate was weakened.
No BUY signal was manufactured.

---

## 1. What was blocking, and what this closes

| # | Blocker (from the remediation addendum) | Closed by |
|---|---|---|
| 2 | **Rule parity unresolved for every gated strategy.** Production applies a weekly MTF trend gate that research never applied, so `wf_edge` was evidence about a rule the engine does not execute. | A walk-forward study re-run **with the gate applied**, written to a rule-indexed table (`wf_edge_rule`). The remedy chosen is (b) *research the production variant* — not (a) remove the gate, which would have loosened production on no evidence. |
| 3 | **`ft_strategy_version` empty**; `strategy_version_id`/`config_hash` NULL on every `ft_signal`. | `engine/strategy_version.py` — a canonical version per strategy, hashed over the backtest function, the live checker, the live gate set and the exit policy. Both forward-test adapters now stamp it. |
| 5 | **No clean forward-test window.** Nothing recorded what "the system" was when a cohort started accumulating, so a quiet config change would silently redefine what was being measured. | `engine/forward_window.py` — pre-registered, append-only windows with a frozen config hash re-checked every cycle; a change closes the window as CONTAMINATED and opens a successor. |

Blockers 1 (no strategy passes OOS validation) and 4 (`engine/platform_info.py` / `engine/ticker_detail.py` failing `test_db_centralization`, owned by concurrent work) are addressed in §6 and §8 respectively.

---

## 2. The weekly gate, expressed exactly

`engine.indicators.calc_weekly_trend(df)` answers "does the **last** bar of this frame pass?".
The walk-forward engine needs a **per-bar** mask. `engine/filters_mtf.py` provides one:

```
weekly_mtf_mask(df)[i]  ==  calc_weekly_trend(df.iloc[:i+1])[0]     for all i
```

**This is asserted, not assumed.** Two independent checks:

| Check | Result |
|---|---|
| Real corpus, 25 random tickers × 40 random bars each | **960 bar-level comparisons, 0 mismatches** |
| Synthetic frames across up / down / flat regimes, including the soft-pass boundaries (<100 bars, <22 weeks) | `tests/test_filters_mtf.py`, 19 tests, all passing |

Causality is asserted separately: truncating the frame after bar *i* must not change `mask[i]`
(`test_mask_value_at_i_is_unchanged_by_later_bars`). The current week's weekly close is bar *i*'s
own close, which is exactly what the live gate sees intraday.

The gate is also proven to be a **pure restriction** — it can only remove candidate entries, never
create one (`TestGateIsAPureRestriction`): the gated trade set is a strict subset of the bare set on
identical frames. This matters twice: it makes running the gate in production strictly conservative
relative to the researched rule, and it bounds what the parity study can find.

---

## 3. Evidence is now indexed by the rule that produced it

New research-owned table, `PRIMARY KEY (ticker, strategy, rule_id)`:

```sql
wf_edge_rule(ticker, strategy, rule_id, expectancy_pct, expectancy_rp, win_rate,
             consistency_pct, sharpe, n_trades, windows_tested, last_computed, run_id)
```

`rule_id` comes from `engine/rule_identity.py`: `<strategy>@<gate set>#<digest>`, e.g.
`NR7 Breakout@weekly_mtf_trend#dcbd1d87d31d` vs `NR7 Breakout@bare#49adb725b2fc`.

`engine/admission.py` now resolves evidence **by rule**:

- live rule == researched (bare) rule — the three `_WEEKLY_GATE_BYPASS` strategies — `wf_edge` **is**
  the rule-valid study and is used directly;
- otherwise **only** `wf_edge_rule` under the live `rule_id` counts. There is deliberately no
  fallback to `wf_edge`: that would be finding L-1 reintroduced one level up.

Three distinct outcomes are now distinguishable, each with its own remedy:

| Verdict stage | Meaning | Remedy |
|---|---|---|
| `rule_parity` | no study exists under the live rule at all | run `python -m research.cli wf-parity` |
| `oos_evidence` | the rule **was** studied, but this (ticker, strategy) has no qualifying sample | nothing — the evidence floor is doing its job |
| `evidence_staleness` | qualifying sample, but older than 14 days | re-run the study |

`wf_edge` and `wf_scores` are **left untouched**. They are the frozen record of the bare-rule study
and remain valid evidence for the bypass strategies. Nothing was migrated or overwritten.

---

## 4. Methodological finding W-1 — the bare study under-warmed its indicators

The parity run changes **two** things relative to the 2026-08-28 bare study, and honesty requires
naming both:

1. the weekly gate is applied (the point of the exercise);
2. the per-window indicator warm-up tail rises from **60 bars to 160**.

The second is not a convenience. `calc_weekly_trend` soft-passes below 100 bars and 22 weeks, and its
MA20 + 5-week slope needs ~25 weeks (~125 bars); a 60-bar tail would have measured *"gate mostly
switched off"* and produced a flattering, meaningless result.

Measuring the two effects separately on eight liquid tickers:

| Strategy | bare / warm-60 | bare / warm-160 | gated / warm-160 |
|---|---|---|---|
| Trend Following Breakout | 13 | **24** | 24 |
| NR7 Breakout | 66 | 66 | **15** |

Two things follow:

- **The existing `wf_edge` under-counts trades for slow-indicator strategies.** TFB nearly doubled its
  pooled trade count purely from a longer warm-up: with only 60 prior bars its 50-bar MA and ADX were
  not warm at each window start, so early test bars could not signal. Live never has this problem —
  it always has years of history. The 160-bar tail is therefore **more faithful to production**, not
  less. This is a defect in the bare study, recorded here rather than silently corrected.
- **The weekly gate binds hard on NR7 (−77% of trades) and not at all on TFB.** TFB only fires in
  uptrends, which is precisely when the weekly gate passes; the gate is close to redundant for it.
  This is a substantive result about the gate, obtainable only by measuring it.

Consequence for interpretation: the parity study is *not* "the bare study plus a gate". It is a
better-warmed study **with** the gate. Comparing its expectancies directly against `wf_edge` mixes
the two effects, and this document does not do so.

---

## 5. Canonical strategy version

`engine/strategy_version.py` records, per strategy, a `config_hash` over:

- the walk-forward **backtest function** source,
- the **live checker** source,
- the **live gate set**,
- the entry-rule and exit-policy references.

Hashing both sides together is deliberate: research and production silently diverging is exactly what
finding L-1 was. A divergence now changes the version, which changes the frozen window config, which
closes the forward-test cohort — so it cannot be absorbed unnoticed.

Recorded in production: **17 rows** in `ft_strategy_version` — all 14 `STRATEGY_FUNCS` entries plus
the three cohort pseudo-strategies (`eod`, `premarket`, `distribution`) so heuristic cohorts are also
pinned to the code that produced them. `NR7 Breakout` carries its registry version
(`v2+6e731afe9787dbc4`); the rest are `live+<hash>`.

Both adapters now stamp `strategy_version_id` and `config_hash` on every ingested signal.
**Pre-existing rows are deliberately left NULL** rather than back-filled with a version they did not
run under.

---

## 6. The clean forward-test window

Opened in production on **2026-09-02**, one per cohort, none pooled:

| Cohort | window | config hash |
|---|---|---|
| `scanner` | `3131fc4fffb1` | `a9cb87f806d48c59` |
| `eod` | `2543a7a1c1ea` | `6af3e200437ea1c7` |
| `premarket` | `0eed1d1270c1` | `76d331f595dc3d22` |

**Frozen configuration** (hashed, re-checked every 18:30 cycle): `edge_score_mode`, registry hash,
`paper_config` (incl. `disabled_strategies` and the event guard), the scanner's regime map /
counter-trend set / momentum family / default-disabled string, admission thresholds
(`WF_EDGE_MAX_AGE_DAYS`, `N_MIN_TRADES`), every `veto.py` threshold and cap, `trade_plan` and
`unified_watchlist` weights, the cost model, the entry rule, and every strategy's `config_hash`.

Deliberately **not** in the hash: the evidence rows themselves. A weekly `wf-refresh` is normal
operation; including it would roll every window weekly and make a 125-session window unreachable. The
window measures the **system's rules**, not its inputs.

**Pre-registered stopping rule**, frozen before the window opened:

> Primary statistic: mean **net** return per signal at a 5-session horizon, entry at the next session
> open after the signal date, both legs through `engine.exits.costs`, benchmarked against IHSG over
> the identical window. Report the **per-date** mean alongside the per-signal mean and bootstrap the
> CI **blocked by date** — overlapping holds on one name are not independent draws. No read before
> **60 sessions**. No GO/NO-GO before **125 sessions AND 100 signals**. GO requires the per-date mean
> excess over IHSG to be positive with a 95% bootstrap CI excluding zero. Multiple-testing family:
> 3 cohorts × 1 horizon, Bonferroni alpha 0.0167 per cohort. Cohorts are never pooled.

Both `ft_window` and `ft_window_event` are append-only (BEFORE UPDATE/DELETE triggers). A window is
never edited; closure is a new event row and status is derived. A configuration change does not fail
the run and does not stop trading — it closes the cohort as `CLOSED_CONTAMINATED` and opens a
successor linked by `predecessor_id`. That is the only honest way to keep a live system under test
while still being allowed to fix it.

---

## 7. Does any strategy pass OOS + rule parity + freshness?

`python -m scripts.parity_evidence_report` answers this in one command, from the rule-indexed study.
A strategy passes only if, for at least one ticker: evidence exists **under the live rule_id**,
pooled OOS sample ≥ 20, pooled net expectancy > 0, evidence ≤ 14 days old, the strategy is not
disabled, it has a live checker, and it is routed by some regime band.

### 7.1 Result — **NO strategy currently passes**

**Conclusion: no strategy is admissible on OOS + rule parity + freshness. Zero BUY signals
remains the correct output.** Nothing was loosened to reach a different answer.

| Strategy | Study consulted | Rows | Qualifying tickers | OOS + parity + fresh | Policy gates |
|---|---|---|---|---|---|
| Liquidity Sweep | `wf_edge` (parity holds) | 724 | **154** | **PASS** | `disabled_strategies` |
| Trend Following Breakout | `wf_edge_rule` | 0 | 0 | studied, nothing cleared n≥20 | — |
| NR7 Breakout | `wf_edge_rule` | 0 | 0 | not yet studied | — (registry **SHADOW**) |
| Crash Recovery | `wf_edge` (parity holds) | 0 | 0 | studied, nothing cleared n≥20 | — |
| Panic Rebound | `wf_edge` (parity holds) | 0 | 0 | studied, nothing cleared n≥20 | — |
| conservative / momentum / vol_weighted | `wf_edge_rule` | 7 (partial) | 0 | nothing cleared n≥20 | `disabled_strategies` |
| vwap_reversion / ORB / Volume Profile POC / Inside Bar Breakout | `wf_edge_rule` | 0 | 0 | study in progress | `disabled_strategies` (+ 3 lack a live checker / regime route) |
| Swing Trend / VWMA Breakout Pullback | `wf_edge_rule` | 0 | 0 | study in progress | no live checker; not routed |

#### The decision reduces to one strategy, and it was measured

Of the fourteen strategies, exactly **one** could have had its admissibility changed by the parity
study — `Trend Following Breakout`. Every other path is closed before evidence is consulted:

- `NR7 Breakout` is registry **SHADOW** (owner decision D-029, 2026-08-19), and SHADOW is refused at
  the registry stage *before* any evidence lookup. No study outcome can admit it.
- Seven strategies are in `disabled_strategies` by the dated 2026-07-04 negative re-baseline.
- `Swing Trend` and `VWMA Breakout Pullback` have no live checker and are not routed by any regime
  band, so admission would produce nothing even with perfect evidence.
- `Crash Recovery` and `Panic Rebound` are bypass strategies (parity already holds) with **zero**
  `wf_edge` rows — under 20 pooled OOS trades on every one of 877 tickers.

**`Trend Following Breakout`, measured under the production rule:**

```
run_id 664b4697…  946/959 tickers scored, 0 errors, 29 minutes
gates=['weekly_mtf_trend']  warmup=160
qualifying rows written: 0
```

Not one ticker out of 946 reached the 20-pooled-OOS-trade evidence floor — even with the corrected
160-bar warm-up that nearly doubled its trade count (§4). This is a measured result, not an
inference from the bare study.

#### Liquidity Sweep passes the evidence criteria and must still stay out

This is the one case where the three evidence criteria are literally satisfied, and it is worth
being explicit about why that is not a finding:

| | |
|---|---|
| Tickers with n ≥ 20 | 724 |
| Tickers with positive expectancy | **154 (21.3%)**, mean of those **+1.430%** |
| Cross-ticker mean expectancy | **−0.935%** (median −1.095%) |
| **Trade-weighted expectancy over all 31,136 pooled OOS trades** | **−0.984%** |

The 154 positives are the right tail of a distribution whose centre is decisively negative, drawn
from **3,869 (ticker, strategy) cells searched with no multiplicity control**. Selecting them is a
textbook data-snooping construction, which is precisely what the strategy's own validation record
already concluded (`data/reports/sweep_validation_2026-06-24.md`: no edge, Sharpe −0.60, 3/15 LQ45
profitable) and why it sits in `disabled_strategies`.

`scripts/parity_evidence_report.py` therefore reports evidence status and policy status in separate
columns and refuses to collapse them into one verdict. **Re-enabling Liquidity Sweep would
manufacture signals from a negative distribution's tail. It was not done and should not be.**

For contrast, `NR7 Breakout` under the **bare** rule is the only strategy with a genuinely positive
signature — 43 of 54 tickers positive, trade-weighted **+1.641%** over 1,311 pooled trades. It is
also the one whose rule parity does *not* hold, whose gate cuts 77% of its trades (§4), and which the
gatekeeper rejected five times out of five. Its parity study is still running; even a positive result
cannot admit it while it is SHADOW.

#### Study still running

The full gated roster (11 strategies × 959 tickers) is in progress at the time of writing; the
targeted `Trend Following Breakout` pass — the only decision-relevant one — completed. The remaining
strategies are all blocked by non-evidence gates, so their numbers refine the record (they matter if
the owner ever re-enables one) but cannot change the verdict above. `wf_rule_study` records every
study that RAN, including those that produced zero qualifying rows, so "studied and nothing
qualified" is never again confused with "never studied".

---

## 8. Reproduction

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && source venv/bin/activate

# equivalence of the mask and the live gate
python -m pytest -q tests/test_filters_mtf.py

# the parity study (long; ~5h for the full gated roster over 959 tickers)
python -m research.cli wf-parity
python -m research.cli wf-parity --strategies "Trend Following Breakout" \
                                 --lock-job wf_parity_tfb      # targeted

# the deliverable
python -m scripts.parity_evidence_report
python -m scripts.parity_evidence_report --json

# admission chain and point-in-time replay
python -m scripts.admission_report
python -m scripts.scanner_replay --days 20 --limit-tickers 150

# window + version state
sqlite3 -readonly data/walkforward.db \
  "SELECT cohort, window_id, config_hash, start_date FROM ft_window;" \
  "SELECT strategy, version FROM ft_strategy_version ORDER BY strategy;"
```
