# Dataset B Foundation Closure Report — 2026-09-10

**Status: `DATASET B = NOT READY`** · 3 blocking items, all data-capture, none methodological.

Read-only against `/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db`
(`mode=ro` + `PRAGMA query_only`). No production writes, no `broker_flow` writes, no registry,
hypothesis, spec or production-consumer changes. No G1 test, no return interpretation.

---

## 1 · Validation result

**35 / 35 checks passed · 0 failed · 0 unresolved · 2 warnings** (see §7).

Artifact: `artifacts/VALIDATION_REPORT_v1.json`

| Group | Checks | Result |
|---|---|---|
| Artifact custody | 3 | pass |
| Session calendar / completeness | 6 | pass |
| PIT roster | 6 | pass |
| Corporate actions | 4 | pass |
| Adjustment-basis residual detector | 2 | pass |
| Calendar-indexed forward returns (k=3,7,15) | 12 | pass |
| Residual price-integrity sweep | 2 | pass |

### Reconciling "32/33" against "13 unexplained"

These were **different populations**, and the brief was right to require the reconciliation.

- The earlier `32/33` was the check count on the *previous* validation build.
- **15** observations breached the naive flat `ARB = −15%` model.
- **13** of those 15 were reported "unexplained"; the other 2 were already attributed
  (RAJA 2026-07-16 to a corporate action, RAJA 2025-03-04 to the quarantine).
- All **15** are now individually resolved: `artifacts/OUTSIDE_BAND_INVESTIGATION_v1.json`.

---

## 2 · Outside-band investigation — all 15 resolved, tolerance NOT widened

The naive model applied IDX's **current** asymmetric floor (ARB −15%) across the whole window.
`LC-PM-0009` — this program's own literature card — records that the floor was **symmetric**
until **2025-04-08** (SK Direksi BEI Kep-00003/BEI/04-2025):

```
R3  2023-09-04 → 2025-04-07   SYMMETRIC    ARB = ARA = 35 / 25 / 20 %
R4  2025-04-08 → present      ASYMMETRIC   ARB = −15 % at every tier
```

**All 14 non-RAJA breaches occur before 2025-04-08 and are inside their R3 symmetric band.**

| Ticker | Date | Regime | Move | Ref | Band | Cause | Disposition |
|---|---|---|---|---|---|---|---|
| CBDK | 2025-01-23 | R3 | −19.89% | 9,425 | ±20% | legal R3 down-move | RETAIN |
| PANI | 2025-01-23 | R3 | −19.89% | 13,825 | ±20% | legal R3 down-move | RETAIN |
| BREN | 2025-02-07 | R3 | −19.94% | 8,775 | ±20% | legal R3 down-move | RETAIN |
| CUAN | 2025-02-07 | R3 | −19.96% | 1,415 | ±25% | legal R3 down-move | RETAIN |
| DSSA | 2025-02-07 | R3 | −17.86% | 1,921 | ±25% | legal R3 down-move | RETAIN |
| PTRO | 2025-02-07 | R3 | −24.61% | 3,820 | ±25% | legal R3 down-move | RETAIN |
| TPIA | 2025-02-07 | R3 | −19.44% | 8,100 | ±20% | legal R3 down-move | RETAIN |
| CUAN | 2025-02-10 | R3 | −19.87% | 1,132.5 | ±25% | legal R3 down-move | RETAIN |
| CUAN | 2025-02-11 | R3 | −19.01% | 907.5 | ±25% | legal R3 down-move | RETAIN |
| RAJA | 2025-03-04 | R3 | −19.87% | 3,120 | ±25% | legal R3 down-move | RETAIN* |
| RATU | 2025-03-04 | R3 | −18.75% | 7,200 | ±20% | legal R3 down-move | RETAIN |
| WIFI | 2025-03-04 | R3 | −17.53% | 2,510 | ±25% | legal R3 down-move | RETAIN |
| BKSL | 2025-03-12 | R3 | −17.24% | 87 | ±35% | legal R3 down-move | RETAIN |
| TPIA | 2025-03-18 | R3 | −18.42% | 6,650 | ±20% | legal R3 down-move | RETAIN |
| **RAJA** | **2026-07-16** | **R4** | **−80.98%** | **4,600** | **+25/−15%** | **unapplied 5:1 split** | **EXCLUDE** |

\* RAJA is quarantined ticker-wide for a separate reason (§4), so this row is excluded in practice.

Two further moves exceeded 30% but are **inside** their band and are deliberately **retained**:
**BUMI 2025-11-11 +32.00%** (session high 202 against a 202.50 ceiling) and
**KIJA 2026-08-18 +34.96%** (high 166 against 166.05). Both landed *on* the regulatory limit —
a data artifact does not do that. A flat 30% rule would have scrubbed two genuine limit-up days.

