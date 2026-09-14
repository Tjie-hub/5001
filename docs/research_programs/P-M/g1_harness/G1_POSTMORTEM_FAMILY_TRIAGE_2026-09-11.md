# G1 POSTMORTEM & FAMILY TRIAGE — 2026-09-11

**Mode:** ANALYSIS / TRIAGE ONLY. No empirical execution, no new hypotheses, no parameter changes, no Dataset B or G1-result modification.

---

## A. G1 outcome (registered, exact)

Run 1 (2026-09-11, exit 0): real Dataset B panel — 28,624 rows, 375 formation dates (2025-01-03→2026-08-27), 1,518,727 frozen flow rows, RAJA quarantined.

**Registered decision rule** (`G1_REGISTRATION_v1_2026-09-11.md` §8): a retained arm is *confirmed* iff Holm-adjusted p < 0.05 at primary k=5 (family = retained arms) AND sign consistency across k ∈ {3,5,10}; the 0.60% RT floor is a reported economic sensitivity, never a statistical verdict.

**Observed** (`G1_FINAL_EXECUTION_REPORT_2026-09-11.md` §E–K):

| Arm | k=3 | k=5 (primary) | k=10 | Holm p (k=5) | Signs | Net of 0.60% floor |
|---|---|---|---|---|---|---|
| C2 | +5.7 bp (t=0.75, p=0.46) | +4.9 bp (t=0.55, p=0.584) | −2.1 bp (t=−0.16, p=0.88) | **1.0** | +/+/− | −45 to −62 bp |
| C3 | +16.0 bp (t=1.11, p=0.27) | +5.8 bp (t=0.32, p=0.75) | −7.3 bp (t=−0.26, p=0.79) | **1.0** | +/+/− | −44 to −67 bp |
| C1a/C1b | WITHDRAWN_FREQ_DEPENDENT — no numbers | | | — | — | — |

**Which criteria failed — all of them, and why the failure is determinate:**
- *Statistical:* raw p at primary = 0.58 (C2) / 0.75 (C3); NW |t| ≤ 0.55 at primary. The largest family effect (C3 k=3, t=1.11) is also non-significant.
- *Sign-consistency:* both arms flip sign at k=10 (+/+/−) — the registered consistency requirement fails independently of significance.
- *Economic:* every cell nets to ≈ −44…−67 bp against the 0.60% floor.
- *Multiplicity:* Holm only pushed p further from 0.05.
- **Determinate, not power-limited:** 329–365 daily observations per cell across 375 formation dates from a complete 30,880-cell frozen capture. The registered inference (NW(k) on the daily series) was applied at its registered lag with no NaN/insufficient-series conditions on the retained arms. The verdict is a real null, not an underpowered ambiguity. (Power/MDE was registered NOT SET — so no *power claim* is made in either direction; the observed failure is at the point estimate and sign level, not a borderline CI.)

## B. What is closed

1. **C2 (conduit disagreement) — NOT CONFIRMED on this specification and data.** The registered falsification direction ("no context cell separates sides" → falsified) was evaluated in its registered unconditional contrast form; it did not confirm.
2. **C3 (breadth surprise) — NOT CONFIRMED.** Broad-minus-narrow daily spread is statistically null at all three horizons and flips sign at k=10.
3. **The G1 replacement registration's family is consumed.** No re-run, re-cut, threshold change, or control addition is authorized (no-rescue, §G).
4. **C1a/C1b remain WITHDRAWN** — freq semantics stay UNKNOWN/FORBIDDEN (SEMANTIC_REGISTER_v1 unchanged; probe evidence stands).
5. Registered limitations stand as limitations: no power claim, C3's ST-control clause inapplicable, C2 ran without species control.

## C. What remains legitimately open

- **Freq-free structure families from the discovery map:** C7 (intensity-state; families D+H), C8 (absorption; families I/L — its "forward-return leg later" contingency is now satisfied by the frozen Dataset B outcome layer), C6 (CONC events; family C, with the BFI-001 prior footprint t=−2.65), C5 (desk program persistence — **freq-dependent**, blocked by the same wall as C1a).
- **BFI-001's never-executed N2 cell** (abnormal-flow z restricted to liquid names) — remains untested; revival would require a T12 supersession registration (registry rule).
- **HYP-PM-0002** remains DRAFT (unregistered, consumes no slot; `stockbit_flow_bars` instrument).
- **Governance records owed:** the G1 FAIL should be appended to `HYPOTHESIS_REGISTRY.md`/family ledger per the append-only rule (registry currently ends at HYP-PM-0003).

## D. Family status table

**Corpus finding first:** the families named "H4 / flow-price divergence", "H5 / sweep-reference-extreme", "H6 / break-retest-continuation", "H7 / retail-response", "H8 / margin", and "H9 / broker-coalition fingerprint" **do not exist anywhere in the accessible repository** — no registration, no specification, no family-map entry under those names or descriptions (searched both corpora). The only registered H-numbers are the older foreign-flow program's H1/H6 (name collision only) and the repository's lifecycle gate labels G1–G4. They are therefore triaged as NOT FOUND rather than assessed as if specs existed; the nearest *existing* map families are noted for orientation only.

