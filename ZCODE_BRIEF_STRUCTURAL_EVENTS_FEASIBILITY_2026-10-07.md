# ZCode brief — structural-event feasibility: counts, point-in-time dates and power only (2026-10-07)

**Category:** Research (P-M), feasibility gate. **Owner-requested 2026-10-07** ("yes, do both").
**Run after the ops consolidation has pushed** `ops/hardening-2026-07-10`. Create
`research/structural-events-feasibility-2026-10` from that tip. New worktree. Push only that
branch.
**Context:** `DECISION_DRAFT_PRICE_PATTERN_CLOSURE_2026-10-07.md`. The price-pattern search is
closing, and research moves to forced-flow and rule mechanisms. This brief is the feasibility step
that decision calls for.

## The rule that matters most: NO OUTCOMES

- Don't compute, print or store **any return, price change or excess return after an event's
  decision date**, for any event, horizon or aggregate.
- Power is estimated from **pre-event** volatility only. Use the stock's daily return standard
  deviation over the 60 sessions ending the day before the decision date.
- Reading outcomes here would contaminate every later registration in these families. If any
  computed field could leak post-event price information, leave it out and say so.

## Event classes to assess

| # | Class | Source | Mechanism to state (one paragraph each) |
|---|---|---|---|
| A | Tender offers | `corporate_action_events` (`tenderoffer`, 165) | mandatory/voluntary offer price as a floor; arbitrage spread; acceptance deadline |
| B | Index reconstitution | `idx80_membership_history` + `idx80_reconstitution_periods` (7 rebalances, 2025–26) | passive buying/selling on known effective dates |
| C | Rights issues | `corporate_action_events` (`rightissue`, 321) | dilution; non-subscriber selling; ex-rights pressure |
| D | Dividend ex-dates | `corporate_action_events` (`dividend`, 4,763) + `corporate_actions` | pre-ex demand, post-ex supply; tax clienteles |
| E | Splits / bonus / reverse | `stocksplit` 194, `bonus` 82, `stock_reverse` 19 | liquidity and tick-size change; retail attention |
| F | Warrants | `warrant` 148 | exercise and conversion supply |

RUPS (shareholder meetings, 6,727) are out of scope unless you can name a forced-flow mechanism.
Ownership composition has only 2 snapshots, so it's infeasible historically: note it as a
forward-collection candidate only.

## For each class, report

1. **Prior coverage:** search HYPOTHESIS_REGISTRY, FAILURE_REGISTRY, DECISION_LOG and
   `docs/research_programs/` for this mechanism. Specifically, does {CF} issuance (D-064,
   SCREEN-PM-CF-001) already cover C or F? Does the D-064 ex-date monitor or issuance adjustment
   touch D? If a class is already tested, say so and don't count it as new.
2. **Point-in-time dates:** which date in `raw_json` is the **decision date**, meaning when the
   market knew? That's the announcement, distinct from the ex-date, effective date or payment date.
   - Give the field names and the % of events that have each one.
   - An event without a known announcement date can only be used if a later date is itself
     public in advance (e.g. a scheduled ex-date). Say which.
   - For B, note that reconstitution announcements come about a week before the effective date
     (cite the period notes).
3. **Counts:** per year, and on the liquid universe (ADV20 ≥ Rp 10 bn as of the day before the
   decision date), split into 2009..2021-09 and 2021-10..2026. Also: duplicates or overlaps per
   ticker, and the fraction with complete daily bars around the event (pre-event window and
   availability only).
4. **Power:** take the median and IQR of pre-event 60-day daily volatility.
   - Compute the minimum detectable mean effect over 5, 10 and 20 sessions at t = 3.06 for n
     liquid events. Assume independent events, then use a month-clustered n to account for overlap.
   - Give one line per class: "detectable ≥ X% over 10 sessions".
5. **Data gaps** and whether they can be filled. Example: the LQ45 / IDX30 / IDX80 history before
   2025, via the same Wayback route as `idx80_*`. Give a rough source and effort estimate; don't
   fetch now.
6. **Recommendation rank:** using mechanism strength, power, PIT quality and prior coverage, rank
   the classes **with reasons**. Name the 1–2 to take to a predeclared G0. Pooled designs are
   preferred where possible.

## Deliverables

- `docs/research_programs/P-M/structural_events/FEASIBILITY_2026-10-07.md`
- `CENSUS_FEASIBILITY.json`: counts and pre-event volatility only
- the script(s) that produced them, read-only, with a fixed seed if any sampling is done
- `HANDOFF.md`, which states explicitly that no post-event price was read
- Push and STOP. No registration, no D-entry, no hypothesis drafts beyond one-paragraph mechanism
  statements.

## Hard constraints

- No outcomes (above). Read-only DB (`data.db.connect(read_only=True)` or a snapshot). Never print
  secrets.
- Research-side code only; run the boundary and fence tests if you add code under `research/`.
- Don't touch the registries, DECISION_LOG, `~/jurnal26`, production, or any other branch.
- No network fetching in this step.
