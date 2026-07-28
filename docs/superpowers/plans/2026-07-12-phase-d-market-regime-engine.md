# Phase D — Market Regime Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `research/regime/` engine that attaches a per-strategy regime profile (edge PRESENT/ABSENT/REVERSED per regime, with declarable vol/liquidity conditioning axes) and a market-wide transition detector, then wire the hierarchical taxonomy into Phase C's multiplicity family — validated on NR7 as the golden reference.

**Architecture:** New read-only `research/regime/` package mirroring `research/gatekeeper/`. Primary partition = 3-class per-ticker entry regime (always in the multiplicity family); vol/liquidity are declarable sub-axes that only widen a strategy's family on pre-registered conditioning evidence. Append-only `regime_profiles` / `regime_profile_cells` tables. Phase C's `gate_config.yaml` bumps to v2 (flat vol/liq placeholders removed) and reads declared sub-cells from a strategy's profile.

**Tech Stack:** Python, pytest, sqlite (`data.db`), pandas/numpy, `research.statistics`, `research.nr7_study`, `engine.regime_filter`, `engine.liquidity`, PyYAML.

**Reference spec:** `docs/superpowers/specs/2026-07-12-phase-d-market-regime-engine-design.md`

---

## File Structure

- Create: `research/regime/__init__.py` — package marker + public exports
- Create: `research/regime/regime_config.yaml` — pre-registered thresholds/cut-points
- Create: `research/regime/config.py` — typed load + `config_hash`
- Create: `research/regime/taxonomy.py` — cell/axis definitions + `TAXONOMY_VERSION`
- Create: `research/regime/conditioners.py` — `vol_tier`, `liq_tier`
- Create: `research/regime/transitions.py` — market-wide transition detector
- Create: `research/regime/profile.py` — cell verdicts, axis declaration, `build_profile`
- Create: `research/regime/storage.py` — DDL + persist/load (append-only)
- Create: `research/regime/cli.py` — populate/query entrypoint
- Modify: `research/gatekeeper/gate_config.yaml` — v2 family `[BULL, BEAR, SIDEWAYS]`
- Modify: `research/gatekeeper/candidate.py` — `build_ctx` reads `meta["declared_labels"]`
- Modify: `tests/test_research_data_fence.py` — add the two new tables
- Create tests: `tests/regime/test_{config,taxonomy,conditioners,transitions,profile,storage}.py`, `tests/regime/test_phase_c_integration.py`

---

## Task 1: Package scaffold + pre-registered config

**Files:**
- Create: `research/regime/__init__.py`
- Create: `research/regime/regime_config.yaml`
- Create: `research/regime/config.py`
- Test: `tests/regime/test_config.py`

- [ ] **Step 1: Write the failing test**

Create `tests/regime/__init__.py` (empty), then `tests/regime/test_config.py`:

```python
from research.regime.config import load_config, config_hash


def test_defaults_match_pre_registered_constants():
    c = load_config()
    assert c.taxonomy_version == 1
    assert c.cell["min_n"] == 100          # = gatekeeper min_n_cell
    assert c.conditioning_bar["min_gap_pct"] == 0.50
    assert c.transitions["k_bars"] == 5
    assert c.seed == 20260711


def test_config_hash_is_deterministic_and_path_independent():
    c1 = load_config()
    c2 = load_config()
    assert config_hash(c1) == config_hash(c2)
    c2.source_path = "/somewhere/else.yaml"
    assert config_hash(c1) == config_hash(c2)   # provenance excluded
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/regime/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'research.regime'`

- [ ] **Step 3: Write the config files**

Create `research/regime/__init__.py`:

```python
"""Phase D — Market Regime Engine (read-only research package).

Produces the regime taxonomy + per-strategy regime profiles that Phase C
consumes. Makes no promotion decisions and changes no production regime usage.
"""
```

Create `research/regime/regime_config.yaml`:

```yaml
# research/regime/regime_config.yaml — Phase D pre-registration (spec §5–§7).
# Versioned + hashed per profile. Never edit silently after a profile is built
# against it — bump `version` (new config_hash → new profile lineage).
version: 1
taxonomy_version: 1
conditioning:
  vol:
    window: 20            # trailing bars for realized volatility at entry
    median_lookback: 120  # bars to compute the ticker's own median vol (self-relative split)
  liq:
    high_multiple: 2.0    # HIGH_LIQ if ADV30 >= high_multiple * VALUE_LIQ_MIN_IDR, else LOW_LIQ
cell:
  min_n: 100              # = gatekeeper min_n_cell / nr7_study t3_min_n
  ci_level: 0.95
  n_boot: 10000
conditioning_bar:
  min_gap_pct: 0.50       # |exp(HIGH_tier) - exp(LOW_tier)| must exceed this to declare an axis
  require_disjoint_ci: true
transitions:
  k_bars: 5               # an IHSG regime change within the last K bars = TRANSITION
seed: 20260711            # = statistics.SEED (reproducible bootstrap)
```

Create `research/regime/config.py`:

```python
"""Regime config: typed load of regime_config.yaml + a deterministic, order-
independent config_hash so every profile pins the exact thresholds it used."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field

import yaml

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "regime_config.yaml")


@dataclass
class RegimeConfig:
    version: int
    taxonomy_version: int
    conditioning: dict
    cell: dict
    conditioning_bar: dict
    transitions: dict
    seed: int
    source_path: str = field(default="", compare=False)


def load_config(path: str = None) -> RegimeConfig:
    path = path or DEFAULT_CONFIG_PATH
    with open(path, "r") as f:
        raw = yaml.safe_load(f) or {}
    return RegimeConfig(
        version=raw["version"],
        taxonomy_version=raw["taxonomy_version"],
        conditioning=raw["conditioning"],
        cell=raw["cell"],
        conditioning_bar=raw["conditioning_bar"],
        transitions=raw["transitions"],
        seed=raw["seed"],
        source_path=path,
    )


def config_hash(config: RegimeConfig) -> str:
    payload = asdict(config)
    payload.pop("source_path", None)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/pytest tests/regime/test_config.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add research/regime/__init__.py research/regime/regime_config.yaml research/regime/config.py tests/regime/__init__.py tests/regime/test_config.py
git commit -m "feat(regime): Phase D config scaffold — pre-registered regime_config.yaml"
```

---

## Task 2: Taxonomy

**Files:**
- Create: `research/regime/taxonomy.py`
- Test: `tests/regime/test_taxonomy.py`

- [ ] **Step 1: Write the failing test**

`tests/regime/test_taxonomy.py`:

