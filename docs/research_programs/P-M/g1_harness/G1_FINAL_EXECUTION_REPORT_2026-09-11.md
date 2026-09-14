# G1 FINAL EXECUTION REPORT — RUN 1 — 2026-09-11

**The first real G1 empirical run.** Executed exactly as registered (`G1_REGISTRATION_v1_2026-09-11.md`). No methodology, threshold, k, α, cost, exclusion, inference, or control change before, during, or after. No post-hoc rescue. Raw output preserved.

**Registered verdict (§N): FAIL — neither retained arm (C2, C3) confirmed.**

---

## A. Pre-run integrity checks (all PASS immediately before execution)

| Check | Result |
|---|---|
| Dataset B store sha256 == freeze manifest | `21661f033145ef90…` — **match** |
| Dataset B FINGERPRINT_v2 reproduced from store | `1a68ab1c6c33409f…` — **match** (30,626 cells / 100 tickers / RAJA quarantined) |
| Stockbit NF digest (identical pinned `sqlite3 -json` serialization) | `60f5f91c33b929cd…` — **match** |
| PIT roster/calendar | v1 `f7e2fec0…`, v2 `afd0d544…` (memberships content-identical, Σ = 30,880), calendar v2 `5012be23…`, 386 sessions |
| Gates | all four TRUE |
| `synthetic` / `freq_resolution` | `false` / `"withdrawn"` |
| C1a/C1b mechanically non-executable | config branch → `WITHDRAWN_FREQ_DEPENDENT` unconditionally (test-verified both with freq gate open and closed) |
| Production DB write target | none — all connections `mode=ro` + `PRAGMA query_only`; harness writes only `g1_real_output.json` in the harness dir |

## B. Exact registration/config identity

- Registration: `G1_REGISTRATION_v1_2026-09-11.md`
- Config: `g1_config.json` sha256 `7211ad94c44614f2…` (the file itself is the preserved snapshot; unchanged post-run)
- Code at execution: `g1_harness.py` `9471c740175b3135…`; `foundation.py` `e427cc482fa1e00c…`
- Command: `G1_CONFIG=./g1_config.json python3 g1_harness.py` (cwd = `g1_harness/`)
- Executed at (UTC): `2026-09-11T02:31:18Z` · exit code 0

## C. Execution status

**COMPLETED.** `run_mode: REAL`. Output: `g1_real_output.json` (preserved byte-identical as `G1_REAL_OUTPUT_RUN1_2026-09-11.json`, sha256 `74883c04cf80a867…`). Run manifest: `G1_RUN_MANIFEST_RUN1_2026-09-11.json`. The prior synthetic dry-run artifact was not touched.

## D. C1a/C1b withdrawal confirmation

All six C1a/C1b cells (3 horizons × 2 arms) emitted **`WITHDRAWN_FREQ_DEPENDENT`** with `theta_mean = nw_t = p = null`. No substitute results were computed. Confirmed in the output exactly as registered.

## E–G. C2 and C3 results across k (exact, as produced)

| Arm | k | n days | θ mean | θ (bp) | NW t | p |
|---|---|---|---|---|---|---|
| C2 | 3 | 365 | +0.000566 | +5.7 | +0.745 | 0.4565 |
| C2 | **5** | **359** | **+0.000492** | **+4.9** | **+0.548** | **0.5835** |
| C2 | 10 | 345 | −0.000209 | −2.1 | −0.157 | 0.8754 |
| C3 | 3 | 335 | +0.001599 | +16.0 | +1.113 | 0.2658 |
| C3 | **5** | **329** | **+0.000577** | **+5.8** | **+0.323** | **0.7468** |
| C3 | 10 | 315 | −0.000734 | −7.3 | −0.261 | 0.7944 |

Sign consistency across k ∈ {3,5,10}: C2 `+/+/−` — inconsistent. C3 `+/+/−` — inconsistent. Neither arm shows the monotone or consistent pattern the registered interpretation requires.

## H. Primary k=5 result

- **C2:** θ = +4.9 bp/period, NW t = +0.548, p = 0.584.
- **C3:** θ = +5.8 bp/period, NW t = +0.323, p = 0.747.
- **C1a:** `WITHDRAWN_FREQ_DEPENDENT` (no numbers, per registration).