**Consequence for study design.** The window straddles the R3/R4 boundary: **58 R3 sessions,
328 R4 sessions**. `LC-PM-0009` states pooling across regimes without conditioning is void
under B8. Every session therefore carries a `band_regime` label. Restricting or conditioning is
a study-design decision, not a dataset one — but the dataset now makes it possible.

---

## 3 · Corporate-action adjustment decision

**Policy: detect the realised basis per ticker; adjust only where a recorded action coincides
with an actual discontinuity; quarantine internally inconsistent tickers rather than patch them.**

Blind application would have corrupted three tickers. Four splits fall in the window, and
`ohlcv` already reflects three of them:

| Ticker | Ex-date | Factor | Observed return | Already adjusted in ohlcv? |
|---|---|---|---|---|
| PTRO | 2025-01-03 | 10:1 | +4.92% | **yes** |
| CUAN | 2025-07-15 | 10:1 | −3.70% | **yes** |
| DSSA | 2026-04-09 | 25:1 | +16.42% | **yes** |
| RAJA | 2026-07-16 | 5:1 | **−80.98%** | **no** |

Primary source is **`corporate_action_events`** (`stocksplit_new`/`stocksplit_old` = 5/1 for
RAJA). `corporate_actions` is secondary: it holds **no** split for RAJA and its latest write
(2026-08-03) predates the window end. No reverse splits or bonus issues fall in scope; four
rights issues do, carrying vendor `rightissue_price_factor` values of 0.9637–1.3485 — recorded,
not yet applied, and none produces a band breach.

---

## 4 · RAJA 1:5 split — quantified across every affected surface

| Surface | Impact |
|---|---|
| OHLCV adjustment | Unadjusted. 4,600 → 875 on 2026-07-16: a fabricated −80.98%. |
| Forward returns | 3 / 7 / 15 formation sessions contaminated at k = 3 / 7 / 15. |
| Outside-band detector | −80.98% against an R4 floor of −15% — breach factor **5.4×**. This is precisely why the regime-aware model isolates RAJA while clearing 14 legal R3 moves. |
| Residual detector | `close ÷ broker-VWAP` median **4.946** (p5 0.985, p95 5.171, n=392, range 0.917–5.495) → `BASIS_MISMATCH`. Spread 4.58 also breaches the instability bound. |
| Feature construction | **RAJA's own flow basis is internally inconsistent**: broker VWAP reads 885 on 07-13, 4,621 on 07-14, 4,641 on 07-15, 895 on 07-16. The vendor restated some sessions and not others. No single factor repairs this. |
| Dataset B | **Quarantined.** 254 member-sessions dropped, 0.82% of 30,880 cells — recorded in the fingerprint's `quarantined` field, not silently removed. |

Historical note carried forward, **not** a reason to rerun anything: RAJA supplied ~22.7% of
HYP-PM-0003's k=7 point estimate and flipped the sign at k=15 under leave-one-out.
**HYP-PM-0003 remains FAILED and untouched.**

---

## 5 · Suspension ≠ scraper gap

`engine/suspension_detector.py:75` classifies on a per-ticker 10% price jump and never asks
whether peers share the gap. Over this window it labels **336 events "suspension"**.

Dataset B discriminates on **breadth**: on the sessions a ticker is absent, what share of its
PIT peers is also absent? A capture failure cannot produce a low peer-absence ratio.

```
ticker-session absences examined : 160
  MARKET_GAP                     : 160  (100%)
  TICKER_ABSENCE_UNVERIFIED      :   0
2026-07-09  80/80 PIT peers absent   2026-07-24  80/80 PIT peers absent
```

**Zero genuine suspensions in the window.** Every absence is infrastructure. Dataset B therefore
declares **no suspension-based exclusion**, and the legacy labels are not consumed. Where a
ticker-specific absence does appear it is recorded `UNVERIFIED` — absence of a bar is consistent
with a halt but does not establish one, and no IDX suspension notice exists in this repository.

### Partial-date audit (all five named dates)

| Date | In calendar | IHSG | ohlcv all / PIT | flow all / PIT | Classification |
|---|---|---|---|---|---|
| 2026-07-09 | excluded | Y | 137 / **0** | 827 / 80 | scraper gap, price side |
| 2026-07-24 | excluded | Y | 134 / **0** | 148 / 79 | scraper gap, price side |
| 2026-08-25 | excluded | **N** | 913 / 80 | **0** / 0 | flow gap, no confirmed session |
| 2026-09-02 | outside window | Y | 916 / 80 | 150 / 12 | partial flow capture |
| 2026-09-08 | outside window | Y | 914 / 80 | 5 / 1 | partial flow capture |

None is a suspension. 2026-09-02 and 2026-09-08 fall after the window end (2026-08-27).

---

## 6 · Foundation components — implemented and validated

