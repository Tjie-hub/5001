# DATA GAP CLOSURE AUDIT v2 — 2026-09-14
## HYP-PM-0008 + next-alpha research readiness

**Authority:** generated point-in-time record. **Mode:** data / infrastructure audit only.

> **ZERO hypothesis execution. ZERO backtests. ZERO return statistics. ZERO registry mutation. ZERO
> Dataset B mutation. ZERO production DB writes. ZERO methodology change.** Every database connection in
> this audit used `file:…?mode=ro`. No IC, t-stat, p-value, forward return, or performance quantity was
> computed. No threshold was tuned. No D-1 or D-3 judgment is offered.

---

# THE ANSWER TO THE QUESTION ASKED

> **ARE WE LOSING BECAUSE THE DATA DOES NOT EXIST, OR BECAUSE WE ARE THROWING AWAY INFORMATION THAT
> ALREADY EXISTS?**

## **Overwhelmingly the second — and the proof is arithmetic, not intuition.**

| Asset | Rows held | Consumed by any registered hypothesis? |
|---|---:|---|
| `stockbit_flow_bars` — 1-minute, **aggressor-side, buy/sell separated** | **98,454,570** | **Never at native resolution.** HYP-PM-0001 summed each ticker-session's 335 bars into one `OFI_day` scalar, then took its **sign** |
| `ticks` | **20,203,151** | **Never** by a registered P-M hypothesis (VPIN path only) |
| `broker_flow_b` (Dataset B, full population, 95 broker identities) | **1,518,727** | Yes — but collapsed to **broker counts** (C3) or **summed away entirely** (C7) |
| `bandar_detector.total_buyer/total_seller` — the **only uncensored** participation measure, VERIFIED | 105,368 cells | **Never** |

Three registered hypotheses (HYP-PM-0001, C3, C7) each reduced their instrument to **one scalar per
ticker-day, then to one bit**, before testing. C7's entire input surface — 1.5 million broker rows carrying
95 distinct identities — became a single binary flag per ticker-day.

And the asset that is **structurally immune to the accounting identity** that voided HYP-PM-0003, BFI-001's
primary and C2 — `stockbit_flow_bars`, whose `buy_lot` and `sell_lot` do not balance — is precisely the one
never used structurally. The program spent four registrations drawing from the one contaminated well
(`broker_flow`) while 98.5 million clean, identity-immune bars sat unread.

**The genuinely unavailable set is real but narrow:** broker identity at intraday resolution, order
book/queue, and client identity. All three are *not disclosed by IDX at all* — no acquisition closes them.

**One important qualifier, stated up front so the headline is not over-read:** the intraday asset is rich in
*content* and empty in *provenance*. It cannot currently be proven point-in-time (§D). It is a research
asset today only if that is fixed or explicitly accepted as a limitation.

---

# A. DATA GAP MATRIX

