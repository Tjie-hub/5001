# C7 INTENSITY-STATE — REGISTERED EXECUTION REPORT (2026-09-14)

**Registered empirical test executed under:** `C7_REGISTRATION_v1_2026-09-11.md` (owner-approved; sha
`27c707efbcb7614bbc67772aa479c3e4f4edf622966dec706ad28afeb336e73d`, pinned in the run preflight manifest)
· authorized by **D-049 R-6** (`docs/roadmap/DECISION_LOG.md`) · governance baseline commit
**`bf9f8ecd71e0e89341604771465f93b17e33f850`** · **D-048 provenance hard gate applied** (`provenance.py`).

**Registered verdict (see §J): C7 NOT CONFIRMED** — primary k=5 Holm p = 0.6128 ≥ α = 0.05. Determinate
null, executed exactly as registered; no parameter was tuned, no variant was run, no rescue attempted.

---

## A. C7 registration confirmation

- Registration act performed this session: `g1_config.json` `c7_registered: false → true` (the only change;
  authorized by D-049 R-6, spec fixed by `C7_REGISTRATION_v1_2026-09-11.md` §2/§3 verbatim).
- Config identity: canonical sha256 **before** the act (HEAD `bf9f8ec` content) `b1099dbb284d1ea1…`;
  **after** the act (the config the run executed with) `8005eff5b53ed59d…` (canonical, `load_config`
  convention; raw-file sha at snapshot `00a2e598516920d6…` per the preflight manifest).
- No feature/threshold/horizon/outcome/control/inference/multiplicity/MDE/exclusion/cost parameter was
  invented or altered. Historical registry/lineage untouched (HYPOTHESIS_REGISTRY C-family rows, D-048/D-049
  receipts, G1 Run 1 artifacts, withdrawn C1a/C1b status all preserved).
- Harness fail-closed gate honored: `run_c7`/`main_c7` refuse without `c7_registered=true`; synthetic
  dispatch refused (`synthetic=false`).

## B. Final preflight gate table

| # | Gate | Result | Evidence |
|---|------|--------|----------|
| 1 | Dataset B frozen | **PASS** | freeze manifest v1 present; sidecar sha `95f2c998…` verified; `gates.dataset_b_frozen=true` |
| 2 | Dataset B hash = `21661f03…` | **PASS** | recomputed store sha256 `21661f033145ef90657f8d133ced62a3cd4ba85cdaa7ece2a4b19f4940b755a8` (276,115,456 bytes); `-wal` 0 bytes (no uncheckpointed content); re-verified by provenance snapshot at run time; unchanged post-run |
| 3 | C7 registration active | **PASS (after act)** | `c7_registered=true`; D-049 R-6 authorization; run stamped config sha `8005eff5…` |
| 4 | Approved stockbit_flow NF definition active | **PASS** | D-049 R-3 ratified + committed; NF = (buy_lot−sell_lot)/(buy_lot+sell_lot), T+1, market-flow-control only. Window counts re-verified: 366,725 rows / 972 tickers. Byte-level digest caveat → §L1 |
| 5 | C7 does not read broker_flow.freq | **PASS** | code-verified: `c7_build_panel` reads only flow `value`; freq-poison determinism test green (suite 7/7) |
| 6 | PIT alignment | **PASS** | roster v2 `afd0d544…` + calendar v2 `5012be23…` verified via fail-closed `load_artifact`; membership at formation only |
| 7 | Corporate-action handling | **PASS** | CA strictly inside (t, t+k] excluded per horizon (3/5/10 observations dropped); G1-registered machinery; unapplied-split detection + RAJA quarantine active |
| 8 | Suspension handling | **PASS** | 474 (ticker, session) formations excluded for suspension at t; counted in panel accounting |
| 9 | No future leakage | **PASS** | formation consumes only info dated ≤ t (flow `trade_date==t`; ADV20 shift(1) — structural test green; ret1 at t) |
| 10 | Required inputs exist | **PASS** | walkforward.db 13.66 GB (ohlcv 1,084,738 rows; suspension_events 3,189; corporate_action_events 12,353; corporate_actions 2,171; stockbit_flow 377,230); store + artifacts present; 365,829 final ohlcv bars in window; flow rows loaded 1,518,727 |
| 11 | No C8 state/conditioning | **PASS** | `run_c7` executes only `c7_build_panel` → `cell_c7`; nothing on the path reads or conditions on C8 constructs |
| 12 | Production DB isolation | **PASS** | all connections `mode=ro` + `PRAGMA query_only=ON`; harness writes only `runs/<run_id>/`; walkforward.db / research.db / store inode+size+mtime **identical** pre/post run; sole external holder (routine cron, python3 PID 6791) documented — mtimes on both DBs (08:00/08:15) predate the run (08:53Z+), so no write is attributable to this task |
| 13 | Registered spec matches committed registration | **PASS** | registration doc unmodified vs `bf9f8ec`; code/spec conformance covered by deterministic suites: **31/31 passed** (C7 7/7, G1 16/16, provenance 8/8) |
| — | D-048 execution conditions | **PASS** | harness/governance committed at `bf9f8ec`; immutable `runs/<run_id>/` provenance wrapper implemented, tested, and enforced (snapshot → seal) |

