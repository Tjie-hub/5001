# G1 Owner Decision Packet — Final Pre-Execution Gates

**Date:** 2026-09-11 · **Mode:** DOCUMENTATION / GOVERNANCE ONLY

**This packet does not run G1, does not modify data, does not modify the G1 methodology, and is not a replacement preregistration.** It exists to lay out, with exact citations, what the repository's own records already establish — so the Owner can make each remaining decision without re-deriving it. Nowhere below does this document choose an option on the Owner's behalf.

---

## 1. H0–H3/P0 artifact status

**Status: NOT FOUND.**

Exact evidence (from `g1_harness/G1_AUTHORITATIVE_PREREG_RETRIEVAL_2026-09-11.md`, an exhaustive prior search, not repeated here):

- The expected location, `C:\Users\tjies\ZCodeProject\`, is a Windows path — **this machine has no Windows volume at all** (`lsblk`-verified: one Linux ext4 system disk, one empty NTFS disk, one populated personal-data NTFS disk with no `broker-flow-v002` content).
- Every reachable location was searched by filename and content grep for `broker-flow-v002`, `BROKER_FLOW_PREREGISTRATION`, `H0`–`H3`, `P0`: the entire `/mnt/storage2tb` volume, `/home/tjiesar/ZCodeProject/**`, `/home/tjiesar/10 Projects/**`, home-directory archive folders, Downloads (including three derived audit PDFs), and a Gmail takeout archive. **Zero definition-bearing hits.**
- `docs/research_programs/HYPOTHESIS_REGISTRY.md` contains zero references to `broker-flow-v002`, `broker_flow_v002`, `H0-H3`, or `walkforward_v002` — confirmed by direct grep in this task, corroborating D-032's own scope note that it is "not yet a registered research object in this repository."

**What D-032 establishes** (`docs/roadmap/DECISION_LOG.md` §2e, 2026-09-08): D-032 is explicitly **not** the preregistration and **not** a verified cross-check against it — it is "a Dell-side record of owner instructions issued directly in that session." It records two ACCEPTED decisions (Decision A — analytical window `2025-01-02` → v002 freeze date, no redefinition to fit current coverage; Decision B — complete-backfill-before-freeze, stop-and-escalate rather than silently changing spec) and leaves two items explicitly OPEN (Items C and D — see §2 below). It also states the authoritative corpus "is understood to live on" the (now confirmed absent) Windows/ZCode machine.

**What cannot be reconstructed:** the primary estimand, controls, inference binding, MDE, PASS/FAIL/KILL criteria, availability convention, and freq/NF definitions for H0–H3/P0 are not recoverable from implementation code, design memos, or audit PDFs — none of those are the preregistration, and the retrieval report's hard rule (honored here) is that nothing gets reconstructed from them. No registered version, date, or hash of the "locked" preregistration exists anywhere on this side to verify a future copy against.

## 2. Open preregistration items

All four items below are recorded verbatim from existing governance/audit artifacts — none are newly characterized by this packet.

**§4 vs §5 OOS/train-test contradiction** — D-032 Item C, status OPEN — NOT RESOLVED, quoted verbatim: *"The locked preregistration contains a contradiction between: §4: no train/test split for H0/H1 specification tests; §5: H0/H1 language containing OOS/fold criteria. This requires a dated explicit preregistration decision before H1 results can be interpreted. No H1 fold criterion is to be silently added or removed."*

**≤200% monthly turnover criterion** — D-032 Item D, status OPEN — NOT RESOLVED, quoted verbatim: *"The §5 ≤200% monthly turnover criterion remains unresolved until an explicit mathematical operational definition is recorded. Do not invent a turnover formula. H1 cannot receive a definitive verdict based on that criterion until it is formally defined."*

**After-close / T+1 convention** — DEP-B matrix row 8 (`ZCodeProject/pm_data_audit/PM_CUSTODY_RECONCILIATION_HANDOFF_2026-09-10.md`), status **NOT FOUND**: "After-close availability asserted in prose only (BFI-001 §C, HYP-PM-0003 MANIFEST); no codified convention artifact in `dataset_b/` or governance docs." The G1 harness's own readiness report (§9, "T+1 LATENCY CHECK — PASS") notes this is a code-level guarantee only (flow rows with `trade_date == t` exclusively feed formation at t) and separately flags: "Standing DEP-B note: the after-close availability *convention* remains prose-only... inherits whatever the authoritative preregistration declares; no code assumption beyond `trade_date==t`."

**Other missing binding parameters identified by ZCode** (`g1_config.json` `_notes`, DEP-B matrix):

| Parameter | Current state | Source |
|---|---|---|
| ST tercile cuts | Frozen at ±1/3 **from the BFI-002 design memo's descriptive distribution**, explicitly NOT from returns; config note: "Must be ratified verbatim in the authoritative preregistration before any real run." | `g1_config.json` |
| ADV20 statistic binding | Implemented as rolling-20-session median, `shift(1)` — the **inherited BFI-001 convention**, not independently ratified for G1 | `G1_MECHANICAL_READINESS_2026-09-10.md` §11 item 2 |
| Inference method binding | Newey-West(k) daily-series clustering — **inherited BFI-001 convention**; config note: "If the authoritative preregistration specifies a different (or additional) inference, THAT config replaces this file's defaults" | `g1_config.json` `_notes.inference` |
| Disclosure-cap composition | DEP-B matrix row 3, status **NOT FOUND** — "No governance treatment; appears only descriptively in ZCode family map (18.2% of ticker-day-side cells at cap; top-1 side share p50 53%)" | `PM_CUSTODY_RECONCILIATION_HANDOFF_2026-09-10.md` |
| Effective-N methodology | DEP-B matrix row 6, status PARTIALLY RESOLVED — bootstrap CI + dependence-sensitivity diagnostic, explicitly labeled "diagnostic, not correction"; no ratified effective-N methodology artifact exists | same |

**Note on matrix staleness:** the DEP-B matrix above is dated 2026-09-10. Two of its rows (5 — forward-return/RAJA implementation; 7 — Dataset B identity/custody) describe a state this packet's own current evidence (§5 below) has since superseded — the "13 unexplained outside-band moves" and "32/33 pass" it cites were resolved (all 15 reconciled: 14 legal, 1 quarantined; 35/35 now passes) and Dataset B capture has since completed. Rows 1, 2, 3, 6, 8 (freq, NF, cap composition, effective-N, timestamp convention) remain open exactly as recorded.

## 3. FREQ decision — evidence only

No authoritative source defines `broker_flow.freq`. Evidence (`G1_PREEXECUTION_SEMANTICS_AUDIT_2026-09-10.md` §1-2):

- `DATASET_B_SEMANTIC_REGISTER_v1.json` — status **UNKNOWN**; `research_use`: "FORBIDDEN as a transaction count or ticket-size denominator until a vendor probe establishes its unit." Evidence: the fetcher maps one vendor field onto both buy and sell rows; against the independent `stockbit_flow` daily summary over 34,017 ticker-days, `SUM(freq)/(buy_freq+sell_freq)` has median 0.0080 (~100× shortfall, beyond what truncation explains).
- BFI-001 frozen preregistration (`91c0eb9a4a42630f…`, frozen 2026-09-03) lists `freq` as a carried field only — no definition given; none of its 14 registered cells consume it.
- BFI-002 design memo (DESIGN ONLY, not registered) uses freq conditionally, every usage marked "[DEP-B: orders-vs-fills semantics still open]"; its own §9: *"If Dataset B resolves freq against us... C1a/C1b are declared untestable as specified and the design is withdrawn, not re-cut."*

Two documented options, presented without a choice made:

**OPTION A — vendor semantics probe.** Run a probe to establish `freq`'s actual unit (orders vs. fills; side-specific; `lot=0` treatment) against Stockbit. Raw vendor responses containing `freq` are already preserved (Dataset B store `raw_responses`, and `pm_data_audit/stockbit_limit150_trial/raw/`) as the available evidence base for such a probe — no such analysis was performed by any prior audit.

**OPTION B — explicitly withdraw freq-dependent C1a/C1b and proceed with freq-free candidates.** The design memo itself names this fallback: C3 (freq-free, cap-robust) as lead, C2 as secondary. The G1 harness already implements this mechanically — `enforce_freq_gate: true` in `g1_config.json` causes C1a/C1b to emit `BLOCKED_FREQ_SEMANTICS` with no numbers while C2/C3 remain computable.

## 4. NF decision — evidence only

Three catalogued constructions, disagreeing on source, formula, and units (`G1_PREEXECUTION_SEMANTICS_AUDIT_2026-09-10.md` §4, N1–N5):

| # | Source | Construction | Status |
|---|---|---|---|
| N1 | `HYP-PM-0003_REGISTERED.md` | `net_flow(ticker,date) = SUM(lot)` from `broker_flow`, signed lots | **Registered historically** (broker_flow), but the hypothesis it fed **FAILED (F2)**, and the construction is **identically zero at limit=150** (exchange identity — buy/sell are the two sides of the same trade) |
| N2 | BFI-001 frozen preregistration (`91c0eb9a…`, frozen 2026-09-03) | `OFI_vendor(t) = (buy_lot−sell_lot)/(buy_lot+sell_lot)` from `stockbit_flow` — "OFI control only" | **Frozen/registered, but scoped to BFI-001's own model ladder** (its M2 generic order-flow control) — not to G1/C1a |
| N3 | BFI-002 design memo (DESIGN ONLY) | `NF(i,t) = (buyV − sellV)/gross` from `broker_flow` rows | The G1-scoped construction as drafted — but design-only, unregistered, and structurally ≡0 at limit=150 |
| N4 | Family map §3 (discovery artifact) | Amendment: NF control should come from `stockbit_flow`'s full-market aggregate instead | Explicitly "**recorded, not registered**"; carries its own unresolved validation requirement (vendor net/lot semantics for `stockbit_flow` are themselves unratified — no `SEMANTIC_REGISTER_v1` entry exists for that table at all) |

Family map's own governing statement: *"No candidate may use broker_flow net as a signal or control — it is mechanically ~0."*

The three documented alternatives, presented without a choice made:

- **broker_flow signed net (N1/N3)** — registered historically (N1, as a hypothesis input) but structurally zero at the now-complete limit=150 capture; the family map forbids its use as signal or control outright.
- **stockbit_flow OFI (N2)** — registered, but only within BFI-001's own scope ("OFI control only" for that program's model ladder), not extended to G1/C1a by any document.
- **stockbit_flow as a G1 NF (N4)** — an unregistered amendment; the underlying table has no semantic-register entry and its own net/lot semantics are separately unvalidated (DEP-B row 2).

## 5. Dataset B — freeze candidate

Exact freeze candidate as it stands today, all values reproduced from `DATASET_B_FINAL_RECONCILIATION_2026-09-11.md` and its underlying artifacts (unchanged since that reconciliation — nothing in this task touched them):

| Field | Value |
|---|---|
| Store path | `docs/research_programs/P-M/dataset_b/store/DATASET_B_BROKER_FLOW_STORE_v1.sqlite` |
| PIT roster hash | `f7e2fec030116a906471d27ee1e3a148aac459f125208d7d6e8e6c6fd3d8c57a` (`DATASET_B_PIT_ROSTER_v1.json`) |
| Session calendar hash | `5012be2315dc82ccfd65a2b117e1977753f0a7d3214693821b39077cd18043fa` (`DATASET_B_SESSION_CALENDAR_v2.json`) |
| Fingerprint | `1a68ab1c6c33409f16fe1c4dd40895c9f5a1b743693d05621e7338086cb8c5d9` (v2, materialized-store-sourced) |
| Capture scope | 30,880/30,880 cells (101 tickers × 386 PIT-admitted sessions), `limit=150`, window 2025-01-02→2026-08-27 |
| Validation result | 35/35 PASS, 0 FAIL, 0 UNRESOLVED (`VALIDATION_REPORT_v1.json`); 13/13 final reconciliation checks PASS (`DATASET_B_FINAL_RECONCILIATION_2026-09-11.md`) |
| Three EMPTY classifications | PTRO 2025-10-06, RAJA 2025-10-13, RATU 2025-11-28 — all `TICKER_LEVEL_ZERO_VOLUME_SESSION` (multi-source evidence: flat zero-volume OHLCV `is_final=1`, independent `bandar_detector` zero-population agreement, not market-wide, no confirming suspension record) |
| Standing exceptions | (1) `freq` UNKNOWN/FORBIDDEN as ticket denominator (unresolved — see §3); (2) `lot`/`side` carry a known ~0.1–0.2% vendor-rounding defect, register status VERIFIED WITH DEFECT, workaround is `sign(value)` not `side`; (3) RAJA quarantined pending its corporate-action adjustment-basis decision (254/30,880 = 0.82% of cells) |

**READY FOR OWNER FREEZE AUTHORIZATION.** `g1_config.json`'s `dataset_b_frozen` gate is currently `false` — unchanged by this packet.

## 6. G1 unlock checklist

| Gate | Current state |
|---|---|
| Dataset B frozen | **NOT SET** (`g1_config.json: dataset_b_frozen = false`) — capture/validation/reconciliation complete and READY FOR FREEZE per §5, but the freeze act itself has not been authorized/executed |
| H0-H3/P0 confirmed OR owner-approved replacement registration | **NOT SET** — artifact NOT FOUND (§1); no replacement registration exists or is proposed here |
| freq decision | **NOT SET** — Option A (probe) vs Option B (withdraw C1a/C1b) undecided (§3) |
| NF decision | **NOT SET** — no G1-scoped source ratified among N1–N4 (§4) |
| Remaining registered parameters locked | **NOT SET** — ST tercile cuts, ADV20 binding, inference binding, timestamp convention, disclosure-cap composition, effective-N methodology all await either preregistration confirmation or explicit owner ratification (§2) |

All five gates are currently closed. None can be closed by this packet.

## 7. Owner decision table

| Decision | Evidence | Options | Required action |
|---|---|---|---|
| H0-H3/P0 | NOT FOUND (exhaustive reachable-filesystem search; D-032 corroborates the corpus lives off-machine) | Recover the artifact from the Windows/ZCode machine · formally re-register H0-H3/P0 from scratch in this repository | **OWNER** |
| §4/§5 (OOS/train-test contradiction) | D-032 Item C, OPEN | Resolve by dated explicit preregistration decision (cannot be inferred; no fold criterion may be added/removed silently) | **OWNER** |
| Turnover (≤200%/month criterion) | D-032 Item D, OPEN — no operational formula exists | Operationalize with an explicit mathematical definition (none may be invented) | **OWNER** |
| freq | UNRESOLVED — no definition anywhere in the corpus | Run vendor semantics probe (Option A) · explicitly withdraw C1a/C1b and proceed freq-free (Option B) | **OWNER** |
| NF | CONFLICTING (N1 dead-at-150, N2 scoped to BFI-001 only, N3 design-only, N4 unregistered) | Explicitly register a source/construction for G1's NF control among the four catalogued candidates, or specify a fifth | **OWNER** |
| Dataset B | READY (13/13 reconciliation PASS, fingerprint v2 recorded) | Freeze now · hold pending the other gates | **OWNER** |

## 8. Scope statement

This packet is a decision aid, not a specification. It creates no new preregistration, ratifies no parameter, selects no option, and changes no gate in `g1_config.json`. Every value above is a direct citation from an existing artifact (this packet's evidence trail: `G1_AUTHORITATIVE_PREREG_RETRIEVAL_2026-09-11.md`, `G1_PREEXECUTION_SEMANTICS_AUDIT_2026-09-10.md`, `G1_MECHANICAL_READINESS_2026-09-10.md`, `DATASET_B_FINAL_RECONCILIATION_2026-09-11.md`, `docs/roadmap/DECISION_LOG.md` D-032, `g1_config.json`, `PM_CUSTODY_RECONCILIATION_HANDOFF_2026-09-10.md`). No code changed. No data changed. Nothing committed. G1 was not run.
