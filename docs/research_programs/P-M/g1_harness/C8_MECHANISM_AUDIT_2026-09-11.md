# C8 ABSORPTION MECHANISM — INDEPENDENT AUDIT (2026-09-11)

**Mode:** READ-ONLY research/data audit. No empirical execution, no new methodology, no parameter
tuning, no hypothesis expansion, no registry mutation, no research.db write, no production DB write,
no Dataset B modification, no owner/governance decision.
**C7 untouched.** This audit did not modify, delay, gate, re-run, or re-specify C7 in any way; C7
proceeds independently under `C7_REGISTRATION_v1_2026-09-11.md`.

**Authority:** generated point-in-time audit record (not canonical, not a specification, not a
registration). Supersession, not edit.

---

## 1 · EXECUTIVE VERDICT

### **NOT REGISTERED**

C8 ("absorption-state conditioning") exists in this estate as a **descriptive discovery artifact and
a candidate label only**. There is no specification document, no registration act, no hypothesis ID,
no family slot, no decision rule, no inference convention, and no code path. It appears **zero
times** in `DECISION_LOG.md`, `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md`,
`EXPERIMENT_LEDGER.jsonl`, `research.db`, and `g1_harness.py`.

Per task §2 and §9, the audit **stopped before any inferential testing**. Sections 4–7 below report
what is determinable from documents, code, artifacts and schemas without executing anything.

Three findings dominate:

1. **No predictive evidence has ever existed for C8.** Every authoritative source says so in its own
   words: family map row I — *"directional value unproven"*; row L — *"NEW FAMILY (contingent: needs
   forward-return leg later)"*; `CLAUDE_INDEPENDENT_REVIEW_G1_C7` TASK 5 — outcome-axis prior
   *"None."*; `FULL_HISTORICAL_EMPIRICAL_AUDIT` §K-3 — all C6/C7/C8 descriptive evidence is *"merely
   exploratory"*. **No forward return has ever been computed for a C8 state.** The claim in
   `G1_POSTMORTEM_FAMILY_TRIAGE` §C that C8's *"forward-return contingency is now satisfied by the
   frozen Dataset B outcome layer"* is a statement that the **data** to run the leg now exists — not
   that the leg was run. It has not been run.

2. **C8 is a strict subset of C7, by construction, in the only executable definition that exists.**
   `absorb ≡ (intensity ≥ 2.0) ∧ (|ret₁| ≤ 0.01)`; `highint ≡ (intensity ≥ 2.0)`. Absorption is
   C7's registered state intersected with an OHLCV-only price-flatness filter. It is not
   conceptually independent of C7 in the registered sense the task asks me to preserve — and the
   only persistence statistic ever offered as C8 evidence (45.7%) is **statistically
   indistinguishable from C7's own (48.1%)** on the same evidence file, i.e. the measured
   persistence is carried entirely by the intensity leg, with no measured increment from the
   flatness leg.

3. **The family map's headline C8 clustering claim is unsourced.** *"absorption clusters: 23.4%
   next-day absorption after absorption day vs 4.3% base"* (family map row I) **does not appear in
   any cited evidence artifact and is not computed by the cited generator.** The only next-day
   quantity `17_family_passD.py` computes is next-day *high-intensity* by state. The nearest numeric
   match in the evidence set (`0.2331`) is C3's breadth-surprise rate, a different measurement. This
   claim currently carries **no evidence receipt**.

**No advancement is supportable.** ADVANCE would require a registered specification and a registered
decision rule; neither exists. FAIL is not available either — nothing was ever tested, and recording
a non-test as a failure would corrupt the F1–F9 self-diagnostic (`HYPOTHESIS_LIFECYCLE` §3.1).
UNRESOLVABLE is wrong — C8 is not blocked by data; it is blocked by the absence of a specification,
which is an ordinary, closable governance act. The correct classification is **NOT REGISTERED**.

---

## 2 · AUTHORITATIVE C8 SPECIFICATION / REGISTRATION STATUS

### 2.1 Registration status: NOT REGISTERED (verified by exhaustive negative search)

| Register / artifact | C8 present? | Evidence |
|---|---|---|
| `docs/research_programs/HYPOTHESIS_REGISTRY.md` | **No** | C-family ledger = `{C2, C3, C7}`, 3 members (HYP-PM-0004/0005/0006). No C8 row, no HYP id |
| `docs/roadmap/DECISION_LOG.md` | **No** | `grep -c '\bC8\b'` = **0** across the whole file, D-001…D-049 |
| `docs/research_programs/FAILURE_REGISTRY.md` | **No** | 0 occurrences |
| `docs/research_programs/EXPERIMENT_LEDGER.jsonl` | **No** | 0 occurrences |
| `data/research.db` · `hypotheses` | **No** | 1 row total (`BROKER-001`, PREREGISTERED). No C-candidate rows at all |
| `data/research.db` · `gate_decisions` / `failure_registry` | **No** | 6 / 3 rows, none referencing C8 or absorption |
| `docs/research_programs/RESEARCH_PROGRAM.md` | **No** | 0 occurrences |
| `g1_harness/g1_harness.py` | **No** | no `c8_*`, no `absorb*`; defs end at `run_c7` |
| `g1_harness/g1_config.json` | **No** | no `c8_registered` gate exists (`c7_registered` is the only candidate gate) |
| Any `C8_REGISTRATION_*.md` | **Does not exist** | no such file anywhere in repo or `ZCodeProject/` |

### 2.2 What the authoritative record *does* contain

C8 is defined nowhere as a specification. The **exact existing definition** is an executable state
expression in a discovery script, plus a one-line prose label in a discovery artifact:

**Executable form** — `ZCodeProject/pm_data_audit/17_family_passD.py` L94 (generator of the cited
evidence file):

```python
inten  = m["gross"] / c["adv20"]                              # gross = Σ|value| over disclosed broker rows
absorb = (inten >= 2.0) and (abs(c["ret"]) <= 0.01)           # ret = close(t)/close(t-1) - 1
highint = inten >= 2.0
```

with `adv20 = median(close×volume)` over the **prior 21 sessions** of that ticker's own OHLCV series
(current session excluded), and three hardcoded excluded dates (`2026-07-24`, `2026-09-02`,
`2026-09-08`).

**Prose form** — `ZCODE_ALPHA_DISCOVERY_FAMILY_MAP_2026-09-10.md` row I:
> *"absorption prevalence 5.2% (gross ≥2×ADV & |ret|≤1%) … **C8** absorption-state conditioning
> (descriptive; directional value unproven) … NEW FAMILY (contingent: needs forward-return leg
> later)"*

### 2.3 Registration completeness, measured against the program's own only precedent

`C7_REGISTRATION_v1_2026-09-11.md` is the sole template for what "registered" means for a
C-candidate in this program. Scoring C8 against its own section headings:

| Registration element (C7 §2/§3) | C8 status | Source if present |
|---|---|---|
| Mechanism statement | **Partial** — a label ("absorption/resilience"), no causal mechanism statement | map rows I/L; TOWR §9 |
| Predictor definition | **Present (citable)** | `17_family_passD.py` L94 |
| State threshold(s) | **Present (citable)** — `intensity ≥ 2.0`, `|ret₁| ≤ 0.01` | same |
| Inputs / instrument | **Present (citable)** — flow `value`, ohlcv close/volume | same |
| Freq status | **Present** — freq-free by construction (never read) | same |
| PIT / availability | **Derivable**, never declared | §4 below |
| Exclusions | **Absent** — discovery applied none; C7's list is inheritable but not inherited | — |
| ADV20 window pin | **Conflicted** — discovery 21-value; C7 registration pins 20 | C7 §2 note |
| **Outcome variable** | **ABSENT** | — |
| **Contrast definition** | **ABSENT** | — |
| **Horizons / primary k** | **ABSENT** | — |
| **Decision rule** | **ABSENT** | — |
| **Falsification direction** | **ABSENT** | — |
| **Multiplicity / family slot** | **ABSENT** — and contested (§9 G-4) | — |
| **Inference procedure** | **ABSENT** for C8 specifically | §7 |
| **MDE / power stance** | **ABSENT** | — |
| Cost convention | Inheritable (0.60% RT floor) but unbound | — |
| Band-regime conditioning (LC-PM-0009/B8) | **ABSENT** | §9 G-7 |
| Dataset B prevalence | **NEVER MEASURED** | §4.8 |
| Incrementality / control design vs C7 | **ABSENT** | §7 |

**12 of 21 registration elements are absent**, including every element that determines what would
count as a result. Per task §2, this is not "PARTIALLY REGISTERED with meaningful gaps" — a
partially-registered object presupposes a registration act, and **no registration act for C8 exists
in any register**. Classification: **NOT REGISTERED**.

### 2.4 Exactly what is missing (the STOP list)

To reach registration, a C8 spec would need, at minimum:

1. A causal mechanism statement (what economic agent does what, and why flat price under heavy
   disclosed flow should carry forward information) — mechanism-first is a **gate**, not a
   preference (ADR-L1-003); without it C8 is evidence class K3-ceilinged.
2. Outcome variable (the C7 precedent: directional forward return, close(t)→close(t+k)).
3. Contrast definition (absorb vs what? — the three live candidates are absorb vs non-absorb,
   absorb vs *the rest of C7's high-intensity state*, and absorb vs all — they are different tests
   and the choice is an owner decision, not an audit inference).
4. Horizon set and primary k.
5. Decision rule and falsification direction.
6. Inference procedure + multiplicity treatment.
7. A **lawful family slot** (see §9 G-4 — this is the binding blocker, as it was for C7).
8. MDE/power stance.
9. Exclusion set (the C7 list is available to inherit, but inheritance must be an explicit act).
10. ADV20 window pin (21 vs 20) and prior-close/session-calendar pin.
11. Band-regime conditioning decision (LC-PM-0009 / B8).
12. Dataset B prevalence re-measurement and a declared minimum-cell-count rule.

---

## 3 · SOURCE AND LINEAGE AUDIT

### 3.1 The complete C8 source set (four primary, six downstream)

