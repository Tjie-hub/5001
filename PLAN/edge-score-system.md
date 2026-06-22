# Edge Score System — Implementation Plan (rev 2)

> Date: 2026-06-22
> Status: Draft (awaiting approval before Phase 1 begins)
> Repo: `/home/tjiesar/10 Projects/idx-walkforward-5001`
> Rev 2 changes: per-trade **% expectancy** (capital-invariant) replaces the
> mis-scaled Rp anchor; **two-tier veto** (directional/flow/catalyst hard gates
> *plus* statistical gates) so the INCO leak is actually closed; **market regime
> vs per-ticker regime** split; regime-scaled **0/1/3 session cap**; catalyst flag;
> `off/shadow/enforce` tri-state flag; dead `win_rate`/`sharpe` params removed from
> the scorer.

---

## Summary

The current system sizes trades on the LLM risk agent's `size_hint` (its weakest, least-validated signal) and uses walk-forward OOS data only as a consistency blacklist (its strongest signal). Walk-forward expectancy, win_rate, and trade count — computed inside `walkforward_multi.py` — are never persisted, and the `weighted_score` in `wf_scores` is normalized *within each ticker*, so it cannot rank ticker A vs ticker B.

This plan does two distinct things, and **both matter**:

1. **Evidence-based sizing** — a deterministic `edge` score, dominated by validated OOS per-trade expectancy, becomes the ranking key and the position-size input (replacing the LLM `size_hint`).
2. **Directional safety** — deterministic pre-LLM vetoes that hard-skip a candidate when *today's* flow/technical/regime points the wrong way and no dated catalyst justifies it. This is what stops the INCO case (great history, but DISTRIBUTING flow + bearish technical *today*). Edge sizing alone does **not** catch this — flow is only a 0.20 term and a strong-history name can still clear the floor while distributing. The hard veto is non-negotiable for that reason.

Guiding principle: **better no pick than bad pick.** An empty survivor list is a valid, good output. All anchors are fixed (not cross-sectional), all missing data excludes rather than zero-fills, and absent catalyst data makes the vetoes *stricter*, not looser.

Four phases, each independently shippable. `.bak` per file. No git-history rewrite. House rules honored throughout.

---

## Architecture Overview

```
Walk-Forward Engine (existing)
    │
    ├──> wf_scores  (existing: consistency_pct, avg_return_pct, avg_sharpe,
    │                weighted_score, windows_tested) [within-ticker norm — unchanged]
    │
    └──> wf_edge    (NEW P1: expectancy_pct, win_rate, n_trades, consistency_pct,
                     sharpe, windows_tested) [cross-sectional, per-trade %]

Stockbit Flow DB (existing)  → composite_score [-8..+8], foreign_score, verdict
Regime Filter (existing)     → detect_regime(df) → BULL / BEAR / SIDEWAYS
                               (a) MARKET regime = detect_regime(IHSG) + macro overlay
                               (b) per-TICKER regime = detect_regime(ticker df)
Technical (existing)         → calc_votes(df) → 1..4
Catalyst flags (NEW P3)      → catalyst_flags table → has_catalyst(ticker, date)

                    │
                    ▼
        ── enrichment (P3) ──  join wf_edge + flow + per-ticker regime + votes
                    │            + market regime + catalyst, per candidate
                    ▼
        engine/edge_score.py (NEW P2)
        edge = 0.40·norm(expectancy_pct) + 0.20·consistency
             + 0.20·flow_strength + 0.10·regime_fit(per-ticker) + 0.10·technical
                    │
                    ▼
        Pre-LLM Veto Stage (NEW P3)  — order matters
          Tier A  directional safety (HARD skip, catalyst-overridable)
                  d1 distributing flow · d2 bearish tech (no MR thesis)
                  d3 tech⇄flow disagree · d4 market RISK_OFF
          Tier B  statistical edge gates (HARD skip)
                  s1 n_trades<20 · s2 consistency<30 · s3 win_rate<35
                  s4 edge < EDGE_FLOOR[market_regime]
          Cap     N_MAX[market_regime] = 3 / 1 / 0 (catalyst may add one)
          Size    size_mult = round(edge, 2)  for survivors only
                    │
                    ▼
        Agent Firm (existing — survivors-only; judgment, not gatekeeping)
                    │
                    ▼
        Paper Trade Execution (existing) — lots_multiplier = size_mult
```