**PIT roster.** 8 periods, 101 distinct tickers, 80 members every session, resolved per session
from `idx80_membership_history` × `idx80_reconstitution_periods`. Declared == observed
constituent count in all 8 periods. The ten never-members (AALI, BBYB, DNET, HMSP, KAEF, LINK,
LPPF, PTPP, TBIG, TINS) are absent. The builder refuses to overwrite an existing version.
**Verification reads the frozen file; `idx_tickers` appears nowhere in the module's code** —
asserted by tokenising the source so docstrings do not mask a real read.

**Session calendar.** 386 sessions admitted, 3 excluded with recorded reasons. Every admitted
session has **coverage exactly 1.0000** — the 0.95 threshold is not load-bearing, because the
distribution is perfectly bimodal (1.0 or 0.0). Each session carries a `band_regime` label.

**Forward returns.** Calendar-indexed. Across k = 3, 7, 15: **0 violations** of exact session
distance, **0 substituted landings**, **0 windows crossing an excluded session**, **0
non-member observations**. Excluded sessions are applied to features *and* outcomes through one
dataset-level set, so 2026-08-25 cannot appear inside any window.

**Broker-flow coverage.** **30,877 / 30,880** intended cells (**100.0%**) have `broker_flow` —
3 missing (PTRO, RATU, RAJA, one cell each). But this is the **legacy limit=25 capture**, and
**23,425 of 30,877 cells (75.9%) are truncated** at that limit. Max true population observed in
the intended sample is **88 brokers**, leaving limit=150 **62 brokers of headroom**.

**Fingerprint.** 16 columns pinned (`broker_flow` 9, `bandar_detector` 2, `ohlcv` 5) plus both
artifact hashes. Per-ticker commutative SHA-256 fold. **12/12 property tests pass**: reordering
and reversal do not change it; mutating `lot`, `value`, `freq`, `investor_type` or `broker_code`
does; NULL ≠ 0; int ≠ float; duplicate rows change it; deterministic across runs.

**Semantic register.** 12 entries. `broker_flow.freq` = **UNKNOWN**: tested against the
independent `stockbit_flow` daily summary over 34,017 ticker-days, `SUM(freq) ÷ (buy_freq +
sell_freq)` has median **0.0080** and no variant reaches 2% agreement on any day. A ~100×
shortfall is far beyond what top-25 truncation can explain. Forbidden as a transaction count or
ticket-size denominator until a vendor probe establishes its unit. `investor_type` = brokerage
ownership; `idx_tickers.in_idx80` = **REJECTED FOR RESEARCH USE**.

---

## 7 · Remaining blockers

| # | Blocker | Why blocking |
|---|---|---|
| **B1** | **Broker flow is captured at limit=25, not limit=150.** | 75.9% of the intended sample is truncated. The trial passed and the methodology is settled, but the historical re-capture over 101 tickers × 386 sessions has **not been run**. Requires explicit authorization (§8). |
| **B2** | **No materialised Dataset B store.** | The fingerprint is computed over live production tables. The DB is written continuously by the running service (`idx-walkforward` active, 2 gunicorn workers, ~51h uptime), so the fingerprint pins a moving target. Dataset B needs its own immutable store. |
| **B3** | **`freq` semantics UNKNOWN.** | Blocking only for ticket-size features. Non-blocking for the rest of the foundation if no such feature is planned; must be declared either way. |

**Warnings (non-blocking).** (i) The R3/R4 regime boundary inside the window — labelled, but any
pooled study must condition on it. (ii) Four rights issues carry vendor adjustment factors that
are recorded but not applied; none produces a band breach.

---

## 8 · Authorization required

**Historical broker-flow re-capture at limit=150.**

```
scope    : 101 PIT tickers × 386 admitted sessions ≈ 30,880 member-cells
endpoint : GET https://exodus.stockbit.com/marketdetectors/{ticker}
params   : transaction_type=TRANSACTION_TYPE_NET  market_board=MARKET_BOARD_REGULER
           investor_type=INVESTOR_TYPE_ALL  limit=150  from={date}  to={date}
cadence  : ~1.5 s/request (established by the closed trial)
runtime  : ≈ 12.9 hours single-threaded
target   : a NEW table or a separate Dataset B store — NOT production broker_flow
retry    : existing 429 ladder in fetch_broker_flow (Retry-After, else 20*(n+1)s, 4 attempts)
```

Two decisions needed before execution:

1. **Write target.** Writing into production `broker_flow` would mutate Dataset A's fingerprint
   and is forbidden without separate authorization. Recommended: a dedicated Dataset B store.
2. **Whether B3 is resolved first** — one extra probe comparing a single broker's `freq` against
   its buy and sell counts would settle `freq`, or it stays UNKNOWN by declaration.

---

## 9 · Artifacts

All under `docs/research_programs/P-M/dataset_b/artifacts/`.

