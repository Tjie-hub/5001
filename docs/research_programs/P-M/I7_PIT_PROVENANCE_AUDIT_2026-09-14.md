# I7 · PIT PROVENANCE DECISION AUDIT — 2026-09-14

**Candidate:** I7 — Intraday Execution Timing / adverse-selection sequencing.
**Authority:** generated point-in-time record. **Mode:** provenance audit only.

> **NO hypothesis registration. NO empirical test. NO return analysis. NO registry mutation. NO database
> writes.** No return, IC, p-value, power or profitability quantity was computed. Every connection used
> `file:…?mode=ro`. The prospective capture service was **not** activated.

**The question:** *can we honestly claim the information used by I7 was available at the time the signal
would have been formed?* **Reproducibility is not provenance, and a freeze hash is not an answer.**

---

# 1. HISTORICAL PROVENANCE — THE COMPLETE LINEAGE

## 1.1 The write path

One writer reaches `stockbit_flow_bars`: `tools/backfill_flow_bars.py:154`, via `_persist()`, using
**`INSERT OR REPLACE`**. The same function writes `stockbit_flow` in the *same transaction and same commit*:

```python
if bars:
    conn.executemany("INSERT OR REPLACE INTO stockbit_flow_bars ...")
conn.execute("INSERT OR REPLACE INTO stockbit_flow (... , updated_at) VALUES (..., ?)", (..., now))
conn.commit()
```

**Two consequences, both load-bearing:**

1. `stockbit_flow_bars` itself carries **no provenance column whatsoever** — no retrieval timestamp, no
   request parameters, no response hash, no raw payload.
2. **`stockbit_flow.updated_at` is a surviving write-time record for the bars written beside it.** It is not
   a mere "database modification time" — it is `datetime.now()` captured by the writer at the moment of the
   paired write. This is the provenance evidence this audit recovers, and it exists because the two tables
   share one commit.

**And the backfill SKIPS rather than overwrites.** `tools/backfill_flow_bars.py` computes gaps via
`flow_bars_gap.bars_cell_complete` and increments `skipped` for already-complete cells (line 292) — it never
re-fetches them. Therefore a cell whose `updated_at` still sits on its own trade date **was never
subsequently rewritten**: any rewrite would have moved the timestamp forward.

## 1.2 When each cohort was actually fetched — the decisive record

`backfill_flow_bars.log` and the cron logs are unambiguous:

| Log line (verbatim) | What it means |
|---|---|
| `[2026-08-24 10:33:44] === Backfill start: 309 date(s) x 958 tickers [2025-01-02,2026-04-28) ===` | the **entire v002 window** was fetched starting **2026-08-24** |
| `[2026-08-26 10:18:54] === Backfill start: 386 date(s) x 79 tickers [2025-01-02,2026-08-25) ===` | IDX80 subset, fetched **2026-08-26** |
| `[2026-09-06 22:28:01] === Backfill start: 1 date(s) x 958 tickers [2026-04-27,2026-04-28) ===` | final pass, **2026-09-06** |

**Sessions from January 2025 were fetched in August–September 2026.**

## 1.3 Quantified retrieval lag — measured on the frozen v002 store

`lag = date(updated_at) − trade_date`, over all **295,145** frozen `stockbit_flow` rows (0 null):

| Lag bucket | Cells | Share |
|---|---:|---:|
| **> 120 days (deep backfill)** | **293,407** | **99.41%** |
| 32–120 days | 1,422 | 0.48% |
| ≤ 1 day (contemporaneous) | 316 | **0.11%** |

**Lag distribution: min 0 · p10 180 · p50 364 · p90 558 · max 599 days.**

> **The median frozen intraday cell was retrieved 364 days after the session it describes.**

The 316 contemporaneous cells are 79 tickers × exactly 4 dates (2026-04-20, 04-21, 04-24, 04-27) — the tail
of the window, not a usable cohort.

## 1.4 What this settles

For the frozen v002 asset, what we hold is **the vendor's 2026 answer to a question about a 2025 session.**
It is a *retrospective query result*, not a capture. No raw response, no request parameters, and no
retrieval timestamp beyond the paired `updated_at` survive anywhere for it.

**Whether the vendor revises history is therefore not the operative question** — and this audit does not
claim to have established that it does. The operative fact is stronger and simpler: **we cannot demonstrate
that what we hold is what was obtainable at 15:49 on the session date, because nobody looked until a year
later.** Absence of a contemporaneous record is not neutral; it is the failure of the claim.

---

# 2. PROVENANCE CLASSES