## C. Exact command executed

```
cd docs/research_programs/P-M/g1_harness
python3 g1_harness.py c7        # exit 0
```

No environment overrides, no flags, no variants, single execution.

## D. Dataset fingerprint / code / run identity

| Item | Value |
|---|---|
| run_id | `RUN-20260914T015335Z-41bea166a025` (created 2026-09-14T01:53:35Z) |
| preflight_digest | `41bea166a025db482eee6d7380abe5f102870ec513d7be49afaae99019f21ac8` |
| store sha256 | `21661f033145ef90657f8d133ced62a3cd4ba85cdaa7ece2a4b19f4940b755a8` |
| freeze manifest sha256 | `95f2c998760ba6f2e687b091950315ce45370854226f419ef768f2b4bcc17af5` |
| DATASET_B_FINGERPRINT_v2 | `1a68ab1c6c33409f16fe1c4dd40895c9f5a1b743693d05621e7338086cb8c5d9` — **reproduced at preflight** (30,626 cells / 100 tickers, RAJA quarantined, capture 30,877 SUCCESS + 3 EMPTY, 0 failed) |
| PIT roster v2 sha256 | `afd0d544a0f9a217c1c6f068fc0f800f2abeb84ff5c7f71a0f0bc14007949d0c` |
| session calendar v2 sha256 | `5012be2315dc82ccfd65a2b117e1977753f0a7d3214693821b39077cd18043fa` |
| executed g1_harness.py sha256 | `139663aac6552c4cc6f700c64a845abee970dc6f5714d1bcaf648ee0112133ff` |
| executed foundation.py sha256 | `e427cc482fa1e00cfda830eb5a6d84eda3cc583dde0a81fc7c1d90c47b7eab29` |
| registration doc sha256 | `27c707efbcb7614bbc67772aa479c3e4f4edf622966dec706ad28afeb336e73d` |
| config sha256 (stamped in output) | `8005eff5b53ed59d80dfb49d7d0a8ac2ffcbeb5af1aeda824f1e796e31611455` |
| git state at run | commit `bf9f8ec`, dirty=true (476 lines — pre-existing tree-wide housekeeping + the registration-act config flip; recorded by the wrapper) |
| output sha256 (seal) | `c1cc10a271dcc9eca51a44a0623a45196708b53010d24ae53f9014ac8d6aa2d3` |
| seal | `valid_provenance = true`, `drifted_files = []`, sealed 2026-09-14T01:54:03Z |

## E. Sample and exclusion counts (panel accounting)

| Count | Value |
|---|---|
| flow rows in (store window) | 1,518,727 |
| dropped quarantine (RAJA flow rows) | 15,440 |
| panel rows formed | **27,640** |
| excluded suspension at t | 474 |
| excluded missing ADV20 history (warm-up) | 1,602 |
| excluded gross ≤ 0 | 0 |
| excluded price < 100 | 489 |
| excluded \|ret1\| ≥ 0.15 / undefined prior close | 263 |
| CA-window exclusions (strictly inside (t, t+k]) | k=3: 3 · k=5: 5 · k=10: 10 |
| formation dates skipped (missing state side) | k=3: 14 · k=5: 18 · k=10: 32 |
| daily observations (n_days) | k=3: 342 · k=5: 338 · k=10: 324 |

## F. Primary registered result (k = 5, family α = 0.05)

- **θ_mean (high-intensity − non-high, daily contrast) = +0.001338 (+13.38 bp)**
- Newey-West t (lag = 5, daily series = date clustering) = **+0.5061**, n = 338 days
- Two-sided p = **0.612807**
- Direction read afterwards (registered convention, never prejudged): positive, statistically indistinguishable from zero.

## G. Comparison result (registered contrast, secondary horizons)