```python
from research.regime import taxonomy as tx


def test_primary_regimes_are_the_three_class_set():
    assert tx.PRIMARY_REGIMES == ("BULL", "BEAR", "SIDEWAYS")


def test_declarable_axes_are_vol_and_liq_with_tier_labels():
    assert tx.DECLARABLE_AXES == ("vol", "liq")
    assert tx.AXIS_TIERS["vol"] == ("HIGH_VOL", "LOW_VOL")
    assert tx.AXIS_TIERS["liq"] == ("HIGH_LIQ", "LOW_LIQ")


def test_subcell_label_composes_regime_and_tier():
    assert tx.subcell_label("BULL", "HIGH_VOL") == "BULL::HIGH_VOL"


def test_regime_is_primary_vol_is_declarable():
    assert tx.is_primary("BULL") is True
    assert tx.is_primary("HIGH_VOL") is False
    assert tx.is_declarable_axis("vol") is True
    assert tx.is_declarable_axis("regime") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/regime/test_taxonomy.py -v`
Expected: FAIL — `ModuleNotFoundError` / `AttributeError`

- [ ] **Step 3: Write minimal implementation**

`research/regime/taxonomy.py`:

```python
"""Canonical regime taxonomy (spec §5).

Primary partition = the 3-class per-ticker entry regime (mutually exclusive,
always in the multiplicity family). vol/liq are ORTHOGONAL declarable axes that
sub-partition a regime cell and only enter a strategy's family when declared.
"""
from __future__ import annotations

TAXONOMY_VERSION = 1

PRIMARY_REGIMES = ("BULL", "BEAR", "SIDEWAYS")
DECLARABLE_AXES = ("vol", "liq")
AXIS_TIERS = {
    "vol": ("HIGH_VOL", "LOW_VOL"),
    "liq": ("HIGH_LIQ", "LOW_LIQ"),
}


def subcell_label(regime: str, tier: str) -> str:
    """Compose a hierarchical sub-cell key, e.g. ('BULL','HIGH_VOL') -> 'BULL::HIGH_VOL'."""
    return f"{regime}::{tier}"


def is_primary(label: str) -> bool:
    return label in PRIMARY_REGIMES


def is_declarable_axis(axis: str) -> bool:
    return axis in DECLARABLE_AXES
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/pytest tests/regime/test_taxonomy.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add research/regime/taxonomy.py tests/regime/test_taxonomy.py
git commit -m "feat(regime): taxonomy — primary regimes + declarable vol/liq axes"
```

---

## Task 3: Conditioners (vol-tier, liq-tier)

**Files:**
- Create: `research/regime/conditioners.py`
- Test: `tests/regime/test_conditioners.py`

- [ ] **Step 1: Write the failing test**

`tests/regime/test_conditioners.py`:

```python
import numpy as np
import pandas as pd

from research.regime.conditioners import vol_tier, liq_tier


def _series_with_vol_jump():
    # 120 calm bars (~0.5% daily moves) then 20 turbulent bars (~4% daily moves).
    rng = np.random.default_rng(0)
    calm = 100 * np.cumprod(1 + rng.normal(0, 0.005, 120))
    turbulent = calm[-1] * np.cumprod(1 + rng.normal(0, 0.04, 20))
    close = np.concatenate([calm, turbulent])
    dates = pd.date_range("2024-01-01", periods=len(close), freq="B")
    return pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "close": close})


def test_vol_tier_high_when_recent_vol_exceeds_ticker_median():
    df = _series_with_vol_jump()
    entry = df["date"].iloc[-1]
    assert vol_tier(df, entry, window=20, median_lookback=120) == "HIGH_VOL"


def test_vol_tier_low_in_calm_window():
    df = _series_with_vol_jump()
    entry = df["date"].iloc[110]     # inside the calm stretch
    assert vol_tier(df, entry, window=20, median_lookback=120) == "LOW_VOL"


def test_vol_tier_no_lookahead_uses_only_bars_up_to_entry():
    df = _series_with_vol_jump()
    entry = df["date"].iloc[110]
    # Corrupting FUTURE bars must not change the tier at bar 110.
    df2 = df.copy()
    df2.loc[120:, "close"] = df2.loc[120:, "close"] * 100
    assert (vol_tier(df, entry, window=20, median_lookback=120)
            == vol_tier(df2, entry, window=20, median_lookback=120))


def test_liq_tier_high_when_adv_at_least_multiple_of_floor():
    # VALUE_LIQ_MIN_IDR = 5e9; high_multiple 2.0 -> HIGH at >= 1e10
    assert liq_tier(adv_value=1.2e10, high_multiple=2.0) == "HIGH_LIQ"
    assert liq_tier(adv_value=6.0e9, high_multiple=2.0) == "LOW_LIQ"


def test_liq_tier_none_adv_is_low():
    assert liq_tier(adv_value=None, high_multiple=2.0) == "LOW_LIQ"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/regime/test_conditioners.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

`research/regime/conditioners.py`:

```python
"""Conditioners (spec §6): tag a trade with a vol-tier and a liq-tier.

Pure and no-look-ahead — everything is computed from data available at the entry
bar. Cut-points are self-relative (vol vs the ticker's own median; liquidity vs a
multiple of the production eligibility floor).
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from engine.liquidity import VALUE_LIQ_MIN_IDR


def _realized_vol(close: pd.Series, window: int) -> pd.Series:
    """Rolling std of daily returns (in %), the realized-vol proxy."""
    ret = close.pct_change() * 100.0
    return ret.rolling(window).std()


def vol_tier(df: pd.DataFrame, entry_date: str, window: int, median_lookback: int) -> str:
    """HIGH_VOL if realized vol at entry >= the ticker's own trailing median, else LOW_VOL.

    df must have 'date' (YYYY-MM-DD str) and 'close'. Only bars with date <= entry_date
    are used (no look-ahead)."""
    hist = df[df["date"] <= entry_date].tail(median_lookback + window + 5)
    if len(hist) < window + 2:
        return "LOW_VOL"
    rv = _realized_vol(hist["close"].reset_index(drop=True), window).dropna()
    if rv.empty:
        return "LOW_VOL"
    current = rv.iloc[-1]
    median = rv.median()
    return "HIGH_VOL" if current >= median else "LOW_VOL"


def liq_tier(adv_value: Optional[float], high_multiple: float) -> str:
    """HIGH_LIQ if 30-day ADV value >= high_multiple * the production liquidity floor."""
    if adv_value is None:
        return "LOW_LIQ"
    return "HIGH_LIQ" if adv_value >= high_multiple * VALUE_LIQ_MIN_IDR else "LOW_LIQ"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/pytest tests/regime/test_conditioners.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add research/regime/conditioners.py tests/regime/test_conditioners.py
git commit -m "feat(regime): conditioners — self-relative vol-tier + ADV liq-tier (no look-ahead)"
```

---

## Task 4: Market-wide transition detector

**Files:**
- Create: `research/regime/transitions.py`
- Test: `tests/regime/test_transitions.py`

- [ ] **Step 1: Write the failing test**

`tests/regime/test_transitions.py`:

```python
import pandas as pd

from research.regime.transitions import detect_transitions


def _labels(rows):
    return pd.DataFrame(rows)


def test_transition_flagged_within_k_bars_of_a_regime_change():
    # A synthetic per-date regime label series: BULL x5, then SIDEWAYS x5.
    regimes = ["BULL"] * 5 + ["SIDEWAYS"] * 5
    dates = pd.date_range("2024-01-01", periods=len(regimes), freq="B").strftime("%Y-%m-%d")
    df = _labels({"date": list(dates), "regime": regimes})
    out = detect_transitions(df, k_bars=2)
    by_date = dict(zip(out["date"], out["state"]))
    # The change happens at index 5; bars 5 and 6 are within k=2 of it -> TRANSITION.
    assert by_date[dates[5]] == "TRANSITION"
    assert by_date[dates[6]] == "TRANSITION"
    # Bar 8 is > k bars past the change -> back to STEADY.
    assert by_date[dates[8]] == "STEADY"


def test_direction_records_from_and_to_regime():
    regimes = ["BULL"] * 5 + ["SIDEWAYS"] * 5
    dates = pd.date_range("2024-01-01", periods=len(regimes), freq="B").strftime("%Y-%m-%d")
    df = _labels({"date": list(dates), "regime": regimes})
    out = detect_transitions(df, k_bars=2)
    row = out[out["date"] == dates[5]].iloc[0]
    assert row["direction"] == "BULL->SIDEWAYS"


def test_steady_run_has_no_transitions():
    regimes = ["BULL"] * 10
    dates = pd.date_range("2024-01-01", periods=len(regimes), freq="B").strftime("%Y-%m-%d")
    df = _labels({"date": list(dates), "regime": regimes})
    out = detect_transitions(df, k_bars=3)
    assert (out["state"] == "STEADY").all()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/regime/test_transitions.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

`research/regime/transitions.py`:

```python
"""Market-wide (IHSG) regime-transition detector (spec §7, Flow B).

