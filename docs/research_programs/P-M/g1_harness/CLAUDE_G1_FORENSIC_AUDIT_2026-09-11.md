# CLAUDE G1 FORENSIC AUDIT, CLASSIFICATION & GOVERNANCE REPAIR PLAN — 2026-09-11

**Authority:** point-in-time forensic record. Not canonical, not an amendment, not a registration.
Supersedes nothing. Makes no governance decision.
**Mode:** READ-ONLY. No alpha test, no G1 rerun, no C7/C6/C8 execution, no parameter tuning, no
methodology change, no Dataset B modification, no rescue specification, no alteration of any
historical result or artifact. All database access `mode=ro` + `PRAGMA query_only`.
**Reviewer:** Claude (Opus 5) · **Branch:** `ops/hardening-2026-07-10`
**Predecessor:** `CLAUDE_INDEPENDENT_REVIEW_G1_C7_2026-09-11.md` (findings F-1…F-11). This document
verifies and classifies F-1 to F-4 and **corrects one of them** (see §3.5).

**Evidence convention.** `[measured]` = my own read-only computation, reproducible, formation-side
only. I computed **no forward returns, no θ, no t-statistic and no p-value**, and per instruction I
did **not** recompute C1a/C1b statistics. Everything else is cited to a repository artifact by path
and line.

**Snapshot warning.** The audited directory was being written by another agent *throughout* this
audit (§8). All hashes and file states below are as of **2026-09-11 10:50 WIB**.

---

## 1 · C2 FORENSIC

### 1.1 Exact registered formula

`G1_REGISTRATION_v1_2026-09-11.md` §4, verbatim:

> for_net = (Σ Asing buy − Σ Asing sell)/gross; loc_net symmetric; for_gross = (Σ Asing |value|)/gross;
> loc_gross symmetric.
> **Disagreement state:** for_gross ≥ 0.15 **AND** loc_gross ≥ 0.15 **AND** sign(for_net) ≠ sign(loc_net).
> Daily spread: mean fwd-return of long-foreign (for_net>0, loc_net<0) − mean fwd-return of
> short-foreign (for_net<0, loc_net>0).

### 1.2 Exact executed formula

`g1_harness.py:344-347` (panel) and `:478-485` (cell):

```python
"for_share":       (a["for_buy"] - a["for_sell"]) / gross
"loc_share":       (a["loc_buy"] - a["loc_sell"]) / gross
"for_gross_share": (a["for_buy"] + a["for_sell"]) / gross
"loc_gross_share": (a["loc_buy"] + a["loc_sell"]) / gross
...
f_ok = r["for_gross_share"] >= 0.15;  l_ok = r["loc_gross_share"] >= 0.15
if not (f_ok and l_ok): continue
if   r["for_share"] > 0 and r["loc_share"] < 0: long_f.append(fr)
elif r["for_share"] < 0 and r["loc_share"] > 0: short_f.append(fr)
```

**Finding: registration and implementation AGREE exactly.** The defect is not a coding error against
the registration. It is that the registration itself codifies a condition that is degenerate on the
data it was executed against, and a gate that differs from the one under which the supporting
evidence was generated.

### 1.3 Broker-flow net identity at limit=150

**[measured]** — frozen store `broker_flow_b`, RAJA excluded, 30,624 ticker-days:

```
|Σ BUY value − Σ |SELL value|| / gross
    p50 = 0.00e+00    p90 = 0.00e+00    p99 = 0.00e+00    max = 0.00e+00
    exactly zero on 100.00% of ticker-days
```

Store sign convention verified independently: **all 802,352 BUY rows positive, all 716,375 SELL rows
negative** [measured], so `gross = buy_v + |sell_v|` is correctly formed and the identity is not an
artifact of sign handling.

This is the exchange identity (every trade is simultaneously a buy and a sell), which top-25
truncation previously masked. It was **already on the record before execution**:

- `g1_harness.py` module docstring, line 26: *"At limit=150 broker_flow net is identically zero
  (2026-09-10 trial)."*
- `ZCODE_ALPHA_DISCOVERY_FAMILY_MAP_2026-09-10.md` §3: *"**broker_flow net flow is structurally
  ~zero** … Consequences: 1. **No candidate may use broker_flow net as a signal or control** — it is
  mechanically ~0."* Family **G** was marked **BLOCKED BY DATA** on exactly this basis.

### 1.4 Is the C2 condition therefore tautological?

**Yes. Proven, not inferred.**

Since `for_net + loc_net ≡ (Σbuy − Σ|sell|)/gross ≡ 0` for every ticker-day, `loc_net ≡ −for_net`.
Therefore `sign(for_net) ≠ sign(loc_net)` **whenever either is non-zero**.

**[measured]:** both non-zero on 30,624 / 30,624 ticker-days; opposite-signed on
**30,624 / 30,624 = 100.00%**.

The registered "disagreement" condition carries **zero information**. The only operative part of the
C2 filter is the pair of ≥15% gates, and the long-F / short-F split reduces exactly to `sign(for_net)`.

**A second, independent deviation compounds this.** The descriptive generator that produced C2's
supporting evidence gates on **|net|**, not on gross participation —
`ZCodeProject/pm_data_audit/12_discovery_structures.py:122`:

```python
if v["asing"] * v["lokal"] < 0 and abs(v["asing"]) > 0.15 * g and abs(v["lokal"]) > 0.15 * g:
```

`abs(net) > 0.15·gross` is a demanding magnitude condition. `for_gross_share ≥ 0.15` is a turnover
participation condition that nearly every liquid name satisfies. **[measured]** on Dataset B:

| Gate | Source | Incidence on Dataset B |
|---|---|---|
| **EXECUTED** — gross-participation ≥ 15% | `g1_harness.py:478-480`, registration §4 | **30,176 / 30,624 = 98.5%** |
| Descriptive generator — \|net\| > 15% of gross | `12_discovery_structures.py:122` | 14,237 = 46.5% |
| Descriptive generator + memo's Lokal-only taxonomy | memo §5 three-way ownership | 8,161 = **26.6%** |
| *Dataset A reference* | `discovery_structures.json` | *30.2%* |

The gate swap — not the dataset change — is what made the filter non-binding. Ported faithfully, the
state would have fired on 26.6% of Dataset B name-days, close to the 30.2% measured on Dataset A. It
was **portable**; the implementation did not port it.

### 1.5 Does the reported C2 state correspond to Dataset A rather than Dataset B?

**Yes, as to its justification.** Traced to source:

- `discovery_structures.json` → `class_disagreement.share_of_days = 0.30207275435491204`,
  `n_ticker_days = 103389`.
- Generator `12_discovery_structures.py:32,133` reads production **`broker_flow`** — the top-25-per-side
  **Dataset A** table.

So the 30.2% incidence that motivated C2 is a **Dataset A** measurement on a **different gate**. The
state definition was never re-validated on Dataset B before execution, and on Dataset B its sign
condition is vacuous and its magnitude gate non-binding.

### 1.6 Classification of C2

**INVALID — not FAIL.**

The executed estimand is:

> mean forward return of names with `for_net > 0` − mean forward return of names with `for_net < 0`,
> over ~98.5% of the panel

— i.e. a **foreign-broker net-flow sign contrast**, on a surface owned by the closed foreign-flow
H1/H6 line. The registered conduit-disagreement mechanism has **zero variation on Dataset B and was
never tested**. A statistical verdict of "not confirmed" cannot be attached to a mechanism whose
conditioning event did not occur — or rather, occurred identically everywhere.

C2 cannot legitimately be classified FAIL. It must be INVALID.

---

## 2 · C1a / C1b WITHDRAWAL

Verified against the preserved raw output `G1_REAL_OUTPUT_RUN1_2026-09-11.json`
(sha256 `74883c04cf80a867…`, hash-verified intact).

| Question | C1a | C1b |
|---|---|---|
| **Was it executed?** | **YES.** `run_g1` calls `cell_c1a(panel, k, kept)` **unconditionally** at `g1_harness.py:821`, inside the `for k in KS` loop, before any withdrawal check. The withdrawal branch at `:832-842` runs *afterwards* and only overwrites fields | **NO.** No C1b cell exists in the code or the output. `run_g1` appends only C1a, C2, C3 (`:821-823`). C1b was **never implemented** |
| **Were statistics produced?** | **YES.** θ_mean, NW t, n_days, p and `theta_net_cost_floor` were all computed. Three fields (`theta_mean`, `nw_t`, `p`) were then set to `null`; **`n_days` and `theta_net_cost_floor` were not** | No |
| **Were daily series produced?** | **YES.** `theta_t` present with **152 / 148 / 142** dated entries for k = 3 / 5 / 10, plus a `detail` block of **190 / 185 / 179** entries carrying `date`, `bucket`, `n_top`, `n_bot`, `contrast` | No |
| **Did any value enter the reported result?** | **NO.** C1a is excluded from the Holm family by the `status == "COMPUTED"` filter (`:849-850`); it carries no `holm_p`, no verdict, and every narrative document reports it as WITHDRAWN | No |

### 2.1 Comparison against the registered withdrawal requirement

`G1_REGISTRATION_v1` §1: C1a/C1b *"**Never executes** while the withdrawal is in force
(`freq_resolution="withdrawn"` → `WITHDRAWN_FREQ_DEPENDENT`, **no numbers**)."*

**The requirement was not met on either clause.** The arm executed, and numbers exist in the
preserved artifact. `theta_net_cost_floor` is published as `θ_mean − 0.006`, so θ_mean is recoverable
by adding 0.006; the full daily series is present verbatim, so the withdrawn arm's inference is
reconstructible by anyone. **Per instruction, I have not recomputed its t or p, and this document
publishes neither.**

Two collateral errors:

- `G1_FINAL_EXECUTION_REPORT` §D: *"All six C1a/C1b cells (3 horizons × 2 arms) emitted
  WITHDRAWN_FREQ_DEPENDENT … No substitute results were computed."* **Three** cells exist, not six —
  the report asserts verification of three cells that do not exist. (The error is in the *safe*
  direction: C1b genuinely never ran.) And numbers *were* computed.
- `test_g1_harness.py:197` `test_withdrawn_arms_represented_and_holm_shrinks` has the docstring
  *"…with **no numbers** regardless of gates"* but asserts only `theta_mean is None and p is None`.
  The test certifies the leak.

### 2.2 Classification

- **C1a — INVALID / NON-REPORTABLE.** Executed in violation of its own registered withdrawal; its
  outputs must not be read, cited, quoted, or used to motivate any successor hypothesis.