---

## Phase 1 — `wf_edge` Table (OOS per-trade expectancy aggregation)

### Motivation

`compute_metrics()` (walkforward_multi.py:32) returns per-window `total_trades`, `total_pnl_rp`, `avg_pnl_pct`, `win_rate` (0–100), and `sharpe` — but `refresh_wf_scores()` (jobs.py) discards them. `weighted_score` is within-ticker normalized (walkforward_multi.py:326–329), useless cross-sectionally.

**Expectancy is stored as per-trade percent, not Rupiah.** Rp expectancy = Σpnl_rp / Σtrades scales with backtest capital (50jt) and per-trade position size, so a fixed Rp anchor is fragile and was the source of the rev-1 1000× bug. `avg_pnl_pct` is already per-trade and capital-invariant.

### `wf_edge` schema

| Column | Type | Source |
|--------|------|--------|
| `ticker` | TEXT | PK part 1 |
| `strategy` | TEXT | PK part 2 |
| `expectancy_pct` | REAL | trade-weighted mean of per-window `avg_pnl_pct`: Σ(avg_pnl_pct·n)/Σn |
| `expectancy_rp` | REAL | Σpnl_rp / Σtrades — informational only (capital-dependent) |
| `win_rate` | REAL | Σwinners / Σtrades across windows (pooled, not avg-of-avg) |
| `consistency_pct` | REAL | % of windows with positive return (from existing summary) |
| `sharpe` | REAL | trade-weighted mean of window sharpe — informational/veto only |
| `n_trades` | INTEGER | Σ OOS trades across windows |
| `windows_tested` | INTEGER | number of walk-forward windows |
| `last_computed` | TEXT | ISO timestamp |

Exclusion gate: rows with `n_trades < N_MIN_TRADES` (default 20) are not inserted. No zero-fill — absence = "not enough evidence."

### Implementation

#### 1.1 New file: `migrations/add_wf_edge.sql`

```sql
CREATE TABLE IF NOT EXISTS wf_edge (
    ticker            TEXT    NOT NULL,
    strategy          TEXT    NOT NULL,
    expectancy_pct    REAL    NOT NULL,
    expectancy_rp     REAL    NOT NULL,
    win_rate          REAL    NOT NULL,
    consistency_pct   REAL    NOT NULL,
    sharpe            REAL    NOT NULL,
    n_trades          INTEGER NOT NULL,
    windows_tested    INTEGER NOT NULL,
    last_computed     TEXT    NOT NULL,
    PRIMARY KEY (ticker, strategy)
);
```

Follow the existing `migrations/` + `migrations/applied/` convention (inspect one applied migration first for the apply/record pattern).

#### 1.2 Patch: `engine/walkforward_multi.py::compute_metrics`

Add an exact winner count so win_rate aggregation is exact rather than reconstructed from a rounded percent. `winners` is already computed there; add to the return dict:

```python
'total_winners': len(winners),
```

(One line. Everything else in `compute_metrics` and `run_walk_forward` is unchanged — the per-window dicts already carry `total_trades`, `total_pnl_rp`, `avg_pnl_pct`, `sharpe`, and now `total_winners`, and `run_walk_forward` preserves them under `summary[name]['windows']`, which `_rank_strategies` passes through in `ranked`.)

#### 1.3 New file: `engine/wf_edge.py`

