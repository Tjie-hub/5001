# VERDICT — market-stress reversal S1 (HYP-PM-0019, D-078/D-075) · 2026-10-09

**Result file:** `RESULT_20261009T020022Z.json` (one run, `STRESS_G1_APPROVED=1`, frozen
`g1_run.py` @ fa78700). **Bar:** 3.2973 (exact 3.297294) at N = 608 — D-074 was NOT registered,
so the 609/3.2978 contingency does not apply (owner 2026-10-09). **Verdict: NULL — the arm is
falsified under D-075's first falsification clause (net mean ≤ 0 and below the bar), and every
secondary condition is negative too.**

## Pass conditions (all must hold; all FAIL)

| # | Condition | Computed | PASS/FAIL |
|---|-----------|----------|-----------|
| 1 | Strength: mean R > 0 **and** t ≥ 3.2973 | mean **−2.1190%**, sd 2.7216%, n 63, t **−6.180** | **FAIL** |
| 2 | Both halves > 0 — E1 2007-01→2020-12, E2 2021-07→ | E1: n 46, mean **−1.6584%** · E2: n 17, mean **−3.3654%** | **FAIL** |
| 3 | Next-day entry (close t+1 → close t+6) > 0 | mean **−2.0102%** | **FAIL** |
| 4 | Parkinson-60-decile-matched excess > 0 | mean **−2.4058%** | **FAIL** |

Events from 2021-01..06 (in the pooled test but in neither half): **none** (n = 0, consistent
with the census). No events were dropped from the tested set: 63/63 events have R.

## Reported controls (a sign flip is named; neither flips)

- **Ex-big-4 banks** (BBCA/BBRI/BMRI/BBNI excluded): mean **−2.1072%** — same sign as S1, no flip.
- **Ex-ex-date** (any dividend/split ex-date in t−1..t+5 excluded; mean 0.51 members dropped per
  event): mean **−2.1471%** — same sign, no flip.

## Overall verdict under D-075's falsification rules

1. **Primary clause triggered:** "S1 beta-adjusted net mean ≤ 0 or below the frozen bar" — both
   hold (−2.12%, t −6.18 ≪ 3.2973). **FALSIFIED.**
2. Not a half-decay artefact: E1 (2007–2020) is already negative (−1.66%); E2 (2021-07→) is
   *worse* (−3.37%). There is no era in which the arm paid.
3. Not an entry-timing artefact: the t+1-close entry is equally negative (−2.01%), so the result
   is not "reversal exists but you couldn't get the close-t fill".
4. Not explained by the VOLEX/{V} overlap: the Parkinson-60-matched control is **more** negative
   (−2.41%) — low-volatility-matched names fell *less*; the losers' basket is not merely a
   high-vol book.
5. Cost decomposition: mean D-059 cost 2.03%/event, so the **beta-adjusted gross excess is
   ≈ −0.09%** (R + cost). Even at zero cost the arm is nowhere near the bar; the sign is not a
   cost artefact — there is no gross edge to pay for.

**Reading:** buying the day's biggest liquid losers on a −2.5σ market day earns nothing gross
over the next 5 sessions (beta-adjusted) and loses ~2.1% net of D-059 cost. Nagel-style
liquidity provision does not pay on IDX in this construction; the market-side view agrees (S2 =
−1.37%: the liquid market itself keeps underperforming its trailing 5-session baseline after a
stress day — continuation, not reversal). The honest prior in D-075 ("NULL is likely — ARB
limits drag forced selling out over days") was the correct one.

**Forward test:** not built — S1 failed, so per the predeclaration the forward recorder
(~3–6 episodes/year, verdict over years) is not warranted.

*— ZCode, 2026-10-09 (one run; planner files the registry outcome)*