| Gap | Historical status | PIT status | Can fix now? | Prospective fix? | Fundamentally unavailable? |
|---|---|---|---|---|---|
| **Board classification** (Utama / Pengembangan / Ekonomi Baru) | **D** — no field in any of 82 tables | none | **No** | **Yes** | No — IDX publishes it |
| **Papan Pemantauan Khusus** | **D** | none | **No** | **Yes** | No — published daily |
| **ETF / DIRE instrument type** | **D** | none | No | Yes | No |
| **Listing date / IPO first day** | **B** — `idx_tickers.first_seen` is a 2026-04-24 scraper artifact, not a listing date | none | Proxy only (first appearance in `ohlcv`, left-censored 2021-07-05) | Yes | No |
| **Suspension status** | **B** — `suspension_events` **EXISTS** (3,189 rows, 956 tickers, 2022-04-28→2026-07-17) but is **derived**: 2,830 `data_gap` vs 359 `suspension` | derived | Usable as a declared proxy | Yes (authoritative feed) | No |
| **IDX80 index membership** | **B** — `idx80_membership_history` (640 rows) + `idx80_reconstitution_periods` (P0–P7), **2025-01-02→2026-08-02 only** | **A within its window** — effective_from/to + confidence tiers | Within window yes; **no 2023 coverage** | n/a | No |
| **ARB decree documents** | **B** — not held; **lawful channel proven** (§C) | n/a | Not in this audit | n/a | **No** |
| **ARB regime table (derived)** | **BUILT** this audit | behaviourally corroborated, not primary-verified | **Yes — done** | n/a | No |
| **Intraday flow content** | **B** — 98,454,570 rows, 399/400 sessions, **100% grid completeness** | **absent** — no provenance columns at all | Content usable now | **Yes** (§G) | No |
| **Intraday flow provenance** | **D** — no `captured_at`, no hash, no raw payload; both writers `INSERT OR REPLACE` | none | **No** (cannot retro-fit provenance to already-overwritten rows) | **Yes** | No |
| **Broker × ticker × date** | **A** — 1,518,727 rows, 95 brokers, median 47/cell, untruncated | **A** — `raw_responses` + manifest + run log, sha256-pinned | Already available | n/a | No |
| **Broker × intraday time** | **D** | none | **No** | **No** | **YES — not disclosed by IDX** |
| **Order book / queue / late-arrival eligibility** | **D** | none | No | No | **YES — unavailable in market** |
| **Client identity** | **D** | none | No | No | **YES** |
| **Short-sell eligibility / borrow** | **D** | none | No | **Yes** | No — IDX publishes the list |
| **Closing-auction microstructure** | **D** — bars structurally absent 15:50–15:59 | none | No | Partially | Largely |
| **`ohlcv` adjustment basis** | **B, quantified here for the first time**: **139 of 959 tickers (14.5%)** carry a fractional close = in-place adjustment, vs only 2,171 `corporate_actions` rows | mixed | Detectable, not repairable in place | Yes | No |

---

# B. HYP-PM-0008 blocker B4 status — **NOT SOLVABLE RETROSPECTIVELY**

B4 requires excluding **Papan Pemantauan Khusus** (a full-call-auction, ±10% mechanism that is not an ARB
exception but a *different market*), **IPO first-trading days** (2× bands), and suspensions, across the
**2023-09-04 → 2026** population.

**Verdict: prospectively fixable, retrospectively not.**

- Board and PPK membership are **class D** — no field exists anywhere, repo-wide grep confirms. IDX
  publishes them daily but the estate has never stored them, so there is nothing to reconstruct *from*.
- The estate's one exemplary PIT classification table, `idx80_membership_history`, **begins 2025-01-02** —
  it cannot reach HYP-PM-0008's R3 control arm at all.
- Suspension is available only as a **derived proxy** (89% of `suspension_events` rows are our own data
  gaps, not observed exchange suspensions).

The R3 boundary audit produced a concrete illustration: **WICO 2023-07-20** fell in a ~−10%/day staircase
consistent with a special-monitoring-board name, and there was no way to confirm it — it had to be excluded
on a *stale-reference* argument instead.

> **B4 is therefore a genuine, irreducible constraint on any 2023-window study**, including HYP-PM-0008 as
> specified. Forward capture (§G) fixes it from its start date onward and **never** retroactively. Any
> claim that B4 has been closed for the R3 arm would be the silent-fill failure this audit exists to
> prevent.

---

# C. HYP-PM-0008 blocker B5 / capturability data status

**Mechanical and legal feasibility only — no return, cost, or profitability quantity was computed.**

| Execution leg | Verdict | Evidence |
|---|---|---|
| Limit-down continuation (short leg) | **NOT CAPTURABLE** | Requires short exposure. IDX is order-driven with no DMM (LC-PM-0006); short-selling rules "not extractable" (M2x discovery §7); the M6/I1 discovery excludes shorting as the capture leg. No borrow/short data in any of 82 tables |
| Limit-up continuation (long leg) | **NOT CAPTURABLE** | LC-PM-0007 (Q4): at an upper limit the queue is buyers; a late arrival does not execute — "the mechanism that creates the effect excludes you from it" |
| Queue position | **UNKNOWN — DATA MISSING** | No order-book/queue data. `ticks` (20.2M rows) carries price/volume/tick_type, no queue state |
| Late-arrival eligibility | **UNKNOWN — DATA MISSING** | depends on queue position |
| T+2 settlement | **CAPTURABLE** | Regular market settles T+2; the SPEC's k=1 close-to-close horizon needs no intraday round-trip |
| Short-selling availability | **UNKNOWN — DATA MISSING** | No eligibility list, no borrow, no fees. LC-PM-0009 notes the list was republished 2023-04-03; never captured |
| Ordinary-board constraints | **UNKNOWN — DATA MISSING** | board membership unavailable (§B); a PPK name cannot execute a continuous-session strategy at all |
| Auction / close execution | **UNKNOWN — DATA MISSING** | Bars end 16:14 with a structural 15:50–15:59 gap; the closing auction is unobservable in held data |
| Suspension constraints | **CAPTURABLE (declared proxy)** | `suspension_events` + calendar non-consecutiveness + zero volume |

