# Forward Testing — Phase 2 (SHADOW Position Engine) Design

**Date:** 2026-06-29
**Status:** Approved (design)
**Depends on:** Phase 1 foundation (shipped, commits `263fb53`→`5b4a4e6`) — `ft_signal`, `ft_signal_state`, `ft_transition_log`, `LifecycleManager`, `SignalAdapter`.
**Blueprint reference:** `docs/Forward_Testing_Architecture.md` — §1.4 (dual-track), §3.4 (SHADOW bypass), §4.3 (`ft_shadow_trade`), §6 (position management).

---

## 1. Goal

Paper-trade **every** ingested signal on the SHADOW track through to a closed round-trip, using each strategy's real exit rules, into the lightweight `ft_shadow_trade` table (per-signal **% return + R-multiple**, no capital, no lots, no daily marks). This is the §1.4 dual-track research spine: because every emitted signal is simulated pre-selection, questions like *"do the slope/volume gates help?"* become a permanent, answerable query rather than a one-off forensic exercise.

**Phase 2 does not select or size.** It records raw, per-signal, exit-policy-accurate round-trips. Selection (Ranker/Sizer) and the PORTFOLIO book are Phase 3.

## 2. Why this scope now

- The SHADOW track is the spine that justifies the whole system (§1.4: "non-negotiable"). Landing it first means strategy-edge measurement begins accumulating from day one.
- It has **no dependency on the Ranker** (Phase 3): SHADOW signals bypass `CONFIRMED` and go straight `GENERATED → OPENED → EXITED` (§3.4). So Phase 2 can run on the signals Phase 1 already ingests.
- It is lightweight (`ft_shadow_trade` carries no daily marks by design — §4.3 YAGNI), so the heavy `ft_position`/`ft_fill`/`ft_position_mark` machinery and equity curve are deferred to Phase 3 where they pay off (a selected book).

## 3. Scope

**In scope:**
- New tables `ft_shadow_position` (open state) and `ft_shadow_trade` (closed round-trip).
- `ExitPolicyRegistry`: per-strategy exit config + a `DEFAULT` fallback, **direction-aware** (long and short).
- `MarketDataResolver`: ATR14 + next-session open from the existing `ohlcv` table, reusing `engine.indicators.calc_atr`.
- `ShadowPositionManager`: next-open fill, daily H/L exit checks, deterministic exit ordering, gap-aware fills, idempotent per-`run_date` EOD run.
- One lifecycle change: add `GENERATED → OPENED` to `LEGAL_TRANSITIONS` (the §3.4 SHADOW bypass).

**Out of scope (deferred to named phases):**
- PORTFOLIO track + `ft_position`/`ft_fill`/`ft_position_mark` + sizing/equity/drawdown (Phase 3).
- Corporate-action **cost-basis adjustment** — splits/dividends/rights (Phase 3, §6.4). Phase 2 includes only the minimal *suspension-hold* safety guard (see §9).
- Ranker / Risk Sizer / agent-firm gate (Phase 3).
- Performance / scoreboard / benchmark engines (Phase 4–5).
- Daily-flow scheduler + reports (Phase 7).
- Partial exits / scaling (YAGNI — §6.3; full round-trips only).

## 4. Data model

Appended to `forward_testing/storage/schema.py` as `FT_PHASE2_SCHEMA`; `init_ft_tables()` picks them up automatically (`CREATE TABLE IF NOT EXISTS`, idempotent). No change to `data/db.py`.