Descriptive/context overlay only — it does NOT re-key edge cells. Input is a
per-date regime label series (from engine.regime_filter.detect_regime rolled over
the IHSG history); output tags each date STEADY / TRANSITION + a direction.
"""
from __future__ import annotations

import pandas as pd


def detect_transitions(regime_series: pd.DataFrame, k_bars: int) -> pd.DataFrame:
    """regime_series: DataFrame with 'date' (sorted asc) and 'regime'. Returns the
    same rows with added 'state' (STEADY/TRANSITION) and 'direction' (str|None).

    A bar is TRANSITION if the regime changed on any of the last k_bars (inclusive
    of the change bar itself)."""
    df = regime_series.sort_values("date").reset_index(drop=True)
    prev = df["regime"].shift(1)
    changed = (df["regime"] != prev) & prev.notna()

    states, directions = [], []
    last_change_idx = None
    last_direction = None
    for i in range(len(df)):
        if changed.iloc[i]:
            last_change_idx = i
            last_direction = f"{prev.iloc[i]}->{df['regime'].iloc[i]}"
        within = last_change_idx is not None and (i - last_change_idx) < k_bars
        states.append("TRANSITION" if within else "STEADY")
        directions.append(last_direction if within else None)

    out = df.copy()
    out["state"] = states
    out["direction"] = directions
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/pytest tests/regime/test_transitions.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add research/regime/transitions.py tests/regime/test_transitions.py
git commit -m "feat(regime): market-wide IHSG regime-transition detector"
```

---

## Task 5: Profile — per-cell verdicts

**Files:**
- Create: `research/regime/profile.py`
- Test: `tests/regime/test_profile.py`

- [ ] **Step 1: Write the failing test**

`tests/regime/test_profile.py`:

```python
from research.regime.profile import cell_verdict


def _trades_with_net(mean_net, n, spread=0.0):
    """Deterministic trade dicts whose round_trip_net_pct == a fixed sequence with
    the requested mean. raw_entry=100 fixed; raw_exit chosen so the net% lands on
    target. We use nr7_study.round_trip_net_pct via the profile code path, so here
    we just hand pre-computed nets through the 'net' shortcut the verdict accepts."""
    nets = [mean_net - spread, mean_net + spread] * (n // 2)
    if len(nets) < n:
        nets.append(mean_net)
    return [{"net": v} for v in nets]


def test_present_when_ci_lower_bound_above_zero():
    trades = _trades_with_net(1.2, 200, spread=0.3)
    v = cell_verdict(trades, min_n=100, ci_level=0.95, n_boot=2000, seed=1)
    assert v["verdict"] == "PRESENT"
    assert v["ci_low"] > 0


def test_reversed_when_ci_upper_bound_below_zero():
    trades = _trades_with_net(-1.2, 200, spread=0.3)
    v = cell_verdict(trades, min_n=100, ci_level=0.95, n_boot=2000, seed=1)
    assert v["verdict"] == "REVERSED"
    assert v["ci_high"] < 0


def test_absent_when_ci_straddles_zero():
    trades = _trades_with_net(0.0, 200, spread=5.0)
    v = cell_verdict(trades, min_n=100, ci_level=0.95, n_boot=2000, seed=1)
    assert v["verdict"] == "ABSENT"
    assert v["ci_low"] < 0 < v["ci_high"]


def test_insufficient_sample_is_absent_flagged():
    trades = _trades_with_net(1.2, 40, spread=0.3)
    v = cell_verdict(trades, min_n=100, ci_level=0.95, n_boot=2000, seed=1)
    assert v["verdict"] == "ABSENT"
    assert v["insufficient"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/regime/test_profile.py -v`
Expected: FAIL — `ImportError: cannot import name 'cell_verdict'`

- [ ] **Step 3: Write minimal implementation**

`research/regime/profile.py` (first increment — `cell_verdict` + net extraction):

```python
"""Per-strategy regime profile (spec §7, Flow A).

