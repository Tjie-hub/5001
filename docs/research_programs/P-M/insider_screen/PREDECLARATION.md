# PREDECLARATION — insider-event screen (SCREEN-PM-INS-001)

**Status:** frozen before any outcome is computed · **Date:** 2026-09-28 ·
**Authority:** owner goal 2026-09-28, "complete test for 1 until exhausted" (recommendation 1 of the
what-is-left review). **This is a screen, not a hypothesis** (the D-058/D-058 pattern): it takes no
family slot and no Rule Card. One run. All cells of the pre-declared grid are reported; the verdict
is the pre-declared primary cell only.

## Source and PIT audit (recorded before the run)

`data/walkforward.db::insider_transactions` — 98,950 rows, event_date 2017-10-12 → 2026-09-24,
fetched in one window 2026-09-22..25 (Stockbit insider page; sources recorded per row: KSEI 78,549,
IDX 20,401). Hygiene observables:

- zero exact duplicate rows on (ticker, event_date, holder_name, action_type, previous_shares,
  changes_shares); `event_id` is NOT unique (4,139 distinct) and is not used;
- 812 BUY rows with `changes_shares <= 0` (1.4% sign inconsistency) — **dropped as defects, counted**;
- 7,203 BUY rows with `previous_shares` null/0 = new position openings — kept (a from-zero opening
  is mechanically an infinite stake change; see E1);
- 31 event_dates fall on weekends — snapped forward to the ticker's next own session by the flag rule;
- `is_posted` is 0 on every row (unused); `badges` carries DIREKTUR/KOMISARIS/PENGENDALI roles on
  8.2% of rows (the rest are unbadged large holders — the table's own scope).

**PIT limitation (accepted, mitigated by convention).** `event_date` is the transaction date;
disclosure latency is not observable in the table (T+1 at earliest by KSEI practice). Convention:
a transaction at date d sets its flag on the ticker's FIRST own session strictly after d (known at
that close), and the event-time engine enters at the NEXT own session's open — i.e. entry is two own
sessions after the transaction. No flag or entry ever uses a row dated before the disclosure-safe
convention. Residual risk (intraday disclosure timing) is a limitation, not a measured quantity.

Survivorship: the DB corpus is survivorship-certain (D-057: 0 of 958 names stop trading); events on
names outside the liquid gate are invisible by construction. Accepted for a screen.

## Event definitions (flags; BUY/SELL action types only, sign defects dropped)

- **E1 "accumulation" (PRIMARY):** a ticker-day with ≥1 BUY row where the holder's stake change is
  ≥1% of prior holding (`changes_shares/previous_shares ≥ 0.01` when `previous_shares > 0`; any
  positive change when `previous_shares` is null/0 — a new block). The 1% bar is fixed from the
  mechanism (a ≥1% personal rebalance is an informative choice, not noise) before any return is read.
- **E2 "confluence":** a ticker-day with ≥2 distinct `holder_name` BUY rows within the trailing 5
  own sessions (inclusive).
- **E3 "director/commissioner":** a ticker-day with ≥1 BUY row carrying a non-empty `badges` role.
- **E1s "distribution" (mirror):** SELL rows under the E1 rule.

## Grid (every cell run and reported)

3 event defs (E1, E2, E3) × hold {5, 20} × split {full, ex-2025} = 12 cells, plus E1s × hold
{5, 20} × split {full, ex-2025} = 4 cells. **16 cells, one run, no re-runs.**

- **PRIMARY cell: E1, hold 20, ex-2025 (entries < 2025-01-01), gross.**
- Sample: entries in [2018-01-01, 2026-09-16] (the program's data cutoff). Full = all entries in
  the window; ex-2025 = entries before 2025-01-01.
- Engine: `research/rulecard/events.py` (D-060) — next-open entry, fixed own-session hold,
  day-weighted calendar-time monthly excess vs the EW liquid book (`liquid_idx_v1`), adv/price
  tercile cells, placebo/random instrumentation available but only run for the primary cell if it
  is read as positive.
- Costs: primary verdict is on GROSS monthly excess. Net observability at the frozen program round
  trip (0.60%) is reported beside it; D-059's finding (0.60% materially understates illiquid
  all-in cost) is applied qualitatively in the verdict via the tercile cells.

## Verdict rule (pre-declared)

- Primary cell readable only if it has ≥ 48 valid months (engine validity) — otherwise the screen
  closes **NOT TESTED — UNDERPOWERED** (RC-0002 precedent), no slot consumed.
- If readable: **screen PASS** requires two-sided |t| ≥ 3.0 on the primary monthly series
  (t = mean / SE of the monthly excess values). t < 3 ⇒ **screen FAIL (null)** — the insider
  accumulation lead closes at screen level; a re-open is a new screen id.
- Everything else (E2, E3, E1s, h5, full, terciles, net) is reported descriptively and gates
  nothing. A PASS here is a recommendation to draft a Rule Card — registration stays an Owner
  decision (D-060 HYP-PM-0008 precedent).

## Falsification note

This screen exists because the dataset (98,950 insider transactions over 9 years) has never been
read by this program and the event-time engine exists to read it cheaply. A null is a first-class
outcome: it closes the last unscanned in-house dataset and hardens the "no tradeable edge" record.