### 4.1 `ft_shadow_position` — open state (new)
One row per open shadow position; deleted-logical (status) on close.
```sql
CREATE TABLE IF NOT EXISTS ft_shadow_position (
    signal_id     INTEGER PRIMARY KEY REFERENCES ft_signal(id),
    ticker        TEXT NOT NULL,
    strategy      TEXT NOT NULL,
    direction     TEXT NOT NULL,            -- LONG / SHORT
    entry_date    TEXT NOT NULL,
    entry_price   REAL NOT NULL,            -- D+1 open, cost-adjusted
    atr14         REAL NOT NULL,            -- ATR at signal_date, from calc_atr
    sl_price      REAL,                     -- initial stop (None for pure-trail)
    tp_price      REAL,                     -- take-profit (None for pure-trail)
    trail_atr_mult REAL,                    -- ATR mult for trailing stop (None if fixed SL)
    trail_anchor  REAL,                     -- highest_seen (long) / lowest_seen (short) used by trail
    highest_seen  REAL,
    lowest_seen   REAL,
    hold_days     INTEGER NOT NULL DEFAULT 0,
    status        TEXT NOT NULL DEFAULT 'OPEN',  -- OPEN / SUSPENDED / CLOSED
    exit_date     TEXT,
    exit_price    REAL,
    exit_reason   TEXT,
    created_at    TEXT DEFAULT (datetime('now','localtime')),
    updated_at    TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_ft_shadow_pos_status ON ft_shadow_position(status);
CREATE INDEX IF NOT EXISTS idx_ft_shadow_pos_ticker ON ft_shadow_position(ticker);
```

### 4.2 `ft_shadow_trade` — closed round-trip (per blueprint §4.3, lightly extended)
```sql
CREATE TABLE IF NOT EXISTS ft_shadow_trade (
    signal_id     INTEGER PRIMARY KEY REFERENCES ft_signal(id),
    ticker        TEXT NOT NULL,
    strategy      TEXT NOT NULL,
    direction     TEXT NOT NULL,
    signal_date   TEXT NOT NULL,
    entry_date    TEXT NOT NULL,
    entry_price   REAL NOT NULL,
    exit_date     TEXT NOT NULL,
    exit_price    REAL NOT NULL,
    exit_reason   TEXT NOT NULL,            -- SL / TP / TRAIL / TIME / SUSPENDED / DELISTED
    pnl_pct       REAL NOT NULL,            -- cost-adjusted, sign-correct per direction
    r_multiple    REAL NOT NULL,            -- realised / |entry - sl| (1R)
    hold_days     INTEGER NOT NULL,
    mae_pct       REAL,                     -- max adverse excursion (cost-adjusted)
    mfe_pct       REAL,                     -- max favourable excursion (cost-adjusted)
    closed_at     TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_ft_shadow_trade_strat ON ft_shadow_trade(strategy, exit_date);
CREATE INDEX IF NOT EXISTS idx_ft_shadow_trade_ticker ON ft_shadow_trade(ticker);
```
PK `signal_id` enforces one round-trip per signal (idempotent close).

## 5. Components

```
forward_testing/positions/
  __init__.py
  exit_policy.py     # ExitPolicy + ExitPolicyRegistry + DEFAULT
  market_data.py     # MarketDataResolver (ATR14, next_open) — reads ohlcv, reuses calc_atr
  shadow_manager.py  # ShadowPositionManager — the only writer of ft_shadow_position/trade
```

### 5.1 `ExitPolicy` + `ExitPolicyRegistry` (`exit_policy.py`, pure — no I/O)
A dataclass capturing one strategy's exit rules. Two flavors:
- **Fixed ATR SL/TP** (`sl_mult`, `tp_mult` set; `trail_atr_mult=None`): stop and target fixed at entry; optional `trail_enable` ratchets the SL.
- **Pure trail** (`trail_atr_mult` set; `sl_mult=tp_mult=None`): no fixed target; trail + time-stop only (TFB / `distribution` default).

```python
@dataclass(frozen=True)
class ExitPolicy:
    sl_mult:        float | None   # ATR units, fixed initial stop (None for pure-trail)
    tp_mult:        float | None   # ATR units, fixed target (None for pure-trail)
    min_rr:         float = 2.0    # enforces tp >= entry + min_rr*risk
    trail_enable:   bool  = False  # if True, the SL ratchets in the profit direction
    trail_atr_mult: float | None = None  # pure-trail ATR mult (None if fixed SL)
    hold_days:      int | None = None     # time-stop (None = no time-stop)
```