```python
"""
engine/wf_edge.py — Cross-window OOS expectancy aggregation.

Aggregates across all walk-forward windows for a (ticker, strategy) pair so
expectancy is pooled, not an average of per-window averages.  Expectancy is
per-trade PERCENT (capital-invariant); Rp expectancy is kept for reference only.
"""
import sqlite3
from typing import List

N_MIN_TRADES = 20   # configurable; below this we make no edge claim


def aggregate_wf_windows(ranked: List[dict]) -> List[dict]:
    """One row per strategy from run_walk_forward()'s `ranked` list."""
    results = []
    for metrics in ranked:
        windows = metrics.get('windows', [])
        if not windows:
            continue

        n = sum(w['total_trades'] for w in windows)
        if n < N_MIN_TRADES:
            continue

        pnl_rp  = sum(w['total_pnl_rp'] for w in windows)
        winners = sum(w.get('total_winners', 0) for w in windows)
        # trade-weighted pooled mean of per-trade % return
        exp_pct = sum(w['avg_pnl_pct'] * w['total_trades'] for w in windows) / n
        sharpe  = sum(w['sharpe']      * w['total_trades'] for w in windows) / n

        results.append({
            'strategy':         metrics['strategy'],
            'expectancy_pct':   round(exp_pct, 3),
            'expectancy_rp':    round(pnl_rp / n, 2),
            'win_rate':         round(winners / n * 100, 1),
            'consistency_pct':  metrics.get('consistency_pct', 0.0),
            'sharpe':           round(sharpe, 2),
            'n_trades':         n,
            'windows_tested':   metrics.get('windows_tested', len(windows)),
        })
    return results


def save_wf_edge(conn: sqlite3.Connection, ticker: str,
                 rows: List[dict], now_str: str) -> int:
    """INSERT OR REPLACE into wf_edge. Returns count written."""
    for r in rows:
        conn.execute(
            """INSERT OR REPLACE INTO wf_edge
               (ticker, strategy, expectancy_pct, expectancy_rp, win_rate,
                consistency_pct, sharpe, n_trades, windows_tested, last_computed)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (ticker, r['strategy'], r['expectancy_pct'], r['expectancy_rp'],
             r['win_rate'], r['consistency_pct'], r['sharpe'],
             r['n_trades'], r['windows_tested'], now_str),
        )
    return len(rows)
```

#### 1.4 Patch: `scheduler/jobs.py::refresh_wf_scores`

Inside the existing per-ticker loop, after the `wf_scores` INSERT, add (uses the in-scope `ranked`, `ticker`, `conn`, `now_str`):

```python
# NEW: persist wf_edge (cross-window OOS per-trade expectancy)
from engine.wf_edge import aggregate_wf_windows, save_wf_edge
save_wf_edge(conn, ticker, aggregate_wf_windows(ranked), now_str)
```

After the loop:

```python
edge_count = conn.execute(
    "SELECT COUNT(*) FROM wf_edge WHERE last_computed=?", (now_str,)
).fetchone()[0]
print(f"[WF] wf_edge updated: {edge_count} rows")
```

#### 1.5 Tests: `tests/test_wf_edge.py`

| Test | Verifies |
|------|----------|
| `test_aggregate_empty` | no windows → `[]` |
| `test_expectancy_pct_pooled` | windows (2%,10t)+(−1%,10t) → trade-weighted 0.5% |
| `test_expectancy_rp_informational` | Σpnl_rp / Σtrades |
| `test_win_rate_pooled_exact` | (3/10)+(7/10) = 10/20 = 50% via `total_winners` |
| `test_n_min_exclusion` | n_trades=15 → excluded |
| `test_n_min_inclusion` | n_trades=25 → included |
| `test_save_and_readback` | temp DB write/read, columns intact |

### Files touched (Phase 1)

| File | Action |
|------|--------|
| `migrations/add_wf_edge.sql` | NEW |
| `engine/wf_edge.py` | NEW |
| `engine/walkforward_multi.py` | PATCH (+1 line: `total_winners` in `compute_metrics`) |
| `scheduler/jobs.py` | PATCH (~6 lines in `refresh_wf_scores`) |
| `tests/test_wf_edge.py` | NEW |

---

## Phase 2 — `engine/edge_score.py` (config-driven edge score)

### Design

Pure functions, no DB/side effects, fixed (not cross-sectional) anchors documented inline. **The scorer takes exactly the five weighted terms.** `win_rate` and `sharpe` are *not* score inputs — they are veto inputs only (Phase 3), so they are deliberately absent from `compute_edge`.

