# Broker-Flow Dataset A — DECLARED-Readiness Package (Phases 1–5)

**Status:** READ-ONLY GOVERNANCE ARTIFACT — does **not** itself transition Dataset A to `DECLARED`, `FINGERPRINTED`,
or `FROZEN`. No hypothesis is registered and no empirical test is authorized by this document.
**Date:** 2026-09-09 · **Program:** P-M · **Object:** `DS-broker_flow-idx80-nonpit-2025_2026v1` (Dataset A, O4)
**Produced under:** the mission "CLOSE P-M BROKER-FLOW DATASET A TO DECLARED / EMPIRICAL-READY," Phases 1–5 (routine
technical/documentary work completable without Owner/CRO approval). Phases 6–9 are explicitly **not** started —
each requires an Owner/CRO ruling this document only surfaces (§5).
**Builds on:** [[DECISION_LOG]] D-032…D-035 · `BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md` (Rev 2.1) ·
`BROKER_FLOW_DATASET_POPULATION_SPECIFICATION_H7C_2026-09-09.md` (Dataset A §A) — none of those documents are
modified by this one.

**Evidence-classification legend (carried forward for consistency):** [CANONICAL] · [DB-VERIFIED] (this session,
read-only, against live `data/walkforward.db`) · [LOG-DERIVED] (see prior session's contamination finding —
never trusted alone) · [OWNER] · [UNRESOLVED] · [PROPOSED].

---

## 1. Phase 1 — DECLARED vs REGISTERED lifecycle resolution

### 1.1 Exact governing text