- **C1b — WITHDRAWN (never implemented).** No execution occurred. Nothing to invalidate.

**Containment note, recorded deliberately.** So that the recoverable C1a values cannot mislead a
later reader: the preserved `detail` block shows C1a's daily contrasts are built on a **median of one
name per leg**, with a singleton on at least one side in **97%** of bucket-cells, across only 148 of
375 formation dates [measured from the artifact]. Whatever the arithmetic yields, it is the
difference between two individual stocks' returns. It is not a finding and cannot become one.

---

## 3 · PROVENANCE FORENSICS

### 3.1 Hash ledger (as of 2026-09-11 10:50 WIB)

| Item | Value | Status |
|---|---|---|
| **Code at execution** | `9471c740175b313582bf01b8dd86b6394985bd767f12f614b03d8b788df103f4` (manifest self-report) | **UNVERIFIABLE** — see §3.4 |
| **Config at execution (raw bytes)** | `7211ad94c44614f2…` | **VERIFIED by reconstruction** — §3.3 |
| **Config at execution (canonical JSON)** | `25114b9c7493f1be…` (self-recorded inside the output) | **VERIFIED by reconstruction** — §3.3 |
| **Output** | `74883c04cf80a867…` | **INTACT** — matches manifest; `g1_real_output.json` and `G1_REAL_OUTPUT_RUN1_2026-09-11.json` byte-identical |
| **Run manifest** (current) | `18b50a45109c2c63…` | Not pinned anywhere; no integrity anchor |
| **`foundation.py`** | `e427cc482fa1e00c…` | **MATCHES** manifest pin |
| **Current code** | `91ecf6d060e064b0…` | ≠ execution pin |
| **Current config (raw / canonical)** | `89ff2b463b382018…` / `b1099dbb284d1ea1…` | ≠ execution pins |

### 3.2 What changed, and exactly when

| Time (WIB) | Event |
|---|---|
| 09:31:18 | G1 executed (`executed_at_utc 2026-09-11T02:31:18Z`, exit 0) |
| 09:32:24 | `g1_real_output.json` written |
| 09:34:09 | Preserved copy `G1_REAL_OUTPUT_RUN1_2026-09-11.json` |
| 09:34:12 | `G1_RUN_MANIFEST_RUN1_2026-09-11.json` |
| 09:35:12 | `G1_FINAL_EXECUTION_REPORT_2026-09-11.md` |
| **10:35:05** | **`g1_harness.py` modified** — C7 path added (`C7_HIGH_THRESHOLD`, `c7_build_panel`, `cell_c7`, `run_c7`, `main_c7`) and `load_real_bundle` signature changed to accept `required_gates` |
| **10:35:17** | **`g1_config.json` modified** — `"c7_registered": false` added; `__pycache__/g1_harness.cpython-312.pyc` overwritten the same second |
| 10:42:58 | `test_c7_registration.py` created |
| 10:44:01 – 10:45:15 | Three C7 documents rewritten; C7 status flipped DRAFT → **REGISTERED — owner-approved** |

### 3.3 Config: RECONSTRUCTED AND DOUBLY VERIFIED

Deleting exactly the entry `"c7_registered": false` (with its preceding comma) from the current
`g1_config.json` reproduces **both** recorded hashes exactly [measured]:

```
reconstruction raw sha256      = 7211ad94c44614f2…   == manifest pin                 ✓
reconstruction canonical sha256 = 25114b9c7493f1be…   == output's self-recorded value ✓
```

**Consequences, all favourable:**

- The executed config is **fully and unambiguously reconstructed**.
- The only post-run config change is the addition of a key the G1 code path **never reads**
  (`c7_registered` is consulted only by `run_c7`/`main_c7`). The mutation is provably inconsequential
  to the G1 result.
- The two differing hash values are **not a contradiction**: the manifest records the raw-file sha256;
  `load_config` records the canonical-JSON sha256. Both were correct.

### 3.4 Code: NOT RECONSTRUCTIBLE

Exhaustive search for any surviving copy of the executed `g1_harness.py` [measured]:

| Location | Result |
|---|---|
| Filesystem-wide (`find /` for `g1_harness.py*`) | Only the single mutated file |
| `/home/tjiesar`, `/tmp`, `/var/tmp` copies outside the harness dir | None |
| Editor artifacts (`*~`, `.orig`, `.bak`, `.swp`, `.tmp`) | None |
| `__pycache__/g1_harness.cpython-312.pyc` | **Overwritten at 10:35:17** — bytecode of the executed version gone |
| Git | Directory is **untracked** (`??`); `git log --all` for the path returns nothing — never committed |

The manifest's `9471c740…` is therefore an **unverifiable self-assertion**: a claim recorded by the
same process, with no surviving artifact to check it against and no independent corroboration.

Per instruction I did **not** attempt to construct a file that hashes to the pin. I note only, as an
inference and explicitly **not** as proof, that the 10:35 edits appear structurally additive to the
G1 path — the C7 functions are new, and the one in-path edit (`load_real_bundle(cfg,
required_gates=None)`) defaults to the prior four-gate behaviour. Behavioural equivalence by
inspection is not hash identity and cannot substitute for it.

### 3.5 Verdict — and a correction to the predecessor review