| Class | Definition | Interval | Bar rows | Ticker-days |
|---|---|---|---|---|
| **A — PIT-PROVEN** | written by our own system **on the session date**, with `updated_at` still on that date (⇒ never rewritten) **and** written after the session's bars complete | **2026-04-28 → 2026-09-14**, post-17:00 writes | ~17.5M of 20,066,555 | ~54k of 62,149 |
| **B — REPRODUCIBLE BUT NOT PIT-PROVEN** | frozen, hash-verified, content-complete — retrieved months to years late | **2025-01-02 → 2026-04-27 (all of v002)** | **77,559,605** | 239,695 |
| **C — KNOWN / LIKELY VENDOR-REVISED** | positive evidence of post-hoc alteration | **none identified** | 0 | 0 |
| **D — UNKNOWN** | provenance indeterminate | 2025-08-04 → 2025-09-17 zone; 2025-04-14 fixture; mid-session-write cells | 20,981 cells (zone) + 768 (fixture) + ~8.6% of same-day writes | — |

**Per-interval findings:**

- **v002, 2025-01-02 → 2026-04-27 — class B in its entirety.** 99.41% at lag > 120 days. The freeze is
  excellent (sha256 `fa7f07b3…`, double-verified, 99.70% coverage, 0 zero-coverage dates) — and the freeze
  establishes *reproducibility only*. **It cannot be converted into PIT provenance by any amount of
  hashing.**
- **2025-08-04 → 2025-09-17 contradiction zone — class D.** 31 sessions, 20,981 traded-without-bars cells.
  Already excluded on integrity grounds; the provenance question is moot.
- **2025-04-14 fixture — class D/excluded by design.** 768 ticker-days, never fetched.
- **Post-freeze production cohort, 2026-04-28 → present — class A** (subject to §2.1).

## 2.1 The contemporaneous era — and the trap inside it

Scanning every session from 2026-01-01, the regime change is sharp and its date is striking:

> **Contemporaneous capture begins exactly 2026-04-28 — precisely the exclusive end of the v002 freeze
> window. The frozen asset and the PIT-capable asset are disjoint: v002 covers exactly the backfilled era
> and stops exactly where contemporaneous capture starts.**

