# G1 EXECUTION REPORT — 2026-09-11

**Task:** finalize Dataset B and run G1 (owner-approved sequence). Read-only except the explicitly authorized freeze act.

---

## EXECUTION OUTCOME: **G1 NOT RUN — 3 GOVERNANCE GATES NOT EXPLICITLY RESOLVED**

Dataset B **is now FROZEN** (step 1 completed and verified). Steps 3–5 were executed up to the fail-closed preflight, which refuses execution on exactly the gates below. Per the task's hard rule — *"If any required governance gate is not explicitly resolved, DO NOT RUN G1. Return the exact blocking gate instead"* — execution stopped here.

### Blocking gates (exact)

1. **`prereg_confirmed`** — H0–H3/P0 artifact NOT FOUND (exhaustive retrieval 2026-09-11); no replacement registration exists. `G1_OWNER_DECISION_PACKET_2026-09-11.md` §1/§7: **OWNER** decision.
2. **`freq_semantics_ratified`** — `broker_flow.freq` UNKNOWN/FORBIDDEN as ticket denominator (`SEMANTIC_REGISTER_v1`); packet §3 presents Option A (vendor probe) vs Option B (withdraw C1a/C1b, proceed freq-free) **without choosing**; §7: **OWNER** decision.
3. **`net_flow_source_ratified`** — no G1-scoped NF source ratified among the four catalogued constructions (packet §4, N1–N4); packet §7: **OWNER** decision.