| k | θ_mean | NW t | n_days | p (2-sided) |
|---|---|---|---|---|
| 3 | +0.000592 (+5.92 bp) | +0.2951 | 342 | 0.767895 |
| 5 (**primary**) | +0.001338 (+13.38 bp) | +0.5061 | 338 | 0.612807 |
| 10 | +0.002866 (+28.66 bp) | +0.8560 | 324 | 0.392020 |

## H. Statistical / inference output

- Inference: daily state-contrast series → Newey-West t with lag = horizon (registered BFI-001 §G
  convention), two-sided p = erfc(|t|/√2).
- Multiplicity: C7 registered as a **single-cell family** (D-049 §3 item 4) → Holm at primary k=5 is the
  identity: **holm_p = 0.612807 = raw p**; `holm_significant = false` at α = 0.05.
- MDE/power: **not used as a confirmation criterion** (registered §3 item 5); no power claim attached.

## I. Cost-adjusted result (registered sensitivity, never a statistical verdict)

`theta_net_cost_floor = θ_mean − 0.006` (0.60% round-trip floor, BFI-002 memo §8):

| k | θ_net (cost floor) |
|---|---|
| 3 | −0.005408 (−54.08 bp) |
| 5 | −0.004662 (−46.62 bp) |
| 10 | −0.003134 (−31.34 bp) |

## J. Final registered verdict

**C7 = VALID execution → NOT CONFIRMED (determinate null).** The registered decision rule is Holm
significance of the primary k=5 contrast at family α = 0.05: observed holm_p = 0.6128 — far from the
threshold; no cell in the horizon set approaches significance. Per the registered rule, C7 is not
confirmed; the intensity-state (gross/ADV20 ≥ 2.0) contrast carries no detectable next-session directional
return information at the registered horizons in Dataset B. The descriptive persistence figures (45.7–48.1%
vs 11.3%) remain context-only. No further interpretation is authorized beyond this rule.

## K. Artifact paths

- Raw output (sealed): `docs/research_programs/P-M/g1_harness/runs/runs/RUN-20260914T015335Z-41bea166a025/c7_real_output.json`
- Preflight manifest: `…/runs/runs/RUN-20260914T015335Z-41bea166a025/preflight_manifest.json`
- Seal: `…/runs/runs/RUN-20260914T015335Z-41bea166a025/seal.json`
- This report: `docs/research_programs/P-M/g1_harness/C7_EXECUTION_REPORT_2026-09-14.md`
- Governance basis: `docs/roadmap/DECISION_LOG.md` D-048/D-049 · `C7_REGISTRATION_v1_2026-09-11.md` ·
  `DATASET_B_FREEZE_MANIFEST_v1.json` (all at commit `bf9f8ec`)

## L. Anomalies / infrastructure observations

1. **NF window digest not byte-reproducible (does not affect C7).** The pin `60f5f91c…` (42,912,339 bytes;
   366,725 rows; 972 tickers — counts re-verified exactly) does not record the extract serialization, and no
   committed code constructs it; byte-level re-verification was therefore impossible. This pin was a
   run-time requirement of the **G1** registration (G1 Run 1 executed 2026-09-11 with the digest recorded in
   its manifest). The registered C7 path never reads `stockbit_flow`/`net_flow` (code-verified), so the C7
   result is invariant to it. Recorded here per the halt-and-repin rule's spirit: **no re-pin was attempted.**
   Recommendation: future pins should carry their construction recipe.
2. **Provenance runs path is doubled** (`runs/runs/<run_id>/`) — `provenance.RUNS_DIR` already ends in
   `runs/` and `snapshot_run` appends another `runs/` segment. Cosmetic; immutability contract unaffected.
   Left unmodified to preserve the executed-code hash.
3. **Stale provenance label in output**: `net_flow_source: "stockbit_flow (PROVISIONAL, unratified)"` — the
   same known caveat as G1 Run 1 (`known_label_caveat`); the label predates D-049 ratification and was left
   unmodified to preserve the executed-code hash. C7 does not consume this field's data.
4. **Working tree not committed.** The registration act (`g1_config.json`), the D-049 R-2 semantic-register
   gate appendix, and this report are uncommitted at report time (the run recorded git_state dirty=true).
   A lineage commit is the natural next owner action; none was performed in this task.
5. Routine cron activity on `research.db`/`walkforward.db` was observed (mtimes 08:00/08:15 local, external
   PID 6791 holding walkforward.db) and attributed via process-level evidence, not mtime alone: pre/post
   inode+size+mtime of both DBs and the store are identical, and the C7 process held only `mode=ro` +
   `query_only` connections.

**Stop:** per registered-run discipline, no follow-up analyses, no C8 testing, no parameter changes follow
this execution.