> ### **EXECUTION PROVENANCE NOT IMMUTABLY ESTABLISHED** — for the **executed code only**.

**Correction to `CLAUDE_INDEPENDENT_REVIEW_G1_C7_2026-09-11.md` F-3.** That review stated that the
config hashes were broken and that the manifest's `config_sha256` "was never the value the run
stamped". Forensics disproves the second clause and materially softens the first: **the config is
reconstructed and doubly hash-verified, the manifest pin was correct, and the only change is inert
for G1.** The finding stands only for the code, and only there.

**Output integrity is unaffected.** `74883c04…` verifies, in two byte-identical copies. The *result*
is intact; what cannot be established is the *instrument* that produced it.

---

## 4 · REGISTRY / MULTIPLICITY

### 4.1 What was inspected

`HYPOTHESIS_REGISTRY.md` · `FAILURE_REGISTRY.md` · `roadmap/DECISION_LOG.md` ·
`ZCODE_ALPHA_DISCOVERY_FAMILY_MAP_2026-09-10.md` · `G1_REGISTRATION_v1_2026-09-11.md` ·
`C7_REGISTRATION_v1_2026-09-11.md` · `research_os/MARKET_INEFFICIENCY_TAXONOMY.md`.

### 4.2 Findings

**G1 is absent from the Hypothesis Registry.** The registry contains exactly two P-M entries —
HYP-PM-0001 (FAILED F2) and HYP-PM-0003 (FAILED F2). There is no HYP-PM-0004, no BFI-002 row, and no
row for C1a/C1b/C2/C3. The declared P-M family is `{I5, I6, I7, I12}` with **2 consumed slots**.

**G1 is absent from the Decision Log.** `DECISION_LOG.md` runs to **D-047** (2026-09-09). It contains
**no entry** for BFI-002, the G1 replacement registration, the C1a/C1b withdrawal, the NF
ratification, the Dataset B freeze as a research object, or the C7 registration. D-034/D-043 govern
*dataset admission* (Dataset A/B as O4 candidates), not hypothesis registration. The most recent
entries pre-date all the G1 work by two days.

Under Decision-Making Hierarchy rule 5, `DECISION_LOG.md` is **the register of record** and a decision
is authoritative only once accepted there. **None of the G1 or C7 governance acts are currently
authoritative.**

**The registry's own rule names the breach.** `HYPOTHESIS_REGISTRY.md` line 3: *"A hypothesis is
counted in its program's multiplicity family **from G1/REGISTERED and never leaves** (PG-3, OS-10)."*
Here "G1" is **Gate 1** — the registration gate. The BFI-002 experiment has appropriated the same
label for an unrelated object (see §4.3).

**The family mapping was never performed.** `{I5, I6, I7, I12}` are, per
`MARKET_INEFFICIENCY_TAXONOMY.md`: I5 inventory-imbalance liquidity premium · I6 illiquidity premium ·
I7 adverse-selection premium · I12 capacity-shielded deviation. No document anywhere maps C2
(ownership-conduit), C3 (participation/consensus breadth) or C7 (turnover-intensity state) onto any
of these entries. For C7 the mismatch is visible on its face: it is an execution/liquidity state
whose own evidence records *"flat baselines across liquidity terciles"*, which argues against an I6
illiquidity reading. **Whether these indicators fall inside `{I5,I6,I7,I12}` or require a widening
amendment is an owner/CRO determination, and it has never been made.** Per PG-3/PG-6/R7.5 and D-028 a
declared family is append-only and monotonic and may be widened only by formal amendment.

**Net effect:** G1 ran a multi-arm return test on the P-M corpus and consumed **zero** inferential
slots. `G1_POSTMORTEM_FAMILY_TRIAGE` §C characterises this as *"Governance records owed … registry
bookkeeping"*. It is not bookkeeping — an uncounted trial is precisely the failure mode invariant #12
and the append-only family rules exist to prevent.

### 4.3 Label collision (unresolved, now actively harmful)

`TAXONOMY_AND_NAMING_STANDARD.md` reserves **G1–G4 for institutional Gates**, and the Hypothesis
Registry uses "G1" in exactly that sense. Three live meanings of "G1" now coexist: the institutional
Gate; the BFI-002 experiment audited here; and `S2-PM-0004_G1_RESULT.md`'s I3 preregistration gate.
The moment this experiment is appended to the registry under the name "G1", the register becomes
self-contradictory.

### 4.4 Governance decision required (stated, not made)

Two, in strict order:

1. **Family determination.** Do C2/C3/C7 fall within the declared P-M family `{I5,I6,I7,I12}`, or does
   the family require a formal widening amendment, or must a new declared family be opened for the
   broker-flow structure program? **Blocking for C7, C6 and C8 alike.**
2. **Retroactive counting.** Given the family determination, how many inferential slots does G1
   consume, and with what status per arm (§5)?

---

## 5 · CLASSIFICATION TABLE (proposed — for owner ratification, not self-adopted)