**1 capturable, 1 capturable-as-proxy, 2 NOT capturable, 5 unknown-data-missing.**

> **The finding that matters:** the two **NOT CAPTURABLE** verdicts are the ones that bind HYP-PM-0008, and
> **neither is a data gap.** They are market-structure facts — no acquisition, no capture system, and no
> budget changes them. Five legs are unknown for want of data, but they only become decision-relevant if
> the two binding legs were capturable, which they are not.
>
> **This is evidence for the D-3 decision. It is not the D-3 decision, which remains the Owner's.**

---

# D. Intraday data status — **B, usable but incomplete**

| Property | Measured |
|---|---|
| Rows | **98,454,570** |
| Coverage | 2025-01-02 → 2026-09-11, **399 distinct sessions** |
| vs `trading_calendar` | 400 sessions in window; **399 present, 1 missing (2026-08-25) = 99.75%** |
| Tickers/session | 828 – 859 |
| Grid | 09:00–11:59, 13:30–15:49, 16:00–16:14 = **335 bars**; gaps are exactly the **lunch break** and the **pre-closing/closing auction** — structural, not defects |
| Internal completeness (probe 2026-03-10) | **859/859 tickers hold the full 335-bar grid — 100.0%** |
| Fields | `buy_lot, sell_lot, buy_freq, sell_freq, net_value, price, delta` |
| **Identity status** | **IMMUNE.** `buy_lot`/`sell_lot` are separate aggressor-side quantities that do not balance; independently verified in `FOUR_TEST_IDENTITY_AND_REGISTRY_AUDIT_2026-09-11` Part D.2 (|NF| p50 = 0.175, genuine variance). **The defect that voided HYP-PM-0003, BFI-001's primary and C2 does not reach this table** |

**Why B and not A — the whole of the deficiency is provenance:**

`stockbit_flow_bars` columns are `ticker, trade_date, bar_time, buy_lot, sell_lot, buy_freq, sell_freq,
net_value, price, delta`. There is **no `captured_at`, no retrieval timestamp, no request parameters, no
response hash, no completeness flag, and no raw payload.** Both writers — `stockbit_fetcher.py:789` and
`tools/backfill_flow_bars.py:154` — use **`INSERT OR REPLACE`**, so a re-fetch silently overwrites history
in place. The table therefore **cannot be proven point-in-time and cannot be deterministically
reconstructed.**

> The content is excellent and the provenance is absent. That is a fixable engineering defect, not a data
> gap — and the fix is a port, not an invention (§G).

**Also recorded:** `stockbit_flow` (daily) has **98 rows with NULL/empty `trade_date`**.

---

# E. Broker-structure data status

Read from the **frozen** Dataset B store; **sha256 re-verified as `21661f033145ef90657f…`, matching
`DATASET_B_FREEZE_MANIFEST_v1` exactly** — proof that this audit's read-only access mutated nothing.

`broker_flow_b`: **1,518,727 rows**, 101 tickers, 386 sessions, **95 distinct broker codes**, 30,877 cells,
**brokers per cell min 20 / p50 47 / p90 65 / max 88**, untruncated (`limit_param=150`, zero truncation
flags).

| Reconstruction target | Verdict |
|---|---|
| broker × ticker × date | **EXISTING DATA SUFFICIENT** |
| broker concentration | **EXISTING DATA SUFFICIENT** (partly consumed as BFI-001 `F4_conc`, t = −2.65) |
| broker persistence | **EXISTING DATA SUFFICIENT** (386 consecutive sessions) |
| broker pair interaction | **EXISTING DATA SUFFICIENT** (95 brokers → 4,465 unordered pairs; co-presence directly observable) |
| broker coalition / group structure | **PARTIALLY SUFFICIENT** — observable, but family map N already measured avg pairwise daily tilt correlation **−0.065** with 80%/day dominant-broker churn: the structure was looked for at *daily* resolution and not found |
| initiator / absorber / chaser | **NEW DATA REQUIRED** — these are **ordering** concepts; `broker_flow_b` is a daily net per broker with **no time dimension** |
| daily flow–price alignment | **EXISTING DATA SUFFICIENT** |