| Artifact | SHA-256 |
|---|---|
| `DATASET_B_PIT_ROSTER_v1.json` | `7fcde06272aa1aaa3278d23c30476c2802de26891db7b101ca58cf203e9c2b2c` |
| `DATASET_B_SESSION_CALENDAR_v2.json` | `d51d4a0d53342121bc8748e8767cdc18dd8b57d702373a6e53ea2f9fb7e31015` |
| `DATASET_B_FINGERPRINT_v1.json` | `361f36f685610d4d64f11f7a9d43cf3648ee5585e0c87e22342e78dfbdac7ab3` |
| `DATASET_B_SEMANTIC_REGISTER_v1.json` | `bed27a39cbd80016c93098c75600dd4a6a1b4296798b9596423b1c323e4b0f3a` |
| `OUTSIDE_BAND_INVESTIGATION_v1.json` | `729b95a0ad078e27d0b78ed36d5122be253bf21ab9b37a59157c74202f3d437d` |
| `GAP_CLASSIFICATION_v1.json` | `93046e1b7fb69b3eac03a80691eaabae2b62a2cc652e9e398d6cd654fdd870c8` |
| `VALIDATION_REPORT_v1.json` | `20bedb29d02ac36678036a4e6f37147007dd8ded5a46e70219df711a344dfef5` |

**Dataset B content fingerprint (internal):**
`b0ad62826671e7da8236c3265304feaf890d20fab44104c3190dac591806f51b`

`_v1` calendar and `_v2` roster are retained (append-only). Roster v1 and v2 are
**membership-identical** — asserted in validation; v2 differs only in the calendar hash it
references. `PIT_ROSTER_v1` is the named custody artifact.

### Code

| Path | Purpose | Production behaviour changed |
|---|---|---|
| `dataset_b/build_calendar_and_roster.py` | builds the two immutable artifacts | no |
| `dataset_b/foundation.py` | calendar, roster, CA policy, residual detector, forward returns | no |
| `dataset_b/validate.py` | 35-check validation suite | no |
| `dataset_b/investigate_outside_band.py` | per-observation band investigation | no |
| `dataset_b/gap_classifier.py` | suspension vs scraper gap | no |
| `dataset_b/fingerprint.py` | feature fingerprint + semantic register | no |

Uncommitted, on `ops/hardening-2026-07-10`. All files live under `docs/`, outside both CI
source-scan scopes (`test_architecture_boundary.py`, `test_db_centralization.py`) — the same
placement precedent as `EXP-PM-0003`.

### Pre-existing failure, not caused by this task

`tests/test_db_centralization.py::test_no_raw_sqlite_connect_in_production` **fails on the
working tree**. Offenders are `engine/platform_info.py:80`, `engine/trade_flow.py:77`,
`engine/ticker_detail.py:48` — all show `sqlite3.connect` count **0 at HEAD**, and two are
untracked. Uncommitted work by another author. `git diff` contains **0** references to this
task. The other 9 boundary tests pass.

---

## 10 · Success condition

| | Criterion | |
|---|---|---|
| ☑ | PIT roster verified and immutable | 8 periods, 101 tickers, hash-verified, overwrite-refusing builder |
| ☐ | **Broker-flow coverage complete for the intended sample** | **100% of cells, but at limit=25; 75.9% truncated — B1** |
| ☐ | **limit=150 capture used correctly** | **methodology settled and trial-passed; not yet applied to history — B1** |
| ☑ | Per-ticker session completeness passes | 386 sessions at coverage 1.0000; 3 excluded with reasons |
| ☑ | Forward returns calendar-indexed | 0 violations across k=3,7,15 on four independent checks |
| ☑ | Corporate-action handling explicit | detect-then-adjust; 3 already-adjusted correctly left alone |
| ☑ | RAJA split correctly handled | quantified on 6 surfaces; quarantined, not patched |
| ☑ | Suspension ≠ scraper gap | breadth classifier; 160/160 MARKET_GAP; 0 suspensions |
| ☑ | Outside-band observations resolved | 15/15 with evidence; tolerance not widened |
| ☑ | Validation rerun passes all hard gates | 35/35 |
| ☑ | `freq` verified or marked UNKNOWN | **UNKNOWN**, with the evidence that establishes it |
| ☑ | Semantic register complete | 12 entries |
| ☑ | Fingerprint generated | 16 columns, 12/12 property tests |
| ☑ | Provenance recorded | source tables, builder, commit, timestamps, hashes |
| ☑ | No future leakage identified | membership resolved at formation; outcomes strictly forward |
| ☑ | No production consumer silently modified | production diff contains 0 references to this work |

**`DATASET B = NOT READY`** — blocked on **B1** (limit=150 historical capture) and **B2**
(materialised store). **B3** is declarable. Every methodological gate is closed.