| Object | Classification | Reason | Primary evidence | Consumes an inferential slot? | Can support a scientific claim? |
|---|---|---|---|---|---|
| **C1a** | **INVALID / non-reportable** | Executed despite a registered withdrawal that says it "never executes … no numbers". θ, `n_days`, full daily series and per-bucket detail all preserved | `g1_harness.py:821` (unconditional call) vs registration §1; output retains `theta_t` 152/148/142 and `detail` 190/185/179 | **No** — withdrawn before execution, excluded from the Holm family | **No.** Doubly barred: registered withdrawn; and legs are a median of 1 name (97% singleton bucket-cells) |
| **C1b** | **WITHDRAWN** (never implemented) | No C1b cell exists in code or output; registered withdrawn and genuinely did not run | `run_g1` appends only C1a/C2/C3 (`:821-823`); zero C1b cells in the artifact | **No** | **No** |
| **C2** | **INVALID** (specification failure) | Registered state condition is an arithmetic tautology on Dataset B (100.00% of 30,624 ticker-days); and the 15% gate was swapped from \|net\| to gross-participation, taking incidence from 26.6% to 98.5%. Supporting evidence is Dataset A under the other gate | net ≡ 0 [measured]; `g1_harness.py:478-480` vs `12_discovery_structures.py:122`; `discovery_structures.json` n=103,389 on production `broker_flow` | **Yes, if the family is repaired** — a trial was run on the corpus and must count (X8 / anti-snooping). *Owner determination* | **No** as to conduit disagreement — that mechanism was never tested. At most an unregistered observation about foreign-net sign, on a surface owned by the closed foreign-flow line |
| **C3** | **VALID execution → NOT CONFIRMED** | Construct sound: count-based, cap-robust, not identity-constrained; real variation (18.9% broad / 20.5% narrow); healthy legs (median 14 v 16 names over 329 dates). Holm p = 1.0, signs +/+/−, −54 bp net of the 0.60% floor | Output cells; leg sizes [measured]; registration §4/§8 | **Yes** | **Yes, bounded:** "the breadth-surprise contrast **as registered** showed no confirmable forward-return effect at k∈{3,5,10} on Dataset B." **Not** "the breadth-surprise mechanism is refuted" — the registration's statistic diverged from the memo (expanding vs 60-obs median) and the executable NF-control clause was not run |
| **G1 overall** | **PARTIAL — not a clean FAIL** | Of the four registered arms: one valid and not confirmed (C3), one invalid (C2), one executed-in-breach and non-reportable (C1a), one never implemented (C1b). A family-level FAIL asserts the family was tested; **half the retained family was not** | §1, §2 above | **Per-arm** (see rows) | **Only C3's bounded claim.** No family-level claim about the BFI-002 mechanism set is supportable |

**Note on direction.** Every methodological deviation found in §1 and in the predecessor review runs
in the **permissive** direction — the executed tests were easier to pass than the designed ones. So
no arm's non-confirmation is an artifact of an error, and **nothing here is a rescue**. The
amendment changes what the ledger records, not what was concluded operationally.

---

## 6 · C7 IMPLICATION

**Material change during this audit:** at 10:44 `C7_REGISTRATION_v1_2026-09-11.md` was rewritten from
*"DRAFT — PENDING OWNER DECISIONS. NOT authorized for execution"* to **"REGISTERED — owner-approved"**,
with all six formerly-NOT-SET items resolved. The config gate `c7_registered` remains **false**, so
no execution is authorized. I did not run C7.

The six resolutions match, item for item, the parameters already hard-coded in `g1_harness.py` at
10:35 — return-based outcome, high-vs-non-high contrast, k∈{3,5,10} primary 5, single-cell Holm. The
implementation preceded the decisions by nine minutes. **Whether that sequence is acceptable is an
owner ruling, not mine**; I record only the timestamps.

### Assessment on the four requested axes

**C7's descriptive evidence.** P(next-day high | high) = 45.7–48.1% vs ~11.3% base. This is
**volume clustering** — a property of the *predictor*, not the outcome. No forward return was ever
computed for C7. Under `EVIDENCE_MODEL` rule U10 and ADR-L1-003 (mechanism-first is a gate), it
supports no claim about returns. The registration's own item 6 correctly confines these figures to
context — but then states the 2.0 threshold derives from *"the family-map/descriptive state
definition"*, which is the same descriptive pass (`family_passD_states.json`). The confinement and
the sourcing are in tension.

**Intensity ↔ breadth relationship — the decisive open item.**
`ZCODE_ALPHA_DISCOVERY_FAMILY_MAP` §5, verbatim: *"Intensity (gross/ADV) vs breadth/species: **not
yet fully crossed — flagged as the one remaining orthogonality check** (single correlation, no
search) **before BFI-002 freezing**."* This is ZCode's own pre-declared prerequisite. It is still
open. The C7 registration cites map rows D/H/K/I/L but **not §5**.

**Is C7 genuinely distinct from G1/C3?** Unproven. Intensity is not C3's statistic, and the freq-free
claim is genuine (verified: `c7_build_panel` and `cell_c7` never read `freq`; the new freq-poison
test is a legitimate strengthening). But with C3 now failed and C2 invalid, the question of whether
intensity partially re-tests the breadth surface is no longer academic — and the one measurement that
would answer it was declared mandatory eight days ago and never run.

**Can the prior descriptive result be used without selection bias?** On the *outcome* axis, yes — no
return was computed, so the threshold is not return-mined. That is real credit and I record it. On
the *calibration* axis, no: the registration cites `high_intensity_prevalence = 0.18109` as the basis
for the 2.0 cut, but **[measured]** on frozen Dataset B under the registered ADV20 convention
(median close×volume over the prior 20 sessions, shift(1)), over 28,866 name-days:

```
intensity = gross/ADV20 :  p10 0.36  p25 0.54  p50 0.86  p75 1.38  p90 2.20  p99 6.06
P(intensity ≥ 2.0) = 12.29%          registration claims 18.11%;  map claims p50 0.82 / p90 3.12
```

The registration attributes any drift to a 21→20 median-window change and calls it *"marginal"*. A
21→20 change cannot move 18.11% → 12.29%. **This is not a request to tune the threshold** — keeping
2.0 is fine. What cannot stand is citing 18.11% as the justification for a state that fires at
12.29% on the dataset it will execute against.

*(Separately verified so the threshold is not misjudged: `gross / (close × volume)` has p50 = 0.93
[measured], so intensity is a clean turnover-surge ratio and **not** a two-sided double-count. The
state is economically meaningful.)*

**Is the outcome axis sufficiently justified?** **No.** The family map classifies D/H as
**execution-type**; C7's entire evidence base is state persistence and next-day volume.
`FAILURE_REGISTRY.md` records the program-level pattern in its own words: *"all three mechanisms died
at short-to-swing horizons against the same 0.60% round-trip friction — a program-level pattern
(horizon/friction mismatch) that no single F-code expresses."* G1 is the fourth instance (all six
C2/C3 cells net −44 to −67 bp). A return-based C7 at k∈{3,5,10} needs θ > 60 bp per period against a
friction-anchored MDE; the largest gross effect observed anywhere across this program's structure
families is 16 bp. The owner has chosen the return outcome; that is their call. The forensic record
should carry the prior alongside it.

### Determination

> ## **B — C7 REMAINS PAUSED.**

Not A: two blockers are independent of the owner's §3 decisions and cannot be cleared by them —
(i) **no lawful multiplicity family exists** (§4), and (ii) the registered threshold's cited incidence
does not reproduce on the execution dataset (§6), a pre-specification defect inside the registration
itself. (iii) The map's own pre-declared orthogonality check is still open.

Not C (redesign): the owner has now registered the parameters; re-opening them is not mine to
propose. Not D (kill): the state is well-formed and economically meaningful, and C7 was pre-designated
a survivor on 2026-09-10, before the G1 result existed — it is not a retrofit.

The three blockers are cheap. None requires a research cycle.

---

## 7 · GOVERNANCE REPAIR PLAN

Smallest sequence before any further empirical test. **I make none of the decisions in group B.**

### A · Required forensic fixes (mechanical — no judgement, no new science)

| # | Action | Closes |
|---|---|---|
| A1 | **Commit `g1_harness/` to git as-is, now**, before anything else changes. The directory is untracked and actively mutating (§8) | F-3 exposure |
| A2 | **Record the config reconstruction** in the run manifest: executed config = current file minus `"c7_registered": false`; raw `7211ad94…`, canonical `25114b9c…`, both verified; the delta is inert for G1 | §3.3 |
| A3 | **Record the code-provenance loss explicitly** in the run manifest: "EXECUTION PROVENANCE NOT IMMUTABLY ESTABLISHED — executed `g1_harness.py` (`9471c740…`) is unverifiable; no copy survives; overwritten 2026-09-11 10:35:05." Do not manufacture a match. Apply a reproducibility (X-axis) downgrade to Run 1 | §3.4 |
| A4 | **Quarantine the C1a leak**: re-emit the preserved output with `theta_t` and `detail` removed from the three C1a cells and `theta_net_cost_floor`/`n_days` nulled — as a **new** file, recording the redaction and reason in the manifest. **Do not overwrite `G1_REAL_OUTPUT_RUN1_2026-09-11.json`**; both versions retained, the original sealed and marked non-reportable | §2 |
| A5 | **Fix the withdrawal mechanism**: move the `freq_resolution == "withdrawn"` check *before* `cell_c1a()` is called (`g1_harness.py:821`), and extend `test_g1_harness.py:197` to assert absence of **all** numeric fields including `theta_t` and `detail` | §2 |
| A6 | **Adopt one hashing convention** and label the two existing fields distinctly (`config_sha256_raw` / `config_sha256_canonical`). Both current values were correct; only the naming was ambiguous | §3.3 |
| A7 | **Per-run immutable artifact directory**: each future run copies its code + config into `runs/<run_id>/` at execution time rather than hashing mutable files in place | prevents recurrence |
| A8 | **Run the map's pre-declared orthogonality measurement**: `corr(intensity, breadth_surprise)` and `corr(intensity, ST)` on Dataset B. One correlation, explicitly "no search", declared mandatory 2026-09-10 (map §5). Descriptive, consumes no slot | §6 |

### B · Required governance decisions (owner / CRO only — I do not make these)

