# C7 REGISTRATION READINESS — 2026-09-11 (updated: owner decisions incorporated)

**Task:** finalize and verify the C7 registration (owner approved the six decisions). Analysis/documentation + minimal mechanical harness work only. **No empirical execution** — C7 was not run on real data; no C7 forward returns were computed; no threshold, subgroup, or outcome inspection occurred.

---

## Verdict: **READY FOR EXECUTION**

The registration is complete, internally consistent, and mechanically executable. The C7 path is fail-closed on its own gate (`c7_registered=false` until the execution authorization). G1 is untouched (16/16 tests). What remains is solely the owner's execution authorization (flip `c7_registered=true`, run the command in §I).

## A. Owner decisions (all six, approved 2026-09-11)

1. **Outcome:** directional forward return (Dataset B calendar-indexed close→close, strict contiguity).
2. **Contrast:** pre-specified high-intensity state vs pre-specified normal/non-high state, frozen before execution; dates lacking either side skipped and counted.
3. **Horizons:** k ∈ {3,5,10}, primary k = 5; program forward-return and session-contiguity conventions.
4. **Multiplicity:** C7 is its own independent family — never pooled with C6/C8 (single-cell Holm: holm_p = raw p).
5. **MDE/power:** "MDE/power not used as a confirmation criterion" — registered verbatim; no power claim may be attached to C7 outputs.
6. **Descriptive persistence (45.7–48.1% vs 11.3%):** CONTEXT ONLY — may not determine thresholds, horizons, contrast, or the decision rule.

## B. Final registered specification

`C7_REGISTRATION_v1_2026-09-11.md` (status: REGISTERED — owner-approved):

- **State:** `intensity = gross/ADV20`; **high-intensity iff intensity ≥ 2.0** (inclusive); ADV20 = median traded value (close × volume) over the prior 20 sessions, shift(1).
- **Inputs:** frozen store `broker_flow_b` values (gross), production `ohlcv` (close, volume), sha-verified calendar/PIT artifacts. **freq never read** (poison-test proven).
- **Exclusions:** quarantine; suspension at t; missing bar; missing ADV20 history; gross ≤ 0; price < 100; |ret1| ≥ 0.15 or undefined; CA ex-date strictly inside (t, t+k]. No breadth-floor exclusion is registered for C7 (its registered exclusion list deliberately omits one — a specification fact, not an omission).
- **Contrast:** per formation date, mean fwd-return of high states − mean fwd-return of non-high states; dates lacking either side skipped and counted.
- **Inference:** daily series → NW t (lag = k), two-sided p, direction read afterwards; single-cell family (Holm identity at primary k).
- **Costs:** 0.60% RT floor reported (`theta_net_cost_floor`), never a verdict.
- **Constants:** `C7_HIGH_THRESHOLD = 2.0`, `C7_ADV_WINDOW = 20`, `PRICE_FLOOR = 100`, `RET1_EXCLUSION = 0.15`, `KS = [3,5,10]`, `PRIMARY_K = 5`, `FAMILY_ALPHA = 0.05`, `COST_RT_FLOOR = 0.006` — all module constants, not tunable config.

## C. Source provenance

Family map rows D/H/K/I/L (sha `e07dc07f…`) · descriptive pass `family_passD_states.json` + generator `17_family_passD.py` (the 2.0 boundary's source of truth) · custody handoff (primary-survivor designation) · BFI-001 frozen prereg `91c0eb9a…` (conventions) · Dataset B freeze manifest v1 (sidecar `95f2c998…`) · semantic register v1 (freq UNKNOWN/FORBIDDEN) · G1 registration/execution reports (conventions and FAIL record).

## D. Parameter consistency audit (registration ↔ harness ↔ sources)

| Parameter | Registration | Harness | Audit |
|---|---|---|---|
| intensity = gross/ADV20, ADV20 median-20 shift(1) | §B | `c7_build_panel` | test_adv20 (structural recompute) + test_intensity (exact values) |
| high ⇔ intensity ≥ 2.0 inclusive | §B | `inten >= C7_HIGH_THRESHOLD` | test_intensity boundary at exactly 2.0 |
| outcome/contrast/k-set/primary | §3 items 1–3 | `cell_c7` + `KS/PRIMARY_K` | test_ks_primary_contrast (engineered +2% verified to 1e-12; k=5/10 empty-by-construction asserted) |
| multiplicity single-family | §3 item 4 | Holm over {C7} at k=5 → holm_p = raw p | test_ks (holm identity) |
| MDE not a criterion | §3 item 5 | no power code exists | — |
| persistence context-only | §3 item 6 | figures never read by code | grep: absent from harness |
| exclusions + counts | §B/§2 | suspension/price/ret1/ADV20/gross/quarantine counters | test_registered_exclusions (all counts match hand-derivation) |
| freq-free | directive | C7 path reads only flow `value` (+ohlcv/calendar/PIT) | test_freq_never_accessed (poison → identical output) |
| fail-closed | `c7_registered` gate | `main_c7` refuses; `run_c7` raises | test_fail_closed_gate |

No registered parameter is unimplementable; no harness capability required a specification change.

## E. Data readiness

READY — identical to the freeze-readiness finding: gross from the frozen store (identity-verified), ohlcv/calendar/PIT pinned, RAJA quarantined, NF ratified but **not consumed by C7**. No Dataset B modification.

## F. Harness readiness

`c7_build_panel` / `cell_c7` / `run_c7` implemented in `g1_harness.py`; dispatch `python3 g1_harness.py c7` with the fail-closed `c7_registered` gate (currently **false**); deterministic JSON output `c7_real_output.json` (guarded path, NaN-sanitized). G1 dispatch and artifacts untouched.

## G. Test results

- `test_c7_registration.py`: **7/7 PASS** (all items in §D table).
- `test_g1_harness.py`: **16/16 PASS** (G1 machinery unaffected by the C7 additions).
- C7 fixture is hand-verifiable: engineered +2% spread asserted to 1e-12; boundary at exactly 2.0 inclusive; exclusion counts match hand-derivation exactly (11 formed / 24 quarantine / 100 ADV-missing / 4 gross-zero / 4 price / 1 suspension).

## H. Exact remaining blockers

**None mechanical or registration-related.** The only remaining step is the execution authorization itself: the owner sets `c7_registered=true` (a one-key change recorded in the run manifest), after which §I runs the registered test. Dataset B, NF, freq, and G1 states require no further action.

## I. Exact eventual execution command

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001/docs/research_programs/P-M/g1_harness"
# owner: set c7_registered=true in g1_config.json (one key), then:
python3 g1_harness.py c7        # → c7_real_output.json (fail-closed until then)
```

Run-book at execution: re-verify store sha256 `21661f03…` against the freeze manifest (NF is not consumed by C7; its digest check is not applicable), preserve `c7_real_output.json` + config snapshot + code sha256 + timestamp per the standing preservation rule.