## I. Holm-adjusted inference (retained family {C2, C3} at k=5, α=0.05)

| Arm | raw p | Holm p | Holm-significant |
|---|---|---|---|
| C2 | 0.5835 | **1.0** | No |
| C3 | 0.7468 | **1.0** | No |

No retained arm is Holm-significant at the primary horizon.

## J. Gross results

As in §E–G: the largest gross effect in the registered family is C3 at k=3 (+16.0 bp/period, NW t = +1.113) — below any conventional significance line and not a registered primary.

## K. Net / cost-adjusted results (0.60% RT floor, reported sensitivity)

| Arm | k | θ net of 0.60% floor |
|---|---|---|
| C2 | 3 | −0.005434 |
| C2 | 5 | −0.005508 |
| C2 | 10 | −0.006209 |
| C3 | 3 | −0.004401 |
| C3 | 5 | −0.005423 |
| C3 | 10 | −0.006734 |

Every cell is far below the cost floor after the registered sensitivity deduction. No economic-relevance reading survives.

## L. Sample / exclusion counts (from the run's own accounting block)

- Flow rows in: **1,518,727** (duplicates 0, abnormal 0, zero-value 0, unclassified 0 — the frozen store is clean).
- Quarantined (RAJA) flow rows dropped: **15,440**.
- Panel rows formed: **28,624**. Exclusions en route: suspension at t **474**; price floor **509**; \|ret1\| ≥ 15% **343** (includes formations with undefined prior close); no ratified NF **516** (stockbit_flow uncovered + zero-denominator cells).
- Formation dates: **375** (11 dropped below the 40-name floor); 2025-01-03 → 2026-08-27.
- Corporate-action window exclusions: k=3 → **3**, k=5 → **5**, k=10 → **10** cells.
- Species classifier (provenance only, C1a withdrawn): 95/95 brokers classified from the frozen prefix; 0 unclassified.

## M. Warnings / INVALID / UNRESOLVABLE conditions

- **Warnings:** none raised by the run (exit 0, no errors). One cosmetic caveat recorded in the run manifest: the output's `provenance.net_flow_source` string reads "PROVISIONAL, unratified" — written before NF ratification; the executed construction IS the ratified stockbit_flow share-ratio NF. The label was left unmodified to preserve the executed-code hash; correction deferred to a future maintenance pass.
- **INVALID / UNRESOLVABLE:** none. All checks passed; the run is valid; the result is determinate (329–365 daily observations per cell — the verdict is not power-limited at the registered inference).

## N. Registered PASS / FAIL / UNRESOLVABLE decision

Per `G1_REGISTRATION_v1_2026-09-11.md` §8 (confirmed iff Holm p < 0.05 at primary k AND sign consistency across k):

- **C2: NOT CONFIRMED** (Holm p = 1.0; signs +/+/−).
- **C3: NOT CONFIRMED** (Holm p = 1.0; signs +/+/−).
- C1a/C1b: WITHDRAWN — no verdict, and no substitute computation.

**Registered G1 family outcome: FAIL** — the retained freq-free family produced no Holm-confirmed arm at the primary horizon, with no sign consistency across horizons, and gross effects far below the registered cost floor. Per the no-rescue rule: C2's failure is not offset by C3, C3's by C2, and the withdrawn arms stay withdrawn. Per the design memo's own falsification language, the honest reading is recorded, not repaired: on this data, at this specification, the breadth-surprise and conduit-disagreement mechanisms did not confirm.

---

## Preservation record

| Artifact | sha256 (16…) |
|---|---|
| Raw output (immutable copy) `G1_REAL_OUTPUT_RUN1_2026-09-11.json` | `74883c04cf80a867` |
| Run manifest `G1_RUN_MANIFEST_RUN1_2026-09-11.json` | (contains all hashes below) |
| Config `g1_config.json` | `7211ad94c44614f2` |
| Code `g1_harness.py` | `9471c740175b3135` |
| Code `foundation.py` | `e427cc482fa1e00c` |
| Freeze manifest | `95f2c998760ba6f2` |
| Dataset B store | `21661f033145ef90` |
| NF window digest | `60f5f91c33b929cd` |

Synthetic dry-run artifact untouched. No commits. No methodology changes. The next action, if any, belongs to the owner: registration of follow-up or closure per the program's own ledger rules — no re-specification of this family.