**[[RESEARCH_OBJECT_SCHEMA]] §3.4, O4 Dataset, "Lifecycle" facet (facet #4 of its nine-facet spec):**
> `DECLARED → FINGERPRINTED → FROZEN` · `→ SUPERSEDED` (retained; prior experiments remain bound to the prior
> fingerprint).

This document's own header states it "**extends [[RESEARCH_OBJECT_MODEL]] v1.0**" (§0.4) and was Last Updated
2026-07-15. It has never been edited to reference `CUSTODY_MODEL` or ROM v2.0.

**[[CUSTODY_MODEL]] §4.1 (asset states), §4.6 (applicability table), row "Dataset":**
> CREATED ✅ · REGISTERED ✅ · PARTITIONED ✅ · LOCKED ✅ · RELEASED — · CONSUMED — · SUPERSEDED ✅ · ARCHIVED ✅

> REGISTERED: *"Identity assigned; fingerprint computed; lineage bound."* (§4.1)
> T-C2 guard: *"CREATED → REGISTERED | Identity + fingerprint + lineage | ✅"* (§4.2)

`CUSTODY_MODEL` §3 declares a **separate** nine-attribute "custody facet" that, per its own header, is "**the
ROM amendment** ([[RESEARCH_OBJECT_MODEL]] v2.0 §3, D-022). Every research asset — without exception — declares
all nine." Its attribute #5, also named **"Lifecycle,"** is defined as *"its admissible states — **a subset of
§4's eight**."* Attribute #3, **"Custody,"** is defined separately as *"its custody class (§3.1) and current
asset state (§4)."*

**The reconciliation attempt that exists — [[CUSTODY_AMENDMENT]] §3, Propagation Matrix:**
> Row 6, `RESEARCH_OBJECT_SCHEMA`: 🟢 **NO CHANGE** — *"Already carries `custody_partition` on O4 and custody in
> 15 places. It anticipated this amendment correctly. **Its facet 4 now resolves to [[CUSTODY_MODEL]] §3 rather
> than to nothing.**"*
>
> Row 9, `HYPOTHESIS_LIFECYCLE`: 🟢 **NO CHANGE** — *"T5's custody guard now resolves to [[CUSTODY_MODEL]] §5.4.
> **The 12 states are the claim axis; custody's 8 are the asset axis (CU-1) — orthogonal, no collision.**"*

### 1.2 Exact conflict

Two textual facts, both [CANONICAL], are in tension and the corpus does not reconcile them for O4 specifically:

1. **The literal string "DECLARED" appears nowhere in the corpus except `RESEARCH_OBJECT_SCHEMA.md` §3.4 itself**
   [DB-VERIFIED — `grep -rn "DECLARED" docs/research_os/*.md docs/governance/*.md`, one substantive hit]. No
   document — including `CUSTODY_MODEL.md`, `CUSTODY_AMENDMENT.md`, or `CUSTODY_PROPAGATION_AUDIT.md` — ever maps
   `DECLARED` to `CREATED`, `REGISTERED`, or any other asset state.
2. **`CUSTODY_AMENDMENT.md`'s own propagation matrix treats two structurally parallel cases inconsistently in
   wording.** For `HYPOTHESIS_LIFECYCLE` (row 9), it explicitly states the object's own lifecycle facet and
   `CUSTODY_MODEL`'s asset-state facet are **"orthogonal, no collision"** — i.e. a Hypothesis carries *both* its
   12-state claim lifecycle *and* a custody asset-state, simultaneously, answering different questions. For
   `RESEARCH_OBJECT_SCHEMA` (row 6, which covers O4 Dataset among other objects), it instead says facet 4
   ("Lifecycle") **"now resolves to CUSTODY_MODEL §3"** — wording that reads as *replacement/grounding*, not
   *coexistence*. The amendment gives no reason for the asymmetry, and does not say whether row 6 intends the
   same orthogonal-coexistence reading as row 9, or a literal replacement of `DECLARED → FINGERPRINTED → FROZEN`
   by `CREATED → REGISTERED → ... → ARCHIVED`.

**Consequence:** it cannot be determined from the text alone whether "Dataset A is DECLARED" is (a) a real,
independent state a Data Engineer can assert once O4's own criteria are met — coexisting with, but distinct from,
its `CUSTODY_MODEL` asset-state — or (b) an informal/superseded label whose institutional meaning is now carried
entirely by reaching `REGISTERED` (identity + fingerprint + lineage, per T-C2) in `CUSTODY_MODEL`'s state machine.
Under reading (b), Dataset A **cannot** reach the functional equivalent of DECLARED without a computed
`provenance_hash`/fingerprint — which §3.4's own text explicitly does **not** require until the *next* stage
(`FINGERPRINTED`). The two readings therefore imply different prerequisites for the same real-world action.

### 1.3 Smallest Owner decision required

Not "which document wins" — `CUSTODY_AMENDMENT.md` row 6 already asserts `CUSTODY_MODEL` governs facet 4 for O4.
The smallest actual decision is:

> **For O4 Dataset specifically, does `DECLARED` (RESEARCH_OBJECT_SCHEMA §3.4) mean the same event as reaching
> `REGISTERED` (CUSTODY_MODEL §4.1, T-C2) — coexisting terms for one transition — or does `CUSTODY_MODEL`'s
> 8-state machine fully replace the DECLARED/FINGERPRINTED/FROZEN vocabulary for O4, with DECLARED retired?**

### 1.4 Proposed decision options

| Option | Description | Consequence for Dataset A |
|---|---|---|
| **1a — Synonym mapping** | `DECLARED` ≡ `REGISTERED` (T-C2: identity + fingerprint + lineage). `FINGERPRINTED` ≡ the fingerprint-computed sub-condition already folded into T-C2. `FROZEN` ≡ `LOCKED`. | Dataset A **cannot** be DECLARED until a `broker_flow` fingerprint exists (currently absent — §3 below, R-9/F-1) — i.e. DECLARED and FINGERPRINTED effectively collapse into one gate. |
| **1b — Orthogonal axes (row-9 analogy)** | O4's `DECLARED → FINGERPRINTED → FROZEN` is the **claim-readiness axis** (Research-Object-Schema facet 4, as literally written); `CUSTODY_MODEL`'s `CREATED → REGISTERED → ... → ARCHIVED` is a **separate asset-mechanics axis** that coexists with it, exactly as ruled for Hypothesis (row 9). | Dataset A can be DECLARED per §3.4's original, narrower criteria (mandatory fields populated, `capability_class` CRO-approved) **without** first computing a fingerprint — fingerprinting remains gated at the `FINGERPRINTED` step, as §3.4 originally intended. The asset-state (CREATED/REGISTERED/…) tracks separately underneath. |
| **1c — Formal amendment** | Neither reading is adopted as-is; `RESEARCH_OBJECT_SCHEMA` §3.4 is edited (Research Architect authority, per its own header) to either restate DECLARED/FINGERPRINTED/FROZEN as an explicit sub-mapping onto CUSTODY_MODEL's 8 states, or to strike the O4-specific lifecycle line and defer entirely to CUSTODY_MODEL. | Removes the ambiguity permanently, at the cost of an explicit corpus amendment (not something this document can perform — Research Architect ownership). |
| **1d — Defer, proceed under explicit caveat** | Owner permits DECLARED to be requested under **either** reading, with the readiness package stating both consequences side by side (as this document now does) and the CRO/Owner accepting the ambiguity as a recorded, open condition rather than resolving it. | Fastest path; leaves a standing, named governance debt rather than closing it — consistent with the corpus's own "record inconsistencies rather than resolving them" discipline (ADR-L1-008), but only if explicitly chosen, not defaulted into. |

### 1.5 Recommendation

**Option 1b**, with low confidence, offered as a recommendation only — not adopted here. Reasoning: it is the
reading `CUSTODY_AMENDMENT.md` itself uses for the one case (row 9, Hypothesis) where it states its intent
unambiguously, and it preserves §3.4's plain text rather than silently overriding it via an inference chain (row
6's "resolves to" wording is genuinely weaker evidence than row 9's explicit "orthogonal, no collision"). Option
1a is the more conservative/safer reading if the Owner prioritizes never letting an unfingerprinted dataset be
called DECLARED. **This document does not choose between them — §5 carries this forward as the first item of the
consolidated decision surface.**