```python
# engine/edge_score.py

# ── Weights (config-driven) ─────────────────────────────────────────
W_EXPECTANCY  = 0.40
W_CONSISTENCY = 0.20
W_FLOW        = 0.20
W_REGIME      = 0.10
W_TECHNICAL   = 0.10

# ── Expectancy anchor (per-trade PERCENT, capital-invariant) ────────
# norm = clip(expectancy_pct, 0, MAX)/MAX.  Fixed anchor (not min-max):
# the best of a weak universe should NOT score 1.0.  3.0%/trade is "as
# good as it gets" for IDX single-stock 2–5d holds.  Negative expectancy → 0.
MAX_EXPECTANCY_PCT = 3.0

# ── Consistency anchor (natural [0,100]) ────────────────────────────
MIN_CONSISTENCY = 30.0
MAX_CONSISTENCY = 100.0

# ── Flow anchor (composite_score is integer [-8, +8], verified) ─────
MIN_FLOW_SCORE = -8.0
MAX_FLOW_SCORE =  8.0

# ── Per-ticker regime fit ───────────────────────────────────────────
REGIME_FIT = {'BULL': 1.0, 'SIDEWAYS': 0.5, 'BEAR': 0.0}
DEFAULT_REGIME_FIT = 0.3

# ── Technical (calc_votes 1..4, verified) ───────────────────────────
MIN_VOTES = 1.0
MAX_VOTES = 4.0


def _clip_norm(v, lo, hi):
    if v <= lo: return 0.0
    if v >= hi: return 1.0
    return (v - lo) / (hi - lo)


def norm_expectancy(expectancy_pct):           # None/negative → 0.0
    if expectancy_pct is None: return 0.0
    return _clip_norm(expectancy_pct, 0.0, MAX_EXPECTANCY_PCT)

def norm_consistency(c):
    if c is None: return 0.0
    return _clip_norm(c, MIN_CONSISTENCY, MAX_CONSISTENCY)

def norm_flow(composite_score):                # 0 → 0.5 (neutral)
    if composite_score is None: return 0.0
    return _clip_norm(float(composite_score), MIN_FLOW_SCORE, MAX_FLOW_SCORE)

def norm_regime(regime):                       # per-ticker BULL/SIDEWAYS/BEAR
    if regime is None: return DEFAULT_REGIME_FIT
    return REGIME_FIT.get(regime, DEFAULT_REGIME_FIT)

def norm_technical(votes):                     # 1..4
    if votes is None or votes < 1: return 0.0
    return _clip_norm(float(votes), MIN_VOTES, MAX_VOTES)


def compute_edge(expectancy_pct=None, consistency_pct=None,
                 flow_score=None, regime=None, technical_votes=None) -> float:
    """Composite edge [0,1].  Five weighted terms; missing → 0 contribution."""
    score = (
        W_EXPECTANCY  * norm_expectancy(expectancy_pct) +
        W_CONSISTENCY * norm_consistency(consistency_pct) +
        W_FLOW        * norm_flow(flow_score) +
        W_REGIME      * norm_regime(regime) +
        W_TECHNICAL   * norm_technical(technical_votes)
    )
    return round(score, 4)
```

### Tests: `tests/test_edge_score.py`

| Test | Verifies |
|------|----------|
| `test_expectancy_zero` / `_negative` | 0% or −1% → 0.0 |
| `test_expectancy_capped` | 5% → 1.0 (clamped at 3.0) |
| `test_expectancy_mid` | 1.5% → 0.5 |
| `test_consistency_floor/ceiling` | 30→0.0, 100→1.0 |
| `test_flow_neutral/bullish/bearish` | 0→0.5, +4→0.75, −4→0.25 |
| `test_regime_bull/sideways/bear/unknown` | 1.0 / 0.5 / 0.0 / 0.3 |
| `test_technical_min/max` | 1→0.0, 4→1.0 |
| `test_full_edge_good/bad` | all-good ≥0.85, all-bad ≈0.0 |
| `test_missing_all_none` | all None → regime default only (0.10·0.3=0.03) |
| `test_edge_bounded` | any combo ∈ [0,1] |

### Files touched (Phase 2)

| File | Action |
|------|--------|
| `engine/edge_score.py` | NEW |
| `tests/test_edge_score.py` | NEW |

---

## Phase 3 — Pre-LLM vetoes (directional safety + statistical), market-regime caps

### Two tiers, in order

**Tier A — directional safety (the INCO fix).** Hard-skip when *today's* signals point the wrong way and no dated catalyst justifies overriding. Catalyst-overridable.

| id | Condition | Action |
|----|-----------|--------|
| d1 | flow distributing (`composite_score ≤ FLOW_DISTRIB_CUT` = −3, or `verdict == DISTRIBUTING`, or net-foreign-sell) **and not** `has_catalyst` | skip |
| d2 | technical bearish (`tech_direction == BEARISH`) **and not** mean-reversion thesis **and not** `has_catalyst` | skip |
| d3 | technical vs flow directions disagree, **neither** catalyst-backed | skip |
| d4 | market regime == `RISK_OFF` (IHSG BEAR) **and not** `has_catalyst` | skip |