| # | Source | Date | Status of that document | What it contributes |
|---|---|---|---|---|
| P1 | `docs/research_programs/P-M/ZCODE_ALPHA_DISCOVERY_FAMILY_MAP_2026-09-10.md` rows I, L, P; scorecard row; §7 | 2026-09-10 | **DISCOVERY ARTIFACT — descriptive only. Not a hypothesis registry entry** (its own header) | The name, the family assignment (I/L), the prose definition, prevalence 5.2%, the contingency ("needs forward-return leg later"), the **unsourced** 23.4%/4.3% clustering claim |
| P2 | `ZCodeProject/pm_data_audit/17_family_passD.py` + `family_passD_states.json` | 2026-09-10 | unversioned working script + JSON, **outside this repository, not git-tracked here** | The **only executable definition**; the only reproducible numbers |
| P3 | `docs/research_programs/P-M/ZCODE_TOWR_BREAKOUT_PULLBACK_DEEP_DIVE_2026-09-10.md` §9, §11, §15, §17, §18 | 2026-09-10 | **DESCRIPTIVE ONLY — no forward-return alpha test, no p-values, no registration** (its own header) | One anchor case (TOWR 2026-09-04); the explicit statement that the C8 signature is **untested across events**; §18's formulation guidance |
| P4 | `ZCodeProject/pm_data_audit/PM_CUSTODY_RECONCILIATION_HANDOFF_2026-09-10.md` §2 | 2026-09-10 | handoff record | Ranks C8 a **secondary** survivor (C1a/C3/C7 are the primaries); *"No alpha claim is made for any of them"* |
| D1 | `g1_harness/G1_POSTMORTEM_FAMILY_TRIAGE_2026-09-11.md` §C, §D, §E, §G | 2026-09-11 | triage record | C8 = "LIVE (candidate), **NOT registered**"; data READY; "prevalence 5.2% ⇒ thinner cells"; **no-rescue**: C8 cannot rescue the G1 FAIL |
| D2 | `g1_harness/CLAUDE_INDEPENDENT_REVIEW_G1_C7_2026-09-11.md` TASK 5, §6, F-4 | 2026-09-11 | independent review | Outcome-axis prior **"None"**; independence **"Low — nested inside C7"**; *"C8 should not be a separate family at all while it is nested inside C7"*; F-4 (no lawful family) blocks C8 equally |
| D3 | `g1_harness/CLAUDE_G1_FORENSIC_AUDIT_2026-09-11.md` B1, §585 | 2026-09-11 | forensic audit | Family determination blocks C8 |
| D4 | `g1_harness/G1_GOVERNANCE_CLOSEOUT_2026-09-11.md` §58, §129 | 2026-09-11 | governance analysis | C8 named prospectively in the family-assignment decision the owner has not made for it |
| D5 | `g1_harness/FULL_HISTORICAL_EMPIRICAL_AUDIT_2026-09-11.md` §8.10, §J-6, §K-3 | 2026-09-11 | historical audit | C8's 5.2% is Dataset-A/top-25-truncated and **never re-measured on Dataset B**; C8 **never mapped to any I-taxonomy entry**; C8 evidence is "merely exploratory" |
| D6 | `C7_REGISTRATION_v1_2026-09-11.md` §2 (multiplicity), §3 item 4; `C7_PROPOSED_DECISION_RECORD` §44 | 2026-09-11 | **registered** (C7's) | Owner decision, verbatim: *"C7 is its own independent family; do NOT pool with C6 or C8."* — the only place an **owner** has ever ruled on anything touching C8 |

### 3.2 Lineage: where C8 came from, and what it is **not** descended from

**Actual lineage (one hop, ten days old):**
`family map pass D (2026-09-10, state measurement over Dataset A)` → `C8 label, families I + L` →
`TOWR deep-dive §9 (2026-09-10, one anchor case)` → `custody handoff (secondary survivor)` →
`G1 postmortem triage (2026-09-11, "LIVE candidate, NOT registered")`. Nothing earlier.

**TOWR deep-dive lineage — explicitly non-confirmatory.** The deep dive is often cited as C8's
supporting case. Read in full, it is the opposite of support:
- §9: *"It is **one day**; intensity was not extreme; and the analogue contrast for absorption-type
  states **has not been tested event-wise**."*
- §16: *"Single-day snapshot per event (pullback-day close only) — intra-pullback structure (like
  TOWR's Sep 4) **is not captured** by the analogue features; **the C8 signature is untested across
  events**."*
- §12/§13: the 1,625-event analogue study measured **C7's intensity profile**, breadth,
  concentration, species tilt, identity overlap and flip counts. **It never measured an absorption
  state.** Its CONT/FAIL discrimination is an intensity result, not a C8 result.
- §16: *"the discriminative content measured so far IS the volume/intensity profile, not broker
  identity"* — the deep dive concedes its own signal is C7-shaped.
- §17: *"Whether Sep-4-type absorption base days … discriminate CONT vs FAIL at event level"* is
  listed under **"What remains unknown."**

**Therefore: the TOWR deep dive contributes n = 1 unlabeled anchor case and zero event-level
evidence for C8.** Its §18 also pre-states the formulation constraint any future spec inherits:
> *"it should be formulated as an C8-conditioned state test … **with the C7 intensity profile as a
> declared control** — **not as a new family registration**."*

**Name collisions that are NOT lineage** (checked and excluded):
- `engine/indicators.py::classify_volume_context` → `'crash_absorption'` (VR ≥ 2.0 ∧ close ≥ 20%
  below 20d high) and `screener/calculator.py::calc_absorption` — **production OHLCV/tick heuristics,
  no relation to C8**; different inputs, different construct, no shared lineage.
- `broker_flow_program/31_MECHANISM_MAP.md` **H5** ("certain codes mainly *absorb* transient order
  flow") and BFI-001's CONC framing ("single-desk absorption") — a **concentration/liquidity-provision**
  construct on the broker-identity axis. This is C6's lineage, **not C8's**. C8 contains no
  concentration term.
- `docs/roadmap/RED_TEAM_REVIEW_2026-07-15.md` "absorption" — governance metaphor, unrelated.

### 3.3 Intended universe / timing / outcome (as recorded — all partial)

| Attribute | Recorded value | Source | Status |
|---|---|---|---|
| Universe | **Not specified for C8.** The measurement ran over all `broker_flow` ticker-days in `walkforward.db` (n = 100,095 formed cells, ~850 names) | `17_family_passD.py` | **Not a declared research universe.** Dataset B's declared universe is 100 tickers / 386 sessions / 30,626 in-scope cells — a different population |
| Timing | Formation implicitly at close(t); both legs observable at close t | derived | **Never declared**; no T+1/PIT statement exists |
| Outcome | **NONE.** Explicitly deferred: *"needs forward-return leg later"* | map row L | **ABSENT** |
| Existing results | prevalence 0.05199; next-day-high-intensity 45.7% vs 11.3%; one TOWR anchor day | `family_passD_states.json`; TOWR §9 | Descriptive only |
| Registration status | none | all registers | **NOT REGISTERED** |

---

## 4 · PIT / DATA / MECHANICAL VALIDATION

> **Scope note (task §3).** C8 is **not** sufficiently registered, so this section is **provisional**:
> it validates the *discovery-era construction* against the frozen estate, to establish whether a
> future registration would be mechanically executable. It is **not** a clearance, and nothing here
> licenses execution. No feature definition was changed to make anything executable.

| # | Check | Result | Detail |
|---|---|---|---|
| 4.1 | **PIT availability** | **PASS (provisional)** | Both legs are facts of session t: disclosed broker flow for `trade_date = t`, and `close(t)/close(t−1) − 1`. Nothing from t+1 or later enters the state. |
| 4.2 | **T+1 availability of inputs** | **PASS (provisional)** | Neither leg consumes a T+1-materialized file. Broker flow is a close-of-session disclosure; ohlcv close/volume are session-t values. (Contrast: the ratified `stockbit_flow` NF is T+1 — **C8 does not consume it**; see §8.) |
| 4.3 | **Session alignment** | **GAP** | Discovery used **each ticker's own OHLCV date series** for prior-close and ADV20 indexing, plus three hardcoded bad dates. The frozen estate uses `DATASET_B_SESSION_CALENDAR_v2` (386 sessions, 2025-01-02→2026-08-27) with a declared `excluded` map. These are different alignment conventions; a spec must pin one. |
| 4.4 | **Corporate-action handling** | **GAP (mechanically solvable)** | Discovery applied **no** CA handling. The frozen path has it: `foundation.load_corporate_actions` + `detect_unapplied_splits` + `vwap_ratio_report` quarantine (RAJA quarantined for adjustment-basis mismatch), plus the registered CA-in-`(t, t+k]` exclusion already implemented in the harness. Material for C8 specifically: **`ohlcv.close` is the flatness leg's only input** and the Semantic Register records the adjustment basis as **MIXED / VERIFIED WITH DEFECT** — an unadjusted split would manufacture or destroy "flat" days. |
| 4.5 | **Suspension handling** | **GAP (mechanically solvable)** | Discovery applied none. Frozen path expands `suspension_events` over the calendar and excludes `(ticker, t)`. Material for C8: a suspended/zero-volume session is a *manufactured* flat day (|ret| = 0) and would be **preferentially** admitted by the `|ret| ≤ 0.01` leg. The `gross ≤ 0` exclusion removes zero-flow days, but a thin-but-nonzero halted session would survive. This is C8's single most spec-sensitive exclusion and it is currently unspecified. |
| 4.6 | **Universe consistency** | **FAIL as measured** | Discovery: ~100,095 ticker-days, whole-market. Dataset B: 30,626 in-scope cells, 100 tickers, PIT roster v2 (sha `f7e2fec0…`). Every published C8 number describes a population Dataset B does not contain. |
| 4.7 | **Future leakage** | **NONE FOUND — with a construct-validity flag** | No future information enters the state. **Flag (not leakage):** the state conditions on the **contemporaneous return**, then (under any plausible spec) would be tested against a **forward return**. Conditioning a return-outcome test on a realized-return-defined state is legal PIT-wise but selects low-realized-move sessions and imports the return process's own autocorrelation/volatility structure into the conditioner. This must be declared and controlled in any registration; it is a construct-validity matter, not a leakage finding. |
| 4.8 | **Truncation / prevalence portability** | **UNRESOLVED — blocking for any cell-count claim** | Dataset A disclosure = top-25 per side (hard cap); Dataset B capture = `vendor_limit 150`. The intensity numerator is a sum over *disclosed* rows, so its scale changes with disclosure depth. C7's measured shift: **18.11% → 12.29%**. **C8's 5.2% has never been re-measured on Dataset B** and will move. At 5.2% Dataset-A prevalence, a proportional shift lands C8 near ~3.5%, i.e. ~1,000–1,100 Dataset-B cells across 375 formation dates — thin, and per-date contrast cells thinner still. `G1_POSTMORTEM` §D already flags "prevalence 5.2% ⇒ thinner cells". |
| 4.9 | **Feature-construction reproducibility** | **GAP (provenance)** | The only generator (`17_family_passD.py`) lives in `/home/tjiesar/ZCodeProject/pm_data_audit/`, **outside this repository and not git-tracked here**. This is the same class of defect (F-3) that was identified and repaired for `g1_harness/` (now tracked). No sha, no run manifest, no fingerprint binds the published C8 numbers to an input state. |
| 4.10 | **Dataset B compatibility** | **READY (in principle)** | `broker_flow_b.value` present (1,518,727 rows); production `ohlcv` (`is_final=1`) supplies close/volume; ADV20 (20-session median, shift(1)) and `ret1` are **both already computed inside `c7_build_panel`** — C8's two legs are, field-for-field, already materialized on the C7 path. Store sha `21661f03…`, FINGERPRINT_v2 `1a68ab1c…`, freeze manifest v1. |
| 4.11 | **Requires `broker_flow.freq`?** | **NO** | Neither leg reads `freq`. `freq` is SEMANTIC_REGISTER status **UNKNOWN / FORBIDDEN**; C8 is freq-free by construction, identically to C7. No freq dependency exists, and none must be introduced. |
| 4.12 | **Depends on aggregate net-flow semantics?** | **NO for the prohibited sense — YES for an undeclared one** | See §8.1. The predictor is `Σ\|value\|`, a magnitude that does **not** algebraically cancel, and is exactly the construction D-049 R-2 ratified for C7. **But** `value` is a *signed broker-level net* (Semantic Register: VERIFIED; `SUM(value) = 0` on 70,424/70,424 complete-disclosure ticker-days), so `Σ\|value\| = 2 × Σ(positive broker nets)` = **twice the net-crossed value among disclosed brokers** — *not* market turnover — while the denominator `ADV20 = median(close × volume)` **is** market turnover. The ratio mixes two populations and two quantities. This is an **unresolved semantic assumption**, not a prohibited construction. |
| 4.13 | **Constructible from approved sources without unresolved semantic assumptions?** | **NO** | Constructible: yes, from approved sources only (`broker_flow_b.value`, production `ohlcv`), with no forbidden field. Without unresolved semantic assumptions: **no** — 4.12 (numerator/denominator population mismatch), 4.4 (mixed adjustment basis on the flatness leg's only input), 4.5 (halted-session flat days), and §9 G-7 (band regime) are each unresolved. |

**Mechanical bottom line:** C8 is **data-ready and semantically unready**. Nothing is blocked by
data availability; several things are blocked by undeclared semantics and by the absence of a
specification.

---

## 5 · EXISTING DESCRIPTIVE EVIDENCE (class A)

All C8 evidence in the estate is descriptive. Independently verified against the cited artifacts:

| # | Claim | Verification | Verdict |
|---|---|---|---|
| A1 | Absorption prevalence **5.2%** | `family_passD_states.json` → `absorption_prevalence = 0.05199060892152455`, `n = 100,095`; generator L94/L111 matches the prose definition exactly | **VERIFIED** — Dataset A, whole-market, top-25-truncated |
| A2 | **P(next-day high-intensity \| absorb) = 45.7%** vs base **11.3%** | `nextday_high_intensity_prevalence_by_state = {absorb: 0.45739, highint: 0.48075, other: 0.11312}` | **VERIFIED as stated** — see the two structural caveats below |
| A3 | *"absorption clusters: **23.4%** next-day absorption after absorption day vs **4.3%** base"* (family map row I) | **Not present in `family_passD_states.json`, `discovery_structures*.json`, `species_design*.json`, `family_passC_broker_stock.json`, or `towr_deepdive.json`. Not computed by `17_family_passD.py`** — the script's only next-day quantity is next-day *high-intensity*, not next-day *absorption*. The nearest numeric match in the evidence set, `0.23312`, is `discovery_structures_B.json → breadth_surprise_rate.rate` (C3's measurement, unrelated) | **UNSOURCED — no evidence receipt** |
| A4 | TOWR 2026-09-04 anchor case (37.6B gross, 1.15×ADV20, 0.0% close-to-close, 68% single-desk buy share, re-acceleration within two sessions) | TOWR §5, §9, §11, `towr_deepdive.json` | **VERIFIED as a description of one day.** n = 1, unlabeled at data end, **not** an event-level result; 1.15×ADV20 means **this anchor case does not satisfy C8's own `intensity ≥ 2.0` threshold** |
| A5 | Absorption clusters are "contingent: needs forward-return leg later" | map row L | **VERIFIED** — the document's own classification |

**Two structural caveats on A2, both material:**

1. **The buckets are disjoint, the prevalences are not.** In the generator,
   `key = "absorb" if absorb else ("highint" if highint else "other")` — so the `highint` bucket is
   high-intensity **and not absorption**, while the separately reported
   `high_intensity_prevalence = 0.18109` counts **all** high-intensity days **including** absorption
   days. The 45.7% and 48.1% figures therefore partition one state space; the 18.11% figure does not
   align with either. Any spec citing these numbers together must reconcile the populations.
2. **A2 is not C8 evidence; it is C7 evidence.** `P(next-day high | absorb) = 45.7%` vs
   `P(next-day high | high ∧ ¬absorb) = 48.1%`. The flatness leg — the *only* thing that
   distinguishes C8 from C7 — moves this statistic by **−2.3 points, in the unfavourable
   direction**. On the single axis where C8 evidence exists, the increment from the C8-specific term
   is nil or slightly negative.

---

## 6 · EXISTING PREDICTIVE EVIDENCE (class B)

### **NONE. Zero forward returns have ever been computed for a C8 state.**

This is not an inference; it is what every authoritative source states:

| Source | Statement |
|---|---|
| Family map row I | *"absorption-state conditioning (**descriptive; directional value unproven**)"* |
| Family map row L | *"NEW FAMILY (**contingent: needs forward-return leg later**)"* |
| Family map §4 scorecard | C8 construct validity: *"Medium (**needs return leg**)"*; credibility Medium; actionability Medium |
| Family map header | *"**no forward-return tests run**"* |
| TOWR deep-dive header | *"**no forward-return alpha test, no p-values**"* |
| TOWR §16 | *"**the C8 signature is untested across events**"* |
| TOWR §17 | Whether absorption base days discriminate CONT/FAIL is listed under *"**What remains unknown**"* |
| Custody handoff §2 | *"**No alpha claim is made for any of them**"* |
| `CLAUDE_INDEPENDENT_REVIEW` TASK 5 | C8 outcome-axis prior: *"**None.** Map row I: 'directional value unproven'"* |
| `FULL_HISTORICAL_EMPIRICAL_AUDIT` §K-3 | *"Merely exploratory: … **all C6/C7/C8 descriptive evidence**"* |

**On the one statement that reads like predictive support.** `G1_POSTMORTEM_FAMILY_TRIAGE` §C/§D
says C8's *"forward-return contingency is now satisfied by the frozen Dataset B outcome layer"* /
*"READY — the forward-return contingency is now satisfied"*. Read precisely, and in the context of
the same table's `Data` column, this asserts that **the outcome data now exists** — not that a
forward-return leg was run or passed. No run, no output file, no p-value, no artifact, and no code
path exists. Treating this sentence as predictive evidence would be exactly the error task §4
prohibits (descriptive mechanism evidence read as predictive evidence).

**A2 is not a substitute.** Next-day *intensity persistence* is a predictor-axis autocorrelation
statistic, not a forward-return result. `CLAUDE_INDEPENDENT_REVIEW` TASK 5 makes the same point
against C7's ranking: it *"ranks a predictor autocorrelation statistic above an actual
forward-return prior."*

**Evidence class ceiling.** Under `EVIDENCE_MODEL.md`, C8's entire corpus is K3 observational
(descriptive state measurement + one anchor case). Per ADR-L1-003, a pattern without a proposed
causal mechanism is **K3 at best**; per rule U10, statistical significance without a mechanism is
inadmissible. C8 currently has neither a mechanism statement nor a statistic. Its reachable tier
today is **E0–E1**.

---

## 7 · INCREMENTALITY EVIDENCE

### 7.1 Governance finding first

**The C8 design specifies no incrementality test. Per task §5, this is reported as a governance gap,
not designed around.** No registered control set, no registered nesting rule, no registered
orthogonality criterion, and no registered model-comparison procedure exists for C8. I did not
invent controls, thresholds, windows, transformations, or model-selection procedures, and I did not
run anything.

### 7.2 What is determinable without a test (arithmetic and set theory only)

**Set containment is exact and is not a statistical claim:**

```
absorb  ≡ (intensity ≥ 2.0) ∧ (|ret₁| ≤ 0.01)
highint ≡ (intensity ≥ 2.0)                      ⟹   absorb ⊂ highint   (strictly, by construction)
```

C8's state is **C7's registered state intersected with an OHLCV-only price-flatness filter.**
Consequences, all derived from published numbers, no new measurement:

- **Share of C7's state that is C8:** 0.05199 / 0.18109 = **28.7%** of Dataset-A high-intensity
  name-days are absorption days.
- **C8 contains no information source C7 lacks on the flow axis.** Its flow term *is* C7's flow
  term, identical construction, identical threshold, identical inputs. The only additional
  information is `|ret₁|`, which is **pure OHLCV** — not broker-flow information at all.
- **Against the other controls named in task §5:** C8 contains **no** breadth term (`nb`, `ns`),
  **no** concentration term (C6's `CONC`/HHI), and **no** species/composition term. Its
  price/volume control content is `ADV20` and `ret₁`, both already in C7's panel.
- **Therefore the only coherent incremental question is internal to C7:** *does the flat-price
  subset of C7's high-intensity state behave differently from the rest of that state?* On the one
  axis ever measured, §5 caveat 2 answers **no measured increment** (45.7% vs 48.1%).

### 7.3 The registered-governance consequence

`C7_REGISTRATION_v1` §3 item 4 records the owner's verbatim decision: *"C7 is its own independent
family; do NOT pool with C6 or C8."* Combined with containment, this creates a live multiplicity
hazard already flagged by the independent review:

> *"**C8 should not be a separate family at all while it is nested inside C7.** … Running C7 then C8
> as two separately-counted registrations would double-count one measurement surface — an F3-style
> multiplicity error waiting to happen."* (`CLAUDE_INDEPENDENT_REVIEW_G1_C7` TASK 5)

And TOWR §18 pre-states the same constraint from the other direction: C8 should be formulated *"with
the C7 intensity profile as a declared control — **not as a new family registration**."*

**This is an owner decision and is recorded here as a gap, not resolved.** No audit finding can
settle whether C8 is (a) a nested sub-cell of C7 requiring no new slot, (b) a separate C-family
member requiring a widening amendment, or (c) inadmissible while C7 is in flight.

---

## 8 · SEMANTIC DEPENDENCIES

### 8.1 The `Σ|value|` numerator — ratified for C7, undeclared for C8

| Layer | Fact | Source |
|---|---|---|
| Field semantics | `broker_flow.value` = **NET rupiah value for that broker on that ticker-session, SIGNED**; `SUM(value) = 0` on 70,424/70,424 complete-disclosure ticker-days. Status **VERIFIED**. Research use: *"the accounting identity makes aggregate net UNINFORMATIVE. Do not resurrect aggregate net-flow as a directional variable."* | `DATASET_B_SEMANTIC_REGISTER_v1.json` |
| Hard gate | All-broker aggregate net flow **MUST NOT** be a directional predictor "in any form: raw net, net/gross ratios, sign() of such a net, abnormal-z of such a net, or decile/rank constructs" | same, `all_broker_net_identity_gate`; D-049 R-2 |
| C8/C7 predictor | `gross = Σ\|value\|` — a **magnitude**, not a net. Does not algebraically cancel. D-049 R-2 explicitly ratifies this form: *"intensity = gross/ADV20 — a Σ\|value\| construction, not a net"* | D-049 R-2 |
| **Undeclared consequence** | Because `SUM(value) = 0` exactly, `Σ\|value\| = 2 × Σ(positive broker nets)` — i.e. **twice the net-crossed value among disclosed brokers**, a quantity the Semantic Register elsewhere warns is *"NET CROSSED volume … NOT market traded totals"* and *"NEVER a denominator for concentration or market volume"*. The C8 denominator `ADV20 = median(close × volume)` **is** market traded value. The ratio therefore divides a net-crossed magnitude by a gross-turnover magnitude. | `bandar_detector.value/volume` entry; derived |

**Assessment:** C8's predictor is **not** a prohibited net construction, and **does** inherit C7's
ratification. But the word "gross" in the family map is a misnomer, and the numerator/denominator
population mismatch has never been declared in writing for either candidate. For C8 specifically it
compounds with §4.8 (disclosure-depth dependence), because `Σ|value|` is a sum over *disclosed* rows
only. **Declare, do not redefine** — I made no change to the feature definition.

### 8.2 Semantic constraints from task §7 — compliance check

| Constraint | C8 status | Evidence |
|---|---|---|
| Do **not** use `broker_flow.freq` as denominator / transaction-count proxy | **COMPLIANT** — C8 never reads `freq`; freq-free by construction on both legs | `17_family_passD.py`; `c7_build_panel` poison-test precedent |
| Do **not** assume broker attribution = beneficial ownership | **COMPLIANT** — C8 uses no broker identity, no `investor_type`, no attribution of any kind; it aggregates magnitudes across all disclosed rows | definition |
| Do **not** revive failed HYP-PM-0003 aggregate signed broker-flow predictor | **COMPLIANT** — HYP-PM-0003's predictor was `SUM(lot)` (the zero identity; D-049 R-1: reclassified **INVALID — DATA/SEMANTICS**). C8 uses `Σ\|value\|`, a magnitude. No signed aggregate anywhere in C8 | D-049 R-1; definition |
| Do **not** use the approved `stockbit_flow` NF unless C8's spec calls for it | **COMPLIANT** — no C8 source mentions NF; C8 does not consume it. (NF is also T+1; C8's legs are close-of-t.) | D-049 R-3; §4.2 |
| C8 must stay conceptually independent of C7 unless the registered design makes them complementary | **CANNOT BE SATISFIED AS DEFINED** — the only existing definition makes C8 a strict subset of C7's registered state (§7.2). This is an inherited property of the discovery definition, not a choice made here. **Reported as governance gap G-4/G-5; not resolved, and no redefinition attempted.** | §7.2 |

### 8.3 Other live semantic dependencies

- **`ohlcv.close` adjustment basis: MIXED / VERIFIED WITH DEFECT.** Split-adjusted for PTRO, CUAN,
  DSSA; **not** for RAJA (quarantined). The flatness leg is 100% dependent on `close`, so an
  unadjusted action manufactures or destroys "flat" days. Quarantine machinery exists; binding it to
  C8 is a registration act.
- **`broker_flow.side`: VERIFIED WITH DEFECT** (757 BUY rows with `lot < 0`, 1,822 SELL rows with
  `lot > 0`). Immaterial to C8 as defined — `Σ|value|` is side-agnostic. Any future variant that
  splits sides must use `sign(value)`, never `side`.
- **`idx_tickers.in_idx80`: REJECTED FOR RESEARCH USE.** C8 must use the frozen PIT roster artifact.
  The discovery pass used neither (it ran whole-market) — §4.6.
- **Band regime (LC-PM-0009 / B8):** the Dataset B window straddles the R3→R4 auto-rejection
  boundary (58 R3 sessions, 328 R4 sessions). The Semantic Register records: *"pooling across
  regimes without conditioning is void under B8."* C8's flatness leg is a volatility-conditional
  construct, making this **more** binding for C8 than for C7's threshold leg. Unaddressed.

---

## 9 · GOVERNANCE GAPS

| # | Gap | Severity | Note |
|---|---|---|---|
| **G-1** | **No specification document exists.** 12 of 21 registration elements absent, including outcome, contrast, horizons, decision rule, falsification direction, inference, multiplicity, MDE | **BLOCKING** | §2.3/§2.4 |
| **G-2** | **No registration act in any register** — DECISION_LOG, HYPOTHESIS_REGISTRY, FAILURE_REGISTRY, EXPERIMENT_LEDGER, research.db all return zero | **BLOCKING** | §2.1 |
| **G-3** | **A published headline claim has no evidence receipt** — the 23.4%/4.3% clustering figures are not in any cited artifact and are not computed by the cited generator | **HIGH** | §5 A3. Under Decision Hierarchy rule 1 (artifacts verify, documents self-report), the artifact wins: the claim is currently unsupported |
| **G-4** | **No lawful family slot.** The C-family is `{C2, C3, C7}` (D-048); C8 is in none. The same F-4 blocker that gated C7 gates C8 | **BLOCKING** | Owner decision. Families are append-only/monotonic (PG-3/PG-6, D-028) — widening is possible, narrowing is not |
| **G-5** | **Nesting/double-count hazard unresolved.** `absorb ⊂ highint`; the owner has ruled C7 a standalone family that must not be pooled with C8; two separately-counted registrations over one measurement surface is an F3-style multiplicity error | **BLOCKING** | §7.3 |
| **G-6** | **C8 has never been mapped to the P-M I-taxonomy** (`{I5, I6, I7, I12}`) — the same unreconciled gap recorded as J-6 for C2/C3/C6/C7 | **HIGH** | `FULL_HISTORICAL_EMPIRICAL_AUDIT` §J-6 |
| **G-7** | **Band-regime conditioning undeclared**, though LC-PM-0009/B8 makes unconditioned pooling void and C8's flatness leg is volatility-conditional | **HIGH** | §8.3 |
| **G-8** | **Prevalence never re-measured on Dataset B.** Every C8 number describes a top-25-truncated whole-market population Dataset B does not contain. C7's comparable figure moved 18.11%→12.29% | **HIGH** | §4.6/§4.8 |
| **G-9** | **Evidence-generator provenance gap.** `17_family_passD.py` is outside this repo and untracked here; no sha, run manifest, or fingerprint binds the published C8 numbers to an input state — the same F-3 class repaired for `g1_harness/` | **MEDIUM** | §4.9 |
| **G-10** | **No mechanism statement.** C8 is a state label, not a causal claim. Mechanism-first is a gate (ADR-L1-003); without it C8 is K3-ceilinged and rule U10 makes any significance it might later show inadmissible on its own | **MEDIUM** | §6 |
| **G-11** | **Numerator/denominator population mismatch undeclared** (net-crossed magnitude ÷ market turnover) | **MEDIUM** | §8.1 |
| **G-12** | **Exclusion set unbound** — in particular the suspended/halted-session case, which is the one exclusion that *preferentially* contaminates C8's flatness leg | **MEDIUM** | §4.5 |

**Out-of-scope observation, recorded for completeness, no action proposed and none implied:**
`g1_config.json` currently carries `"c7_registered": false`, while DECISION_LOG D-049 R-6 records
that `c7_registered = true` was authorized and lists `g1_config.json` among its changed files. This
is a C7 matter, is unrelated to C8, and this audit takes no action on it and recommends none.

---

## 10 · FINAL CLASSIFICATION

# NOT REGISTERED

**Why not the alternatives:**

- **Not ADVANCE.** Advancement requires a registered specification and a registered decision rule.
  Neither exists, and the underlying evidence would not support advancement even if they did:
  predictive evidence is **zero**, and the sole incremental axis ever measured shows **no increment**
  (45.7% vs 48.1%).
- **Not PASS.** Task §8 forbids PASS absent a registered decision rule that supports it. No decision
  rule of any kind is registered for C8.
- **Not FAIL.** Nothing was ever tested. Recording a non-test as a failure would corrupt the F1–F9
  failure-mode self-diagnostic (`HYPOTHESIS_LIFECYCLE` §3.1) and misuse the append-only, immutable
  Failure Registry.
- **Not UNRESOLVABLE.** C8 is not blocked by data availability, by a forbidden field, or by an
  unobtainable semantic. It is blocked by the absence of a specification and a family slot — ordinary,
  closable governance acts. Dataset B can, mechanically, carry both legs today (§4.10).

**What this audit did not do:** no C8 methodology, no parameter tuning, no hypothesis expansion, no
primary/secondary test, no empirical execution, no registry modification, no research.db write, no
production DB write, no Dataset B modification, no C7 modification, no owner decision. All database
access was read-only (`mode=ro`, `PRAGMA query_only`).

**Prerequisites before C8 could be reconsidered** (stated as gaps, not as a recommended plan — the
sequencing and the nesting question are owner decisions):

1. Owner determination on G-4 + G-5 — whether C8 can hold a lawful slot at all given `absorb ⊂ highint`.
2. A dated C8 specification closing the 12 absent registration elements (§2.4).
3. Correction or retraction of the unsourced 23.4%/4.3% claim (G-3).
4. Dataset B prevalence re-measurement and a declared minimum-cell rule (G-8).
5. Provenance repair for the evidence generator (G-9).

---

**Artifacts examined (read-only):** `ZCODE_ALPHA_DISCOVERY_FAMILY_MAP_2026-09-10.md` ·
`ZCODE_TOWR_BREAKOUT_PULLBACK_DEEP_DIVE_2026-09-10.md` · `PM_CUSTODY_RECONCILIATION_HANDOFF_2026-09-10.md` ·
`ZCodeProject/pm_data_audit/17_family_passD.py` + `family_passD_states.json` + `discovery_structures*.json` ·
`HYPOTHESIS_REGISTRY.md` · `FAILURE_REGISTRY.md` · `EXPERIMENT_LEDGER.jsonl` · `DECISION_LOG.md` (D-048, D-049) ·
`data/research.db` (hypotheses / failure_registry / gate_decisions) · `C7_REGISTRATION_v1_2026-09-11.md` ·
`C7_REGISTRATION_READINESS_2026-09-11.md` · `C7_PROPOSED_DECISION_RECORD_2026-09-11.md` ·
`G1_POSTMORTEM_FAMILY_TRIAGE_2026-09-11.md` · `CLAUDE_INDEPENDENT_REVIEW_G1_C7_2026-09-11.md` ·
`CLAUDE_G1_FORENSIC_AUDIT_2026-09-11.md` · `G1_GOVERNANCE_CLOSEOUT_2026-09-11.md` ·
`FULL_HISTORICAL_EMPIRICAL_AUDIT_2026-09-11.md` · `g1_harness.py` · `g1_config.json` ·
`DATASET_B_FREEZE_MANIFEST_v1.json` · `DATASET_B_SEMANTIC_REGISTER_v1.json` ·
`DATASET_B_BROKER_FLOW_STORE_v1.sqlite` (schema/counts) · `data/walkforward.db` (`broker_flow` schema, sign convention) ·
`LC-PM-0005.md` · `LC-PM-0009.md` · `engine/indicators.py` · `screener/calculator.py` (collision exclusion).