---

## 2. Phase 2 — DATA_FEASIBILITY_STUDY.md refresh — COMPLETE

Applied directly to the working tree (not committed), per the document's own footer rule ("re-run the inventory
query… whenever a provider or table changes") — a routine Data-Engineer-level correction of a stale measured
fact, not an Owner/CRO decision:

- §3 `broker_flow` row: `872k rows / 2026-04-01 → present (~3.5 mo) / 871 tickers` → **`3.00M rows / 2025-01-02 →
  2026-09-08 (~20 mo) / 872 tickers`** [DB-VERIFIED, this session], with an explicit caveat that density is
  tiered/uneven across the full 958-ticker active universe (D-032) and this row states calendar span, not
  uniform per-ticker depth.
- §3 `bandar_detector` row: `36k rows / 2026-04-01 →` → **`102.9k rows / 2025-01-02 → 2026-09-08`**
  [DB-VERIFIED].
- §4.1 informed-flow/adverse-selection proxy caveat: `"Only ~3.5 mo"` → corrected span, with the same
  tiered-density caveat and a pointer to Dataset A as the one fully-reconciled subset.
- §5.3: the `~3.5 mo` figure for `broker_flow` in the short-history list is corrected/removed, but **the
  history-maturity-gate judgment itself is explicitly left open** — corrected calendar span is not asserted to
  clear the gate; that determination is flagged as a Research-Architect/CRO call, not resolved here.
- **`capability_class` was not touched** — still CRO-gated, per mission instruction.

Diff available via `git diff docs/governance/DATA_FEASIBILITY_STUDY.md` (uncommitted).

---

## 3. Phase 3 — Receipt closure, R-1…R-10 and F-1…F-5

Original definitions: `BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md` §J.1/§J.2. Re-audited against
D-032…D-035 now persisted, and against fresh [DB-VERIFIED] evidence gathered in this pass (R-3/R-4/R-5 below).