`dataset_b_frozen` is now TRUE (authorized by this task's step 1).

---

## A. Freeze verification (step 1 — COMPLETED)

| Step | Result |
|---|---|
| WAL checkpoint | `PRAGMA wal_checkpoint(TRUNCATE)` → `(0,0,0)`; WAL was already empty (backfill closed cleanly); store file hash **identical before and after** the checkpoint |
| Final store integrity | `PRAGMA integrity_check` → **ok** |
| Final store file identity | sha256 `21661f033145ef90657f8d133ced62a3cd4ba85cdaa7ece2a4b19f4940b755a8`, 276,115,456 bytes |
| Post-checkpoint counters | 30,880 manifest cells = **30,877 SUCCESS + 3 EMPTY**; 1,518,727 `broker_flow_b` rows; truncation 0 |
| **Dataset B fingerprint v2 reproduced** | `1a68ab1c6c33409f16fe1c4dd40895c9f5a1b743693d05621e7338086cb8c5d9` — recomputed from the materialized store post-checkpoint, **== recorded artifact** (30,626 cells / 100 tickers in scope, RAJA quarantined) |
| **Supplementary candidate digest reproduced** | `1303378683819f17afa41001dd64574708127a6494ecdd135df23c6b6a2088dd` — recomputed, **== recorded** (an initial MISMATCH was diagnosed as a verification-script bug — the draft manifest's own `store_fingerprint` key was included in the re-hash input; with the key stripped, exact match. Store content never changed: FINGERPRINT_v2 reproduced independently throughout) |
| Production fingerprint v1 reproduced | `b0ad62826671e7da…` — exact (isolation evidence) |
| Freeze manifest created | `dataset_b/artifacts/DATASET_B_FREEZE_MANIFEST_v1.json` (sidecar sha256 `95f2c998760ba6f2…`) — records store hash/size, all three fingerprints, capture summary, validation receipts (35/35 + 13/13), standing exceptions, immutability rule |
| Frozen | **YES** — after all checks passed. Underlying data untouched (checkpoint is file-layout only; content digests reproduce) |

## B. Gate states and their explicit authorization

| Gate | State | Authorization source |
|---|---|---|
| `dataset_b_frozen` | **TRUE** (set 2026-09-11) | Owner directive, this task step 1 ("Execute … 1. DATASET B FREEZE"); packet §5 marks the candidate READY FOR OWNER FREEZE AUTHORIZATION with "Freeze now" the exercised option |
| `prereg_confirmed` | **FALSE — BLOCKING** | Packet §1/§7: NOT FOUND, OWNER decision. Not resolved by the owner approval |
| `freq_semantics_ratified` | **FALSE — BLOCKING** | Packet §3/§7: Option A vs B explicitly unchosen ("presented without a choice made"). Not resolved by the owner approval |
| `net_flow_source_ratified` | **FALSE — BLOCKING** | Packet §4/§7: N1–N4 catalogued, none registered for G1. Not resolved by the owner approval |

The packet's own scope statement governs: *"It creates no new preregistration, ratifies no parameter, selects no option, and changes no gate… All five gates are currently closed. None can be closed by this packet."* "OWNER HAS APPROVED PROCEEDING" authorized **this sequence** (freeze → gate check → conditional run); it did not itself ratify freq/NF/prereg, and no other repository record does.

## C. Exact execution configuration

Final configuration assembled and preflighted (`synthetic=false`, `dataset_b_frozen=true`, other gates false). It was **not** used for execution (refused). Contents: `g1_config.json` gates as in §B; capture grid roster `f7e2fec0…` (v1) / calendar `5012be23…` (v2) — verified content-identical memberships; store fingerprint `1a68ab1c…` verified at load time by the manifest checks above.

## D. Execution result

**NOT EXECUTED.** `python3 g1_harness.py` under the final configuration exits with code 2 before any data access:

```
G1 NOT LAUNCHED — mechanical gates:
  - gate prereg_confirmed is false — H0-H3/P0 not locked
  - gate freq_semantics_ratified is false — C1a/C1b blocked (SEMANTIC_REGISTER_v1: broker_flow.freq UNKNOWN)
  - gate net_flow_source_ratified is false — broker_flow net is identically 0 at limit=150; control source unratified
exit=2
```

## E. Sample/exclusion counts

**NOT EXECUTED** (no sample formed). The only population counts produced are the freeze verification counts in §A.

## F. Primary C1a result

**NOT PRODUCED.** (Independently of the gates: C1a would additionally emit `BLOCKED_FREQ_SEMANTICS` under the current freq decision — §B.)

## G. C2/C3 results

**NOT PRODUCED.** C2/C3 are freq-free and mechanically computable, but running a partial family was not authorized: the packet leaves Option A vs B explicitly open, and running G1 freq-free would itself be a freq decision.

## H. Holm-adjusted inference

**NOT EXECUTED.** Harness machinery verified separately (synthetic suite); no real family p-values exist.

## I. Gross and net/cost-adjusted results

**NOT PRODUCED.**

## J. INVALID / UNRESOLVABLE conditions

1. H0–H3/P0 preregistration: **NOT FOUND** anywhere reachable; no registered version/hash exists on this side to verify any future copy against (`G1_AUTHORITATIVE_PREREG_RETRIEVAL_2026-09-11.md`).
2. §4/§5 H1 OOS/train-test contradiction: **OPEN** (D-032 Item C).
3. ≤200% monthly turnover criterion: **OPEN** — no operational formula (D-032 Item D).
4. `freq` semantics: **UNKNOWN/FORBIDDEN** (vendor probe or withdrawal decision outstanding).
5. NF control source: **CONFLICTING/unratified** (N1–N4).
6. After-close/T+1 convention, ST tercile cuts, ADV20 binding, inference binding, disclosure-cap composition, effective-N: **unratified** (packet §2) — code-level defaults exist but await the authoritative anchor.

## K. Registered decision rule verdict

**UNRESOLVABLE.** No registered decision rule (PASS/FAIL/KILL) is available to apply — the preregistration that would contain it has not been located, and no G1 numbers exist to feed it. This is a governance state, not an empirical result.

## Preservation record (step 5, partial — nothing to preserve from an unrun execution)

- Freeze manifest: `dataset_b/artifacts/DATASET_B_FREEZE_MANIFEST_v1.json` (+ `.sha256`)
- Freeze candidate + verification: `g1_harness/G1_FREEZE_CANDIDATE_STORE_MANIFEST_2026-09-11.json` (draft digest reproduced at freeze)
- Gate-check transcript: reproduced verbatim in §D
- Dry-run artifact `g1_dry_run_output.json` **not overwritten** (last write remains the byte-identical triple-verified synthetic artifact, sha256 `70dff8d5cc4c4089…`)
- No configuration/specification/harness changes in this task beyond `g1_config.json` `dataset_b_frozen: false→true` (+note) and the new freeze manifest artifact

## Unblocking path (owner actions only)

1. Recover `BROKER_FLOW_PREREGISTRATION.md` from the Windows/ZCode machine (or issue a dated replacement registration) → sets `prereg_confirmed`.
2. Choose freq Option A (vendor probe — raw responses already preserved) or Option B (withdraw C1a/C1b, proceed freq-free) → sets `freq_semantics_ratified`.
3. Register an NF source/construction for G1 among N1–N4 (or a fifth) → sets `net_flow_source_ratified`.
4. Re-run this exact command (§D transcript) — the harness will then execute end-to-end with no further engineering.
