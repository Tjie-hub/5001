# Universe-screen split — pre-declaration (frozen before the run)

**Written:** 2026-09-25, before `screen_split.py` was run for the first time · **Authority:** D-058
(Owner instruction 2026-09-25, "Save and test") · **Source note:** `SCREEN_HYPOTHESIS_2026-09-25.md`

## What is tested

Whether the note's two testable structural filters change the in-sample result of the T1 trend rule
(HYP-PM-0010 reference, spec 002). **Exploratory and descriptive.** It is not a Rule Card run and
produces no verdict. It changes no protocol, ledger or decision rule — FWD-PM-REGIME-002 keeps its
frozen universe (`adv20 >= Rp 1e9`, `close >= Rp 50`) whatever this shows.

## Data and trades

- Trades: `overlap_audit.t1_trades` (the audited replication of the spec-002 reference), unchanged.
- Data: `ohlcv` with `is_final = 1`, date ≤ **2026-09-16** (the registration-era corpus; nothing
  from the forward window).
- Endpoint: per-trade excess over IHSG, net of the 0.60% round trip (the protocol endpoint).

## Filters — fixed now, no others will be run

Evaluated at the entry session, with the same information the frozen universe filter uses
(`adv20` = 20-session mean of close × volume, shifted 1; `close` = entry close):

| id | rule | why this number (structural, not fitted) |
|---|---|---|
| **P200** | `close >= 200` | IDX tick-size tier boundary (Rp 1 → Rp 2) and the ±35% auto-rejection tier boundary; the note's number |
| **A5** | `adv20 >= Rp 5e9` | the note's number, taken as given |
| **P200+A5** | both | the note's combined screen |

No other cutoff (Rp 100, Rp 500, Rp 2bn, Rp 10bn, quantiles, …) will be tried. The trade-level ADV and
price distribution is printed for the "reconcile against your own data" item, but only as quantiles.

## Statistics reported for each filter × {FULL, ex-2025} × {in, out}

- N, mean excess (%/trade).
- t under month clustering and under Driscoll-Kraay with L = 60 (the overlap-robust estimators of
  D-057 R-1; the registered entry-date t is shown for reference only).
- Difference in − out: OLS on an in-filter dummy, CR1 standard errors clustered by entry month.

## Interpretation — fixed now

- **"Filter does no harm"** (the note's §4.2 test): in-filter mean ≥ full-universe mean in **both**
  FULL and ex-2025.
- **"Filter costs return"**: in-filter mean < full-universe mean in both.
- Otherwise **mixed**.
- The in − out difference counts as detected only if |t_month| ≥ 2.0 in **both** FULL and ex-2025.
  Otherwise it is reported as "no detectable difference".
- Whatever the outcome, adopting a screen for any live or paper strategy is a separate Owner decision,
  it cannot apply to FWD-PM-REGIME-002 mid-test, and Filter 1 (board status) stays untested.

## Trial accounting

Three filter variants × two periods, one run. Logged as one `exploratory_split` line in
`EXPERIMENT_LEDGER.jsonl`. It uses no family slot (a universe definition, not a hypothesis). If a
screen is later registered as part of a rule, these trials count toward that card's trial total.
