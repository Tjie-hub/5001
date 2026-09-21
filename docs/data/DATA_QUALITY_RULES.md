# Data Quality Rules

**Status:** Canonical · **Effective:** 2026-07-27

> General rules for distinguishing a genuine data-quality problem from an expected characteristic
> of a dataset. Dataset-specific application lives in each dataset's own contract
> (e.g. `docs/data/DATASET_CONTRACT_STOCKBIT_FLOW.md`); this document states the rules once so they
> aren't re-derived, or re-argued, per audit.

## Why This Exists

The Stockbit daily-flow gap investigation (`docs/audit/STOCKBIT_FLOW_GAP_REPORT.md`,
`STOCKBIT_FLOW_BACKFILL_FEASIBILITY.md`) initially looked, on the surface, like a large ingestion
failure — 969 missing trading dates out of 1,212. Evidence-based testing showed 847 of those were
never obtainable in the first place (a hard upstream retention boundary), and only 122 were a real,
fixable gap. Treating "data is missing" as automatically "ingestion is broken" produces wasted
investigation and, worse, backfill attempts against dates that can never succeed. These rules exist
to make that distinction mechanical instead of re-litigated per incident.

## Rule Set

### R1 — A retention boundary is not missing data
If an upstream source has a documented, evidence-established point before which it does not serve
history, dates before that point are **out of expectation**, not gaps. They must be excluded from
"missing" counts, not merely explained away after the fact. Establishing a boundary requires
**evidence** (e.g. a bisected request/response trail), not inference from silence — see R7.

### R2 — Blank/sentinel key values are artifacts, not corruption, if the producer explains them
A row with an empty, null, or placeholder value in a key field (e.g. `trade_date=''`) is an artifact
when the upstream API's own documented/observed behavior explains it (e.g. a live endpoint omitting
a date field pre-/post-session). Artifacts are excluded from coverage arithmetic and reported
separately, not silently dropped and not treated as proof of a broken pipeline.

### R3 — Duplicate primary keys are always invalid
Regardless of source quirks, more than one row for the same primary key is corruption or a write-path
bug — never an expected artifact. If the schema enforces the key as `PRIMARY KEY`, a duplicate
indicates the constraint was bypassed (e.g. direct `sqlite3.connect()` outside the centralized
`data.db.connect()` path, or a schema migration gap) and must fail loudly.

### R4 — A trading date must be defined by an external calendar, not by the dataset's own presence
"Was this a trading day" cannot be answered by asking whether the dataset itself has a row for it —
that's circular. Use an independent, already-validated trading-calendar source (in this repo,
`ohlcv`'s distinct dates, or `engine/calendar_filter.py`) as ground truth for what "should" exist.

### R5 — Partial coverage on a trading day is a signal, not automatically a failure
A date with unusually low row/ticker coverage relative to its neighbors is worth surfacing, but a
single fixed "expected count" is often wrong across a dataset's history — legitimate scope changes
(a narrower ticker universe used for a specific backfill, a smaller product tier at an earlier date,
etc.) look identical to a bug from row counts alone. Compare each date to a **local trailing
baseline** (e.g. the median of the last N non-empty sessions), not a single global constant, and
report deviations below threshold as a **warning**, not an automatic hard failure — unless the
dataset's own contract states a fixed, unconditional per-day expectation.

### R6 — Zero rows for an in-window date is always a genuine gap
Unlike partial coverage (R5), a date inside the dataset's supported/retained window with **zero**
rows at all is unambiguous: either the fetch never ran, or it ran and failed entirely. This is a
hard failure condition, not a warning.

### R7 — Boundaries and artifacts must be evidenced, never assumed
Do not classify a gap as "expected" (R1) or a value as "an artifact" (R2) from pattern-matching or
prior belief alone. Reproduce the condition against the live source (or its logs/traces) and record
the evidence in the relevant audit/contract document. An unverified claim of "this is expected" is
itself a data-quality risk — it can hide a real regression behind a plausible-sounding excuse.

### R8 — A validator should fail only on what it can be sure is wrong
A coverage/quality tool's non-zero exit code should be reserved for conditions that are unambiguous
under R1–R7 (a genuine in-window gap, a duplicate key, a violated hard schema/contract rule).
Conditions that require judgment or historical context to classify (partial-day coverage, artifact
counts) should be **reported**, always, but should not by themselves fail a check — otherwise the
tool trains its operators to ignore its failures, which is worse than not having the check.

## Applied Rule Summary (stockbit_flow)

| Condition | Rule | Treatment |
|---|---|---|
| Missing trading date, `trade_date >= 2025-01-02` | R6 | Genuine gap — hard failure |
| Missing trading date, `trade_date < 2025-01-02` | R1 | Expected — excluded from gap count |
| `trade_date = ''` row | R2 | Expected artifact — reported, not a failure |
| Duplicate `(ticker, trade_date)` | R3 | Invalid — hard failure |
| Trading-day ground truth | R4 | Sourced from `ohlcv`, never from `stockbit_flow` itself |
| Ticker coverage far below trailing local median | R5 | Warning — reported, not a hard failure |
| All of the above | R7 | Backed by `docs/audit/STOCKBIT_FLOW_BACKFILL_FEASIBILITY.md`'s live-request evidence trail |