**Tier B — statistical edge gates.** Hard-skip on weak OOS evidence.

| id | Condition | Action |
|----|-----------|--------|
| s1 | `n_trades < 20` (or wf_edge missing) | skip |
| s2 | `consistency_pct < 30` | skip |
| s3 | `win_rate < 35` | skip |
| s4 | `edge < EDGE_FLOOR[market_regime]` | skip |

**Cap & size.** Session cap by **market** regime, then edge-based size:

| market regime | EDGE_FLOOR | N_MAX |
|---------------|-----------|-------|
| TRENDING (IHSG BULL) | 0.65 | 3 |
| UNCERTAIN (IHSG SIDEWAYS) | 0.72 | 1 |
| RISK_OFF (IHSG BEAR) | 0.72 | 0 (catalyst may raise to 1) |

`size_mult = round(edge, 2)` for survivors. Below floor = **skip, never shrink**.

### Deterministic direction helpers (no LLM)

- `tech_direction(df)` → `BULLISH / BEARISH / NEUTRAL` from MA structure (e.g. close vs MA20 & MA50 and MA20 vs MA50). Documented; `calc_votes` (1..4, momentum-only) feeds the *score*, not direction.
- flow direction from `composite_score` sign / `verdict`.
- `is_mean_reversion` from the candidate's strategy/source (reversal_watchlist, bear_dip, vwap_reversion, panic_rebound) — these legitimately enter against a bearish tape.

### Catalyst flag (minimal, strict-by-default)

#### 3.0 New: `migrations/add_catalyst_flags.sql`

```sql
CREATE TABLE IF NOT EXISTS catalyst_flags (
    ticker        TEXT NOT NULL,
    catalyst_date TEXT NOT NULL,   -- ISO date the catalyst is live
    kind          TEXT NOT NULL,   -- DIVIDEND_EX | EARNINGS | INDEX_EVENT | CORP_ACTION | NEWS_HARD
    note          TEXT,
    created_at    TEXT NOT NULL,
    PRIMARY KEY (ticker, catalyst_date, kind)
);
```

`has_catalyst(conn, ticker, date, window_days=2)` → any row for `ticker` within ±window of `date`. **Empty table → always False**, so absent catalyst data makes Tier A *stricter* (better no pick). Population is out of scope here: seed manually + later auto-feed from `engine/calendar_filter.py` (index/FOMC/BI events) and `news_filter`. A name only escapes a directional veto with an explicit dated catalyst on record.

#### 3.1 New: `engine/veto.py`

