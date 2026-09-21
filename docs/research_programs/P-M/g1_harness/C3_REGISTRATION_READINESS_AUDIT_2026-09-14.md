# C3 REGISTRATION / READINESS AUDIT — 2026-09-14

**Authority:** generated point-in-time record (audit only). **No empirical execution performed.**
No C3 test run, no methodology change, no registration change, no `HYPOTHESIS_REGISTRY.md` edit,
no `research.db` write, no Dataset B change, no C7 change, no C8 test, no C3 variant created.

---

## 1. Executive verdict

**The audit's own framing does not hold against the record.** C3 is not an unexecuted candidate
awaiting a readiness determination. **C3 already has a registered hypothesis ID (`HYP-PM-0005`), a
complete frozen specification, and a completed, terminal empirical execution**, dated 2026-09-11 —
three days before this task and **before** C7's 2026-09-14 execution, not after it. Its outcome is
**NOT CONFIRMED (VALID, bounded null)**: primary k=5 θ = +5.8 bp, NW t = +0.323, Holm p = 1.0, N=329
daily observations. It is receipted in three independent canonical places (`DECISION_LOG.md` D-048,
`HYPOTHESIS_REGISTRY.md` row `HYP-PM-0005`, `FAILURE_REGISTRY.md` row `FAIL-PM-0005-G1`), and the
Owner-ratified postmortem states, verbatim: **"C3 will not be rerun."**

There is therefore no live question of whether C3 is "sufficiently registered and mechanically ready
for an independent empirical test." It was registered, it was mechanically capable (it ran), and it
produced a determinate result that governance has explicitly closed to re-run. Treating C3 as "the
next legitimate empirical candidate after the C7 null" is not supported by the record — C3's own
empirical slot was consumed and closed *before* C7 ran at all. This report documents that finding in
full rather than forcing the requested five-way classification to fit a premise the evidence
contradicts (see §11 for the classification actually assigned and why).

---

## 2. Authoritative C3 definition

Source of record: `docs/research_programs/P-M/g1_harness/G1_REGISTRATION_v1_2026-09-11.md` §1/§4
("C3 — breadth surprise (lead)"), the sole authoritative, dated, frozen specification. No
reconstruction from memory or from C7 was performed; every element below is quoted/paraphrased
directly from that document.

- **breadth(i,t)** = (n_buy − n_sell)/(n_buy + n_sell), from full-population broker-flow store rows
  of (ticker i, session t).
- **surprise(i,t)** = breadth(i,t) − per-ticker trailing median of breadth over ALL prior valid panel
  rows (strictly past; minimum history 30 observations).
- **States:** surprise ≥ +0.30 ("broad") vs ≤ −0.30 ("narrow") — threshold frozen from measured
  incidence (design memo §7), not re-derived here.
- **Contrast:** daily spread = mean forward-return of broad-state names − mean forward-return of
  narrow-state names, computed per formation date.
- **Unit of observation:** one row per (ticker i, formation session t), t on the Dataset B PIT
  roster, 386 admitted sessions 2025-01-02→2026-08-27.
- **Outcome/horizons:** forward close(t)→close(t+k), k ∈ {3, 5, 10}; **primary read k = 5**; no
  post-hoc horizon selection.
- **Family status at registration:** "RETAINED — LEAD" (i.e., the surviving, primary arm of the
  original C1/C2/C3 discovery-stage design; C1a/C1b were WITHDRAWN, C2 retained as secondary).

---

## 3. Registration status

**REGISTERED.**

- Hypothesis ID **`HYP-PM-0005`**, `docs/research_programs/HYPOTHESIS_REGISTRY.md` line 14, family
  **P-M · C-family · C3 breadth surprise**.
- Registering document: `G1_REGISTRATION_v1_2026-09-11.md` — an explicitly dated **new** registration
  (the original `BROKER_FLOW_PREREGISTRATION.md` was searched for exhaustively and confirmed NOT
  FOUND per the 2026-09-11 retrieval report; the replacement is documented as a new registration, not
  a reconstruction — this distinction is preserved from the source record, not asserted independently
  here).
