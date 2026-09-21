# FAMILY #3: FLOW — FAMILY REPORT (new constructions only)

**Date:** 2026-09-15 · family-by-family discovery, family 3 of 6 · DISCOVERY ONLY.
**Base:** suspension-clean liquid canvas (123.3K obs), daily Stockbit platform flow.
**Declared skip-list honored:** no A4/A5/raw-flow/z≥2/streak-count retreads.

## 1. DATA / SEMANTICS (declared)

- `net_value` = vendor-signed daily net platform flow in Rp; `buy_lot/sell_lot` = lot counts (used
  only via their ratio); `buy_freq/sell_freq` **not used** (program rule forbids freq as denominator);
  `composite_score/verdict/smart_money/foreign_score` not used (opaque vendor composites).
- Coverage ~958 tickers/day, 405 sessions 2025-01-02..2026-09-14; 2026-08-25 missing (fetch gap).
- PIT: daily post-close snapshot, usable for close(t+1) entry. Production table verified
  byte-identical to frozen v002 through 2026-04-27; the 2026-04-28+ extension carries small
  restatement risk (declared).
- z-scores: trailing 60 sessions, shift(1), min 20 obs. Missing flow = NaN (excluded); zero flow =
  genuine zero and enters z-scores.
- **Platform flow is never end-investor identity.** No pre-2025 flow exists → **no flow signal can
  ever reach true OOS status**; entry survivors are capped at CONDITIONAL by construction.

## 2–3. TREE RESULTS (all 30 declared constructions; h5 gross, net of 60bp)

**Entry candidates — every one fails the kill rule (net60 h5 ≥ +30bp):**

| Cell | n | h5 (net) | FM β (t) w/ full controls | Verdict |
|---|---|---|---|---|
| B2 flow flip − → + | 4,352 | +0.40% (−0.20%) | +0.06% (0.26) | DEAD |
| B3 3d-sum sign flip | 17,211 | +0.62% (+0.02%) | — | below margin |
| C2 exhaustion after ≥4-day buy run | 1,519 | +0.64% (+0.04%) | — | below margin |
| C4 neg-run exhaustion bounce | 6,367 | +0.19% (−0.41%) | −0.21% (−1.46) | DEAD |
| D1 lot-share acceleration | 7,288 | +0.35% (−0.25%) | −0.20% (−1.37) | DEAD |
| D3 fading inflow | 3,357 | +0.77% (+0.17%) | — | below margin |
| E2 extreme capitulation nbz≤−3 | 1,563 | −0.33% | +0.33% (0.78) | DEAD (no bounce) |
| H3 flow on dead tape | 196 | +1.58% | — | breadth fail |

A1 (outflow into strength, general form) −0.16%; A2 (buying into weakness — absorption control)
**−0.78%**: absorption is again the worst cell in its family. A4x quartile profile within up-moves:
Q1 +0.41% / Q2 +0.43% / Q3 +0.37% / Q4 +0.47% — **flat**: up-move continuation does not care about
flow direction at the quartile level. E1 extreme chase (nbz≥+3) −0.33%: even extreme chasing is
merely bad, not usefully bad, after costs.

## 4. INCREMENTALITY — decisive

Full-control FM (ret1, ret5z, volz, ADV tercile, chase flag) on every notable entry cell: all
|t| < 1.5, signs unstable. **No flow construction carries information beyond the observable
price/volume/liquidity state that is large enough to trade.**

## I. THE INCUMBENT FILTER — attacked, and downgraded

"Platform outflow into strength" (up-move & nbz ≤ −1):
- **What survived:** the veto-cell h5 is negative at all six declared (move × flow) grid points
  (−0.34%..−0.68%), and the spread vs flow-neutral up-moves is negative in **4/4 halves in all six
  cells** (−5..−31bp per half). Threshold-robust and time-stable.
- **What killed it as a filter candidate:** the FM ladder. β = +1.58% (t=5.82) with price control
  only (up-move momentum selection), collapsing to **+0.27% (t=0.49) once an ADV-tercile control
  enters**. Liquidity tiers: ADV-top **+0.07%**, ADV-mid −1.34%, ADV-bot +0.13% — the toxic cell is
  a **mid-cap pocket, absent in the most liquid names, non-monotonic across tiers**.
- Per the declared filter rule ("survives FM incl. liquidity"), it **fails**. Downgraded from
  AVOIDANCE-candidate to a parked observation: *mid-cap up-moves with heavy platform outflow
  underperformed in 2025-26* — a liquidity/regime composition pattern, not demonstrable flow
  information. It cannot be confirmed retrospectively regardless (no pre-2025 flow); only the
  prospective capture stream could ever revive it, with a liquidity-conditional spec.

## VERDICT: **DEAD — close the flow family**

- **Survivors:** none.
- **Near misses:** D3 fading inflow (+0.17% net, n=3,357) and C2 exhaustion (+0.04% net) — below
  margin, no incrementality tested worthwhile.
- **Killed:** 30 declared constructions, all listed above; every FM test insignificant or negative.
- **Strongest negative information:** absorption (buying into weakness with strong positive flow,
  −0.78% h5) remains the single most reliably negative construction across all three sprints; and
  extreme chasing (nbz≥+3, −0.33% with 42.4% hit) confirms flow-chasing toxicity — both already
  implied by prior kills, now confirmed at extremes.
- **Unknowns:** whether mid-cap outflow-toxicity is a durable regime feature — unanswerable without
  prospective data; vendor flow construction is a black box (restatement risk post-2026-04).
- **Further flow research:** **not justified** on existing data. The declared tree is exhausted and
  the incrementality bar (price+volume+liquidity+flow-level controls) is not met by anything.
- **Next family:** #4 broker-structure — the one genuinely different representation that exists
  (per-broker `investor_type` Lokal/Asing/Pemerintah classes in frozen Dataset B: foreign vs local
  vs government *broker-class* net flow, never tested; classic IDX foreign-flow proxy with the
  standing caveat that broker domicile ≠ end-investor identity).

```json
{
  "family": "flow",
  "verdict": "DEAD",
  "entry_survivors": [],
  "near_misses": ["D3 fading inflow", "C2 exhaustion day"],
  "incumbent_filter": "platform-outflow-into-strength DOWNGRADED to parked observation (fails FM-liquidity incrementality; mid-cap pocket only)",
  "constructions_tested": 30,
  "next_family": "broker-structure (investor_type split - genuinely new representation)"
}
```