```python
"""
engine/veto.py — Deterministic pre-LLM vetoes + edge-based sizing.

Tier A (directional safety, catalyst-overridable) THEN Tier B (statistical),
then a market-regime session cap.  Runs BEFORE evaluate_staged(); failures are
dropped from the list handed to the agent firm.
"""
from typing import List
from engine.edge_score import compute_edge

N_MIN_TRADES    = 20
MIN_CONSISTENCY = 30.0
MIN_WIN_RATE    = 35.0
FLOW_DISTRIB_CUT = -3            # composite_score at/below = distributing

EDGE_FLOOR = {'BULL': 0.65, 'SIDEWAYS': 0.72, 'BEAR': 0.72}
DEFAULT_EDGE_FLOOR = 0.72
N_MAX = {'BULL': 3, 'SIDEWAYS': 1, 'BEAR': 0}   # by MARKET regime
DEFAULT_N_MAX = 1


def _flow_distributing(c) -> bool:
    cs = c.get('flow_score')
    if c.get('flow_verdict') == 'DISTRIBUTING':
        return True
    return cs is not None and cs <= FLOW_DISTRIB_CUT

def _tech_bearish(c) -> bool:
    return c.get('tech_direction') == 'BEARISH'

def _directions_disagree(c) -> bool:
    td, fd = c.get('tech_direction'), c.get('flow_direction')
    return td and fd and td != 'NEUTRAL' and fd != 'NEUTRAL' and td != fd


def apply_vetoes(candidates: List[dict], market_regime: str,
                 open_positions_count: int = 0) -> List[dict]:
    floor   = EDGE_FLOOR.get(market_regime, DEFAULT_EDGE_FLOOR)
    cap     = N_MAX.get(market_regime, DEFAULT_N_MAX)
    survivors = []

    for c in candidates:
        cat = bool(c.get('has_catalyst'))

        # ── Tier A: directional safety (catalyst-overridable) ──
        if _flow_distributing(c) and not cat:                       # d1
            continue
        if _tech_bearish(c) and not c.get('is_mean_reversion') and not cat:  # d2
            continue
        if _directions_disagree(c) and not cat:                     # d3
            continue
        if market_regime == 'BEAR' and not cat:                     # d4
            continue

        # ── Tier B: statistical edge gates ──
        n = c.get('n_trades')
        if n is None or n < N_MIN_TRADES:        continue            # s1
        if (c.get('consistency_pct') or 0) < MIN_CONSISTENCY: continue  # s2
        if (c.get('win_rate') or 0) < MIN_WIN_RATE: continue        # s3

        edge = compute_edge(
            expectancy_pct=c.get('expectancy_pct'),
            consistency_pct=c.get('consistency_pct'),
            flow_score=c.get('flow_score'),
            regime=c.get('regime'),              # per-ticker
            technical_votes=c.get('technical_votes'),
        )
        if edge < floor:                          continue           # s4

        c['edge_score'] = edge
        c['size_mult']  = round(edge, 2)
        survivors.append(c)

    survivors.sort(key=lambda x: x['edge_score'], reverse=True)
    # market-regime cap; a catalyst may add one slot in RISK_OFF
    eff_cap = cap + (1 if (market_regime == 'BEAR'
                           and any(s.get('has_catalyst') for s in survivors)) else 0)
    eff_cap = max(0, eff_cap - open_positions_count)
    return survivors[:eff_cap]
```

### 3.2 Insertion points (behind the flag)

**A — EOD momentum** (`scheduler/scanner.py`, before `run_agent_firm_gate` at line 1346). `intersection_results`, `flow_confirmed`, `ohlcv_map`, `ihsg_df` are in scope:

```python
if _edge_mode() != 'off':
    from engine.veto import apply_vetoes
    market_regime = detect_regime(ihsg_df)            # IHSG-level
    enriched  = _enrich_with_edge_data(intersection_results, ohlcv_map, conn)
    survivors = apply_vetoes(enriched, market_regime, _count_open_positions(conn))
    if _edge_mode() == 'enforce':
        keep = {s['ticker'] for s in survivors}
        flow_confirmed = [r for r in flow_confirmed if r['ticker'] in keep]
        for r in intersection_results:
            m = next((s for s in survivors if s['ticker'] == r['ticker']), None)
            if m:
                r['edge_score'] = m['edge_score']
                r['agent_size_hint'] = m['size_mult']   # replaces LLM size_hint
    # shadow: log survivors + breakdown, do not alter flow_confirmed
```

**B — Premarket** (`scheduler/jobs.py::run_premarket_firm_scan`, before `evaluate_staged`):

```python
if _edge_mode() != 'off':
    from engine.veto import apply_vetoes
    market_regime = detect_regime(_ihsg_df(conn))
    enriched  = _enrich_premarket_with_edge(longs, conn, date_str)
    survivors = apply_vetoes(enriched, market_regime, _count_open_positions(conn))
    if _edge_mode() == 'enforce':
        if not survivors:
            print(f"[{now_str}] Premarket: all candidates failed edge/veto — skipped")
            return
        longs = survivors                       # re-rank by edge; rebuild candidates
    # shadow: log, keep existing longs
```

### Enrichment (`_enrich_with_edge_data` / `_enrich_premarket_with_edge`)

Per candidate, join: best `wf_edge` row for the ticker (max expectancy_pct over its strategies, or the matching strategy) → `expectancy_pct, win_rate, consistency_pct, n_trades, sharpe`; latest `stockbit_flow` → `flow_score (composite_score), flow_verdict, flow_direction`; `detect_regime(ticker_df)` → per-ticker `regime`; `calc_votes` → `technical_votes`; `tech_direction(df)`; `is_mean_reversion` from source/strategy; `has_catalyst`. Missing wf_edge → s1 drops it.

### 3.3 Tests: `tests/test_veto.py`