| # | Decision | Blocking for |
|---|---|---|
| B1 | **Family determination.** Do C2/C3/C7 fall inside `{I5,I6,I7,I12}`; does the family require a formal widening amendment; or must a new declared family be opened? | **C7, C6, C8 — everything** |
| B2 | **Ratify or amend the §5 classification table**, in particular: C2 as INVALID rather than FAIL, and C1a as INVALID/non-reportable | Ledger correctness |
| B3 | **Retroactive slot counting.** How many inferential slots does G1 consume, per arm, given B1 | Multiplicity integrity |
| B4 | **Amend the G1 verdict** from family-level FAIL to the split verdict (§5, §9D) | Register of record |
| B5 | **Authorize the A4 redaction** — it touches a preserved artifact and needs explicit sign-off under the preservation rule | A4 |
| B6 | **Rule on the C7 implementation-before-decision sequence** (code 10:35 → owner decisions 10:44): does it compromise the registration's independence? | C7 status |
| B7 | **Reconcile the C7 threshold provenance** — 18.11% cited vs 12.29% measured. Keep 2.0 with the corrected incidence recorded, or re-express as a quantile. **Not a tuning decision** | C7 execution |
| B8 | **Resolve the "G1" label collision** before anything is appended to the registry | Registry coherence |
| B9 | **Enter the G1 and C7 governance acts into `DECISION_LOG.md`** — none is currently authoritative (§4.2) | Register of record |

### C · Optional housekeeping

- C1 · Remove the dead `BREADTH_SURPRISE_WINDOW = 60` constant, or reconcile it with the expanding
  median actually used — three documents currently disagree.
- C2 · Correct `G1_FINAL_EXECUTION_REPORT` §D's "all six C1a/C1b cells" to three.
- C3 · Split the double-incremented `excluded_no_net_flow` counter; remove the dead
  `excluded_ca_at_t`; emit per-date leg sizes for every arm (their absence is why §4's power claim
  was unsupported at the time it was made).
- C4 · Correct the stale `provenance.net_flow_source = "PROVISIONAL, unratified"` label — the reason
  for retaining it (preserving the executed-code hash) no longer applies.
- C5 · Correct registration §6 exclusion 9 and `G1_FINAL_GOVERNANCE_STATUS` §5: "freq is never read"
  is false for C2/C3 (the species classifier reads it and gates row inclusion), though immaterial in
  Run 1 (0 rows dropped). It **is** true for C7.

---

## 8 · DIRECTORY OWNERSHIP

**Multiple agents are modifying the same files. Confirmed, not suspected.**

| Evidence | Detail |
|---|---|
| Second runtime | `zcode-cli` **PID 347269**, started 2026-09-10 20:04:18, **running 14h 46m** — the author of every G1/C7 artifact |
| Concurrent mutation during this audit | `g1_harness.py` + `g1_config.json` rewritten 10:35 *while* the predecessor review was reading and hashing them |
| Post-review overwrite | Three C7 documents rewritten 10:44:01–10:45:15, **1–3 minutes after** `CLAUDE_INDEPENDENT_REVIEW…md` was written at 10:44:02; C7 status changed DRAFT → REGISTERED |
| No protection | Directory **untracked in git**; no lockfile, no ownership marker, no `.gitignore` entry, no per-run isolation |
| Consequence | The artifact set audited at 10:35 no longer exists in that form. The executed harness was destroyed by a concurrent writer (§3.4) |

This is the **direct cause** of the only unrecoverable finding in this audit. The code loss was not
carelessness about hashing — it was two writers in one unversioned directory.

### Recommended ownership rule (simple, for the next phase)

1. **Single writer per directory.** `docs/research_programs/P-M/g1_harness/` is owned by **ZCode**.
   Review agents write **only** files matching `CLAUDE_*` and modify nothing else. (This audit
   complied; my two files are the only ones I have written.)
2. **Git before anything else.** Commit the directory now (A1). An untracked directory with two
   writers has no recovery path — as just demonstrated.
3. **Executed artifacts are immutable.** Once a run's output is preserved, its code and config are
   **copied** into `runs/<run_id>/` and never edited again. New work goes in a new file — the C7 path
   belongs in `c7_harness.py`, exactly as `C7_REGISTRATION_READINESS` §H originally specified.
4. **Freeze during audit.** While a review is open, the owned directory is read-only to its owner;
   the reviewer announces completion before writing resumes.

---

## 9 · CONCLUSIONS

### A · What is definitely valid

- **The G1 output artifact.** `74883c04cf80a867…` verifies, in two byte-identical copies. Intact.
- **The executed configuration.** Fully reconstructed and verified against **both** recorded hashes;
  the single post-run change is inert for G1 (§3.3). *This corrects the predecessor review.*
- **Dataset B identity.** Store `21661f03…` matches the freeze manifest; `foundation.py` matches;
  PIT roster v1 ≡ v2 `period_members` byte-identical; both cited specification sources exist off-repo
  and their sha256 match registration §11 exactly.
- **C3 as an execution.** Sound construct, healthy legs (median 14 v 16 names over 329 dates), real
  state variation, correct inference. **NOT CONFIRMED** is a valid finding about the registered
  statistic.
- **The C1a/C1b withdrawal decision** (as a decision) and **C1b's non-execution** (as a fact).
- **C7's freq-free property** — verified in code and by the new poison test.
- **Core machinery**: Newey–West, Holm, strict contiguity, PIT membership, no look-ahead in feature
  construction, read-only discipline. All independently checked and correct.

### B · What is invalid

- **C2 — INVALID.** The registered disagreement condition is an arithmetic tautology on Dataset B
  (100.00% of 30,624 ticker-days), and the 15% gate was swapped from |net| to gross-participation,
  taking incidence from 26.6% to 98.5%. The executed estimand is a foreign-net sign contrast. The
  registered mechanism was **never tested**.
