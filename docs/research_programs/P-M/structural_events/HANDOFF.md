# HANDOFF — structural-event feasibility (Task 2, 2026-10-07)

**Branch:** `research/structural-events-feasibility-2026-10` (from the post-Task-0 hardening tip
`a28ec7e`) · **Authority:** `ZCODE_BRIEF_STRUCTURAL_EVENTS_FEASIBILITY_2026-10-07.md` +
`ZCODE_NEXT_TASKS_2026-10-07.md` (Task 2). **Serves D-070** §Decision 4.

## The rule, stated explicitly

**No post-event price was read.** The census (`structural_events_census.py`) touches the
database strictly read-only (`mode=ro`) and every price query filters
`date < decision_date` — no row on or after any event's decision date is selected, for any
event, horizon or aggregate. No return, price change or excess return after a decision date was
computed, printed or stored. Power comes from pre-event volatility only: the daily-return
standard deviation over the 60 sessions ending the day before the decision date. Complete-bars
fractions count pre-event availability only. There is no network access anywhere in the script.

## What was produced

- `structural_events_census.py` — the read-only census (decision-date conventions declared
  per class in the module docstring; fixed rules; no sampling, no seed needed).
- `CENSUS_FEASIBILITY.json` — counts (total, parsed, per-year, liquid by era, multi-event
  tickers, 60-pre-bar fractions), pre-event 60-session volatility (median/IQR), and the minimum
  detectable effect at t = 3.06 over 5/10/20 sessions (independent and month-clustered n).
- `FEASIBILITY_2026-10-07.md` — the full report: mechanisms, prior coverage, PIT dates, counts,
  power, data gaps, and the recommendation ranking.

## Result in one paragraph

Prior coverage: rights issues are already tested and null (SCREEN-PM-CF-001 / S1, every grid
cell |t| ≤ 1.07) and D-064's monitor/adjustments touch dividends and splits as data hygiene —
no edge study exists for any of the others. PIT dates: every class has a stored scheduled public
date usable as the decision date (100% coverage; IDX80 announcements are ~1 week before
effective, an approximation). Power: only dividends have workable n (574 liquid events; MDE
≈ 0.95–1.63% over 10 sessions); tender offers are mechanism-strong but count-poor (23 liquid,
MDE ≈ 4.2–7.7%); index reconstitution is clean but only 7 events exist (2025–26); splits, bonus,
reverse splits and warrants are infeasible (0–20 liquid events).

**Recommendation: take A (tender offers, pooled) and D (dividend ex-dates, pooled) to
predeclared G0; B (index reconstitution) conditional on sourcing LQ45/IDX30 history via the
proven Wayback route; C skip (already null); E/F skip (infeasible).** No registration, no
D-entry, and no hypothesis drafts beyond the one-paragraph mechanism statements in
FEASIBILITY_2026-10-07.md — per the brief.

## Governance

Read-only DB; no network; registries/DECISION_LOG/`~/jurnal26`/production/other branches
untouched; no secrets printed; `logs/TELEGRAM_OFF` untouched. Boundary/fence tests unaffected
(no code added under `research/`). **Per the brief: push and STOP.**

*— ZCode, 2026-10-07*