| Family (task name) | STATUS | Registration | Data | Semantic deps | Executable without new methodology | Principal gate | Next action |
|---|---|---|---|---|---|---|---|
| H4 flow-price divergence | **NOT FOUND** | none | — | — | — | — | none (nearest existing: map family G, blocked-then-partially-unblocked by NF ratification — still spec-less) |
| H5 sweep-reference-extreme | **NOT FOUND** | none | — | — | — | — | none |
| H6 break-retest-continuation | **NOT FOUND** (name collides with the closed foreign-flow H6 extreme-events line) | none | — | — | — | — | none |
| H7 retail-response | **NOT FOUND** | none | — | aggregator-led states are freq-dependent ⇒ same wall as C1a | no | freq | none |
| H8 margin | **NOT FOUND** — no margin data in the estate | none | no data | — | no | data acquisition | none |
| H9 broker-coalition fingerprint | **NOT FOUND** (nearest existing: map family N — **REJECTED**, avg pairwise tilt corr −0.065, no coordination) | none | — | — | — | — | none |
| **C7 intensity-state** (map families D+H) | **LIVE (candidate)** | **NOT registered** — descriptive evidence only (handoff "primary survivor"; persistence 45.7–48.1% vs 11.3% base; intensity ≥2×ADV on 18.1% of name-days) | **READY** — derivable entirely from the frozen store (gross, ADV20) + ohlcv | **none** (freq-free, cap-robust) | **yes** — same execution form as G1 (daily state contrasts, NW(k), Holm) | needs its own dated registration/spec freeze first | draft spec → owner freeze → execute |
| **C8 absorption-state** (map families I/L) | **LIVE (candidate)** | **NOT registered** | **READY** — the forward-return contingency is now satisfied by frozen Dataset B | none (freq-free) | yes (same machinery) | needs registration; prevalence 5.2% ⇒ thinner cells | draft spec → owner freeze → execute |
| C6 CONC events (map family C) | **LIVE (candidate)** | **NOT registered** | READY (side-value HHIs from the frozen store) | none (freq-free) | yes | BFI-001 prior footprint (t=−2.65, unconfirmed-Holm) is suggestive, not a spec | draft spec → owner freeze → execute |
| C5 desk program persistence (map family D) | **BLOCKED** | none | — | freq-dependent (desk classifier) | no | same freq wall as C1a | none while freq UNKNOWN |
| HYP-PM-0002 (draft) | DRAFT | unregistered | instrument `stockbit_flow_bars` — coverage for the window not assessed | — | — | registration decision | owner |
| BFI-001 N2 liquid-restricted cell | alive via T12 supersession | BFI-001 consumed/terminal | READY (value-only) | none | yes (new registration required) | registry T12 | owner |

## E. Recommended next execution family

**C7 — intensity-state (discovery families D + H).**

Basis, strictly on existing governance and evidence — not economic appeal:
1. **Named a primary survivor by the program's own custody handoff** ("C7 flow intensity/state (freq-free, cap-robust; next-day high-intensity persistence 48%/46% vs 11% base)") when freq was already known to be unresolved — i.e., C7 was pre-designated as a lead for exactly the world we are now in.
2. **Freq-free and cap-robust** — zero unresolved semantic dependency; nothing it consumes is FORBIDDEN.
3. **Data-ready with zero new engineering:** every input (gross, ADV20, per-cell flow presence) comes from the frozen store and production ohlcv already wired into the harness; the execution form (daily state contrasts, NW(k), Holm) is the machinery just validated end-to-end.
4. Strongest measured descriptive footprint among the unregistered survivors (persistence 45.7–48.1% vs 11.3% base; intensity ≥2×ADV on 18.1% of name-days).

**Explicit caveat (required by the task):** no candidate family — including C7 — currently has a frozen specification. Strictly, **no family meets all five prefer-conditions simultaneously** until C7 (or another) is registered. The recommendation is therefore: register C7 next (a G1-style dated spec freeze: intensity-state definition, thresholds, k-set, inference, exclusions, decision rule — all derivable from the map's measured evidence and existing conventions, nothing from returns), obtain owner sign-off, then execute. C6 and C8 are the documented alternates; C8 additionally inherits a now-satisfied contingency.

## F. Exact prerequisite(s) for the recommended family

1. Owner-approved registration document for C7 (intensity-state): state definition (gross/ADV20 thresholds), formation timing, horizons, inference, exclusions, decision rule — drafted from the family map's measured evidence and existing conventions only.
2. Owner gate act: no new gate is needed (`freq_semantics_ratified` concerns freq only; C7 never reads freq). The G1 harness gates remain as they are; C7 execution would be a new registered run under its own registration.
3. Registry bookkeeping: append the G1 FAIL (C2/C3) and the C7 registration to the program ledger/registry per the append-only rule.

## G. Governance / no-rescue statement

- **C2 will not be rerun.** **C3 will not be rerun.** **C1a/C1b remain withdrawn** (freq UNKNOWN; withdrawal registered).
- The G1 FAIL is final for the registered G1 family and **cannot be rescued by H4/H5/H6/H7/H8/H9, C7, C8, or any other arm** — those are different mechanisms/measurement families (distinct-family test already applied in the map), and any future execution is a **separate registered test** under its own dated registration, consuming its own multiplicity slot.
- The G1 result, artifacts, and hashes stand unmodified: store `21661f03…`, FINGERPRINT_v2 `1a68ab1c…`, NF digest `60f5f91c…`, raw output `74883c04…`, code `9471c740…`.
- No new methodology, tuning, empirical rerun, subgroup search, hypothesis, overlay, ML, or Dataset B/G1 modification was performed in producing this triage.