**Registry** (concrete, derived from each strategy's `run_strategy` call-site in `engine/strategies.py`):

| key (`ft_signal.strategy`) | sl_mult | tp_mult | min_rr | trail_enable | trail_atr_mult | hold_days |
|---|---|---|---|---|---|---|
| `vol_weighted` | 1.0 | 2.0 | 2.0 | False | — | — |
| `momentum` | 1.2 | 2.4 | 2.0 | True | — | — |
| `vwap_reversion` | 0.8 | 1.6 | 2.0 | False | — | — |
| `conservative` | 0.7 | 1.4 | 2.0 | False | — | — |
| `Liquidity Sweep` | 1.0 | 2.5 | 2.5 | False | — | — |
| `DEFAULT` (distribution & unmapped) | — | — | — | True | 3.0 | 10 |

`ExitPolicyRegistry.get(strategy)` returns the matching policy or `DEFAULT`. The `DEFAULT` mirrors the WF-validated TFB trailing exit (3.0×ATR) plus a 10-day time-stop (the R8 time-stop pattern); it is the policy for the ~93% of SHADOW signals labelled `distribution` (SHORT).

### 5.2 `MarketDataResolver` (`market_data.py`)
- `atr14(ticker, as_of_date) -> float | None`: loads `SELECT date,high,low,close FROM ohlcv WHERE ticker=? ORDER BY date` (cached per ticker per run), computes `engine.indicators.calc_atr(df, 14)`, returns the value at `as_of_date` (None if insufficient history).
- `next_open(ticker, after_date) -> (date, open) | None`: the first bar with `date > after_date`; returns its `(date, open)` (None if not yet available — e.g. signal generated today, market not yet opened).
- `bar(ticker, on_date) -> Row | None`: the `open/high/low/close` for `on_date` (used by the exit check; None if missing).

### 5.3 `ShadowPositionManager` (`shadow_manager.py`) — the only writer
Constructor: `(repo, resolver, registry, lifecycle_manager, db_path)`. `run(run_date)` performs two idempotent passes, each in short compute-then-write transactions via `ft_get_db`:

**Pass A — OPEN** (for each `ft_signal` on `track='SHADOW'` in state `GENERATED`):
1. Resolve `next_open(signal_date)`. If None (D+1 bar not yet available) → leave `GENERATED`, retry next run.
2. Resolve `atr14(signal_date)`. If None (insufficient history) → skip + flag (do not open blind).
3. `policy = registry.get(signal.strategy)`. Compute initial `sl_price`/`tp_price`/`trail_anchor` from policy + direction (§6). Entry = `apply_costs(next_open, side=BUY for LONG / SELL for SHORT)`.
4. Insert `ft_shadow_position` (status `OPEN`, `highest_seen=lowest_seen=entry_price`, `hold_days=0`). Transition `GENERATED → OPENED` via `LifecycleManager`.
5. Immediately evaluate exits on the entry bar itself (a gap can exit on day one — §6).

**Pass B — EXIT-CHECK** (for each `ft_shadow_position` with `status='OPEN'`):
1. `bar = resolver.bar(ticker, run_date)`. If None → hold + flag (§9). If ticker suspended (§9) → set `SUSPENDED`, hold.
2. Update `highest_seen`/`lowest_seen` from `bar.high`/`bar.low`; bump `hold_days`.
3. Evaluate exits in deterministic order: **SL → TP → trail → time** (§6). On the first trigger: compute gap-aware fill price, realised `pnl_pct` + `r_multiple` + `mae_pct` + `mfe_pct`, write `ft_shadow_trade`, set position `status='CLOSED'`, transition `OPENED → EXITED`.

**Idempotency:** Pass A skips signals that already have an `ft_shadow_position` (PK `signal_id`) or are past `GENERATED`. Pass B skips positions already `CLOSED`. Re-running `run(run_date)` is a no-op. Each run records `ft_run`/`ft_run_log` rows (Phase 1 bookkeeping).

## 6. Exit semantics (direction-aware, deterministic)

**Initial levels at entry** (1R = |entry − sl|):
- Fixed-SL/TP policy: `sl = entry ∓ sl_mult×ATR` (− for long, + for short); `tp = entry ± tp_mult×ATR`, clamped to `min_rr` (tp ≥ entry ± min_rr×1R). If `trail_enable`, the SL ratchets (below).
- Pure-trail policy: no `tp`; initial `trail_anchor = entry`; `stop = anchor ∓ trail_atr_mult×ATR`.

**Daily update + trigger** (using the bar's `high`/`low`):
- **Long:** `highest_seen = max(highest_seen, high)`; if `trail_enable`/pure-trail, `stop = highest_seen − trail_atr_mult×ATR` (ratchets up only). Trigger when `low ≤ stop` (SL/trail) or `high ≥ tp` (TP).
- **Short:** `lowest_seen = min(lowest_seen, low)`; `stop = lowest_seen + trail_atr_mult×ATR` (ratchets down only). Trigger when `high ≥ stop` (SL/trail) or `low ≤ tp` (TP).
- **Time:** trigger when `hold_days ≥ policy.hold_days`.

**Conflict-day ordering** (same bar touches multiple): **SL → TP → trail → time**. Same-bar SL+TP → assume SL first (capital-protective). Documented and deterministic.

**Fill price:**
- If the bar **opens beyond** the trigger level (gap) → fill at `bar.open`, tag `exit_reason` with the original reason (the §6.2 gap rule; e.g. a gap beyond SL is still `SL`). Slippage is implicit in the gap.
- Else → fill at the trigger level price.
- Exit cost via `apply_costs(price, side=SELL for long close / BUY for short cover)`.

**Realised metrics:**
- `pnl_pct` = cost-adjusted return with sign by direction: long `(exit−entry)/entry`, short `(entry−exit)/entry`, both after `apply_costs` on entry and exit.
- `r_multiple` = realised_R / 1R, where `1R = |entry − sl_price|` (for pure-trail policies, 1R = `trail_atr_mult×ATR`).
- `mae_pct`/`mfe_pct` = worst/most-favourable cost-adjusted excursion over the hold, from `highest_seen`/`lowest_seen`.

## 7. Lifecycle change (touches Phase 1)

Add the SHADOW bypass edge to `LEGAL_TRANSITIONS` in `forward_testing/lifecycle/states.py`:
```python
SignalState.GENERATED: {SignalState.CANDIDATE, SignalState.OPENED, SignalState.ARCHIVED},
```
`OPENED → EXITED` is already legal. The PORTFOLIO track (Phase 3) still walks `GENERATED → CANDIDATE → CONFIRMED → OPENED`. The transition remains forward-only and is audited through the existing `LifecycleManager` / `ft_transition_log`. The `test_lifecycle_states.py` "skip transition illegal" test (which currently asserts `GENERATED → HOLDING` is illegal) is unaffected; a new test asserts `GENERATED → OPENED` is legal.

## 8. EOD run flow

```
ShadowPositionManager.run(run_date):
  create_run(run_date, kind='EOD')
  Pass A: open eligible GENERATED SHADOW signals (next-open fill)        -> ft_shadow_position + GENERATED->OPENED
  Pass B: exit-check all OPEN positions against run_date bar             -> ft_shadow_trade + OPENED->EXITED  (or hold)
  finish_run(OK)
```
Not scheduled in Phase 2 (scheduler is Phase 7); invoked manually / by a thin CLI or test harness. Idempotent: re-running for the same `run_date` upserts, never duplicates (§5.3).

## 9. Error handling

| Case | Action |
|---|---|
| No D+1 open yet (signal generated today) | Defer: signal stays `GENERATED`; retried next run. |
| Insufficient ATR history | Skip + flag; do not open blind. |
| Missing `ohlcv` bar for an OPEN position | Hold + flag (`ft_run_log.error`); do **not** force-exit (§5.4). |
| Ticker in `suspension_events` for `run_date` | `status='SUSPENDED'`, hold, no exit; resume re-evaluates exits next run. (Full CA cost-basis adjustment is Phase 3.) |
| Delisting / ticker drop | Out of scope for Phase 2; position stays OPEN + flagged for Phase 3. |
| DB write contention | `busy_timeout=30s` + retry; never hold a write across compute (compute-then-write, proven in the Phase 1 smoke). |

All decisions are deterministic functions of `(signal, policy, ohlcv, run_date)` — no wall-clock/random dependencies, so re-runs are reproducible.

## 10. Testing

**Unit (`tests/forward_testing/`):**
- `test_exit_policy.py`: registry resolution per named strategy; `DEFAULT` fallback for `distribution`/unknown; fixed-SL/TP vs pure-trail construction; `min_rr` clamping.
- `test_market_data.py`: `atr14` matches `calc_atr`; `next_open` returns the first post-signal bar; None when missing.
- `test_shadow_manager.py` (the core): direction-aware SL/TP/trail math (long & short); deterministic SL→TP→trail→time ordering on conflict bars; gap-fill at open vs level fill; `pnl_pct`/`r_multiple`/`mae`/`mfe` correctness; `trail_enable` ratchet only; time-stop trigger; idempotent re-run (no duplicate positions/trades); missing-OHLCV hold; suspension hold; entry-bar gap exit on day one.
- `test_lifecycle_states.py`: new `GENERATED → OPENED` legal edge (extend existing file).

**Integration:**
- `test_phase2_e2e.py`: seed signals (one per strategy + a `distribution` SHORT) + synthetic `ohlcv`; run `ShadowPositionManager.run(...)`; assert `ft_shadow_position` opens, lifecycle `GENERATED→OPENED→…→EXITED`, `ft_shadow_trade` rows with correct `exit_reason`/`pnl_pct`/`r_multiple`; re-run is a no-op.

Reuses the Phase 1 conftest pattern (tmp DB + `ft_db`/`repo` fixtures), extended with an `ohlcv` fixture and seed helpers.

## 11. File structure

```
forward_testing/
  positions/
    __init__.py
    exit_policy.py        # ExitPolicy, ExitPolicyRegistry, DEFAULT
    market_data.py        # MarketDataResolver (ohlcv + calc_atr)
    shadow_manager.py     # ShadowPositionManager (only writer)
  storage/
    schema.py             # append FT_PHASE2_SCHEMA (ft_shadow_position, ft_shadow_trade)
    repo.py               # append shadow-position/trade DAOs (open_position, get_open_positions, close_position, insert_trade)
    db.py                 # init_ft_tables() extended to apply FT_PHASE2_SCHEMA (idempotent)
  lifecycle/
    states.py             # add GENERATED -> OPENED to LEGAL_TRANSITIONS
tests/
  forward_testing/
    conftest.py           # extend: ohlcv fixture + seed helpers
    test_exit_policy.py
    test_market_data.py
    test_shadow_manager.py
    test_lifecycle_states.py   # extend: GENERATED -> OPENED
    test_phase2_e2e.py
```

## 12. Follow-ups (later phases)

- **Phase 3:** Ranker/Sizer → PORTFOLIO track (`ft_position`/`ft_fill`/`ft_position_mark`/`ft_trade`) + daily marks + equity snapshots; full corporate-action cost-basis adjustment (§6.4).
- **Phase 4–5:** Performance/scoreboard/benchmark engines consume `ft_shadow_trade` (raw edge) and `ft_trade` (book).
- **Phase 7:** daily-flow scheduler invokes `ShadowPositionManager.run(run_date)` post-close.
- **Tunable:** the `DEFAULT` policy's `trail_atr_mult`/`hold_days` are config; revisit once Phase 4 metrics surface `distribution` edge.