**82 sessions** (2026-04-28 → 2026-09-14) have `lag ≤ 1` for *every* cell, covering **~874–972 tickers**
each; **76 of them carry bars**, totalling **20,066,555 bar rows** across **62,149 ticker-day cells**
(81.9% bar-cell ratio — the remainder being genuinely-empty sessions, matching v002's own ~81%).

**Enumerable exceptions inside the era** (backfilled later, therefore class B):
2026-05-18..21 and 2026-06-17..19 (the seven outage sessions, 79 tickers each, lag 68–100);
partial backfills on 2026-05-29, 06-04, 07-13, 07-23, 07-27; and lag-2/3 sessions 2026-05-26, 07-24.

### The trap — write time-of-day

Same-day capture is **not** the same as full-session capture. Hour-of-write over the 76,797 same-day writes:

| Write hour (WIB) | Share |
|---|---:|
| 20:00 | **81.92%** |
| 18:00 | 3.87% |
| 21:00 | 1.50% |
| 16:00 | 4.01% |
| 17:00 / 19:00 | 0.07% |
| **09:00, 12:00, 13:00, 14:00, 15:00** | **~8.6% — written *during* the session** |

The IDX continuous session ends **15:49**; bars run to **16:14**. A cell written at 13:00 on its own trade
date contains **only a partial session**.

> **This would have silently corrupted I7.** Its signal is the share of the day's net buying occurring in
> the **14:50–15:49** window. A cell captured at 13:00 has *structurally zero* late-segment flow and would be
> classified `EARLY_TILTED` **by capture artifact rather than by market behaviour** — a systematic bias
> correlated with nothing observable in the row itself. **Mandatory exclusion E-PIT-3 below.**

---

# 3. CAN I7 BE PREREGISTERED? — THE THREE DESIGNS

### Design A — historical I7 on class-B data with a declared limitation

| | |
|---|---|
| **Scientific validity** | **Fails on its own terms.** The claim I7 makes is about information *available at formation*. Running it on data first observed ~364 days later does not test that claim; it tests a proposition about the vendor's 2026 archive |
| **Selection / leakage risk** | Unquantifiable, not merely unquantified. Neither we nor a reviewer can bound what the vendor may have restated |
| **Sample** | Largest (77.6M bars, ~277 admitted sessions) |
| **Primary estimand meaningful?** | **No** — its PIT premise is false |
| **Independently reproducible?** | Yes — and this is the trap. Perfect reproducibility with a false PIT premise is *more* dangerous than visible noise, because it presents as rigour |
| **Governance amendment?** | Yes — an explicit Owner waiver of the PIT requirement |
| **Verdict** | **REJECT.** This is the "rescue it with reproducibility" move the brief forbids. It is also the HYP-PM-0003 failure mode: a procedurally correct test of a semantically invalid quantity |

### Design B — historical I7 restricted to class-A cells only

| | |
|---|---|
| **Scientific validity** | **Sound.** Every retained cell was written by our system on the session date, was never rewritten (timestamp unmoved), and — after E-PIT-3 — was written after the session closed |
| **Selection / leakage risk** | **Low, and the residual is declarable.** The class boundary is a *capture-infrastructure* change dated 2026-04-28, determined by our cron, not by any market or outcome property. It is exogenous to the hypothesis |
| **Sample** | **~76 sessions**, ~54k ticker-day cells, ~17.5M bars after exclusions. Roughly **23% of C3's 329 daily observations** |
| **Primary estimand meaningful?** | **Yes — unchanged.** The estimand is a daily series; a shorter series is a smaller *n*, not a different quantity |
| **Independently reproducible?** | **Only after a v003 freeze** — this cohort lives in the *live, still-being-written* production table. See §5.2 |
| **Governance amendment?** | **No.** Restricting a population to provenance-qualified cells at registration is ordinary specification |
| **Verdict** | **VIABLE — the recommended design, subject to the v003 freeze and an Owner decision on sample size** |

### Design C — forward-only I7 beginning after prospective capture activation

| | |
|---|---|
| **Scientific validity** | **Highest.** Raw payloads, retrieval timestamps, request parameters, response hashes |
| **Selection / leakage risk** | Lowest |
| **Sample** | **Zero at registration**; accrues ~21 sessions/month |
| **Primary estimand meaningful?** | Yes |
| **Independently reproducible?** | Yes, by construction |
| **Governance amendment?** | No |
| **Verdict** | **VIABLE, strictly stronger, strictly slower.** To reach ~250 sessions from a cold start is ≈ 12 months (≈ 2027-09) |

> **B and C are not exclusive.** Design B registers now on the existing class-A cohort; activating capture
> in parallel upgrades every *future* session to class C quality and lets the same frozen specification
> accrue. This audit does not choose between them.

---

# 4. CAN HISTORICAL PROVENANCE BE RECOVERED? — **NO, AND THIS IS FINAL**

Searched, read-only, for pre-existing evidence only:

| Source | Result |
|---|---|
| `stockbit_flow_bars` columns | **No provenance columns at all** |
| Raw response cache / archive | **None.** No raw payload is persisted anywhere for flow bars — confirmed by repo-wide search. `ohlcv_cache` is unrelated |
| Request parameters | **Not persisted** |
| `backfill_flow_bars.log`, cron logs | **Run-level only** — start/end, counts, budget, stop point. **No per-cell retrieval timestamps, no payloads, no hashes** |
| `job_execution_log`, `screen_run_log`, `audit_events` | job-level orchestration records; no per-cell flow-bar provenance |
| Dataset B `raw_responses` (30,880 gzipped payloads) | **Broker-flow only.** Does **not** cover `stockbit_flow_bars` |
| Backup / archive copies | v002 freeze is a *derived export of the same rows*, not an independent capture |
| `stockbit_flow.updated_at` | **The one genuine recovery** — a write-time timestamp surviving via the shared commit (§1.1) |

**What was recovered:** *when we wrote each cell*, and (via the skip-not-overwrite semantics) *whether it was
ever rewritten*.

**What cannot be recovered, ever:** *what the vendor returned at the time*, for any class-B cell. There is no
raw payload, no hash, and no contemporaneous observation. **For the entire v002 frozen asset —
77,559,605 bars — historical PIT provenance is unrecoverable.**

**Explicitly not done:** no provenance was inferred from file mtimes, DB modification times, or the freeze
hash. The freeze timestamp (2026-09-07) post-dates every session in the window and says nothing about
retrieval. Filesystem metadata was used only to locate logs, never as evidence of capture time.

---

# 5. THE PROSPECTIVE PATH

## 5.1 Service state

`docs/research_programs/P-M/flow_capture_prospective/` (design + `prospective_capture.py`) and the spec at
`prospective_capture/INTRADAY_FLOW_CAPTURE_SPEC_v1.md` exist. **Built, not activated. Not activated by this
audit.**

## 5.2 Earliest genuinely PIT-proven start dates

| Path | Earliest start | Sessions available today |
|---|---|---|
| **Class A cohort already in production** (Design B) | **2026-04-28** | **~76 usable** (of 82 contemporaneous) |
| **Full class-C capture** (Design C) | first session after activation | 0 |

**A v003 freeze is a hard prerequisite for Design B.** The class-A cohort currently sits in the live
production table, which is written daily; without a freeze the study population is mutable and the result
would not be reproducible — the mirror image of v002's defect. The v003 freeze must cover
**2026-04-28 → the registration date**, follow the v002 manifest pattern (double-verified sha256, integrity
check, coverage predicate), and record the class-A qualification per cell.

## 5.3 Exact operational requirement for activation (stated, not performed)

1. Owner authorization to activate.
2. Stand up the store with `raw_responses` (gzipped payload + `response_sha256` + `retrieved_at_utc`),
   `capture_manifest` (completeness vs the 335 Mon–Thu / 275 Fri grid), `capture_run_log` (`code_sha256`).
3. **Schedule the capture to run after 16:15 WIB** — the §2.1 trap is an operational requirement, not only
   an analytical exclusion.
4. Pass the 7-test harness, with `test_deterministic_reconstruction` as the gate.
5. Write to an isolated store; never to `data/walkforward.db`.

---

# FINAL STATUS

## **I7 HISTORICAL PIT ACCEPTABLE WITH EXCLUSIONS**

The exclusions are severe and must not be read as a formality: **they remove 100% of the frozen v002
asset — 77,559,605 of the ~97.6M available bars — leaving ~76 sessions and ~17.5M bars.**

### Can registration proceed?

**Not yet.** Two prerequisites are mechanical, one is a judgment:

1. **v003 freeze** of the class-A cohort (§5.2) — hard prerequisite; the population is currently mutable.
2. **Exclusions E-PIT-1..4 written into the registration** (below).
3. **Owner decision on sample size** — ~76 sessions vs C3's 329.

### Is an Owner decision required? **Yes — one.**

> **Register I7 now under Design B on ~76 class-A sessions, or wait for accrual (Design C, and/or letting
> the class-A cohort grow at ~21 sessions/month) before registering?**
>
> The trade-off, stated without a recommendation: Design B tests the claim honestly today on a sample
> roughly a quarter the size of the program's recent nulls, accepting a real risk of an **indeterminate**
> result — which under the program's own rules is **RETIRED — UNPOWERED**, not a failure, but still spends
> a permanent family slot. Waiting buys statistical determinacy and full class-C provenance at the cost of
> months. **This audit takes no position; both are lawful.**

Subsidiary and unchanged from the prior audit: whether to spend P-M slot #3, and acceptance of the B4
(PPK/board) limitation.

### Exact historical exclusions (mandatory, to be frozen at registration)

| # | Exclusion | Scale |
|---|---|---|
| **E-PIT-1** | **All cells with `trade_date ≤ 2026-04-27`** — the entire v002 frozen asset, class B | **77,559,605 bars / 239,695 ticker-days** |
| **E-PIT-2** | Within the contemporaneous era, all cells whose `updated_at` lag > 1 day — the seven outage sessions (2026-05-18..21, 06-17..19) and the partial backfills (2026-05-26, 05-29, 06-04, 07-13, 07-23, 07-24, 07-27) | ~12 sessions |
| **E-PIT-3** | **All cells written before 17:00 WIB on their own trade date** — mid-session captures holding a partial session | **~8.6% of same-day writes** |
| **E-PIT-4** | Sessions with no bars, or `n_bars` not matching that weekday's structural grid (335 Mon–Thu / 275 Fri) | 6 of 82 sessions |

The v002-era exclusions (2025-04-14 fixture; 2025-08-04 → 2025-09-17 contradiction zone) become **moot** —
E-PIT-1 already removes the entire interval containing them.

### Earliest prospective start

- **Class-A cohort already available: 2026-04-28** (~76 usable sessions today, growing ~21/month).
- **Full class-C capture: the first session after Owner activation**, which has not occurred.

---

**The honest answer to the question posed:** for 99.4% of the intraday evidence — **no**, we cannot claim the
information was available at formation time, and no amount of reproducibility repairs that. For the
disjoint cohort from 2026-04-28 onward — **yes**, and it is provable from our own write records, subject to
the four exclusions above.

# CONFIRMATIONS

- **No hypothesis registration** · **no empirical test** · **no return analysis** · **no power calculation**
- **No registry mutation** — `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md`, `EXPERIMENT_LEDGER.jsonl`,
  `DECISION_LOG.md` untouched · **no family slot consumed** · **`g1_config.json` untouched**
- **No database writes** — every connection `mode=ro`; no historical data modified
- **Prospective capture NOT activated**
- **No provenance fabricated** from mtimes, DB modification times, or the freeze hash
- **Files created by this task: 1** — this report