| # | Receipt | Status now | Canonical/External | Blocks DECLARED? | Blocks FINGERPRINT? | Blocks FREEZE? | Required action |
|---|---|---|---|---|---|---|---|
| **R-1** | Persisted Owner authorization receipt for the data-layer backfill | **OPEN** — D-032/D-033 record the Owner's decisions but no separate canonical authorization artifact exists | External | **Yes** | Yes | Yes | Owner/CRO ruling: does D-032+D-033 (now persisted) *constitute* R-1, or is a separate artifact required? (§5) |
| **R-2** | Backfill completion receipt — exact invocation and scope | **SATISFIED at evidence level** — this session's reconciliation traced the backfill to an exact accounting identity (30,652 = 24,109 + 144 + 6,399, FULLY RECONCILED) using log + DB cross-verification | Session evidence, recorded in D-035; no separate artifact file | No | No | No | None — recorded in D-035; optional future: a dedicated evidence-package file if the Owner wants R-2 as a standalone artifact |
| **R-3** | Pinned IDX80 roster — source query, timestamp, hash | **CLOSED this session** — see §3.1 below | [DB-VERIFIED] | No (was blocking `point_in_time`) | No | Partial (roster hash is a fingerprint input) | None |
| **R-4** | Production boundary verification receipt, incl. 2026-08-25 zero-row check | **CLOSED this session** — see §3.2 below, Dataset-A-exact-scoped (roster × window × exclusion), stricter than the admission draft's ungoverned version | [DB-VERIFIED] | No | No | No | None |
| **R-5** | Lot-sign evidence receipt | **CLOSED this session** — see §3.3 below, re-derived fresh and Dataset-A-exact-scoped | [DB-VERIFIED] | No | No | No | None |
| **R-6** | P1/P2 provenance resolution receipt | **CLOSED** — H-7C/D-034 resolves this by splitting, not merging; Dataset A membership is defined extensionally by (roster × window × exclusion), which the H-6 investigation proved is structurally disjoint from any other write path (composite PK + gap-gated writers) — no provenance tag is needed to disambiguate membership | [CANONICAL] — D-034 | No | No | Partial — `provenance_hash` scope declaration (F-1) still needs to state this explicitly | None for DECLARED; carry the reasoning into F-1's fingerprint-scope declaration |
| **R-7** | CRO `capability_class` receipt | **OPEN — CRO only** | External | **Yes** | No | No | CRO decision (§5) |
| **R-8** | Updated DATA_FEASIBILITY_STUDY, resolving the stale-inventory discrepancy | **CLOSED this session** — Phase 2 above | [DB-VERIFIED] + working-tree edit | No | No | No | None |
| **R-9** | Dataset ID / registry ruling | **CLOSED at interim tier** — Owner already accepted the interim non-canonical ID (H-5, per mission's own COMPLETED list); full registry machinery remains a separate, non-blocking future item | [OWNER] | No | No | Yes (a real registry ID would be needed before FROZEN under most readings) | None for DECLARED |
| **R-10** | D-032/D-033(+H-2…H-6) decision persistence | **CLOSED at working-tree tier** — D-032…D-035 all present in `DECISION_LOG.md`, same working-tree-only status D-033 itself already accepted as satisfying R-10 | [CANONICAL] (uncommitted) | No | No | No | Branch commit remains outstanding but is explicitly non-blocking per D-033's own precedent |

**Net effect: R-1 and R-7 are the only remaining DECLARED-blocking receipts, and both are Owner/CRO-only.**
R-2/R-3/R-4/R-5/R-6/R-8/R-9/R-10 are now closed or satisfied without requiring Owner/CRO action.

### 3.1 R-3 receipt — Pinned IDX80 roster

```
Query:    SELECT ticker FROM idx_tickers WHERE status='active' AND in_idx80=1 ORDER BY ticker;
Executed: 2026-09-09, read-only, data/walkforward.db
Count:    79
SHA-256:  7d4eb1004e7d1e83153eede9a5d4e458ab5298ac1a4a4d7fa301f095f665eee0
Roster:   AALI,ACES,ADRO,AKRA,AMMN,AMRT,ANTM,ARTO,ASII,BBCA,BBNI,BBRI,BBTN,BBYB,BMRI,BNGA,BREN,BRIS,BRPT,BSDE,
          BTPS,BUKA,CMRY,CPIN,CTRA,DNET,EMTK,ERAA,ESSA,EXCL,GGRM,GOTO,HMSP,HRUM,ICBP,INCO,INDF,INKP,INTP,ISAT,
          ITMG,JPFA,JSMR,KAEF,KIJA,KLBF,LINK,LPPF,LSIP,MAPI,MBMA,MDKA,MEDC,MIKA,MNCN,MTEL,MYOR,NCKL,NISP,PANI,
          PGAS,PGEO,PNBN,PTBA,PTPP,PWON,RAJA,SCMA,SIDO,SMGR,SMRA,TBIG,TINS,TKIM,TLKM,TOWR,TPIA,UNTR,UNVR
Point-in-time note [DB-VERIFIED]: MIN(updated_at) = MAX(updated_at) = 2026-04-27T11:57:40.101066 across every
  row of this roster — the in_idx80 flag was last touched in a single batch operation on that date, well before
  the 2026-08-27–29 backfill campaign. This confirms the roster the backfill would have queried live is
  identical to the roster queried by this receipt today; "current-at-backfill-time" and "current-today" coincide
  for this specific roster.
```

### 3.2 R-4 receipt — Production boundary verification (Dataset A exact scope)

```
Scope: broker_flow JOIN idx_tickers ON ticker, status='active' AND in_idx80=1,
       trade_date BETWEEN '2025-01-02' AND '2026-08-27'
Executed: 2026-09-09, read-only, data/walkforward.db

Row count (excl. 2026-08-25):        1,222,713
MIN(trade_date) / MAX(trade_date):   2025-01-02 / 2026-08-27
Distinct tickers present:            79  (= full roster; none missing entirely)
2026-08-25 row count, roster-scoped: 0   (exclusion confirmed clean)
```

This is strictly more precise than the admission draft's original §I queries, which were not universe-scoped.

### 3.3 R-5 receipt — Lot-sign evidence (Dataset A exact scope)

```
Scope: same as §3.2. Executed 2026-09-09, read-only.

side  rows     neg_lot  zero_lot  pos_lot  min_lot      max_lot     neg_lot_value
BUY   633,817  757      3,700     629,360  -8,925       49,173,306  0
SELL  588,896  575,111  11,963    1,822    -46,827,346  43,249      0
```

Confirms, Dataset-A-scoped and DB-VERIFIED (previously only [EXT-PROD] at the full-table level in the admission
draft): `lot` is empirically signed (BUY predominantly positive — 99.3%; SELL predominantly negative — 97.7%),
`lot_value` is non-negative throughout (0 negative rows either side). The `lot=0 ∧ lot_value>0` population
(3,700 BUY + 11,963 SELL rows in this exact scope) remains **[UNRESOLVED]** — no explanation is offered, per the
admission draft's own discipline against inventing one.

### F-1…F-5 (FROZEN-gate prerequisites — status only, not actioned; Phase 7 is not started)

| # | Item | Status |
|---|---|---|
| F-1 | `broker_flow` fingerprint scope/mechanism | Still none exists. R-6's resolution (§3 above) supplies the scope argument a future fingerprint declaration would need to state (CU-15) — not itself a fingerprint |
| F-2 | Formal IDX80-scoped coverage audit receipt via the D-032 completion predicate | Effectively satisfied by this session's FULLY RECONCILED classification (D-035), but not yet re-expressed as a standalone formal receipt using `broker_cell_complete()` output directly |
| F-3 | `corporate_actions_applied` verification | Not established — unchanged |
| F-4 | Production consumer-formula audit | Unscheduled — unchanged, non-blocking per the admission draft |
| F-5 | `regime_classification` assessment | Not performed — unchanged, not invented |

---

## 4. Phase 4 — O4 field closure (RESEARCH_OBJECT_SCHEMA §3.4)

| Field | Value | Evidence | Class | Status |
|---|---|---|---|---|
| `dataset_id` | `DS-broker_flow-idx80-nonpit-2025_2026v1` | H-5 Owner acceptance of interim string | [OWNER] | DERIVABLE (interim, non-canonical) |
| `asset_class` | Not established in this session — no canonical asset-class taxonomy for O4 was located in the corpus | — | — | **UNRESOLVED** — not invented |
| `resolution` | Daily, broker-level; one row per (ticker, trade_date, broker_code, side) | `stockbit_fetcher.py:590-604` schema | [CANONICAL] | VERIFIED |
| `regime_classification` | Not assigned | No `regime_profiles` entry exists for this dataset; O15 Regime lifecycle (`DEFINED→DECLARED→APPLIED`) never entered for it | — | **PENDING** — not invented; whether mandatory-before-DECLARED is itself part of the §1 ambiguity |
| `provenance_hash` | Not computed | No function fingerprints `broker_flow` (F-1 open) | — | PENDING (correctly gated at FINGERPRINTED under §3.4's literal text) |
| `capability_class` | Not formally assigned to this O4 instance | DATA_FEASIBILITY_STUDY §4.1 already lists `broker_flow` under "Available Today" as an informed-flow/adverse-selection proxy — the *category* is indicated, the *formal CRO approval act* for Dataset A specifically has not occurred | [CANONICAL] (category) / [OWNER-PENDING] (approval act) | **PENDING — CRO (R-7)** |
| `fidelity_limit` | Cannot distinguish: (a) historical IDX80 membership as-known-then — Dataset A is explicitly retrospective/current-roster, not PIT; (b) P1/P2 row provenance by inspection (no `source` column; resolved extensionally, §3 R-6); (c) `lot=0 ∧ lot_value>0` semantics; (d) cause of the 2026-08-25 gap | Derived from §3 R-3/R-4/R-5 and the H-6 investigation | [DB-VERIFIED] + [PROPOSED synthesis] | DERIVABLE |
| `proxy_for` | Informed-flow / adverse-selection proxy — proxy tier, not true OFI | DATA_FEASIBILITY_STUDY §4.1 | [CANONICAL] | DERIVABLE (final mechanism-level assignment still belongs to the hypothesis that later binds this dataset) |
| `point_in_time` | **NO** for any index-composition-dependent interpretation — confirmed by §3.1's roster-timestamp receipt (roster fixed since 2026-04-27, applied uniformly and retrospectively across the full 2025-01-02→2026-08-27 window) | [DB-VERIFIED] R-3 | [DB-VERIFIED] | VERIFIED (the negative/limitation claim is now fully evidenced, closing what the admission draft left OPEN) |
| `corporate_actions_applied` | Not established | No evidence gathered this session either | — | UNRESOLVED (F-3 open) |
| `custody_partition` | Not assigned | No partitioning act has occurred (T-C3 not exercised) | — | N/A pre-DECLARED — assignment is a later governance act per the admission draft |

**Two fields now genuinely closed this session that were OPEN in the admission draft:** `point_in_time`'s
composition-dependent limitation (was "OPEN/PENDING," now VERIFIED with a hard receipt) and the provenance
elements' "Retrieval/backfill execution timestamps" line (now covered by R-2's FULLY RECONCILED evidence,
D-035). **Nothing else changed status** — no field was upgraded by assertion; `asset_class`, `regime_classification`,
`provenance_hash`, `capability_class`, `corporate_actions_applied`, and `custody_partition` remain exactly as
open as the admission draft left them, because no new evidence bearing on them was available or gathered.

---

## 5. Phase 5 — Consolidated Owner/CRO decision surface

**One request, not a sequence of small questions.** Everything below genuinely requires human authority; nothing
in Phases 1–4 was left open by oversight.

| # | Decision | Options | Blocks |
|---|---|---|---|
| **D-1** | **DECLARED vs REGISTERED lifecycle resolution** (§1) — does O4's `DECLARED` mean `CUSTODY_MODEL`'s `REGISTERED` (fingerprint required first), or an orthogonal claim-readiness state that can precede fingerprinting (as ruled for Hypothesis, `CUSTODY_AMENDMENT` row 9)? | 1a / 1b / 1c / 1d (§1.4) | **BLOCKS DECLARED** — the criteria for the DECLARED request itself differ under each reading |
| **D-2** | **`capability_class` formal approval** (R-7) — CRO assigns a value for Dataset A. `DATA_FEASIBILITY_STUDY` §4.1 already indicates the category (Available Today, informed-flow/adverse-selection proxy tier); this is the formal act of approving it for this specific O4 instance | Approve as indicated / approve with modification / defer | **BLOCKS DECLARED** |
| **D-3** | **R-1 authorization-receipt sufficiency** — does the now-persisted D-032/D-033 (Owner decisions, DECISION_LOG) constitute R-1's required "persisted Owner authorization receipt," or is a separate canonical artifact still required? | D-032+D-033 sufficient / separate artifact required | **BLOCKS DECLARED** |
| **D-4** | **History-maturity-gate determination for `broker_flow`** (DATA_FEASIBILITY_STUDY §5.3, corrected span ~20 mo, tiered density) — is the gate now cleared, in whole or for Dataset A's fully-reconciled IDX80 subset specifically, or does it remain open pending a full-universe density reassessment? | Cleared for Dataset A only / cleared broadly / remains open | **NON-BLOCKING for DECLARED** (DECLARED does not require the gate cleared per §3.4's literal text) but **blocks any future hypothesis** binding this dataset at G1 |
| **D-5** | **Branch commit of D-032…D-035 and this session's DATA_FEASIBILITY_STUDY correction** | Commit now / hold uncommitted | **NON-BLOCKING** — working-tree persistence already accepted as sufficient for R-10 per D-033's own precedent |

**D-1, D-2, D-3 are the three items that actually block DECLARED.** D-4 and D-5 are recorded for completeness
and do not block DECLARED itself.

---

## 6. Worktree note

This artifact and the Phase 2 edit to `docs/governance/DATA_FEASIBILITY_STUDY.md` are the only files this
mission's Phases 1–5 touched. Neither is committed. `docs/roadmap/DECISION_LOG.md` (D-034/D-035) was applied in
the immediately preceding turn, also uncommitted. No production code, schema, or `data/walkforward.db` content
was modified at any point.