| Test | Verifies |
|------|----------|
| `test_d1_distributing_no_catalyst` | composite=−5, no catalyst → skip |
| `test_d1_distributing_with_catalyst` | composite=−5, catalyst → survives Tier A |
| `test_d2_bearish_tech_no_mr` | tech BEARISH, not MR, no catalyst → skip |
| `test_d2_bearish_tech_mr_thesis` | tech BEARISH but is_mean_reversion → passes d2 |
| `test_d3_direction_disagree` | tech BULLISH / flow distributing, no catalyst → skip |
| `test_d4_market_risk_off` | market BEAR, no catalyst → skip (cap 0 anyway) |
| `test_s1/s2/s3` | n<20 / cons<30 / wr<35 → skip |
| `test_s4_floor_bull/bear` | edge below 0.65(BULL)/0.72(BEAR) → skip |
| `test_cap_trending_3` / `_uncertain_1` / `_riskoff_0` | N_MAX by market regime |
| `test_cap_riskoff_catalyst_allows_1` | RISK_OFF + catalyst → 1 slot |
| `test_cap_with_open_positions` | cap reduced by open count |
| `test_inco_regression` | strong WF stats + distributing + bearish, no catalyst → **skipped** |
| `test_sort_and_size_injected` | sorted desc by edge; `size_mult` set |

`test_inco_regression` is the guardrail for the case that started this project.

### Files touched (Phase 3)

| File | Action |
|------|--------|
| `migrations/add_catalyst_flags.sql` | NEW |
| `engine/veto.py` | NEW |
| `engine/catalyst.py` (`has_catalyst`) | NEW |
| `engine/technicals.py` (`tech_direction`) or local helper | PATCH/NEW |
| `scheduler/scanner.py` | PATCH (~35 lines, before `run_agent_firm_gate`) |
| `scheduler/jobs.py` | PATCH (~20 lines, before `evaluate_staged`) |
| `tests/test_veto.py` | NEW |

---

## Phase 4 — Feature flag & A/B path

### Tri-state flag (matches the existing MTF-reversal `off/shadow/enforce` convention)

```python
# config.py — env EDGE_SCORE_MODE ∈ {off, shadow, enforce}, default off
EDGE_SCORE_MODE = os.getenv("EDGE_SCORE_MODE", "off")
def _edge_mode() -> str: ...
```

- `off` — system behaves exactly as today; nothing changed.
- `shadow` — vetoes + edge run and are logged (with full per-term breakdown), **no** trade/sizing impact.
- `enforce` — survivors-only to the firm, `size_mult = round(edge, 2)` drives sizing.

A boolean cannot express `shadow`; the tri-state is required and consistent with the rest of the codebase.

### CLI / endpoint — ranking with breakdown

`scripts/edge_ranking.py` (and/or `GET /api/edge/ranking?date=…`) dumps today's candidates with **every weighted term shown**:

```
ticker  strat  edge  | exp%(w.40)  cons(.20)  flow(.20)  reg(.10)  tech(.10) | vetoes_hit
```

so each name's score is fully explainable.

### Rollout sequence

1. Phase 1 only → populate `wf_edge` ~2 weeks, validate data quality.
2. Phase 2 (no flag wiring) → `compute_edge` exists, unused.
3. `EDGE_SCORE_MODE=shadow` → vetoes + edge logged, no trade impact; review ~1 week, tune anchors / `EDGE_FLOOR` / `N_MAX`.
4. `EDGE_SCORE_MODE=enforce`.

### Files touched (Phase 4)

| File | Action |
|------|--------|
| `config.py` | PATCH (`EDGE_SCORE_MODE` + `_edge_mode`) |
| `scripts/edge_ranking.py` | NEW |

---

## Complete file inventory

| # | File | Phase | Action |
|---|------|-------|--------|
| 1 | `migrations/add_wf_edge.sql` | 1 | NEW |
| 2 | `engine/wf_edge.py` | 1 | NEW |
| 3 | `engine/walkforward_multi.py` | 1 | PATCH (+1 line `total_winners`) |
| 4 | `scheduler/jobs.py` | 1 | PATCH `refresh_wf_scores` |
| 5 | `tests/test_wf_edge.py` | 1 | NEW |
| 6 | `engine/edge_score.py` | 2 | NEW |
| 7 | `tests/test_edge_score.py` | 2 | NEW |
| 8 | `migrations/add_catalyst_flags.sql` | 3 | NEW |
| 9 | `engine/catalyst.py` | 3 | NEW |
| 10 | `engine/veto.py` | 3 | NEW |
| 11 | `engine/technicals.py` | 3 | PATCH/NEW (`tech_direction`) |
| 12 | `scheduler/scanner.py` | 3 | PATCH `scheduled_multi_strategy_scan` |
| 13 | `scheduler/jobs.py` | 3 | PATCH `run_premarket_firm_scan` |
| 14 | `tests/test_veto.py` | 3 | NEW |
| 15 | `config.py` | 4 | PATCH (`EDGE_SCORE_MODE`) |
| 16 | `scripts/edge_ranking.py` | 4 | NEW |

