# HANDOFF — data-acquisition scoping (D-c) · 2026-09-30

**Executed under:** `ZCODE_BRIEF_DATA_ACQUISITION_SCOPING_2026-09-30.md` (Claude, planner role).
**Authority respected:** scoping/feasibility only. No hypothesis registered, no family slot
consumed, no forward test opened, no edits to `DECISION_LOG.md`, `HYPOTHESIS_REGISTRY.md`,
`FAILURE_REGISTRY.md`, or any frozen protocol. Nothing wired into the pipeline; no backfill run.
**D-b standing guard (recorders censoring issuance ex-dates): NOT TOUCHED**, exactly as the brief
required — it stays queued at zero urgency.

## Deliverables in this directory

- `01_PRIVATE_PLACEMENTS_PMTHMETD_FEASIBILITY_2026-09-30.md`
- `02_SUSPENSION_UMA_PIT_FEASIBILITY_2026-09-30.md`
- `03_LOCKUP_EXPIRY_CALENDAR_FEASIBILITY_2026-09-30.md`
- `04_CROSS_ASSET_SERIES_FEASIBILITY_2026-09-30.md` (contains the POC run results)
- `05_NEWS_MENTIONS_EXTENSION_FEASIBILITY_2026-09-30.md`
- `fetch_crossasset_poc.py` + `SAMPLE_OUTPUT_crossasset_poc.json` — POC pair for item 4
  (**left uncommitted deliberately**: scripts are never committed from the Windows mirror —
  exec-bit discipline. Ubuntu side: please `git add` both from WSL/Linux, optionally +x the
  script; the sample JSON was captured from the single run on 2026-09-30T03:01Z).

## Ranked recommendation for the Owner

**1. Item 4 — cross-asset {X} series (do first; free, ~1 day).** The only item with a working
same-day POC: TLK 1995→present with zero gaps >7d, USD/IDR, IHSG; coal/CPO honestly negative
(equity-grade proxy at best). Literature check against the Owner's own NotebookLM corpus (35
sources): **no prior test of US→IDX overnight transmission exists in it** — the lane is open,
and nothing in our in-house null set touched cross-asset transmission. Every day without the
recorder is overnight data lost forever.

**2. Item 3 — lock-up expiry calendar (manual, ~1 day).** Serves the live screen-PASS lead
(S2 young-listing avoidance, D-064 kept open): N is only 158 liquid listings, prospectus-sourced
dates are PIT, and lock-up expiry is the mechanism test that could graduate {LC} from cohort
artifact to mechanism. Manual effort, but the highest mechanism-value per hour in this list.

**3. Item 2 — suspension/UMA forward recorder (0.5–1 day; backfill uncertain).** Cheap and starts
accruing PIT data permanently, but the literature prior is weak-to-null (IDX event study finds no
significant CAAR/TVA move around UMA; corpus silent on directional predictability) — frame any
future {TS} test as avoidance/risk-side, not a long edge. Archive-depth verification before
promising any pre-2021 backfill.

**4. Item 1 — private placements (manual pilot 4–8 h when {CF} is revisited).** No free bulk
source; manual curation is tractable but the family's other half just closed null at screen level
(S1, D-064), which lowers urgency. Any automated IDX/Stockbit pull needs an Owner ToS ruling
first.

**5. Item 5 — news_mentions: nothing to do now.** Recorder accrues on production; revisit at the
~2027-04 decision point. (Optional ops hygiene, flagged not done: a periodic accrual check.)

## Execution notes

- POC ran on the Windows mirror 2026-09-30T03:01Z (yfinance 1.7.0, Python 3.12.10); no research
  DB was written to (Windows mirror DB is intentionally stale and was only read for schema/range
  facts — `suspension_events`, `news_mentions`, `corporate_actions` columns — to keep memo
  statements grounded).
- The ranked order above deliberately inverts the handoff's a-priori order (private placements
  were #1 there): feasibility findings changed it, per the brief's own §2.
- Literature-prior lines cite the Owner's NotebookLM notebook "Wisdom of the Crowd: Retail Orders
  and Stock Returns" (35 sources), queried 2026-09-30 in-session; answers are grounded summaries,
  not primary sources — verify against the cited papers before a card cites them.