**The missing cross, stated precisely:** two datasets each hold what the other lacks —

- `broker_flow_b`: **WHO** (95 identities) — but daily net only, no time.
- `stockbit_flow_bars`: **WHEN** (1-minute) and identity-immune buy/sell — but **no broker dimension**.

Their intersection — **broker identity × intraday time** — exists in neither and is **not disclosed by IDX**
(`ZCODE_ALPHA_DISCOVERY_FAMILY_MAP` §6: "Intraday broker timing (not disclosed at broker level) —
blocked"). **Class D, permanent.** No acquisition closes it.

---

# F. INFORMATION-LOSS MAP

```
RAW DATA                          -> MATERIALIZATION        -> FEATURE            -> WHAT WAS DISCARDED
```

**C3 · HYP-PM-0005 breadth surprise**
`1,518,727 broker rows / 30,877 cells / 95 identities / median 47 brokers per cell`
→ per-cell counts of net-buying vs net-selling brokers
→ breadth-imbalance scalar → **binary state** (±0.30 vs trailing median)
→ **one daily contrast series, 329 observations**
**Discarded:** broker identity entirely; per-broker magnitudes; the whole distribution behind the count.
**Compression: 1,518,727 rows → 329 numbers.**

**C7 · HYP-PM-0006 intensity state**
same 1.5M rows + `ohlcv close×volume`
→ `gross = Σ|value|`, `ADV20` → `intensity = gross/ADV20` → **binary flag at ≥ 2.0**
→ one daily high-vs-non-high contrast
**Discarded:** everything distinguishing one broker from another; the entire magnitude distribution either
side of 2.0; each broker's direction; all intraday shape.
**Compression: 1,518,727 rows → one bit per ticker-day.**

**HYP-PM-0001 (and the HYP-PM-0002 draft)**
`98,454,570 one-minute bars, buy_lot and sell_lot separate`
→ `OFI_day = Σdelta / Σ(buy_lot+sell_lot)` — **one scalar per ticker-day**
→ `sign(OFI_day)` → signed reversal at k=15
**Discarded:** 335 bars per ticker-session reduced to one number and then to one bit — intraday timing,
shape, front/back-loading, within-day reversal, the buy/sell split itself, and `buy_freq`/`sell_freq`.
**Compression: 98,454,570 bars → one sign per ticker-day.**

### Genuinely missing (never collected)

| Item | Fixable? |
|---|---|
| Broker identity at intraday resolution | **No — not disclosed by IDX** |
| Order book / queue / order events | **No — unavailable in market** |
| Client identity | **No — unavailable** |
| Board classification incl. PPK | Yes, prospectively |
| Short-sell eligibility / borrow | Yes, prospectively |
| Authoritative suspension feed | Yes, prospectively |
| The two ARB decrees **as documents** | **Yes — class B, lawful channel proven (§G)** |

### Held but discarded (collected, then thrown away by the pipeline)

- **98,454,570 intraday bars** — never consumed at native resolution by any registered hypothesis
- **20,203,151 ticks** — never consumed by a registered P-M hypothesis
- **`buy_freq` / `sell_freq`** on the intraday table — note `broker_flow.freq` is UNKNOWN/FORBIDDEN, but
  these are a *different field from a different endpoint*, and were the trusted reference used to condemn
  `broker_flow.freq` in the first place
- **Broker identity** — 95 codes present in every cell, collapsed to counts or summed away
- **The magnitude distribution** either side of every threshold C3/C7 binarized
- **`corporate_action_events`** — 12,353 rows with `raw_json`, while the research path consumes the
  2,171-row `corporate_actions` projection
- **`bandar_detector.total_buyer/total_seller`** — the estate's *only* uncensored participation measure,
  graded VERIFIED, used by no registered hypothesis

---

# G. FIXES IMPLEMENTED

| # | Artifact | What it closes |
|---|---|---|
| 1 | **`reference/ARB_REGIME_TABLE_v1.json`** | **Part 2 delivered.** Canonical PIT band table, R1–R4, with `primary_verified` and `behaviourally_corroborated` as **separate fields that are never conflated**. Confidence vocabulary adopted verbatim from `idx80_reconstitution_periods` so both PIT reference tables grade evidence on one scale |
| 2 | **`data_inventory_v2.json`** | Full measured inventory: 82 production tables, coverage, classifications, defects |
| 3 | **`prospective_capture/INTRADAY_FLOW_CAPTURE_SPEC_v1.md`** | Provenance schema for intraday flow + a PIT `security_classification` table, with 6 invariants, a 7-test validation harness, and explicit no-silent-fill and no-retroactive-claim rules |

## G.1 The most valuable finding: the decree channel is **class B, not D**

`idx80_reconstitution_periods` cites, verbatim, official IDX documents retrieved **"(via Wayback Machine)"**
— `Peng-00139/BEI.POP/07-2025`, `Peng-00014/BEI.POP/01-2026`, `Peng-00067/BEI.POP/04-2026` — plus an
official IDX XLSX for `Peng-00012/BEI.POP/01-2025`. **This repository has already obtained IDX primary
regulatory documents and graded rows `PRIMARY_VERIFIED` on them.**

So D-2's missing documents are **not unavailable**; they are **unretrieved via a channel already proven to
work here**. That reclassifies the D-2 documentary gap from **D → B**.

**Attempted in this audit, and its limit:** the Wayback CDX index was queried; archived snapshots of the
IDX `keputusan-direksi` listing page **do exist after the 2025-04-08 decree** (2025-05-27, 2025-06-08,
2025-08-04, 2026-03-01, all HTTP 200). Fetching the 2025-05-27 snapshot returned 169,537 bytes containing
**no decree numbers** — the page is a JS-rendered SPA and only the shell was archived; the decree list loads
from an API that was not captured. The decree PDF URLs were not located under the URL patterns tried.

**No WAF circumvention was attempted.** The Internet Archive is a separate public archive, not a bypass of
idx.co.id's access control, and the live site's 403 was respected throughout.

## G.2 Two corrections to earlier claims in this session

| Claim | Correction |
|---|---|
| "No suspension table exists" (blocker audit §C.5, SPEC §20 B4) | **WRONG.** `suspension_events` exists: 3,189 rows, 956 tickers, 2022-04-28→2026-07-17. It is *derived* (89% `data_gap`), which is a weaker and different defect than absence |
| "No board-membership table" / `idx_tickers.in_idx80` is all there is | **Incomplete.** `idx80_membership_history` + `idx80_reconstitution_periods` are a proper PIT index-membership pair with confidence tiers — but they are **index** membership, not **board** classification, and start 2025-01-02. The board gap stands; the characterisation did not |

Neither correction changes B4's verdict for the 2023 window (§B).

---

# H. REMAINING IRREDUCIBLE GAPS

| Gap | Why irreducible |
|---|---|
| **Broker identity × intraday time** | Not disclosed by IDX at broker level intraday. No vendor, budget, or capture system obtains it |
| **Order book / queue depth / late-arrival eligibility** | Not available in this market at all |
| **Client identity** | Not available |
| **Retrospective board/PPK classification before capture starts** | Nothing to reconstruct from; forward capture is structurally incapable of reaching backwards. **This is B4 for the 2023 window, and it is permanent** |
| **Provenance for intraday rows already written** | `INSERT OR REPLACE` destroyed the history. Provenance can begin, never be back-filled |
| **Capturability of both HYP-PM-0008 legs** | Market structure (no practical shorting; ARA queue excludes late arrivals), not data |

---

# I. EXACT EVIDENCE AND PROVENANCE

**Read-only, `file:…?mode=ro` throughout.**

| Source | Use |
|---|---|
| `data/walkforward.db` (13,660,860,416 bytes) | 82-table schema + row counts; coverage queries |
| `docs/research_programs/P-M/dataset_b/store/DATASET_B_BROKER_FLOW_STORE_v1.sqlite` | broker structure; **sha256 `21661f033145ef90657f…` verified against the freeze manifest — unchanged** |
| `dataset_b/foundation.py`, `investigate_outside_band.py` | band model + methodology precedent |
| `FOUR_TEST_IDENTITY_AND_REGISTRY_AUDIT_2026-09-11.md` | identity-immunity of the vendor instrument (Part D.2) |
| `ZCODE_ALPHA_DISCOVERY_FAMILY_MAP_2026-09-10.md` §6 | permanent unavailability list |
| `LC-PM-0006/0007/0009`, `DISCOVERY_2026-08-21_*` | capturability and market-design evidence |
| `HYP-PM-0008_R3_BOUNDARY_BEHAVIOURAL_AUDIT_2026-09-14.md` | ARB regime behavioural evidence |
| `archive.org` CDX + one archived snapshot fetch | decree channel assessment (§G.1) |

**Key measured counts:** `stockbit_flow_bars` 98,454,570 rows / 399 sessions / 100% grid at probe ·
`ticks` 20,203,151 · `broker_flow` 3,071,043 · `broker_flow_b` 1,518,727 / 95 brokers ·
`bandar_detector` 105,368 · `ohlcv` 1,085,437 / 959 tickers · `corporate_action_events` 12,353 ·
`suspension_events` 3,189 · `idx80_membership_history` 640 · `trading_calendar` 1,247 ·
`ownership_composition` **0** · fractional-close tickers **139 / 959**.

**Files created:** 4 — this report, `data_inventory_v2.json`, `reference/ARB_REGIME_TABLE_v1.json`,
`prospective_capture/INTRADAY_FLOW_CAPTURE_SPEC_v1.md`. **Files modified: none.**

---

# J. RECOMMENDED NEXT INFRASTRUCTURE ACTION (one only)

## **Port the Dataset B capture pattern onto `stockbit_flow_bars`.**

Stand up `prospective_capture/` per the spec: `raw_responses` (gzipped immutable payload + `response_sha256`
+ `retrieved_at_utc`), `capture_manifest` (completeness against the 335-bar grid), `capture_run_log`
(`code_sha256`), and the 7-test harness — with `test_deterministic_reconstruction` as the gate.

**Why this and not anything else:**

1. It converts the estate's **largest and only identity-immune** asset from unprovable to research-grade.
   Nothing else in the inventory has that leverage.
2. It is a **port of a proven in-repo pattern**, not a design exercise — Dataset B's store hash verified
   clean in this audit.
3. It is **strictly additive**: a separate store, no change to `stockbit_flow_bars`, to
   `data/walkforward.db`, or to the frozen Dataset B contents.
4. **Every day of delay is unrecoverable.** `INSERT OR REPLACE` means provenance can only ever start; it
   can never be back-filled. That asymmetry is the reason this ranks first.
5. Board / PPK / short-eligibility capture (Stream B) should ride the same harness once it exists — but it
   is second, because it cannot help any hypothesis whose population predates it.

*This is an infrastructure recommendation only. No hypothesis is recommended, and D-1 and D-3 remain
entirely the Owner's.*

---

# FINAL STATUS

## **MATERIAL DATA GAPS REMAIN**

Chosen over "partially closed" deliberately. Three artifacts were delivered and the D-2 documentary gap was
reclassified **D → B**, but the gaps that actually bind are **not** closed: **B4 is retrospectively
irreducible** for HYP-PM-0008's R3 window; the ARB decrees remain unretrieved; intraday provenance exists
as a spec, not a system; and broker × intraday, order book, and client identity are permanently unavailable.

**This coexists with — and does not soften — the headline finding.** The dominant constraint on this
research program is not absent data. It is 98.5 million unread intraday bars, 20.2 million unread ticks,
95 discarded broker identities, and an unused uncensored participation measure, against a narrow and
genuinely permanent unavailability set.

# CONFIRMATIONS

- **Empirical hypothesis tests: ZERO** · **Predictive/backtest runs: ZERO** · **Return statistics: ZERO**
- **Hypothesis registrations: ZERO** · **Registry mutations: ZERO** (`HYPOTHESIS_REGISTRY.md`,
  `FAILURE_REGISTRY.md`, `EXPERIMENT_LEDGER.jsonl`, `DECISION_LOG.md` untouched)
- **Dataset B frozen-store mutations: ZERO** — sha256 re-verified identical to the freeze manifest
- **Production DB writes: ZERO** — every connection `mode=ro`
- **Methodology changes: ZERO** · **`g1_config.json` mutations: ZERO** · **Semantic register: unmodified**
- **No threshold tuned, no profitable parameterization searched, no alpha feature created, no variable
  selected on return outcomes**
- **No D-1 family decision. No D-3 capturability decision. No hypothesis recommendation.**