---

## Configuration constants summary

| Constant | Default | Location | Notes |
|----------|---------|----------|-------|
| `N_MIN_TRADES` | 20 | `wf_edge.py` / `veto.py` | min OOS trades for an edge claim |
| `W_EXPECTANCY` | 0.40 | `edge_score.py` | dominant term |
| `W_CONSISTENCY` | 0.20 | `edge_score.py` | |
| `W_FLOW` | 0.20 | `edge_score.py` | |
| `W_REGIME` | 0.10 | `edge_score.py` | per-ticker regime fit |
| `W_TECHNICAL` | 0.10 | `edge_score.py` | |
| `MAX_EXPECTANCY_PCT` | 3.0 | `edge_score.py` | **% per trade**, capital-invariant (fixes rev-1 1000× bug) |
| `MIN/MAX_CONSISTENCY` | 30 / 100 | `edge_score.py` | |
| `MIN/MAX_FLOW_SCORE` | −8 / +8 | `edge_score.py` | verified DB range |
| `REGIME_FIT` | BULL 1.0 / SIDEWAYS 0.5 / BEAR 0.0 | `edge_score.py` | per-ticker |
| `FLOW_DISTRIB_CUT` | −3 | `veto.py` | composite_score ≤ this = distributing (d1) |
| `EDGE_FLOOR` | BULL .65 / else .72 | `veto.py` | by **market** regime |
| `N_MAX` | BULL 3 / SIDEWAYS 1 / BEAR 0 | `veto.py` | by **market** regime, catalyst may +1 in BEAR |
| `MIN_WIN_RATE` | 35 | `veto.py` | s3 veto (not a score term) |
| `EDGE_SCORE_MODE` | off | `config.py` | off / shadow / enforce |

---

## Key decisions (rev 2)

**Expectancy = per-trade percent, fixed anchor.** Rp expectancy scales with backtest capital/sizing — the rev-1 `1500` "≈3% on 50jt" was 1000× off (3% of 50jt = 1,500,000) and would have saturated the dominant term to a near-binary flag. `avg_pnl_pct` is already computed and capital-invariant; anchor `[0, 3.0%]`, negative → 0. Cross-sectional min-max is rejected (it hands 1.0 to the best of a losing universe, violating *better no pick than bad pick*).

**Two-tier veto — sizing alone does not fix INCO.** Flow is only a 0.20 score term, so a strong-history distributing name can still clear the floor. Tier A hard-vetoes distributing flow / bearish technical / direction-disagreement / market RISK_OFF unless a **dated catalyst** is on record. `test_inco_regression` locks this in.

**Market regime ≠ per-ticker regime.** Floors and the 0/1/3 session cap key off **IHSG** regime (the risk-on/off state). The 0.10 `regime_fit` score term keys off the **candidate's own** regime. Rev-1 conflated them, giving a bullish single stock the lenient floor on a risk-off day.

**Catalyst strict-by-default.** Empty `catalyst_flags` → `has_catalyst` is always False, so vetoes bite harder when we have no catalyst data. A name escapes a directional veto only with an explicit dated catalyst.

**`win_rate` / `sharpe` are vetoes, not score terms.** Removed from `compute_edge` (rev-1 accepted them but never used them). They live in `veto.py` (`s3`) and `wf_edge` (informational) only.

---

## House rules

- `.bak` copy of every file before destructive edits; patch-based edits, full-file writes only for new files.
- No `git push --force`, no history rewrite.
- Never touch the `idx-walkforward-5004` directory or its service.
- Show the diff before any patch that modifies >5 lines.
- Tests green before advancing to the next phase. TDD: failing test first for every new function.
