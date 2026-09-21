# Dataset A — Empirical-Ready Handoff

**Status:** **FROZEN** ([[DECISION_LOG]] D-043, 2026-09-09). This is the authoritative, consolidated handoff for
research use — no new evidence is gathered here; every fact below is a citation to work already completed and
recorded in D-032…D-043 and the artifacts listed. **This document does not register a hypothesis, does not run
an empirical test, and does not itself grant an empirical-gate pass** (§14).
**Program:** P-M — Microstructure Flow · **Prepared:** 2026-09-09

---

## 1. Dataset ID

`DS-broker_flow-idx80-nonpit-2025_2026v1` — **interim, non-canonical** (H-5; D-039 ruled this sufficient for
DECLARED without further ratification). No registry-issued ID exists; no dataset-registry machinery exists in
this repository (`CUSTODY_MODEL.md` header: Dataset Custody "has no realization").

## 2. Lifecycle state

```
DECLARED (D-040, 2026-09-09) → FINGERPRINTED (D-041, 2026-09-09) → FROZEN (D-043, 2026-09-09)
```
All three transitions Owner-approved, each with a closed prerequisite set (R-1…R-10 for DECLARED; F-1…F-2 for
FINGERPRINTED; F-3…F-5 for FROZEN). **Amendment is now prohibited** ([[RESEARCH_OBJECT_SCHEMA]] §3.4 — "Amend
after freeze: prohibited"; Versioning — "Immutable on fingerprint. A revised dataset is a new Dataset"). Any
future correction to this population is a **new** Dataset Object, not an edit to this one.

## 3. Exact population definition

`broker_flow` rows where:
- `ticker` ∈ the 79-ticker roster (§4), **and**
- `trade_date` ∈ `[2025-01-02, 2026-08-27]` inclusive, **and**
- `trade_date ≠ 2026-08-25`.

**1,222,713 rows** at this exact scope [DB-VERIFIED, R-4/F-1 receipts].

## 4. Universe definition

`idx_tickers WHERE status='active' AND in_idx80=1` — **79 tickers**, current-at-query roster, applied
**uniformly and retrospectively** across the entire window (the same 79 tickers for every date, regardless of
true historical IDX80 membership on that date).

**Roster (sorted), R-3 receipt:**
```
AALI,ACES,ADRO,AKRA,AMMN,AMRT,ANTM,ARTO,ASII,BBCA,BBNI,BBRI,BBTN,BBYB,BMRI,BNGA,BREN,BRIS,BRPT,BSDE,
BTPS,BUKA,CMRY,CPIN,CTRA,DNET,EMTK,ERAA,ESSA,EXCL,GGRM,GOTO,HMSP,HRUM,ICBP,INCO,INDF,INKP,INTP,ISAT,
ITMG,JPFA,JSMR,KAEF,KIJA,KLBF,LINK,LPPF,LSIP,MAPI,MBMA,MDKA,MEDC,MIKA,MNCN,MTEL,MYOR,NCKL,NISP,PANI,
PGAS,PGEO,PNBN,PTBA,PTPP,PWON,RAJA,SCMA,SIDO,SMGR,SMRA,TBIG,TINS,TKIM,TLKM,TOWR,TPIA,UNTR,UNVR
```
**SHA-256: `7d4eb1004e7d1e83153eede9a5d4e458ab5298ac1a4a4d7fa301f095f665eee0`**

`updated_at` on every roster row is uniformly `2026-04-27T11:57:40.101066` — the `in_idx80` flag was set in a
single batch operation well before the Aug 2026 backfill campaign, confirming "current-at-backfill-time" and
"current-today" coincide for this specific roster [DB-VERIFIED, R-3].

## 5. NON-PIT limitation — explicit, load-bearing

**This dataset does NOT represent historical IDX80 membership.** It cannot support any claim of the form "was
ticker X in IDX80 on date Y." The roster is fixed and applied retrospectively; a ticker present in the roster
today may not have been an IDX80 member for all or part of `[2025-01-02, 2026-08-27]`, and vice versa. Any
research use implying historical index composition is **out of scope for this Dataset** — Dataset B
(`DS-broker_flow-idx80-pit-2025_2026-04v1`, PIT-aware, a separate candidate) exists for that purpose and was
deliberately **not** collapsed into this one (H-7C, D-034).

## 6. Analytical window and exclusion

- **Window:** `2025-01-02` → `2026-08-27` inclusive (H-2, satisfied by Dataset A's own H-7C-specified identity).
- **Exclusion:** `2026-08-25` — 0 rows [DB-VERIFIED], **not repaired, not imputed** (H-3). Cause **[UNRESOLVED]**:
  this date also fails the canonical IHSG-bar predicate independently (`trading_calendar` carries a
  `scraper_eod`-sourced row for it, but no IHSG `ohlcv` bar exists) — so the gap is not `broker_flow`-specific;
  even the market-wide reference series has no confirmed session that day. No cause is asserted.
- **388 canonical trading dates** in the window after exclusion (`canonical_trading_dates()`, IHSG-confirmed).

## 7. Coverage

**30,652 expected cells (79 tickers × 388 dates) = 30,652 accounted, 0 genuinely missing.** Independently
confirmed twice by different methods that agree exactly:
1. D-035's FULLY RECONCILED accounting (`30,652 = 24,109 backfill-touched + 144 pre-campaign catch-up +
   6,399 ordinary-live-covered`), traced from log + DB cross-verification.
2. F-2's direct invocation of the canonical predicate, `tools.broker_flow_idx80_gap.broker_cell_complete()`,
   against the live database — zero missing cells, no log evidence involved at all.

## 8. Provenance

- **Vendor:** Stockbit broker summary, `marketdetectors/{ticker}` endpoint [CANONICAL].
- **Authorization receipt (R-1):** satisfied by D-032 (analytical-window/freeze-strategy decisions) + D-033
  (H-1 IDX80-scoped admission APPROVED) as persisted in `DECISION_LOG.md` — ruled sufficient without a separate
  artifact (D-038).
- **P1 (ordinary live collection) / P2 (authorized IDX80 backfill) distinguishability (R-6):** resolved by
  splitting rather than merging (H-7C, D-034). `broker_flow`'s composite primary key
  `(ticker, trade_date, broker_code, side)` structurally prevents duplicate/overlapping rows, and the two write
  paths (`stockbit_fetcher.py` ordinary-live vs. `tools/backfill_broker_flow_idx80.py` backfill) are
  independently gap-gated against each other — co-writes to the same cell are structurally impossible. Dataset
  A's membership is defined **extensionally** by (roster × window × exclusion), not by a provenance tag (none
  exists — no `source` column in `broker_flow`).
- **No `source`/`provenance` column exists** on `broker_flow` — row-level P1/P2 attribution by inspection is not
  possible; this is a stated `fidelity_limit` (§10), not a defect fixed by this dataset's admission.

## 9. `capability_class`

**Available Today — informed-flow / adverse-selection proxy** (D-037, per `DATA_FEASIBILITY_STUDY.md` §4.1,
corrected 2026-09-09). Not true order-flow-imbalance (no LOB access); a proxy, and the claim inherits the
proxy's fidelity (LR-5).

## 10. `fidelity_limit`

This data **cannot** distinguish:
- (a) historical IDX80 membership as-known-then (§5, NON-PIT);
- (b) P1 vs. P2 row-level provenance by inspection (§8 — resolved extensionally at the dataset level, not at
  the row level);
- (c) the semantics of `lot = 0 ∧ lot_value > 0` rows (3,700 BUY + 11,963 SELL rows in-scope) — **[UNRESOLVED]**,
  no explanation offered, not invented;
- (d) the cause of the `2026-08-25` gap (§6).

## 11. `proxy_for`

Informed-flow / adverse-selection proxy tier ([[DATA_FEASIBILITY_STUDY]] §4.1) — **not** true order-flow
imbalance. Final mechanism-level assignment belongs to whichever hypothesis later binds this dataset (R9,
[[RESEARCH_OBJECT_SCHEMA]] §3.2); this handoff does not assign one.

## 12. Transformation lineage

`Stockbit marketdetectors/{ticker}` (vendor, per-ticker per-date HTTP response) → `stockbit_fetcher.py::
fetch_broker_flow()` (direct field passthrough, no adjustment computation — [CODE-VERIFIED]) →
`INSERT OR REPLACE INTO broker_flow` (production write path, gap-gated against the ordinary-live path per §8).

**`corporate_actions_applied`:** our own pipeline applies **zero** correction of any kind. The vendor's own
adjustment convention is unknown and unestablished (not inferred). **Immaterial for this specific population:**
zero `split` corporate actions occurred for any of the 79 roster tickers anywhere in
`[2025-01-02, 2026-08-27]` [DB-VERIFIED] — only `dividend` events occurred (irrelevant to lot/price-basis
adjustment). This immateriality finding does **not** generalize to a future window/ticker extension crossing a
split ex-date.

## 13. Fingerprint

```
provenance_hash: 329b22e49f0ef882b6da031f437e9d87084d2863837ebf8c830de362b7942558
```
**Method (F-1):** per-ticker aggregate — `ticker, COUNT(*), MIN(trade_date), MAX(trade_date),
SUM(CAST(lot AS INTEGER)), SUM(CAST(lot_value AS INTEGER))`, `GROUP BY ticker ORDER BY ticker`, SHA-256 over
`"|".join(str(x))+"\n"` per row — reusing `research/tracking.py::dataset_fingerprint()`'s exact byte-level
convention, applied to `broker_flow` instead of `ohlcv`. 79 rows, 1,222,713 total rows hashed.

**Scope declaration (CU-15 — states what this pins and what it explicitly does not):** pins per-ticker row
count, date range, and signed-`lot`/`lot_value` sums. **Does NOT pin** `broker_code`/`side` granularity
(aggregated away), `freq`, `avg_price`, `investor_type`, `value`/`value_total`, or row-insertion order. A
consumer needing broker-level or side-level guaranteed granularity must define a separate, finer fingerprint.

**Custody note:** per `RESEARCH_OBJECT_MODEL.md` §3.2 ("Dataset | C-FROZEN-ON-USE | Frozen on fingerprint"),
this fingerprint's computation is also the event that froze Dataset A's custody asset-state (the practical
content of `CUSTODY_MODEL`'s `LOCKED`) — no separate custody action was or is required.

## 14. Freeze state

**FROZEN** (D-043, 2026-09-09). Amendment prohibited. Coverage, provenance, and content are fixed to the
fingerprint above.

## 15. Known limitations (consolidated, none newly invented)

1. **NON-PIT** — no historical index-composition claim is supportable (§5).
2. **`2026-08-25` gap, cause unresolved** — not repaired, not imputed (§6).
3. **`lot = 0 ∧ lot_value > 0` semantics unresolved** — 3,700 BUY + 11,963 SELL rows, no explanation offered
   (§10).
4. **Vendor corporate-action-adjustment convention unknown in general** — immaterial for *this* window only,
   because no split occurred in it; would need re-examination for any future extension (§12).
5. **`regime_classification` is a lightweight, descriptive characterization (D-042), not a formal O15 Regime
   object.** Index-level (IHSG), not per-ticker; a different rule-based classifier could shift exact boundaries;
   carries no evidence tier and must not be cited as support for any hypothesis without that hypothesis
   independently defining its own regime-conditioning.
6. **`asset_class` carries only a PROPOSED value** (D-039 ruled it sufficient for DECLARED, not formally
   ratified in the same sense `dataset_id` was via H-5).
7. **DECLARED-vs-REGISTERED lifecycle interpretation (D-036, Option B — orthogonal axes)** applies as ratified;
   the FINGERPRINTED/FROZEN-vs-`LOCKED` question was separately resolved via direct primary evidence (ROM v2.0
   §3.2, §13 above), not by extending D-036's literal text.
8. **`DATA_FEASIBILITY_STUDY.md` §5.3's history-maturity gate for `broker_flow` has NOT been explicitly
   cleared** — the 2026-09-09 span correction (~3.5 mo → ~20 mo) was a measured-fact fix only; whether it clears
   the gate (in whole, or for Dataset A's subset specifically) remains an open Research-Architect/CRO
   determination. **This directly constrains §16 below.**
9. **Dataset ID is interim/non-canonical**; no registry machinery exists (§1).

## 16. Empirical gate status

**NOT PASSED / BLOCKED.** No hypothesis has been registered against this dataset. No empirical or forward test
is authorized. `HYPOTHESIS_LIFECYCLE` G1 has not been entered. Reaching FROZEN is a **data-governance**
milestone, not a research-permission milestone — these are deliberately separate gates.

## 17. Permitted research use

- **Permitted, subject to §15's limitations:** per-ticker broker-flow / return exploratory and mechanism-level
  work within P-M, at the **proxy tier** stated in §9/§11, using the **frozen, fingerprinted population** as-is.
  Any hypothesis binding this dataset must (a) go through standard `HYPOTHESIS_LIFECYCLE` G1 registration,
  (b) explicitly state its own signed-`lot` treatment convention before G1 (recommended: treat `lot` as already
  signed, `SUM(lot)` directly, no additional BUY-minus-SELL subtraction — the double-sign-application pitfall
  this session's F-4 audit confirmed no production consumer currently makes), and (c) cite this document's
  fingerprint (§13) for reproducibility.
- **NOT permitted:** any historical-IDX80-membership claim (§5); regime-stratified or walk-forward
  **validation** specifically, until §15 item 8's history-maturity-gate determination is made — this handoff
  does **not** clear that gate, only the FROZEN data-governance gate.
- **Dataset B remains separate** — do not merge or conflate with this Dataset A population for any research
  purpose (H-7C, D-034).

## 18. Worktree note

This document is the only file this step produced. No code, DB, schema, or lifecycle-state change occurred.
Nothing committed.