Groups collected trades into primary regime cells, assigns each a verdict
(PRESENT/ABSENT/REVERSED) from a bootstrap CI, then runs a secondary conditioning
check that may DECLARE a vol/liq axis for a (strategy, regime).
"""
from __future__ import annotations

import research.nr7_study as ns
from research import statistics as st


def _nets(trades):
    """Round-trip net % per trade. Accepts either raw prices (raw_entry/raw_exit,
    the live corpus shape) or a pre-computed 'net' (test shortcut)."""
    out = []
    for t in trades:
        if "net" in t:
            out.append(float(t["net"]))
        else:
            out.append(ns.round_trip_net_pct(t["raw_entry"], t["raw_exit"]))
    return out


def cell_verdict(trades, *, min_n: int, ci_level: float, n_boot: int, seed: int) -> dict:
    """Verdict for one regime cell. N is checked first; only then the CI sign."""
    nets = _nets(trades)
    n = len(nets)
    ci = st.bootstrap_ci(nets, n_boot=n_boot, ci=ci_level, seed=seed) if n >= 2 else {
        "point": float("nan"), "lo": float("nan"), "hi": float("nan"), "n": n}
    lo, hi = ci["lo"], ci["hi"]
    if n < min_n:
        verdict, insufficient = "ABSENT", True
    else:
        insufficient = False
        if lo > 0:
            verdict = "PRESENT"
        elif hi < 0:
            verdict = "REVERSED"
        else:
            verdict = "ABSENT"
    return {"verdict": verdict, "insufficient": insufficient, "n": n,
            "mean_net": ci["point"], "ci_low": lo, "ci_high": hi}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/pytest tests/regime/test_profile.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add research/regime/profile.py tests/regime/test_profile.py
git commit -m "feat(regime): profile cell verdicts — PRESENT/ABSENT/REVERSED via bootstrap CI"
```

---

## Task 6: Profile — axis-declaration (conditioning check)

**Files:**
- Modify: `research/regime/profile.py`
- Test: `tests/regime/test_profile.py` (add cases)

- [ ] **Step 1: Write the failing test**

Append to `tests/regime/test_profile.py`:

```python
from research.regime.profile import axis_declaration


def _tagged(mean_net, n, tier, spread=0.2):
    nets = [mean_net - spread, mean_net + spread] * (n // 2)
    if len(nets) < n:
        nets.append(mean_net)
    return [{"net": v, "vol_tier": tier} for v in nets]


def test_axis_declared_when_high_low_gap_exceeds_bar_with_disjoint_ci():
    # HIGH_VOL cell strongly profitable, LOW_VOL cell flat -> gap >> 0.50, CIs disjoint.
    trades = _tagged(2.0, 200, "HIGH_VOL") + _tagged(0.0, 200, "LOW_VOL")
    res = axis_declaration(trades, axis="vol", tier_key="vol_tier",
                           min_gap_pct=0.50, require_disjoint_ci=True,
                           ci_level=0.95, n_boot=2000, seed=1)
    assert res["declared"] is True
    assert res["gap"] > 0.50


def test_axis_not_declared_when_tiers_are_similar():
    trades = _tagged(1.0, 200, "HIGH_VOL") + _tagged(1.0, 200, "LOW_VOL")
    res = axis_declaration(trades, axis="vol", tier_key="vol_tier",
                           min_gap_pct=0.50, require_disjoint_ci=True,
                           ci_level=0.95, n_boot=2000, seed=1)
    assert res["declared"] is False


def test_axis_not_declared_when_a_tier_is_empty():
    trades = _tagged(2.0, 200, "HIGH_VOL")   # no LOW_VOL trades
    res = axis_declaration(trades, axis="vol", tier_key="vol_tier",
                           min_gap_pct=0.50, require_disjoint_ci=True,
                           ci_level=0.95, n_boot=2000, seed=1)
    assert res["declared"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/regime/test_profile.py -v`
Expected: FAIL — `ImportError: cannot import name 'axis_declaration'`

- [ ] **Step 3: Add the implementation**

Append to `research/regime/profile.py`:

```python
def axis_declaration(cell_trades, *, axis: str, tier_key: str, min_gap_pct: float,
                     require_disjoint_ci: bool, ci_level: float, n_boot: int,
                     seed: int) -> dict:
    """Decide whether a regime cell's edge DEPENDS on a conditioning axis.

    Splits the cell's trades by their tier tag; the axis is DECLARED only if the
    HIGH-vs-LOW expectancy gap exceeds min_gap_pct and (optionally) the two tier
    CIs are disjoint. Never declared if either tier is empty."""
    from research.regime.taxonomy import AXIS_TIERS
    hi_label, lo_label = AXIS_TIERS[axis]
    hi = [t for t in cell_trades if t.get(tier_key) == hi_label]
    lo = [t for t in cell_trades if t.get(tier_key) == lo_label]
    if len(hi) < 2 or len(lo) < 2:
        return {"declared": False, "axis": axis, "gap": 0.0,
                "n_high": len(hi), "n_low": len(lo)}

    hi_ci = st.bootstrap_ci(_nets(hi), n_boot=n_boot, ci=ci_level, seed=seed)
    lo_ci = st.bootstrap_ci(_nets(lo), n_boot=n_boot, ci=ci_level, seed=seed)
    gap = abs(hi_ci["point"] - lo_ci["point"])
    disjoint = (hi_ci["lo"] > lo_ci["hi"]) or (lo_ci["lo"] > hi_ci["hi"])
    declared = gap > min_gap_pct and (disjoint or not require_disjoint_ci)
    return {"declared": bool(declared), "axis": axis, "gap": gap,
            "n_high": len(hi), "n_low": len(lo),
            "high_exp": hi_ci["point"], "low_exp": lo_ci["point"],
            "disjoint_ci": bool(disjoint)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/pytest tests/regime/test_profile.py -v`
Expected: PASS (7 tests total)

- [ ] **Step 5: Commit**

```bash
git add research/regime/profile.py tests/regime/test_profile.py
git commit -m "feat(regime): axis-declaration — declare vol/liq only on disjoint-CI gap"
```

---

## Task 7: Storage — append-only profile tables

**Files:**
- Create: `research/regime/storage.py`
- Test: `tests/regime/test_storage.py`

- [ ] **Step 1: Write the failing test**

`tests/regime/test_storage.py`:

```python
import sqlite3

from research.regime.storage import (ensure_profile_tables, persist_profile,
                                      load_latest_profile)


def _profile():
    return {
        "strategy_fn": "nr7_breakout",
        "config_hash": "abc123",
        "taxonomy_version": 1,
        "corpus_fingerprint": "fp1",
        "cells": [
            {"regime": "BULL", "verdict": "PRESENT", "n_trades": 300,
             "mean_net": 1.2, "ci_low": 0.32, "ci_high": 2.06,
             "vol_axis_declared": False, "liq_axis_declared": False,
             "evidence": {"note": "golden"}},
            {"regime": "BEAR", "verdict": "ABSENT", "n_trades": 150,
             "mean_net": -0.1, "ci_low": -0.8, "ci_high": 0.6,
             "vol_axis_declared": False, "liq_axis_declared": False,
             "evidence": {}},
        ],
    }


def test_round_trip_persist_and_load():
    conn = sqlite3.connect(":memory:")
    ensure_profile_tables(conn)
    pid = persist_profile(conn, _profile())
    loaded = load_latest_profile(conn, "nr7_breakout")
    assert loaded["profile_id"] == pid
    assert loaded["cells"]["BULL"]["verdict"] == "PRESENT"
    assert loaded["cells"]["BULL"]["ci_low"] == 0.32


def test_append_only_rerun_makes_a_new_profile_id():
    conn = sqlite3.connect(":memory:")
    ensure_profile_tables(conn)
    p1 = persist_profile(conn, _profile())
    p2 = persist_profile(conn, _profile())
    assert p1 != p2
    n = conn.execute("SELECT COUNT(*) FROM regime_profiles").fetchone()[0]
    assert n == 2
    # load_latest returns the most recent.
    assert load_latest_profile(conn, "nr7_breakout")["profile_id"] == p2


def test_load_latest_none_when_absent():
    conn = sqlite3.connect(":memory:")
    ensure_profile_tables(conn)
    assert load_latest_profile(conn, "no_such_strategy") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/regime/test_storage.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

`research/regime/storage.py`:

```python
"""Append-only storage for regime profiles (spec §8). Never UPDATE/DELETE — a
re-run inserts a new profile_id, preserving full lineage (like gate_decisions)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime

PROFILES_DDL = """
CREATE TABLE IF NOT EXISTS regime_profiles (
    profile_id        TEXT PRIMARY KEY,
    strategy_fn       TEXT NOT NULL,
    config_hash       TEXT,
    taxonomy_version  INTEGER,
    corpus_fingerprint TEXT,
    created_at        TEXT NOT NULL
)
"""

CELLS_DDL = """
CREATE TABLE IF NOT EXISTS regime_profile_cells (
    cell_id           TEXT PRIMARY KEY,
    profile_id        TEXT NOT NULL,
    regime            TEXT NOT NULL,
    verdict           TEXT NOT NULL,
    n_trades          INTEGER,
    mean_net          REAL,
    ci_low            REAL,
    ci_high           REAL,
    vol_axis_declared INTEGER,
    liq_axis_declared INTEGER,
    evidence_json     TEXT
)
"""


def ensure_profile_tables(conn) -> None:
    conn.execute(PROFILES_DDL)
    conn.execute(CELLS_DDL)
    conn.commit()


def persist_profile(conn, profile: dict) -> str:
    """Insert one regime_profiles row + one regime_profile_cells row per cell.
    Returns the freshly minted profile_id (new every call — append-only)."""
    profile_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO regime_profiles (profile_id, strategy_fn, config_hash, "
        "taxonomy_version, corpus_fingerprint, created_at) VALUES (?,?,?,?,?,?)",
        (profile_id, profile["strategy_fn"], profile.get("config_hash"),
         profile.get("taxonomy_version"), profile.get("corpus_fingerprint"),
         datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")))
    for c in profile["cells"]:
        conn.execute(
            "INSERT INTO regime_profile_cells (cell_id, profile_id, regime, verdict, "
            "n_trades, mean_net, ci_low, ci_high, vol_axis_declared, liq_axis_declared, "
            "evidence_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (uuid.uuid4().hex, profile_id, c["regime"], c["verdict"], c["n_trades"],
             c["mean_net"], c["ci_low"], c["ci_high"],
             int(c["vol_axis_declared"]), int(c["liq_axis_declared"]),
             json.dumps(c.get("evidence", {}), default=float)))
    conn.commit()
    return profile_id


def load_latest_profile(conn, strategy_fn: str) -> dict | None:
    row = conn.execute(
        "SELECT profile_id, config_hash, taxonomy_version, corpus_fingerprint, "
        "created_at FROM regime_profiles WHERE strategy_fn=? "
        "ORDER BY created_at DESC LIMIT 1", (strategy_fn,)).fetchone()
    if row is None:
        return None
    profile_id = row[0]
    cells = {}
    for c in conn.execute(
            "SELECT regime, verdict, n_trades, mean_net, ci_low, ci_high, "
            "vol_axis_declared, liq_axis_declared, evidence_json "
            "FROM regime_profile_cells WHERE profile_id=?", (profile_id,)):
        cells[c[0]] = {"verdict": c[1], "n_trades": c[2], "mean_net": c[3],
                       "ci_low": c[4], "ci_high": c[5],
                       "vol_axis_declared": bool(c[6]), "liq_axis_declared": bool(c[7]),
                       "evidence": json.loads(c[8]) if c[8] else {}}
    return {"profile_id": profile_id, "strategy_fn": strategy_fn,
            "config_hash": row[1], "taxonomy_version": row[2],
            "corpus_fingerprint": row[3], "created_at": row[4], "cells": cells}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/pytest tests/regime/test_storage.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add research/regime/storage.py tests/regime/test_storage.py
git commit -m "feat(regime): append-only regime_profiles + regime_profile_cells storage"
```

---

## Task 8: Extend the research write-fence

**Files:**
- Modify: `tests/test_research_data_fence.py:21-22`

- [ ] **Step 1: Update the fence table set (this is the test change itself)**

In `tests/test_research_data_fence.py`, extend `RESEARCH_TABLES`:

```python
# Phase C gate_decisions / gate_evidence and Phase D regime profiles are research
# products too — only research/ writes them; production may read but not write.
RESEARCH_TABLES = ("wf_scores", "wf_edge", "backtest_cache",
                   "gate_decisions", "gate_evidence",
                   "regime_profiles", "regime_profile_cells")
```

- [ ] **Step 2: Run the fence test to verify production stays clean**

Run: `./venv/bin/pytest tests/test_research_data_fence.py -v`
Expected: PASS — no production scope writes the new tables (only `research/regime/storage.py` does, which is outside the scanned scopes)

- [ ] **Step 3: Commit**

```bash
git add tests/test_research_data_fence.py
git commit -m "test(regime): add regime_profiles tables to the research write-fence"
```

---

## Task 9: Profile orchestrator + CLI

**Files:**
- Modify: `research/regime/profile.py` (add `build_profile`)
- Create: `research/regime/cli.py`
- Test: `tests/regime/test_profile.py` (add `build_profile` case)

- [ ] **Step 1: Write the failing test**

Append to `tests/regime/test_profile.py`:

```python
from research.regime.profile import build_profile
from research.regime.config import load_config


def test_build_profile_assembles_cells_and_declares_declared_axis():
    cfg = load_config()
    # Two regimes; BULL edge depends on vol (big HIGH/LOW gap), BEAR is flat.
    trades = (
        [{"net": 2.0, "regime": "BULL", "vol_tier": "HIGH_VOL", "liq_tier": "HIGH_LIQ"}] * 150 +
        [{"net": 0.0, "regime": "BULL", "vol_tier": "LOW_VOL", "liq_tier": "HIGH_LIQ"}] * 150 +
        [{"net": -0.1, "regime": "BEAR", "vol_tier": "HIGH_VOL", "liq_tier": "LOW_LIQ"}] * 150
    )
    prof = build_profile("demo_strategy", trades, cfg,
                         corpus_fingerprint="fp", n_boot=2000)
    cells = {c["regime"]: c for c in prof["cells"]}
    assert cells["BULL"]["verdict"] == "PRESENT"
    assert cells["BULL"]["vol_axis_declared"] is True
    assert cells["BEAR"]["verdict"] == "ABSENT"
    assert prof["taxonomy_version"] == cfg.taxonomy_version
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/regime/test_profile.py::test_build_profile_assembles_cells_and_declares_declared_axis -v`
Expected: FAIL — `ImportError: cannot import name 'build_profile'`

- [ ] **Step 3: Add `build_profile` to `research/regime/profile.py`**

```python
def build_profile(strategy_fn, trades, config, *, corpus_fingerprint: str,
                  n_boot: int = None) -> dict:
    """Assemble a full regime profile from pre-tagged trades.

    Each trade must carry 'regime', 'vol_tier', 'liq_tier' (tagging done upstream
    by the collector). Pure: no DB, no I/O."""
    from research.regime.config import config_hash
    from research.regime.taxonomy import PRIMARY_REGIMES

    n_boot = n_boot or config.cell["n_boot"]
    ci_level = config.cell["ci_level"]
    seed = config.seed
    min_n = config.cell["min_n"]

    by_regime = {}
    for t in trades:
        by_regime.setdefault(t["regime"], []).append(t)

    cells = []
    for regime in PRIMARY_REGIMES:
        cell_trades = by_regime.get(regime, [])
        v = cell_verdict(cell_trades, min_n=min_n, ci_level=ci_level,
                         n_boot=n_boot, seed=seed)
        evidence = {"insufficient": v["insufficient"]}
        vol_decl = liq_decl = {"declared": False}
        if v["verdict"] == "PRESENT":
            vol_decl = axis_declaration(
                cell_trades, axis="vol", tier_key="vol_tier",
                min_gap_pct=config.conditioning_bar["min_gap_pct"],
                require_disjoint_ci=config.conditioning_bar["require_disjoint_ci"],
                ci_level=ci_level, n_boot=n_boot, seed=seed)
            liq_decl = axis_declaration(
                cell_trades, axis="liq", tier_key="liq_tier",
                min_gap_pct=config.conditioning_bar["min_gap_pct"],
                require_disjoint_ci=config.conditioning_bar["require_disjoint_ci"],
                ci_level=ci_level, n_boot=n_boot, seed=seed)
            evidence["vol"] = vol_decl
            evidence["liq"] = liq_decl
        cells.append({
            "regime": regime, "verdict": v["verdict"], "n_trades": v["n"],
            "mean_net": v["mean_net"], "ci_low": v["ci_low"], "ci_high": v["ci_high"],
            "vol_axis_declared": bool(vol_decl["declared"]),
            "liq_axis_declared": bool(liq_decl["declared"]),
            "evidence": evidence,
        })

    return {"strategy_fn": strategy_fn, "config_hash": config_hash(config),
            "taxonomy_version": config.taxonomy_version,
            "corpus_fingerprint": corpus_fingerprint, "cells": cells}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/pytest tests/regime/test_profile.py -v`
Expected: PASS (8 tests total)

- [ ] **Step 5: Write the CLI (thin driver; verified by the live run in Task 11)**

`research/regime/cli.py`:

```python
"""Phase D CLI: build/persist a strategy's regime profile, or query the latest.

Usage:
  DB_PATH=<db> python -m research.regime.cli build  nr7_breakout
  DB_PATH=<db> python -m research.regime.cli query  nr7_breakout
"""
from __future__ import annotations

import os
import sys

from data.db import connect as db_connect
from research.regime.config import load_config
from research.regime.profile import build_profile
from research.regime.storage import (ensure_profile_tables, persist_profile,
                                      load_latest_profile)
from research.regime.collect import collect_tagged_trades, corpus_fingerprint


def _build(strategy_fn: str) -> None:
    cfg = load_config()
    with db_connect() as conn:
        ensure_profile_tables(conn)
        trades = collect_tagged_trades(conn, strategy_fn, cfg)
        fp = corpus_fingerprint(trades)
        prof = build_profile(strategy_fn, trades, cfg, corpus_fingerprint=fp)
        pid = persist_profile(conn, prof)
    print(f"persisted profile {pid} for {strategy_fn}")
    for c in prof["cells"]:
        print(f"  {c['regime']:9} {c['verdict']:9} n={c['n_trades']:4} "
              f"CI[{c['ci_low']:+.3f},{c['ci_high']:+.3f}] "
              f"vol_decl={c['vol_axis_declared']} liq_decl={c['liq_axis_declared']}")


def _query(strategy_fn: str) -> None:
    with db_connect() as conn:
        ensure_profile_tables(conn)
        prof = load_latest_profile(conn, strategy_fn)
    if prof is None:
        print(f"no profile for {strategy_fn}")
        return
    print(f"profile {prof['profile_id']} ({prof['created_at']})")
    for regime, c in prof["cells"].items():
        print(f"  {regime:9} {c['verdict']:9} n={c['n_trades']}")


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) != 2 or argv[0] not in ("build", "query"):
        print(__doc__)
        return 2
    (_build if argv[0] == "build" else _query)(argv[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Commit**

```bash
git add research/regime/profile.py research/regime/cli.py tests/regime/test_profile.py
git commit -m "feat(regime): build_profile orchestrator + cli (build/query)"
```

---

## Task 10: Live-corpus collector (tag trades with regime + tiers)

**Files:**
- Create: `research/regime/collect.py`
- Test: `tests/regime/test_collect.py`

- [ ] **Step 1: Write the failing test**

`tests/regime/test_collect.py`:

```python
from research.regime.collect import tag_trade, corpus_fingerprint


class _StubConn:
    pass


def test_tag_trade_adds_regime_and_both_tiers(monkeypatch):
    import research.regime.collect as col
    # Stub the three enrichers so tag_trade is unit-testable without a DB/df.
    monkeypatch.setattr(col, "_regime_at", lambda df, t, d: "BULL")
    monkeypatch.setattr(col, "vol_tier", lambda df, d, window, median_lookback: "HIGH_VOL")
    monkeypatch.setattr(col, "liq_tier", lambda adv_value, high_multiple: "LOW_LIQ")
    monkeypatch.setattr(col, "get_adv_value_30d", lambda conn, ticker, date: 6e9)

    from research.regime.config import load_config
    cfg = load_config()
    base = {"ticker": "AALI", "entry_date": "2024-03-01",
            "raw_entry": 100.0, "raw_exit": 102.0}
    out = tag_trade(_StubConn(), base, full_df=None, config=cfg)
    assert out["regime"] == "BULL"
    assert out["vol_tier"] == "HIGH_VOL"
    assert out["liq_tier"] == "LOW_LIQ"


def test_corpus_fingerprint_is_stable_and_order_independent():
    a = [{"ticker": "A", "entry_date": "2024-01-01"},
         {"ticker": "B", "entry_date": "2024-02-01"}]
    b = list(reversed(a))
    assert corpus_fingerprint(a) == corpus_fingerprint(b)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/regime/test_collect.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

`research/regime/collect.py`:

```python
"""Live-corpus collector for Phase D (spec §7, Flow A).

Reuses the gatekeeper's proven no-look-ahead trade collector, then tags each trade
with its per-ticker entry regime + vol-tier + liq-tier so build_profile can group
into hierarchical cells. Read-only w.r.t. production.
"""
from __future__ import annotations

import hashlib
import json

from data.loaders import load_ohlcv_df
from engine.liquidity import get_adv_value_30d
from research.studies.regime_edge_scan import _regime_at
from research.regime.conditioners import vol_tier, liq_tier


def tag_trade(conn, trade: dict, full_df, config) -> dict:
    """Attach regime + vol_tier + liq_tier to one trade dict (in place, returned)."""
    ticker, entry = trade["ticker"], trade["entry_date"]
    vcfg = config.conditioning["vol"]
    lcfg = config.conditioning["liq"]
    trade["regime"] = _regime_at(full_df, ticker, entry)
    trade["vol_tier"] = vol_tier(full_df, entry, window=vcfg["window"],
                                 median_lookback=vcfg["median_lookback"])
    adv = get_adv_value_30d(conn, ticker, entry)
    trade["liq_tier"] = liq_tier(adv, high_multiple=lcfg["high_multiple"])
    return trade


def collect_tagged_trades(conn, strategy_fn, config, *, universe=None) -> list:
    """Collect OOS trades for a strategy across the liquid universe and tag each.

    NR7 uses the gatekeeper's exact collector (preserving the validated trade set);
    other strategies are the documented extension point (Task 12 follow-up)."""
    from research.gatekeeper.candidate import _default_collect
    from research.gatekeeper.cli import _default_universe  # existing universe helper

    universe = universe if universe is not None else _default_universe(conn)
    tagged = []
    for ticker in universe:
        df = load_ohlcv_df(conn, ticker)
        if len(df) < 300:
            continue
        df = df.sort_values("date").reset_index(drop=True)
        for tr in _default_collect(conn, ticker, config):
            tagged.append(tag_trade(conn, tr, df, config))
    return tagged


def corpus_fingerprint(trades) -> str:
    """Order-independent sha256 of the (ticker, entry_date) trade identities."""
    ids = sorted(f"{t['ticker']}@{t['entry_date']}" for t in trades)
    return hashlib.sha256(json.dumps(ids).encode()).hexdigest()
```

> **Note for the implementer:** verify the universe helper name/path before running.
> Search: `grep -rn "def liquid_universe\|def .*universe" research/gatekeeper/cli.py`.
> If the gatekeeper CLI exposes the universe differently, import the actual symbol
> (the gatekeeper live run in memory used 187 liquid tickers, so the helper exists).

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/pytest tests/regime/test_collect.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add research/regime/collect.py tests/regime/test_collect.py
git commit -m "feat(regime): live-corpus collector — tag trades with regime + vol/liq tiers"
```

---

## Task 11: Phase C integration — v2 family + declared-axis widening

**Files:**
- Modify: `research/gatekeeper/gate_config.yaml` (family → 3 regimes; bump version)
- Modify: `research/gatekeeper/candidate.py` (`build_ctx` reads `meta["declared_labels"]`)
- Test: `tests/regime/test_phase_c_integration.py`
- Test: existing `tests/gatekeeper/` suite must stay green

- [ ] **Step 1: Write the failing test**

`tests/regime/test_phase_c_integration.py`:

```python
from research.gatekeeper.config import load_config as load_gate_config
from research.gatekeeper.candidate import Candidate, build_ctx


def test_gate_config_v2_family_is_three_regimes_only():
    cfg = load_gate_config()
    assert cfg.version == 2
    assert cfg.multiplicity["family"]["regimes"] == ["BULL", "BEAR", "SIDEWAYS"]


def _candidate(regime_cells, declared_labels):
    trades = [t for cell in regime_cells.values() for t in cell]
    meta = {"target_regime": "BULL", "declared_labels": declared_labels,
            "wf": {}, "oos": {}}
    return Candidate(strategy_fn="demo", trades=trades, regime_cells=regime_cells,
                     scan_family=[], meta=meta)


def test_no_declared_labels_family_is_config_only():
    cells = {"BULL": [{"raw_entry": 100, "raw_exit": 102}] * 5,
             "BEAR": [{"raw_entry": 100, "raw_exit": 99}] * 5}
    ctx = build_ctx(_candidate(cells, declared_labels=[]), load_gate_config())
    assert ctx["family_labels"] == ["BULL", "BEAR", "SIDEWAYS"]


def test_declared_label_widens_the_family():
    cells = {
        "BULL": [{"raw_entry": 100, "raw_exit": 102}] * 5,
        "BULL::HIGH_VOL": [{"raw_entry": 100, "raw_exit": 103}] * 3,
    }
    ctx = build_ctx(_candidate(cells, declared_labels=["BULL::HIGH_VOL"]),
                    load_gate_config())
    assert "BULL::HIGH_VOL" in ctx["family_labels"]
    # one p-value per label, aligned
    assert len(ctx["family_pvalues"]) == len(ctx["family_labels"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/regime/test_phase_c_integration.py -v`
Expected: FAIL — config still v1 with 7-label family; `build_ctx` ignores `declared_labels`

- [ ] **Step 3: Update `gate_config.yaml` to v2**

In `research/gatekeeper/gate_config.yaml`, change the version and family:

```yaml
version: 2                     # v2: hierarchical family (Phase D). v1 had flat
                               # vol/liq placeholders that never carried trades and
                               # inflated the Stage-3 multiplicity denominator (7→3).
```

and:

```yaml
  family:                      # PRE-REGISTERED — primary partition only. vol/liq are
                               # declarable sub-cells added per-strategy by Phase D.
    regimes: [BULL, BEAR, SIDEWAYS]
    parameter_axes: []         # named scan axes, if any (explicit to prevent denominator-hacking)
```

- [ ] **Step 4: Update `build_ctx` to honor declared labels**

In `research/gatekeeper/candidate.py`, `build_ctx`, replace the family-label block:

```python
    labels = list(config.multiplicity["family"]["regimes"])
    if governing not in labels:
        labels.append(governing)
```

with:

```python
    labels = list(config.multiplicity["family"]["regimes"])
    if governing not in labels:
        labels.append(governing)
    # Phase D: a strategy's profile may DECLARE vol/liq sub-cells for its governing
    # regime; those widen this strategy's multiplicity family (never silently loosen).
    for extra in candidate.meta.get("declared_labels", []):
        if extra not in labels:
            labels.append(extra)
```

The existing p-value loop already resolves each label via `candidate.regime_cells.get(r, [])`, so declared sub-cell labels (e.g. `"BULL::HIGH_VOL"`) get their p-value automatically when their trades are present in `regime_cells` under that key.

> **Honest scope note:** this task wires the *widening hook* and unit-tests it with a
> synthetic candidate that already carries `meta["declared_labels"]` + the `regime::tier`
> sub-cell trades. It does **not** wire live `build_candidate` to (a) look up a strategy's
> profile and (b) split the governing regime cell into `regime::tier` sub-cells. That live
> population is unnecessary this session because **NR7 declares no axis** (design §9) and no
> other roster strategy is populated yet — it lands with the Task 13 roster follow-up. The
> golden regression (Task 12) confirms NR7's `declared_labels` is empty, so the live gate
> behaves exactly as the v2 config-only family.

- [ ] **Step 5: Run tests to verify they pass**

Run: `./venv/bin/pytest tests/regime/test_phase_c_integration.py -v`
Expected: PASS (3 tests)

Run the full gatekeeper suite (config-hash / golden references must absorb the v2 bump):
Run: `./venv/bin/pytest tests/gatekeeper/ -v`
Expected: PASS. If a test pins the old v1 `config_hash` or the 7-label family literally, update that expected value to the v2 hash/family — the config change is intentional and version-bumped. Document any such expected-value change in the commit message.

- [ ] **Step 6: Commit**

```bash
git add research/gatekeeper/gate_config.yaml research/gatekeeper/candidate.py tests/regime/test_phase_c_integration.py tests/gatekeeper/
git commit -m "feat(regime): Phase C v2 family (3 regimes) + declared-axis widening hook"
```

---

## Task 12: Golden regression — NR7 verdict unchanged + live reference run

**Files:**
- Test: `tests/regime/test_phase_c_integration.py` (add NR7 golden regression)
- Modify: `docs/superpowers/specs/2026-07-12-phase-d-market-regime-engine-design.md` (record live result)

- [ ] **Step 1: Write the golden-regression test**

Append to `tests/regime/test_phase_c_integration.py`:

```python
def test_nr7_multiplicity_family_shrank_to_three_and_still_passes():
    """v1→v2: the empty vol/liq placeholders leave the family. NR7 already PASSED
    multiplicity at 7 labels; at 3 it must still PASS (fewer tests = not stricter).
    DSR n_trials is derived from non-empty scan cells, so it is unaffected."""
    from research.gatekeeper.stages import stage_multiplicity

    cfg = load_gate_config()
    assert cfg.multiplicity["family"]["regimes"] == ["BULL", "BEAR", "SIDEWAYS"]

    # NR7 BULL is the strongly-significant governing cell (p ~ 0); BEAR/SIDEWAYS weak.
    ctx = {
        "family_labels": ["BULL", "BEAR", "SIDEWAYS"],
        "family_pvalues": [0.0005, 0.40, 0.30],
        "governing_index": 0,
    }
    res = stage_multiplicity(ctx, cfg)
    assert res.verdict == "PASS"
```

- [ ] **Step 2: Run test to verify it passes**

Run: `./venv/bin/pytest tests/regime/test_phase_c_integration.py::test_nr7_multiplicity_family_shrank_to_three_and_still_passes -v`
Expected: PASS

- [ ] **Step 3: Run the full suite (no production regression)**

Run: `./venv/bin/pytest -q`
Expected: PASS. Record the passing count (Phase C baseline was 1433). No production code path changed — only `research/` + `tests/`.

- [ ] **Step 4: Live NR7 golden-reference run (record, do not gate CI on it)**

Run against a copy of the production DB (never write the prod DB from research):

```bash
cp data/walkforward.db /tmp/phase_d_ref.db
DB_PATH=/tmp/phase_d_ref.db ./venv/bin/python -m research.regime.cli build nr7_breakout
```

Expected: BULL cell `PRESENT` (CI lower bound ≈ +0.32, consistent with the committed Phase C run), BEAR/SIDEWAYS `ABSENT`/insufficient, and — per the design's expectation — **no axis declared** for NR7.

- [ ] **Step 5: Record the reference result in the spec**

Edit `docs/superpowers/specs/2026-07-12-phase-d-market-regime-engine-design.md` §10, adding a "Live NR7 golden reference (recorded YYYY-MM-DD)" block with the actual per-cell verdicts, CIs, n_trades, and declared-axis booleans printed by the CLI. If NR7 unexpectedly declares an axis, STOP and flag it (the design predicts none) — do not silently accept it.

- [ ] **Step 6: Commit**

```bash
git add tests/regime/test_phase_c_integration.py docs/superpowers/specs/2026-07-12-phase-d-market-regime-engine-design.md
git commit -m "test(regime): NR7 golden regression + recorded live reference profile"
```

---

## Task 13 (follow-up, optional this session): batch-populate the roster

**Files:**
- Modify: `research/regime/collect.py` (generalize `collect_tagged_trades` beyond NR7)

This is the documented follow-up that fulfils Phase D's literal completion criterion
("*every roster strategy carries a regime profile*"). It reuses `walkforward_multi.STRATEGY_FUNCS`
+ `regime_edge_scan.collect_trades_for_strategy` (already no-look-ahead) instead of the
NR7-only `_default_collect`. Out of scope for the golden-reference build; schedule as a
separate `cli.py build <strategy>` run per roster entry once the engine is validated.

---

## Final Verification

- [ ] `./venv/bin/pytest tests/regime/ -v` — all Phase D unit + integration tests pass
- [ ] `./venv/bin/pytest tests/gatekeeper/ tests/test_research_data_fence.py -v` — Phase C + fence green
- [ ] `./venv/bin/pytest -q` — full suite green, count ≥ 1433 (+ new Phase D tests), zero production files changed outside `research/` and `tests/`
- [ ] Spec §10 carries the recorded live NR7 reference profile
- [ ] `git log --oneline` shows one commit per task, all on `ops/hardening-2026-07-10`
