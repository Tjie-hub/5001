# CLOSE-TO-CLOSE REVERSAL — COHORT PRE-DECLARATION
## FROZEN BEFORE ANY OUTCOME VARIABLE WAS COMPUTED

**Doc:** S1-PM-0005-PREDECL · **Date:** 2026-08-25 · **Owner:** Claude
**Status:** DISCOVERY ONLY — no hypothesis registered, no registry modified, `HYP-PM-0002` untouched.

---

## 1 · Formation variable

```
r_t = log( close_t / close_{t-1} )
```

**`open` is not used anywhere** — not for formation, not for entry, not for outcome. G-1 failed and is
closed; the field is out of the programme for this candidate.

## 2 · Universe (pre-declared, not tuned)

- `ohlcv`, `COALESCE(is_final,1)=1`, `ticker <> 'IHSG'`, `close > 0`
- **liquid stratum:** same-day `volume >= 100,000` shares — carried over unchanged from the frozen
  G-1 pre-registration, **not re-chosen for this task**
- day `t` and day `t-1` must be **consecutive** trading sessions; day `t+1` must be the **next**
  consecutive session
- **session regime S2** (2023-04-03 → 2025-12-12) is the pre-designated primary window; other
  regimes are reported as falsification, not as the primary result

## 3 · Extreme-move definition — ONE cutoff, declared in advance

> **EXTREME := `|r_t| >= 0.10`** (log), reported separately for **DOWN (`r_t <= -0.10`)** and
> **UP (`r_t >= +0.10`)**.

**Why 0.10 and why only one.** It is a round number chosen for being round. It is *not* a quantile
estimated from the data, *not* a profitability-optimised cutoff, and **no other cutoff will be
searched.** A secondary cutoff of `0.15` is declared here **only** as a monotonicity check — if a
real effect exists it should not vanish or invert at a nearby threshold — and it may **not** be
substituted for 0.10 if it looks better.

## 4 · Outcome

```
r_{t+1} = log( close_{t+1} / close_t )
```

Reported as: **reversal frequency** (sign of `r_{t+1}` opposite to sign of `r_t`), **mean**, and
**median**. No Sharpe, no cumulative return, no equity curve, no portfolio construction, no ranking
of alternative signals.

**`r_{t+1} == 0` is reported as its own category, not silently assigned to either side.** Step 1
found `P(r == 0)` between 14.6% and 22.6% in the liquid stratum, so a two-way reversal split would
be actively misleading.

## 5 · Pre-declared falsification checks (all five run regardless of outcome)

**F-a** Effect present in S2 but absent in S0/S1/S3 → regime artefact.
**F-b** Effect concentrated in a small ticker subset → report share of total from the top 10 tickers
and the median-ticker result.
**F-c** Corporate-action dates drive it → repeat excluding known CA dates at `t` and `t+1`.
**F-d** One or two extreme observations drive it → report trimmed and winsorised means, and the
result after dropping the single largest contributor.
**F-e** Transaction costs obviously destroy it → compare against the **0.60% round-trip** floor
(`engine/exits/costs.py`). A one-day holding period pays that in full.

## 6 · Additional check forced by Step 1 (declared before outcomes)

Step 1 showed the negative tail of `r_t` is **truncated by the ARB band** (S3 `q1% = -0.1514`, sitting
on the 15% band). **Selecting on large DOWN moves is partly selecting on proximity to the
auto-rejection band**, which is the M6/I1 mechanism the brief excludes. The cohort is therefore
**also** stratified by **ARB regime R1–R4** (a different partition from the session regimes S0–S3),
and the DOWN result must be shown not to be an ARB-band effect in disguise.

## 7 · What this run costs

**Running Step 3 computes the outcome variable on the primary window. That burns S2 — and, because
the falsification checks cover the other regimes, effectively the whole corpus — for confirmatory
use on this formation.** Any subsequent confirmatory test must therefore use **out-of-sample forward
data** or a pre-registered replication on a different universe. This is stated in advance so it
cannot later be presented as a fresh confirmation.

## 8 · Prohibitions in force

No hypothesis registration · no registry modification · `HYP-PM-0002` untouched · no `open` ·
no `stockbit_flow_bars` · no OFI · no `cont_k` · no threshold optimisation · no parameter sweep ·
no Sharpe/profitability-based selection · no ranking of alternative signals.

**FROZEN 2026-08-25, prior to computation of any `r_{t+1}`.**
