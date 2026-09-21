# Dataset A — FROZEN Gate (F-3, F-4, F-5, Custody/LOCKED)

**Status:** **TECHNICAL WORK COMPLETE — NOT FROZEN.** F-3 and F-4 closed this session with evidence. F-5 remains
a genuine, unclosed blocker — not resolvable without either out-of-scope regime-analysis work or an Owner
ruling on how to treat it. **This document does not transition Dataset A to FROZEN.**
**Date:** 2026-09-09 · **Program:** P-M · **Object:** `DS-broker_flow-idx80-nonpit-2025_2026v1` (Dataset A,
DECLARED D-040, FINGERPRINTED D-041)
**Builds on:** `BROKER_FLOW_DATASET_A_FINGERPRINTED_GATE_2026-09-09.md` — not modified. All work below is
read-only against `data/walkforward.db` and read-only against repository source files; no code or DB write.

---

## A. F-3 — `corporate_actions_applied`

**Pipeline inspection [CODE-VERIFIED]:** `stockbit_fetcher.py::fetch_broker_flow()` (lines 651–750) writes every
`broker_flow` field as a direct passthrough of the vendor JSON response (`marketdetectors/{ticker}`) — no
split-factor, no adjustment computation, anywhere in the write path. Cross-checked against
`data/adjustments.py`: its only entry point, `adjust_ohlcv(df, splits)`, is called exclusively from
`data/loaders.py` for `ohlcv` frames — `broker_flow` is never passed through it (confirmed by exhaustive grep
for `adjustments\.` across the non-test codebase: only the definition file and one loader docstring mention
it). **Our own pipeline applies zero corporate-action adjustment to `broker_flow`, and none is claimed.**

**What this does NOT establish [UNRESOLVED, unchanged]:** whether Stockbit's `marketdetectors` vendor feed
itself returns split-adjusted or raw historical figures is a vendor-semantics question our code cannot answer,
and this session found no documentation of it. Per instruction, this is **not** inferred from the absence of
adjustment code.

**Materiality check [DB-VERIFIED] — this is what actually closes F-3 for Dataset A:**
```sql
SELECT ca.ticker, ca.date, ca.action, ca.value FROM corporate_actions ca
JOIN idx_tickers t ON t.ticker = ca.ticker AND t.status='active' AND t.in_idx80=1
WHERE ca.action='split' AND ca.date BETWEEN '2025-01-02' AND '2026-08-27';
```
**Zero rows.** No `split` event occurred for any of Dataset A's 79 tickers anywhere in its
2025-01-02→2026-08-27 window (137 `dividend` events did occur — irrelevant here, since a cash dividend does not
change share count or require the lot/price-basis adjustment a split does). **The vendor-adjustment question is
therefore immaterial to Dataset A's current population**, regardless of which way it would resolve: with no
split in-window, an adjusted feed and a raw feed would be numerically identical for this population.

**F-3 disposition: CLOSED for Dataset A specifically, by immateriality, not by resolving the underlying vendor
question.** The vendor question itself remains open and would need re-examination before any future window
extension that crosses a split ex-date, or before admitting a different ticker/window combination.

## B. F-4 — Consumer-formula audit (final, targeted)

Full sweep, superseding the admission draft's original 4-file list (`grep -rn "FROM broker_flow" --include="*.py"`
across the whole non-test codebase, every hit inspected):

| Consumer | Formula | Verdict |
|---|---|---|
| `engine/dashboard.py::_get_foreign_flow` + 2 more instances (lines 85, ~271, ~283) | `SUM(lot_value) WHERE side='BUY'` − `SUM(lot_value) WHERE side='SELL'` | **Correct** — unsigned field, explicit side-split subtraction |
| `engine/agent_firm_context.py` (line 166) | Same pattern | **Correct** |
| `engine/premarket_revision.py::_overnight_foreign_net` (line 148) | Same pattern | **Correct** |
| `routes/flow.py` (line 292) | Same pattern | **Correct** |
| `scheduler/jobs.py` (786–787), `scheduler/scanner.py` (1469–1470) | Same pattern, identical query text | **Correct** |
| `flow_filter.py` (net-lots scorer, ~line 317) | `SUM(lot)` — **signed** field, **no** side filter, **no** subtraction | **Correct** — this is exactly the admission draft's own recommended convention ("treat `lot` as already signed and use `SUM(lot)` directly... not to additionally compute BUY-minus-SELL arithmetic on top of the already-signed field") |
| `routes/screener.py` (×2), `routes/flow.py` (~line 133) | Raw per-broker `lot`/`value` passthrough for UI display, side-split only via the `side` column, sorted by `ABS(lot)` | **Not a formula** — display-only, no aggregation, no sign risk |

**No defect found anywhere.** Two consumer classes exist in production, both internally correct and mutually
non-conflicting: (1) unsigned `lot_value` with explicit side-split subtraction, (2) signed `lot` summed directly
with no further subtraction. Neither double-applies the sign convention. The `lot=0 ∧ lot_value>0` unresolved
population (§D of the admission draft) contributes exactly `0` to every `SUM(lot)`/`SUM(lot_value)` consumer
regardless of its unexplained semantics — its ambiguity carries no formula risk for any consumer identified.

**F-4 disposition: CLOSED. Non-blocking, as originally classified — now with a wider, verified consumer list
instead of a code-sweep-only claim.**

## C. F-5 — `regime_classification`

**Governing requirement inspected:** `RESEARCH_OBJECT_MODEL.md` line 43 defines the field only as *"Market
conditions during the sample period"* — no stated optionality or deferred-value convention at the ROM level.
`RESEARCH_OBJECT_SCHEMA.md` §3.4 cites it as one of ROM's five mandatory fields, without further constraint.
The admission draft's own F-5 entry (§J.2) is directive: *"Required before the field set is complete at
freeze."*