- Owner-authorized per DECISION_LOG **D-048** (2026-09-11, Option B), which explicitly formalizes
  `{C2, C3, C7}` as a family and receipts the registration act.
- **Status beyond registration: EXECUTED and TERMINAL** — see §6. Registration status alone
  undersells where C3 actually sits in its lifecycle; it is not merely registered, it is registered
  *and closed out*.

No missing binding elements were found (see §4) — this is not a PARTIALLY REGISTERED case.

---

## 4. Registration-element checklist

Every element the task asked me to locate, with its source. Nothing here was inferred or filled in;
where the source document itself declares an element "NOT SET," that is reported as such rather than
treated as a gap this audit could fill.

| Element | Value | Source |
|---|---|---|
| Hypothesis definition | breadth-surprise state (±0.30 vs strictly-past trailing median) → forward-return continuation | `G1_REGISTRATION_v1_2026-09-11.md` §4 |
| Feature construction | breadth(i,t) from full-population broker-flow store; surprise = breadth − trailing per-ticker median (min 30 obs history) | §4 |
| Universe | Dataset B PIT roster, 386 admitted sessions 2025-01-02→2026-08-27 | §2 |
| Timing/PIT convention | formation consumes only data dated ≤ t; ADV20 shifted; trailing median strictly past; synthetic-tested against T+1 dumps/excluded sessions/forward-dated rows | §2 |
| Outcome | close(t)→close(t+k), calendar-indexed, strict contiguity, no substitution | §5 |
| Horizons | k ∈ {3, 5, 10}; primary k = 5; no post-hoc horizon selection | §5 |
| Contrast | mean fwd-return(broad) − mean fwd-return(narrow), per formation date | §1/§4 |
| Inference | per-cell mean, Newey-West t (lag=k, BFI-001 convention), two-sided p via erfc | §7 |
| Multiplicity | Holm step-down across retained arms **{C2, C3}** at k=5, α=0.05 | §1/§7 |
| MDE/power treatment | **explicitly NOT SET** — "No ratified power/effective-N methodology exists... No power claim may be attached to any G1 output" | §9.1 |
| Exclusions | 9 named exclusion rules (quarantine, suspension/missing bar, non-positive gross, price floor, formation-day move proxy, unratified NF, CA ex-date in window, breadth-floor date exclusion, N/A species-classifier row) | §6 |
| Cost treatment | `theta_net_cost_floor = theta_mean − 0.006` (estate cost authority), reported per cell, **never used to flip a statistical verdict** | §7, §8 |
| Decision rule | confirmed iff Holm-adjusted p < 0.05 at primary horizon AND sign consistency across k∈{3,5,10} reported; otherwise "not confirmed" — no rescue, no re-specification, no secondary-arm promotion | §8 |
| Falsification direction | **no KILL rule pre-registered for C2/C3** — registered explicitly as an absence, not invented | §8 |

**Conclusion:** every requested element is present in the authoritative registration document, either
as a concrete specification or as an explicitly-registered "NOT SET"/absence. There is no undocumented
gap.

---

## 5. Data/PIT/mechanical readiness

Not merely theoretically ready — **empirically proven ready by the fact that it already ran to
completion.** Per §10 of `G1_REGISTRATION_v1_2026-09-11.md` and the execution report:

- Dataset B store sha256 `21661f033145ef90…` verified against the freeze manifest (re-verified live
  in this session, see prior task's post-commit checks; unchanged).
- FINGERPRINT_v2 `1a68ab1c…` reproduced at freeze.
- PIT roster/calendar: `DATASET_B_PIT_ROSTER` sha `f7e2fec0…`, `DATASET_B_SESSION_CALENDAR_v2.json`
  sha `5012be23…`, strict contiguity enforced.
- Formation timing: broker-flow rows `trade_date == t` only; ADV20 `shift(1)`; trailing breadth
  median strictly past; synthetic-tested against leakage vectors.
- T+1 availability: `stockbit_flow` (NF control) materializes T+1 morning per owner-declared
  convention; OHLCV gated on `is_final=1`.
- CA/suspension handling: corporate-action ex-dates inside (t, t+k] excluded per-k; suspensions
  expanded over the declared calendar and excluded.
- **`broker_flow.freq`:** C3 **does not use it** — this is precisely why C3 (not C1a/C1b, which are
  freq-dependent and WITHDRAWN) survived as the lead retained arm; registered explicitly as
  "freq-free, cap-robust" (§1 note).
- **Aggregate broker-flow net:** C3 does not use net-flow as its signal (breadth is a name-count
  ratio, not a value-signed net); NF is carried only as a ratified covariate, not consumed inside the
  C3 contrast itself.
- Reproducibility: execution preserved output JSON with config snapshot, code sha256, freeze
  fingerprint, NF digest, execution timestamp (§10.5).

No mechanical readiness question remains open for C3 — it was mechanically sufficient to execute, and
did.

---

## 6. Existing evidence and lineage

Three distinct evidence layers were checked and are explicitly distinguished, per the task's own
A/B/C split:

**A. Descriptive evidence (pre-registration, exploratory):** `ZCODE_ALPHA_DISCOVERY_FAMILY_MAP_2026-09-10.md`
§2 row "B. Participation/breadth" — breadth imbalance p10/p90 ±0.28/+0.39, autocorrelation
0.24/0.21/0.19 (lags 1-3), sign runs p50/p90/p99 = 1/4/9 days, surprise >0.3 on 23% of name-days,
next-day volume asymmetry 0.92 (extreme sell) vs 1.005 (extreme buy). This is the discovery-stage
material that motivated registering C3 as "breadth surprise." **This is descriptive only — a
distributional/incidence characterization, not a predictive test.** It is correctly *not* cited
anywhere in the corpus as the registered result.

**B. Predictive evidence:** none exists separate from C. The only predictive test of C3 that exists
*is* the registered empirical execution in C below — there is no exploratory predictive run that was
later "upgraded."

**C. Registered empirical evidence — the one this audit was specifically asked to characterize:**

> *"the previously reported C3 bounded-null evidence"* — located and verified as:

- **What was measured:** the C3 contrast exactly as specified in §2/§4 above (broad-minus-narrow
  daily spread of forward returns).
- **On which dataset:** frozen Dataset B (`broker_flow_b`, store sha256 `21661f03…`, FINGERPRINT_v2
  `1a68ab1c…`), 329 daily observations (of 386 admitted PIT sessions, after exclusions).
- **With which definition:** the frozen §4 definition above — unchanged from registration to
  execution.
- **Whether it was registered:** **yes**, under `HYP-PM-0005` / `G1_REGISTRATION_v1_2026-09-11.md`,
  executed once as part of "G1 Run 1," 2026-09-11.
- **Result (all figures reproduced identically across `DECISION_LOG.md` D-048,
  `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md` FAIL-PM-0005-G1, and
  `G1_POSTMORTEM_FAMILY_TRIAGE_2026-09-11.md`):** primary k=5 θ = +5.8 bp, NW t = +0.323, Holm
  p = 1.0; full horizon ladder k=3/5/10 → +16.0 bp (t=1.11, p=0.27) / +5.8 bp (t=0.32, p=0.75) /
  −7.3 bp (t=−0.26, p=0.79); sign pattern +/+/−; net of the 0.60% cost floor ≈ −44 to −67 bp.
  Classified **NOT CONFIRMED (VALID, bounded)** — i.e., a determinate null under the registered
  decision rule, not an indeterminate or underpowered result (MDE/power was registered NOT SET, but
  the postmortem records this as "not a power claim," a distinct and narrower statement — see §9.1
  source above).

No exploratory evidence was or is being upgraded here. The registered result already exists at full
evidentiary weight for its registered claim; this audit adds no new evidentiary claim.

---

## 7. C7 independence check

- `C7_REGISTRATION_v1_2026-09-11.md` contains **zero references to C3** (verified by direct search:
  no "C3," no conditioning language, no fallback/rescue language). C7's registered design is
  self-contained.
- Chronologically, **C3 executed and closed out (2026-09-11) before C7 executed (2026-09-14, per
  `C7_EXECUTION_REPORT_2026-09-14.md` / `runs/RUN-20260914T015335Z-41bea166a025/c7_real_output.json`,
  observed live in this session)**. C3's result cannot have been, and was not, conditioned on C7's
  outcome — it predates it. The reverse relationship (C7 conditioned on C3) is also absent from the
  C7 registration text.
- This task's own framing — "is C3 the next candidate after the C7 null" — inverts the actual
  chronology. C3 is not downstream of C7; it is a separate, earlier-closed arm of the same
  2026-09-11 replacement registration event. Per §8/§10 this audit does **not** treat C3 as
  conditioned on, filtered by, or combined with C7, and flags that the task's premise implicitly
  risks exactly that framing if taken at face value.
- No unregistered C7 filter, threshold, or composite with C3 was found or introduced.

**Independence: verified. No rescue relationship in either direction exists in the record.**

---

## 8. Family/multiplicity status

Current C-family state, `HYPOTHESIS_REGISTRY.md` "Family-slot ledger" row **P-M · C-family**:

| Family | Members registered | Detail |
|---|---|---|
| `{C2, C3, C7}` | **3 / 3** | HYP-PM-0004 (C2, INVALID-governance), **HYP-PM-0005 (C3, NOT CONFIRMED — terminal)**, HYP-PM-0006 (C7, now executed per `C7_EXECUTION_REPORT_2026-09-14.md`, outcome outside this task's scope to characterize) |

The family was opened, and its exact membership fixed, by **D-048** (2026-09-11, Owner Option B):
"the already-registered arms {C2, C3, C7}." **C3 already occupies its lawful slot, and that slot is
closed** ("C3 will not be rerun" — `G1_POSTMORTEM_FAMILY_TRIAGE_2026-09-11.md` §G). There is no open
slot question to resolve for C3: it does not need a slot assigned (it has one), and no slot exists
for a *new*, separate C3-labeled test without a fresh, dated, Owner-approved registration and — per
repository invariant #12 and rules PG-3/PG-6/R7.5 (`CLAUDE.md`) — a **formal governance amendment**
widening the family, since {C2, C3, C7} is otherwise fixed at 3 members per D-048.

Per the task's own instruction 6 ("if the registry does not provide a lawful slot, report the
governance blocker instead of creating one"): **the registry provides a slot for C3, but that slot
is already consumed and closed.** A *new* C3-labeled empirical test would require a new family
member — not a re-run of `HYP-PM-0005` — which is a governance act this audit does not have standing
to authorize or draft.

---

## 9. Cost/economic specification

**Registered, present, and correctly scoped as reporting-only — not a decision input.**

- `theta_net_cost_floor = theta_mean − 0.006` (the estate's 0.60% round-trip cost authority),
  computed per cell and reported alongside every statistical result (`G1_REGISTRATION_v1_2026-09-11.md`
  §7).
- Explicitly registered as **never flipping a statistical verdict** (§8: "Cost-floor figures are
  economic-relevance readings only").
- Realized in the executed result: net of the 0.60% floor, C3's already-null gross effect moves
  further negative (≈ −44 to −67 bp across horizons) — consistent with, not contradicting, the
  NOT CONFIRMED classification.

No cost model was invented for this audit; the figure above is quoted directly from the registration
and execution record.

---

## 10. Governance blockers

1. **No-rescue instruction is explicit and unconditional.** `G1_POSTMORTEM_FAMILY_TRIAGE_2026-09-11.md`
   §G: *"C3 will not be rerun,"* and *"No re-run, re-cut, threshold change, or control addition is
   authorized (no-rescue, §G)."* This is the binding blocker against treating C3 as executable again
   under `HYP-PM-0005`.
2. **D-048 fixes the C-family at exactly {C2, C3, C7}, 3 members, no pooling, no I-taxonomy
   assignment.** A *new* C3-flavored test is not a continuation of `HYP-PM-0005` — it would need its
   own registration and consume a new family slot, requiring the formal, widen-only governance
   amendment invariant #12 demands. That amendment does not exist and is outside this audit's scope
   to create (task instruction 8: do not modify registration).
3. **MDE/power was never ratified for C2/C3** (§9.1 of the registration) — this is a standing,
   registered limitation, not a defect introduced by execution. It does not block the *existing*
   result's validity (the result is reported as a determinate null, not as underpowered), but it
   would block any claim that a *new* C3 test could be power-justified without first ratifying a
   power/effective-N methodology (flagged in the source as DEP-B row 6, still open).
4. **This task's own premise is a governance risk if acted on literally.** Instruction framing ("is
   C3 sufficiently registered and mechanically ready for an independent empirical test") could be
   read as inviting a fresh C3 execution. Per blockers 1–2, that would be an unauthorized rescue of a
   terminal, closed result — exactly the failure mode repository invariants and this task's own
   instruction 8 ("do not rescue C7," by the same logic extended to C3) are designed to prevent.

---

## 11. Final classification

### UNRESOLVABLE (as framed)

Not because any registration element is missing, ambiguous, or because data/PIT mechanics are in
question — every one of those checks out (§§3–5, 9). It is UNRESOLVABLE **because the question the
task asks cannot be truthfully answered inside the five offered categories**: C3 is not
under-registered (rules out NOT REGISTERED / PARTIALLY REGISTERED / READY FOR OWNER REGISTRATION),
and it cannot be honestly called READY FOR EXECUTION, because executing it again is exactly what
governance (`G1_POSTMORTEM_FAMILY_TRIAGE_2026-09-11.md` §G) has explicitly forbidden. The accurate
status, stated plainly outside the five-way scheme: **TERMINAL / CONSUMED — REGISTERED, EXECUTED,
CLOSED (2026-09-11), NO FURTHER EXECUTION LAWFUL UNDER THE EXISTING REGISTRATION.**

C3 is not the next legitimate empirical candidate after the C7 null. It is not a candidate at all —
it is a closed prior result from the same family, and its closure predates C7's own execution.

---

## Deliverable summary (for the requesting task)

- **Report path:** `docs/research_programs/P-M/g1_harness/C3_REGISTRATION_READINESS_AUDIT_2026-09-14.md`
- **Registration status:** REGISTERED (`HYP-PM-0005`) — and further, **EXECUTED and TERMINAL**
  (2026-09-11), which the requested classification scheme does not have a category for.
- **Exact blockers:** (1) explicit "C3 will not be rerun" governance statement
  (`G1_POSTMORTEM_FAMILY_TRIAGE_2026-09-11.md` §G); (2) D-048 fixes the C-family membership at 3,
  consumed; (3) no ratified MDE/power methodology exists for any new C-family test.
- **Can C3 legally proceed without a new methodology decision?** **No.** Not because of a
  methodology gap in the existing registration (there is none — see §4), but because the existing
  registration's single authorized execution has already occurred and is closed; any further C3
  execution requires a **new, separately dated registration and a formal governance amendment**
  widening the fixed 3-member C-family, which is an Owner act, not something this audit can supply.
- **Files changed:** one file created — the report above. No other file in the repository was
  created, edited, or deleted by this task.
- **Confirmation no empirical C3 test was run:** confirmed. No C3 computation was executed, no
  output artifact was produced or modified, `research.db` was not written, Dataset B was not
  touched, `HYPOTHESIS_REGISTRY.md`/`FAILURE_REGISTRY.md`/`g1_config.json` were not modified, and no
  C3 variant was created. (Note, for completeness and not as a product of this task: the working
  tree currently shows `g1_config.json` with `c7_registered: true`, uncommitted — this reflects the
  C7 execution that occurred elsewhere between 2026-09-14 01:53–08:54Z, outside this task's actions
  and outside this task's scope to touch.)
