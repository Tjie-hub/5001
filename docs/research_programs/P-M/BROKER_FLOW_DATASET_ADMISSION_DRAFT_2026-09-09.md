# Broker-Flow Dataset Object — Admission Package (DRAFT — REV 2)

**Status:** **DECLARED** (2026-09-09, [[DECISION_LOG]] D-040) — governance-approved O4 Dataset Object. **Not yet
FINGERPRINTED or FROZEN**; no hypothesis registered; no empirical test authorized.
**Date:** 2026-09-09 · **Rev:** 2 (revised the same day to incorporate governance-review findings; Rev 1 superseded, not a corpus artifact)
**Rev 2.1 annotation (2026-09-09):** Owner approval of the decision surface recorded in [[DECISION_LOG]] **D-033** — H-1 (IDX80-scoped admission path) APPROVED, explicitly against D-032 Decision B. **DECLARED is not granted**; H-2…H-6 and §J.1 receipts R-1…R-10 remain outstanding; no field values were changed by this annotation. *(Superseded by Rev 2.2 below — retained verbatim as the historical record of this document's state as of D-033; not edited.)*
**Rev 2.2 annotation (2026-09-09):** Subsequent to Rev 2.1, all ten §J.1 receipts closed ([[DECISION_LOG]]
D-032…D-039), the DECLARED-vs-REGISTERED lifecycle ambiguity was ruled (D-036, orthogonal axes), `capability_class`
was approved (D-037), R-1 sufficiency was ruled (D-038), and `asset_class` was accepted at PROPOSED tier (D-039).
**DECLARED was then granted by D-040.** H-2 (window end) and H-3 (2026-08-25 exclusion) are satisfied by Dataset
A's own H-7C-specified identity (D-034), which already fixes both; H-5 (dataset ID) and H-6 (P1/P2 provenance)
closed via R-9/R-6 respectively. **H-4 (DECLARED authority) was operationally exercised — Owner approved D-040
directly, `Approval authority: Owner` — but was never separately ruled as its own named decision; this remains a
minor, non-blocking documentation gap, noted rather than silently closed.**
**Prepared for:** Owner review · **Program:** P-M
**Object type:** [[RESEARCH_OBJECT_MODEL]] O4 Dataset, extended per [[RESEARCH_OBJECT_SCHEMA]] §3.4
**Authority basis:** Production/data-layer authorization is established by external Owner evidence, but the corresponding
canonical governance evidence receipt has not yet been persisted in the Research Governance Corpus (§C, §J R-1). The
authorized scope, as established externally: IDX80, 2025-01-02 → 2026-08-27, vendor-backfill / data-completeness
purpose, **data-layer only** — no Research OS admission/freeze authorization. Cross-references [[DECISION_LOG]] **D-032**
(Broker-Flow-v002 Phase 1); this package does not amend, supersede, or satisfy D-032.

**Evidence-classification legend (claim hygiene — applies throughout).** Every substantive claim below is classified as
one of:

- **[CANONICAL]** — verifiable in the Research Governance Corpus on branch `ops/hardening-2026-07-10`, or verifiable in
  the repository at a cited `file:line`.
- **[EXT-PROD]** — externally supplied production evidence from a prior reconciliation session. It is real input to this
  package, but it is **not** a canonical receipt; persistence is required before it can support any lifecycle transition
  (§J).
- **[PROPOSED]** — proposed by this package; a term offered for Owner decision, not a governance act and not an
  established fact.
- **[UNRESOLVED]** — open question; this draft deliberately offers no interpretation.
- **[OWNER]** — requires an explicit Owner decision; no option is preselected here.
- **[PREREQ]** — tracked in §J (Remaining prerequisites / evidence receipts).

> This document does not declare, fingerprint, freeze, or admit anything. It proposes the fields a Dataset Object
> declaration would carry, for Owner approval, per §H. Per instruction, no DB query, repair, hypothesis registration, or
> empirical test was run to produce this draft. The quantitative facts below are **[EXT-PROD]**: they are carried
> forward from an external production reconciliation, unverified by this drafting session, and they are not canonical
> evidence until receipts are persisted (§J). Repeating them here does not convert them into canonical evidence.

---

## A. Proposed dataset identity and O4 mandatory field set

### A.1 Identity [PROPOSED]

| Field | Value | Note |
|---|---|---|
| `dataset_id` | **UNASSIGNED — proposed descriptive string:** `DS-broker_flow-idx80-2025_2026v1` — **PROPOSED / NON-CANONICAL / PENDING REGISTRY DECISION** | No dataset-registry or ID-assignment authority currently exists in this repository [CANONICAL — [[CUSTODY_MODEL]] header: Dataset Custody "has no realization"; §K.7]. The string follows the descriptive pattern of [[WORKED_EXAMPLE_END_TO_END]] §S4 (`DS-ohlcv-2021_2026-liquid`); it is a label, **not** a registry-issued ID. Registry treatment is Owner decision §H-5. |
| `dataset_name` | Broker-Flow IDX80 Backfill (v002 data-layer scope) [PROPOSED] | Distinguishes from `stockbit-flow-bars-v002` — a different, already-frozen artifact (§K.4) |
| `version` | v0 / PROPOSED (not DECLARED) | Per O4 lifecycle [[RESEARCH_OBJECT_SCHEMA]] §3.4: `DECLARED → FINGERPRINTED → FROZEN`. This package proposes entry into `DECLARED`; it is not there yet. |
| `source_db` | `data/walkforward.db` (production canonical DB) [CANONICAL — repository] | Tables: `broker_flow`, `suspension_events`, `broker_period_summary` |
| `intended_research_use` | P-M program, per-ticker broker-flow/return mechanism study (subject to §F limitations) [PROPOSED] | Not authorized to include index-membership or composition claims (§F) |
| `explicit_boundary` | IDX80-universe, 2025-01-02 → 2026-08-27 inclusive, excluding 2026-08-25 — **PROPOSED SCOPE ONLY** | See §B. The window end (2026-08-27 vs the v002-freeze-date boundary referenced by D-032 Decision A) is an explicit Owner decision (§H-2, §K.1). |

### A.2 O4 mandatory field set (per [[RESEARCH_OBJECT_SCHEMA]] §3.4)

A declaration, if approved, must carry every mandatory O4 field. Status per field — unpopulatable fields are marked
OPEN/PENDING, not invented:

| Field | Requirement source | Proposed value / status |
|---|---|---|
| `dataset_id` | ROM fields (schema §3.4) | **PROPOSED / NON-CANONICAL / PENDING REGISTRY DECISION** (§A.1) |
| `asset_class` | ROM fields | **PROPOSED:** IDX equities, IDX80 universe (fixed backfill-time roster — **not** PIT membership; §C) |
| `resolution` | ROM fields (bound to [[DATA_FEASIBILITY_STUDY]] §3–§4) | Daily, broker-level — one row per (ticker, trade_date, broker_code, side) [CANONICAL — `stockbit_fetcher.py:590-604`] |
| `regime_classification` | ROM fields | **OPEN — PENDING ASSESSMENT.** No regime analysis was run for this package; no value is proposed. |
| `provenance_hash` | ROM fields | **NOT COMPUTED — PREREQ (§J.2 F-1).** No existing function fingerprints `broker_flow` (§I); a fingerprint scope/mechanism must be defined before `FINGERPRINTED`. |
| `capability_class` | O4 addition — **approval is CRO's** (schema §3.4; [[DATA_FEASIBILITY_STUDY]] is binding) | **OPEN — PENDING CRO (§J R-7).** Binding context [CANONICAL]: study §4.1 classes `broker_flow` Available Today **only as an informed-flow proxy**, limited history; §4.2 lists deeper broker-summary backfill as *Obtainable Later*; §5.3 imposes a history-maturity gate (§F.7). |
| `fidelity_limit` | O4 addition (LIM1 — what this data **cannot** distinguish) | **PROPOSED** (derived from §F; not invented): this data cannot distinguish (a) historical IDX80 membership as-known-then; (b) P1 from P2 row provenance (no `source` column exists); (c) the semantics of `lot = 0 ∧ lot_value > 0` rows; (d) the cause of the 2026-08-25 gap. |
| `proxy_for` | O4 addition (LR-5 — the claim inherits the proxy's fidelity) | **CANONICAL + OPEN:** the capability this data backs is the *informed-flow / adverse-selection proxy* [[DATA_FEASIBILITY_STUDY]] §4.1 — proxy tier, not true OFI. Final mechanism-level assignment belongs to the hypothesis that binds this dataset. |
| `point_in_time` | O4 addition (F7) | **NO for any index-composition-dependent interpretation** (fixed backfill-time roster; §C, §F.1). Full construction argument: **OPEN/PENDING** — requires roster pinning (§J R-3) and P1/P2 resolution (§J R-6). |
| `corporate_actions_applied` | O4 addition | **OPEN — NOT ESTABLISHED.** No evidence available to this package establishes whether `broker_flow` quantities are corporate-action-adjusted. No adjustment is assumed; none is claimed. Verification required before freeze (§J.2 F-3). |
| `custody_partition` | O4 addition | **OPEN — NOT ASSIGNED.** Per [[RESEARCH_OBJECT_MODEL]] §4.1, partitions are first-class objects with their own fingerprints; this package proposes none. Assignment is a later, separate governance act. |

**Provenance elements required by schema §3.4** (beyond `provenance_hash`):

| Element | Status |
|---|---|
| Vendor + retrieval time | **PARTIAL.** Vendor: "Stockbit broker summary" [CANONICAL — [[DATA_FEASIBILITY_STUDY]] §3]. Retrieval/backfill execution timestamps for the P2 population: **[EXT-PROD], unreceipted — §J R-2/R-3.** |
| Transformation lineage | **PARTIAL / PROPOSED:** vendor EOD broker summary → production `broker_flow` via the standing collection pipeline (P1 population) and the owner-authorized backfill (P2 population). Lineage receipt required (§J). |
| `point_in_time` construction argument | **OPEN/PENDING** — the partial argument drafted in §C covers only the composition dimension. |

---

## B. Inclusion / exclusion rule (Option A) — PROPOSED SCOPE ONLY

**Included population [PROPOSED]:**
- Universe: IDX80 (owner-authorized backfill population only — **not** the full active universe; see §K.1)
- Date range: `2025-01-02` → `2026-08-27` inclusive [PROPOSED; window end subject to §H-2]
- Source: the Owner-authorized data-layer backfill run, as reconciled against the production `broker_flow` table
  [EXT-PROD]

**Proposed exclusions:**
- `2026-08-25` — confirmed zero-row date, cause unknown, no journal entries (§E). **Proposed** exclusion pending
  separate Owner decision (§H-3). Not repaired, not imputed; no repair-impossibility claim is made.
- Any `broker_flow` row **outside** the IDX80-authorized backfill population that happens to share the same date range
  — i.e., rows attributable to the earlier, separate "ordinary live-ALL collection" process are **not** part of this
  proposed Dataset Object and must not be silently merged in.

**Provenance-class separation (do not silently mix) [EXT-PROD population description, PROPOSED treatment]:**
The external production reconciliation describes `broker_flow` rows before 2026-04-23 (1,197,293 rows,
2025-01-02 → 2026-04-22) as a distinct, earlier population from the owner-authorized IDX80 backfill. This draft treats
these as **two provenance classes**:

| Class | Description | In this proposed Dataset Object? |
|---|---|---|
| P1 — Ordinary live-ALL collection | Rows collected before 2026-04-23 by the standing production pipeline; universe scope not established as IDX80-authorized-backfill [EXT-PROD] | **Not yet resolved** — open question below |
| P2 — Owner-authorized IDX80 backfill | Rows from the specific, scoped, owner-authorized backfill (2025-01-02 → 2026-08-27, IDX80) [EXT-PROD] | Proposed inclusion, subject to §K |

**Open question this draft does NOT resolve [UNRESOLVED]:** whether P1 rows that happen to fall inside
2025-01-02 → 2026-08-27 for IDX80 tickers are (a) superseded/overwritten by the P2 backfill, (b) coexist with P2 in the
same table without a provenance-class column, or (c) are a distinct, currently unlabeled row population. The schema
provides no way to tell: `broker_flow` has **no `source`/`provenance` column** [CANONICAL — `stockbit_fetcher.py:590-604`],
and this draft does not invent one. **Reproducible partitioning of the overlapping P1/P2 populations is therefore not
currently possible and remains an admission blocker wherever the Dataset Object requires exact row-count
reproducibility or a scoped `provenance_hash`** (§F.6, §J R-6).

---

## C. Provenance statement

- **Authorization [EXT-PROD → PREREQ]:** Production/data-layer authorization is established by external Owner evidence,
  but the corresponding canonical governance evidence receipt has not yet been persisted in the Research Governance
  Corpus. The externally confirmed scope: **IDX80; 2025-01-02 → 2026-08-27; vendor-backfill / data-completeness purpose;
  data-layer only.** Persistence of that receipt is a prerequisite (§J R-1) for any capital-facing Dataset admission.
- **What this authorization is NOT [EXT-PROD scope statement]:** it is not authorization to declare, fingerprint, or
  freeze a Research OS Dataset Object, and not authorization to register a hypothesis or run empirical tests against
  this data. Per the O4 lifecycle ([[RESEARCH_OBJECT_SCHEMA]] §3.4), `DECLARED`/`FINGERPRINTED`/`FROZEN` are each
  distinct governance acts from a data-layer backfill.
- **Historical-universe limitation [EXT-PROD scope, disclosed]:** the backfill population used a fixed
  backfill-time/live IDX80 roster, **not** date-specific historical IDX80 membership. This dataset therefore **cannot
  support point-in-time historical index-composition claims** and carries survivorship/look-ahead risk on any claim
  that depends on "was this ticker in IDX80 on date X." The actual roster used must eventually be pinned by evidence
  receipt (source query + retrieval timestamp + hash) if the dataset is admitted (§J R-3); `point_in_time` field
  treatment in §A.2.
- **Production vs. Research OS distinction [CANONICAL — `tests/test_research_data_fence.py:30-35`]:** `broker_flow`,
  `suspension_events`, and `broker_period_summary` are production-owned operational tables — none appear in
  `RESEARCH_TABLES` — so production may write them and any Dataset Object here is a **research-side read/derivation** of
  production data, not a research-owned table. Admission would be a *record about* a slice of `broker_flow`, not a
  claim that `broker_flow` becomes research-owned or write-fenced.
- No claim is made that this dataset is PIT-correct historical IDX80 composition (see §F.1–§F.2).

---

## D. Data semantics

**Observed lot population [EXT-PROD — unreceipted; receipt required, §J R-5]:**

| Population | Rows | Negative lot | Zero lot | Positive lot | min lot | max lot | Negative lot_value |
|---|---|---|---|---|---|---|---|
| BUY | 1,583,777 | 3,547 | 22,473 | 1,557,757 | -36,574 | 49,173,306 | 0 |
| SELL | 1,420,899 | 1,365,960 | 47,640 | 7,299 | -46,827,346 | 77,756 | 0 |

- **Signed lot semantics [EXT-PROD]:** `broker_flow.lot` is empirically a signed quantity — BUY predominantly positive,
  SELL predominantly negative.
- **`lot_value` is non-negative [EXT-PROD]** in the observed population: 0 negative `lot_value` rows in both the BUY
  and SELL populations.
- **Research net-flow treatment [PROPOSED rule]:** research net-flow calculations must **explicitly define** their
  treatment of signed `lot`. The recommended convention is to treat `lot` as already signed and use `SUM(lot)` directly,
  and **not** to additionally compute BUY-minus-SELL arithmetic on top of the already-signed field, which would
  double-apply the sign convention. Any hypothesis binding this dataset must state its convention before G1.
- **Consumer-formula audit — separate verification item [CANONICAL — code sweep on this branch]:** the identified
  BUY-minus-SELL consumers (`engine/dashboard.py:83-99`, `engine/agent_firm_context.py:163-177`,
  `engine/premarket_revision.py:143-158`, `routes/flow.py:292`) operate on **`lot_value`**, which is non-negative in the
  observed production population [EXT-PROD]. **No confirmed consumer defect is established by the current sweep**, and
  this package does **not** claim that production consumers currently conflict with signed-`lot` semantics. Whether any
  consumer misuses the signed `lot` field remains open and belongs to the separate audit (§J.2 F-4). No production code
  was altered by this package.
- **Unresolved semantics — do not invent an explanation [UNRESOLVED]:** the meaning of `lot = 0` rows with
  `lot_value > 0` (22,473 BUY, 47,640 SELL rows [EXT-PROD]) is not established. Recorded as unresolved — not as a
  data-quality defect and not as a vendor-reporting artifact; either interpretation would be invented.
- **Extreme values, no interpretation [EXT-PROD]:** BUY min lot = -36,574 / max lot = 49,173,306; SELL min lot =
  -46,827,346 / max lot = 77,756. No outlier-treatment rule is proposed here.

---

## E. Gap treatment — 2026-08-25

| Fact | Value | Class |
|---|---|---|
| Row count, 2026-08-25 | 0 | [EXT-PROD] |
| Row count, adjacent dates (2026-08-24 / -26 / -27) | 21,190 / 21,964 / 20,948 | [EXT-PROD] |
| `journalctl -u idx-walkforward`, 2026-08-24 → 2026-08-26 | No entries | [EXT-PROD] |
| Cause | **Not established** | [UNRESOLVED] |
| Disposition | **Proposed:** excluded from the research dataset, **pending separate Owner decision** (§H-3). Not repaired, not imputed. | [PROPOSED] |

No inference is drawn about failure mode (vendor outage, scheduler gap, holiday miscoding, etc.), and **no claim is
made that repair is possible or impossible**. No repair or imputation was performed, and none is proposed by this
package. If the Owner later directs repair investigation, that is a separate act outside this package.

---

## F. Research limitations

1. **Survivorship / look-ahead risk** — the IDX80 backfill roster is fixed at backfill time, not date-specific
   historical membership [EXT-PROD scope]. Any per-date "was this ticker in the index" claim is at risk of look-ahead
   bias.
2. **No historical index-composition claims** — this dataset cannot be used to assert what IDX80's membership was on
   any historical date.
3. **Consumer-formula audit open** — identified BUY-minus-SELL consumers use `lot_value` (non-negative in the observed
   population); no confirmed consumer defect is established by the current sweep; the audit remains a separate
   verification item (§D, §J.2 F-4) and is not itself a defect *of this dataset*.
4. **Proposed excluded date** — 2026-08-25, cause unknown, proposed exclusion pending Owner decision (§E, §H-3).
5. **Unresolved lot=0/value>0 semantics** — no explanation offered (§D).
6. **Unresolved provenance-class boundary** — whether/how P1 and P2 rows are distinguished inside `broker_flow` for
   dates where both could apply (§B). This is a **blocking ambiguity for exact row-count reproducibility** and for any
   scoped `provenance_hash` — not merely a caveat (§J R-6).
7. **History-maturity gate [CANONICAL — [[DATA_FEASIBILITY_STUDY]] §5.3]:** short-history datasets — broker flow is
   explicitly listed — "cannot yet support regime-stratified or walk-forward validation," and any hypothesis depending
   on them must declare a *history-maturity gate*; the study calls this "a first-class scope rule, not a footnote."
   Program P-M · Microstructure Flow is registered at **PROXY** capability tier
   (`docs/research_programs/RESEARCH_PROGRAM.md`, programs table) [CANONICAL]. Regardless of how the §K.6 inventory
   discrepancy resolves, `broker_flow` must **not** be treated as a fully mature informed-flow observation capability:
   the canonical classification (Available Today *as a proxy*, limited history) governs until superseded by an updated
   study.
8. Per-ticker flow/return mechanism tests **may** remain compatible with prior P-M scope analysis, but only subject to
   the explicit limitations above and Owner/governance approval — this draft does not itself grant that compatibility a
   green light.

---

## G. Governance checklist

| Item | Status |
|---|---|
| DECLARED | **DECLARED, 2026-09-09** — [[DECISION_LOG]] D-040; all §J.1 receipts R-1…R-10 (D-032…D-039) and H-2…H-6 closed. See `BROKER_FLOW_DATASET_A_DECLARED_TRANSITION_REQUEST_2026-09-09.md`. |
| FINGERPRINTED | **YES, 2026-09-09** — [[DECISION_LOG]] D-041; `provenance_hash = 329b22e49f0ef882b6da031f437e9d87084d2863837ebf8c830de362b7942558`. See `BROKER_FLOW_DATASET_A_FINGERPRINTED_GATE_2026-09-09.md`. |
| FROZEN | **YES, 2026-09-09** — [[DECISION_LOG]] D-043; F-1…F-5 closed (D-040…D-042). Amend after freeze: prohibited. See `BROKER_FLOW_DATASET_A_FROZEN_TRANSITION_REQUEST_2026-09-09.md`. |
| EMPIRICAL GATE | NOT PASSED |
| HYPOTHESIS REGISTRATION | NOT AUTHORIZED / NOT YET |
| EMPIRICAL TEST | BLOCKED |

No status above was changed by Rev 2, and none may be read as upgraded. Per [[EVIDENCE_MODEL]] EV-8, nothing promotes
by default; every transition requires a positive act with an evidentiary receipt (§J). `capability_class` remains OPEN
pending CRO (§J R-7).

---

## H. Owner decision block

**Decision requested:** whether to approve entry of this proposed Dataset Object into the `DECLARED` state (O4
lifecycle, [[RESEARCH_OBJECT_SCHEMA]] §3.4) on the terms drafted in §A–§F — **conditional on the explicit sub-decisions
below and the receipts in §J.1**.

**Recorded outcome (2026-09-09, [[DECISION_LOG]] D-033):** the Owner approved the decision surface — **H-1 APPROVED**
(IDX80-scoped admission path, explicitly against D-032 Decision B, receipt gates preserved). **H-2…H-6 remain OPEN**;
the approval did not specify their options and none is recorded here. DECLARED was **not** granted by D-033; no
lifecycle transition occurred. *(Historical record as of D-033 — not edited; superseded in effect by the outcome
below.)*

**Subsequent recorded outcome (2026-09-09, [[DECISION_LOG]] D-040):** following closure of all ten §J.1 receipts
(D-032…D-039) and the four lifecycle/field micro-decisions (D-036…D-039 — DECLARED-vs-REGISTERED interpretation,
`capability_class`, R-1 sufficiency, `asset_class`), the Owner approved and D-040 recorded Dataset A's transition
into **DECLARED**. See `BROKER_FLOW_DATASET_A_DECLARED_TRANSITION_REQUEST_2026-09-09.md` for the full closure
record. FINGERPRINTED and FROZEN were **not** granted by D-040; both remain gated on §J.2 (F-1…F-5).

**Explicit sub-decisions requested (no option is preselected):**

| # | Decision requested | Status |
|---|---|---|
| H-1 | Whether an **IDX80-scoped** broker_flow Dataset Object may be declared **in light of D-032 Decision B** — narrowing must be an explicit specification decision, not an implicit workaround for Decision B's full-active-universe freeze basis (§K.1) | **APPROVED — 2026-09-09, D-033** (explicit specification decision; receipt gates preserved; D-032 B unchanged) |
| H-2 | **Analytical window end:** 2026-08-27 (proposed) vs the v002-freeze-date boundary referenced by D-032 Decision A | **OWNER — OPEN** |
| H-3 | **2026-08-25 exclusion** — ratify the proposed exclusion, direct a repair investigation, or otherwise dispose (cause currently unknown; §E) | **OWNER — OPEN** |
| H-4 | **Authority for the DECLARED transition** — the corpus names no single approving authority for `DECLARED` (§K.7); this gap must be closed explicitly, not by practice | **OWNER — OPEN** |
| H-5 | **Dataset ID / registry treatment** — no registry machinery exists; rule on the proposed non-canonical string and on whether/when to stand up registry and ID-assignment machinery | **OWNER — OPEN** |
| H-6 | **P1 provenance-boundary treatment** — the resolution mechanism for the P1/P2 overlap (§B), noting it may implicate a production schema decision | **OWNER — OPEN** |

Separately, and not an Owner item under the schema's role model: `capability_class` approval is a **CRO** responsibility
([[RESEARCH_OBJECT_SCHEMA]] §3.4) — §J R-7.

- [ ] **APPROVE DATASET DECLARATION** — as drafted in §A–§F, conditional on §J.1 receipts and sub-decisions H-1…H-6
- [ ] **REJECT**
- [ ] **REQUEST CHANGES** — (specify which section)

*This session does not select an option. Recorded here strictly as a decision surface for the Owner.*

---

## I. Verification commands

Read-only. None of these mutate `data/walkforward.db`; several use `sqlite3 -readonly` (or `PRAGMA query_only = ON` in
an interactive session) as a belt-and-suspenders guard. Schema reference (`stockbit_fetcher.py:590-604`):
`broker_flow(ticker, trade_date, broker_code, side, lot, lot_value, value, value_total, avg_price, freq,
investor_type)`, `PRIMARY KEY (ticker, trade_date, broker_code, side)` — **no `source`/`provenance` column exists**
[CANONICAL], which is why the row-count queries below cannot themselves resolve the P1/P2 boundary flagged in §B; they
verify what the schema can currently answer. When an authorized session executes these with recorded outputs, the
result constitutes the **production boundary verification receipt** (§J R-4); this draft itself ran none of them.

**Important — row counts are not the coverage audit.** The queries below establish raw row-count coverage only. The
canonical coverage methodology is the **D-032 completion predicate** (`broker_flow` row OR confirmed-empty
`bandar_detector` marker, per `tools/broker_flow_idx80_gap.py` — the predicate D-032 itself reused, not reinvented)
[CANONICAL — [[DECISION_LOG]] D-032]. A formal IDX80-scoped coverage audit using that predicate is a separate
prerequisite (§J.2 F-2) and must not be substituted by these counts.

**Exact row count, proposed boundary (date range only — not yet universe-scoped, see §B):**
```bash
sqlite3 -readonly data/walkforward.db "SELECT COUNT(*) FROM broker_flow WHERE trade_date BETWEEN '2025-01-02' AND '2026-08-27';"
```

**Exact row count, boundary minus the proposed excluded date:**
```bash
sqlite3 -readonly data/walkforward.db "SELECT COUNT(*) FROM broker_flow WHERE trade_date BETWEEN '2025-01-02' AND '2026-08-27' AND trade_date != '2026-08-25';"
```

**Date range actually present in that window:**
```bash
sqlite3 -readonly data/walkforward.db "SELECT MIN(trade_date), MAX(trade_date) FROM broker_flow WHERE trade_date BETWEEN '2025-01-02' AND '2026-08-27';"
```

**Ticker count (distinct tickers appearing in the window — not itself an IDX80-membership check; see §C's
PIT-composition limitation):**
```bash
sqlite3 -readonly data/walkforward.db "SELECT COUNT(DISTINCT ticker) FROM broker_flow WHERE trade_date BETWEEN '2025-01-02' AND '2026-08-27';"
```

**Per-date coverage (re-derives the §E gap and surfaces any other unexpected zero/low-count dates the external
reconciliation did not check):**
```bash
sqlite3 -readonly data/walkforward.db "SELECT trade_date, COUNT(*) AS n FROM broker_flow WHERE trade_date BETWEEN '2025-01-02' AND '2026-08-27' GROUP BY trade_date ORDER BY trade_date;"
```

**Exclusion verification (2026-08-25 must be exactly zero; a nonzero result means §E's externally supplied fact no
longer holds and this draft's proposed exclusion needs re-review, not silent acceptance):**
```bash
sqlite3 -readonly data/walkforward.db "SELECT COUNT(*) FROM broker_flow WHERE trade_date = '2026-08-25';"
```

**Fingerprint inputs — NOT a fingerprint.** No existing function computes a fingerprint for `broker_flow` —
`research.tracking.dataset_fingerprint()` (`research/tracking.py:119`) is scoped to `ohlcv` + `corporate_actions` only
[CANONICAL — also [[CUSTODY_MODEL]] §5.5], and nothing here extends or invokes it. Per [[CUSTODY_MODEL]] CU-15, every
fingerprint declares its scope and that declaration is part of the fingerprint's meaning; **defining the
`broker_flow` fingerprint scope/mechanism is prerequisite §J.2 F-1, before `FINGERPRINTED`**. The query below produces
only the *candidate inputs* a future fingerprint could hash, mirroring that function's established method
(order-independent per-ticker aggregate, stable regardless of query plan):
```bash
sqlite3 -readonly data/walkforward.db "SELECT ticker, COUNT(*), MIN(trade_date), MAX(trade_date), SUM(CAST(lot AS INTEGER)), SUM(CAST(lot_value AS INTEGER)) FROM broker_flow WHERE trade_date BETWEEN '2025-01-02' AND '2026-08-27' AND trade_date != '2026-08-25' GROUP BY ticker ORDER BY ticker;"
```
Piping that output through `sha256sum` (or hashing inside `data.db.connect()` per the `data/db.py` centralization rule,
if done in Python rather than the `sqlite3` CLI) would produce a candidate `provenance_hash` — a capability this draft
documents as available, **not one it exercises, and not one that exists for `broker_flow` today**.

---

## J. Remaining prerequisites — evidence receipts and open items

### J.1 Receipts required before the DECLARED transition can be requested

| # | Receipt required | Current status |
|---|---|---|
| R-1 | **Persisted Owner authorization receipt** for the data-layer backfill, scope as §C (IDX80; 2025-01-02 → 2026-08-27; vendor-backfill/data-completeness; data-layer only) | Authorization established by external Owner evidence [EXT-PROD]; **no canonical receipt in the corpus** |
| R-2 | **Backfill completion receipt** — exact invocation and scope of the backfill run | [EXT-PROD], unreceipted |
| R-3 | **Pinned IDX80 roster** — source query, retrieval timestamp, hash of the exact membership list used | Not pinned; required for the fixed-roster limitation to be checkable and for the `point_in_time` construction argument |
| R-4 | **Production boundary verification receipt** — the §I queries executed with recorded outputs, incl. the 2026-08-25 zero-row check at declaration time | Not executed by this package |
| R-5 | **Lot-sign evidence receipt** — the §D population statistics re-derived and persisted | [EXT-PROD], unreceipted |
| R-6 | **P1/P2 provenance resolution receipt** — mechanism by which overlapping populations are distinguished/excluded, where required by the Dataset Object (§B, §F.6) | Unresolved; admission blocker for exact reproducibility and scoped `provenance_hash` |
| R-7 | **CRO `capability_class` receipt** (schema §3.4; [[DATA_FEASIBILITY_STUDY]] binding) | OPEN |
| R-8 | **Updated [[DATA_FEASIBILITY_STUDY]]**, if required by its footer, resolving the §K.6 inventory discrepancy | Not re-run |
| R-9 | **Dataset ID / registry ruling** (§H-5) — either registry machinery/ID assignment, or an explicit Owner ruling on the interim non-canonical string | Governance gap; no machinery exists |
| R-10 | **D-032 decision persistence** — the recorded D-032 decisions, plus the Owner's §H-1/H-2 scope decision, persisted in the canonical corpus (DECISION_LOG entry or superseding entry) | H-1 scope decision recorded (D-033, 2026-09-09, working tree — **commit to branch outstanding**); H-2 still OPEN; D-032 itself also uncommitted |

### J.2 Required between DECLARED and FROZEN

| # | Item | Note |
|---|---|---|
| F-1 | **`broker_flow` fingerprint scope/mechanism** — define and implement a reproducible, scope-declaring fingerprint (CU-15) before `FINGERPRINTED` | None exists today (§I) |
| F-2 | **Formal IDX80-scoped coverage audit receipt** using the canonical D-032 completion predicate (not raw row counts) | D-032 Decision A requires post-repair coverage audit; audit must be against the scope actually being declared (§H-1/H-2 outcome) |
| F-3 | **`corporate_actions_applied` verification** (§A.2 OPEN) | Not established by any current evidence |
| F-4 | **Production consumer-formula audit** (§D) — separate verification item; no confirmed defect established by the current sweep | Unscheduled; does not block admission |
| F-5 | **`regime_classification` assessment** (§A.2 OPEN) | Required before the field set is complete at freeze |

**Standing open items, independent of admission:** D-032 **Items C and D remain OPEN** [CANONICAL] — both block
*interpretation* of any downstream H1 result on this data, independent of dataset admission itself; noted here so they
are not silently forgotten if this dataset is later declared.

---

## K. Discrepancies between this package and canonical governance documents

1. **Scope narrowing vs. D-032 (recorded, escalated, not resolved).** D-032 (2026-09-08, ACCEPTED) recorded Decision A
   (retain the original analytical window beginning 2025-01-02 through the v002 freeze date; do not redefine the window
   to accommodate coverage; repair gaps where technically/vendor-supported before freeze; explicitly audit tiered
   coverage after repair) and Decision B (complete-backfill-before-freeze; *"Do NOT freeze broker-flow-v002 with the
   currently known structural coverage gap… If vendor/data limitations make complete coverage impossible, STOP and
   escalate rather than silently changing the specification."*) [CANONICAL]. Stated precisely:
   - Decision B blocks **freezing broker-flow-v002 on the full-active-universe coverage basis recorded there**
     (958 tickers; 0 of 393 dates fully complete; ~275,253 missing ticker-day cells at measurement).
   - It does **not** itself explicitly authorize a narrowed IDX80 Dataset Object.
   - Narrowing the specification must **not** be used as an implicit workaround for Decision B; any IDX80-scoped
     declaration must be an **explicit Owner decision** (§H-1).
   - This draft does not silently convert D-032's full-universe requirement into an IDX80-only requirement; the
     discrepancy is escalated here, which is the path Decision B itself prescribes.
   - Related sub-decision: the proposed window end (2026-08-27) differs from D-032 Decision A's "through the v002 freeze
     date" boundary (§H-2).
2. **D-032 Items C and D remain unresolved** [CANONICAL] and are not re-litigated by this draft (per the explicit
   no-repair / no-empirical-test instructions). They are carried in §J as blocking prerequisites for *interpretation*,
   separate from dataset admission itself.
3. **No Dataset Object has ever been declared through the O4 lifecycle in this repository** — [[RESEARCH_OBJECT_SCHEMA]]
   §3.4 and [[WORKED_EXAMPLE_END_TO_END]] §S4 describe the intended lifecycle and fields, but no live instance, registry,
   or `dataset_id` assignment authority exists [CANONICAL — [[CUSTODY_MODEL]]: Dataset Custody "has no realization"].
   The out-of-lifecycle frozen artifact `stockbit-flow-bars-v002` (§K.4) was not created through the O4 lifecycle and
   does not contradict this statement; this draft is the first attempt at populating the schema for a real dataset and
   surfaces the registry gap as prerequisite R-9 rather than resolving it.
4. **`broker-flow-v002` vs. `stockbit-flow-bars-v002` naming collision risk** — `stockbit-flow-bars-v002` is an
   already-frozen, distinct artifact (freeze manifest 2026-09-07, 99.7% complete coverage, `broker_flow` explicitly
   excluded from its scope) [CANONICAL — `data/frozen/stockbit-flow-bars-v002/MANIFEST.json`]. The proposed
   `dataset_id` deliberately avoids reusing that name; flagged so reviewers do not conflate the two artifacts.
5. **HYP-PM-0002's "`broker_flow` (investor-type)" is not the population this package proposes** — `HYP-PM-0002_DRAFT.md`
   §5 records the investor-type window as 2026-04-01 → 2026-08-19 (~4.5 months) and excludes that dataset from its
   round; §8 records broad daily flow coverage of **62 trading days (2026-04-28 → 2026-08-19, ≥500-ticker days)** as the
   binding constraint [CANONICAL]. The externally supplied evidence for this package describes the raw per-broker
   signed-lot BUY/SELL population over the proposed window 2025-01-02 → 2026-08-27 [EXT-PROD] — a different slice/use of
   the same underlying `broker_flow` table, not investor-type decomposition. Whoever reconciles this package against
   HYP-PM-0002 should confirm the two are not silently conflated; this draft treats them as distinct until stated
   otherwise.
6. **Canonical inventory vs. externally supplied production evidence ([[DATA_FEASIBILITY_STUDY]] §3) — recorded, not
   resolved.** The canonical inventory records `broker_flow` as: investor-type broker summary (Asing/Lokal/Pemerintah),
   **2026-04-01 → present, ~872k rows, 871 tickers**, classified Available Today **only as an informed-flow proxy** with
   a limited-history caveat, with §5.3 history-maturity as a first-class scope rule, and §4.2 listing deeper
   broker-summary backfill as **Obtainable Later** [CANONICAL]. The external production reconciliation supplied to this
   package records a materially larger historical population: **1,197,293 rows before 2026-04-23 (MIN 2025-01-02,
   MAX 2026-04-22)** [EXT-PROD]. **This draft does not choose which source is correct.** Reconciliation — by re-running
   the study's inventory per its own footer ("Re-run the inventory query and re-classify whenever a provider or table
   changes") and/or by persisting receipts for the external reconciliation — is prerequisite R-8. Per that footer, any
   scope decision contradicting §4 must cite an updated version of the study; none yet exists.
7. **DECLARED-transition authority / lifecycle-vocabulary ambiguity — recorded, not resolved.** [[RESEARCH_OBJECT_SCHEMA]]
   §3.4 defines the O4 dataset lifecycle `DECLARED → FINGERPRINTED → FROZEN`; [[CUSTODY_MODEL]] §5 contains a different
   lifecycle vocabulary in which REGISTERED requires identity + fingerprint + lineage (custody transition T-C2). The
   corpus does not clearly identify a single approving authority for the O4 `DECLARED` transition (schema §3.4 names the
   Data Engineer for create/maintain and the CRO for `capability_class`, but no authority for `DECLARED`). This draft
   does not invent an authority; routing the declaration decision to the Owner (§H-4) follows the D-032 practice and is
   recorded here as a **governance gap requiring explicit Owner decision**.