- **C1a — INVALID / non-reportable.** Executed in breach of its registered withdrawal; θ, the full
  daily series and per-bucket detail are preserved and recoverable. Not to be read or cited.
- **`G1_FINAL_EXECUTION_REPORT` §D's six-cell claim** — three cells exist; C1b was never implemented.
- **Registration §6 exclusion 9 / governance status §5's "freq is never read"** — false for C2/C3.
- **The family-level "FAIL" as currently stated** — see D.

### C · What is unresolved

- **The executed code.** `9471c740…` is an unverifiable self-assertion; no copy survives anywhere.
  **EXECUTION PROVENANCE NOT IMMUTABLY ESTABLISHED.**
- **Family membership** of C2/C3/C7 against `{I5,I6,I7,I12}` — never mapped, anywhere (B1).
- **Slot accounting** for G1 — currently zero, which cannot be right (B3).
- **The "G1" label collision** — three live meanings (B8).
- **C7 threshold provenance** — 18.11% cited vs 12.29% measured (B7).
- **Intensity ↔ breadth orthogonality** — ZCode's own pre-declared prerequisite, still open (A8).
- **The C7 implementation-before-decision sequence** — code 10:35, decisions 10:44 (B6).
- Whether the §3 owner decisions were transmitted as recorded — outside my visibility; I report only
  the file timestamps.

### D · Should the original G1 FAIL classification be amended?

> ## **Yes.**

Not because the conclusion was wrong operationally — nothing is promoted either way, and every
deviation found runs in the permissive direction, so **this is not a rescue**. It should be amended
because a family-level **FAIL asserts that the family was tested**, and half the retained family was
not:

| Arm | Current record | Proposed |
|---|---|---|
| C3 | FAIL / not confirmed | **VALID → NOT CONFIRMED** (bounded claim only) |
| C2 | FAIL / not confirmed | **INVALID — specification failure, not a prediction failure** |
| C1a | WITHDRAWN, "no numbers" | **WITHDRAWN but EXECUTED IN BREACH — INVALID / non-reportable** |
| C1b | WITHDRAWN (one of "six cells") | **WITHDRAWN — never implemented** |
| **G1** | **FAIL** | **PARTIAL — one valid non-confirmation, one invalid arm, two withdrawn (one executed in breach)** |

Recording C2 as a prediction failure would enter a refutation of a mechanism that was never tested —
the exact error `HYPOTHESIS_LIFECYCLE.md` §3.1 names as corrupting the institution's own failure-mode
self-diagnostic. The Failure Registry currently shows N=3, all F2; a fourth mis-coded F2 would
reinforce a pattern that is partly an artifact of mis-specification rather than of the market.

### E · Does C7 remain paused?

> ## **Yes — B.**

Three blockers, none requiring a research cycle, none cleared by the owner's §3 decisions:

1. **No lawful multiplicity family** (B1) — blocks C7, C6 and C8 equally.
2. **Threshold provenance unreconciled** — 18.11% cited, 12.29% measured (B7). Not a tuning issue; a
   citation issue inside the registration.
3. **The map's own pre-declared orthogonality check is open** (A8) — newly material now that breadth
   has failed.

Secondary, for the record: the outcome axis (directional forward return) is the owner's choice, but
it sits against four consecutive P-M mechanisms killed by the same 0.60% friction floor, for a family
the map classifies as execution-type with zero outcome-axis evidence.

### F · Exact next owner decisions required

In strict order. **B1 blocks everything else.**

| Order | Decision | Ref |
|---|---|---|
| **1** | **Family determination** — C2/C3/C7 inside `{I5,I6,I7,I12}`, widen by amendment, or open a new declared family | B1 |
| **2** | **Ratify or amend the §5 classification table** — especially C2 = INVALID (not FAIL) and C1a = INVALID/non-reportable | B2 |
| **3** | **Retroactive slot counting** for G1, per arm, given decision 1 | B3 |
| **4** | **Amend the G1 verdict** from FAIL to the split verdict | B4 |
| **5** | **Authorize the C1a redaction** (new file; original sealed, never overwritten) | B5 |
| **6** | **Accept or reject Run 1 as valid-but-non-reproducible.** *For the owner's information: the output is intact and the config is verified; only the instrument is unestablished. Re-executing would change no conclusion — but that is the owner's call, not mine* | A3 |
| **7** | **Rule on the C7 implementation-before-decision sequence** | B6 |
| **8** | **Reconcile the C7 threshold citation** — keep 2.0 with corrected incidence, or re-express as a quantile | B7 |
| **9** | **Resolve the "G1" label collision** before any registry append | B8 |
| **10** | **Enter all G1/C7 governance acts into `DECISION_LOG.md`** — none is currently authoritative | B9 |

---

*No code modified. No data modified. No G1 rerun. No C7/C6/C8 execution. No parameter tuned. No
methodology changed. No artifact overwritten. No registry or decision-log entry created or edited. No
commits. No governance decision made. No C1a/C1b t-statistic or p-value recomputed or published. All
`[measured]` values are read-only formation-side diagnostics against the frozen store and production
`ohlcv` (`mode=ro` + `PRAGMA query_only`); no forward return, θ, t or p was computed by this audit.
State as of 2026-09-11 10:50 WIB — the audited directory has a second active writer (§8).*