**Precedent checked:** `WORKED_EXAMPLE_END_TO_END.md` §S4 shows a populated example — `regime_classification:
mixed (BULL/BEAR/SIDEWAYS present across 5 yr)` — a lightweight descriptive phrase, not necessarily a full O15
Regime object application. This establishes that a *short characterization* is the expected form, not
necessarily a formal `DEFINED → DECLARED → APPLIED` regime object.

**Existing machinery checked [DB-VERIFIED]:** `SELECT COUNT(*) FROM regime_profiles` → **table does not exist in
this database.** No regime analysis of any kind — for Dataset A, for `broker_flow`, or for anything else — has
ever been run and persisted in this repository. There is no existing evidence this session could cite rather
than invent.

**Why this session does not populate the field:** per instruction, inventing a characterization (even a
lightweight one, matching the worked example's style) would require actually computing a regime read on Dataset
A's window from raw price/return data — a new analytical act, not a documentation lookup. That is either (a)
formal O15 Regime object work, whose Ownership rule requires **Research Architect create, CRO approve**, or (b)
an informal characterization this session has no authority to assert as evidence rather than assertion. Neither
is available within this session's technical-work mandate.

**F-5 disposition: NOT CLOSED. This is the one genuine remaining FROZEN blocker.** No documented N/A/deferred
treatment exists in the corpus for this field — the admission draft's own F-5 wording is directive ("required"),
not optional. The exact remaining requirement is one of:
1. A CRO-approved O15 Regime object applied to Dataset A's sample period (real analytical work, out of scope
   here), **or**
2. An Owner ruling accepting a lightweight, worked-example-style characterization **once one is actually
   computed** by an authorized future pass (this session cannot supply that computation without inventing it).

## D. CUSTODY asset-state / LOCKED cross-check against D-036

**Resolved by direct primary-source evidence, not by extending D-036's reasoning.** `RESEARCH_OBJECT_MODEL.md`
§3.2 ("Custody class per object" — the ROM v2.0 table added by the Custody Amendment, D-022) states plainly:

> | Dataset | **C-FROZEN-ON-USE** | **Frozen on fingerprint** |

Cross-referenced against `CUSTODY_MODEL.md` §3.1: *"C-FROZEN-ON-USE — Mutable until first referenced; frozen
thereafter (OS-4)"*, and §4.1: *"LOCKED — Frozen. Fingerprint is authoritative. No content change is
admissible."* **These three statements, read together, directly pin the trigger:** a Dataset's custody
asset-state transitions to its frozen condition (the practical content of `LOCKED`) **at the moment of
fingerprinting** — not at any later, separate step.

**Consequence:** Dataset A's custody asset-state already entered its frozen condition when D-041 recorded
FINGERPRINTED (`provenance_hash = 329b22e49f0ef882b6da031f437e9d87084d2863837ebf8c830de362b7942558`). **O4's own
FROZEN transition (the next lifecycle step) does not need to separately trigger any custody mechanism — that
already happened.** No additional custody requirement is created by O4 entering FROZEN.

**This finding does not reinterpret D-036.** D-036 ruled DECLARED and REGISTERED orthogonal by Owner decision;
this finding instead cites a *different, more specific* piece of primary evidence — ROM v2.0's own custody-class
table — that happens to answer the FINGERPRINTED/FROZEN-vs-LOCKED question directly, without needing to invoke
or extend D-036's axis-orthogonality reasoning at all. The two are independent and, as it happens, consistent:
neither requires the other's fingerprint/lock event to wait on the O4 axis's own separate transitions.

## E. F-1/F-2 re-verification (integrity spot-check, no recomputation of the population)

Per instruction, the population was **not** recomputed. A minimal drift check confirms nothing changed since F-1/F-2
were produced:

```
broker_flow rows, Dataset A exact scope:  1,222,713   (unchanged — matches F-1's total_rows_hashed exactly)
2026-08-25 row count:                     0            (unchanged)
Active IDX80 roster count:                79           (unchanged)
```

**Fingerprint `329b22e49f0ef882b6da031f437e9d87084d2863837ebf8c830de362b7942558` remains valid.** Coverage
remains **30,652 expected / 30,652 accounted / 0 missing**, unchanged from D-035/D-041.

---

## F. Exact remaining FROZEN blockers

**One: F-5 (`regime_classification`).** F-3 and F-4 are closed. The custody/LOCKED question (item D) is
resolved with no additional requirement. F-1/F-2 remain valid, unchanged.

## G. Is Owner/CRO approval required now?

**Yes — but only for F-5, not for F-3, F-4, or the custody question.** This is a genuine governance question
surfaced by investigation (per instruction), not a routine technical item: the Owner needs to choose between
authorizing formal O15 Regime object work (Research Architect + CRO), or providing/approving another way to
satisfy F-5. **No approval is requested for F-3/F-4/D — those are reported closed, not asked about.**

## H. Proposed final FROZEN decision wording

**Not proposed — F-5 remains open, so FROZEN's technical prerequisites are not yet fully satisfied.** Drafting
D-042 now would be premature by the same standard this session applied to DECLARED and FINGERPRINTED (explicit
Owner act only after every technical prerequisite closes). Once F-5 is resolved by whichever path the Owner
selects, a D-042 proposal following the same request-package pattern as
`BROKER_FLOW_DATASET_A_FINGERPRINTED_GATE_2026-09-09.md` §5 can be prepared.

## I. Worktree note

This document is the only file created this turn. No other file, code, or DB write occurred.
