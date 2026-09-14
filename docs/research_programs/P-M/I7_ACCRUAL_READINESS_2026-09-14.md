# I7 · ACCRUAL READINESS — v003 ADMISSIBLE-COHORT FREEZE — 2026-09-14

**Authority:** generated point-in-time record. **Mode:** infrastructure implementation + verification.

> **SUPERSEDED (mechanical correction, later the same day): the v003 freeze is retained immutable as a
> historical artifact; the live cohort freeze is now V004 — see section 0.** The correction enforces the
> specification's exclusion X3 and extends the session calendar through 2026-09-11; nothing substantive
> changed. **I7 remains NOT registered and NOT executed.**

---

## 0. V004 — MECHANICAL CORRECTION (X3 enforcement + session-calendar extension)

Remediates `I7_REGISTRATION_READINESS_REVIEW_2026-09-14.md` §2.4 via its remediation (a): the base
session calendar (Dataset B SESSION_CALENDAR v2, sha `5012be23…`) ended 2026-08-27, so X3
("non-admitted sessions per `session_calendar`") was unevaluable for the 11 sessions
2026-08-28..2026-09-11, and 2026-07-09 (`is_admitted = 0`, *member price coverage below threshold*)
sat in the v003 cohort against the registered exclusion set.

**What changed — mechanical only:**

| Change | Detail |
|---|---|
| Session calendar extended | `store/I7_SESSION_CALENDAR_EXTENSION_v1.json` (sha256 `a7a4eedf45f3d4b2ced4f9a9f2d90d28e011ef0425b115c127a04fcdda0f189e`) — the base calendar's **own** admission rule (roster period → IHSG confirmation → member price coverage ≥ 0.95, copied verbatim from `build_calendar_and_roster.py`, nothing added) applied to 2026-08-28..2026-09-11 from source data: **11/11 sessions admitted** (coverage 1.0000 each), 0 excluded |
| X3 enforced at cohort layer | `build_v004_freeze.py` excludes every candidate cell whose session is not calendar-admitted (precedence: X3 session-level first, then E-PIT cell rules; E-PIT-1 still bounds the candidate set) |

**What did NOT change:** the I7 hypothesis, estimator, state definition, threshold, inference, decision
rule — all untouched. **No minimum-cell/session rule was added** (2026-09-08 keeps its single admissible
cell and is handled at estimation time, exactly as in v003). X1/X2 are subsumed by E-PIT-1 (asserted:
both regions end before the 2026-04-28 boundary). X4 is the same predicate as E-PIT-4. X5/X6 remain
**estimation-time** filters over ohlcv (review §2.5) and are deliberately not applied at accrual —
applying them here would require reading prices/outcomes.

**V004 freeze:**

| Field | Value |
|---|---|
| Store | `i7_accrual/store/I7_V004_ADMISSIBLE_v1.sqlite` |
| **sha256** | **`e1375264133b42f417d8e74f48a48646197d15b8961e3bdf431d6eebc8784fba`** |
| Bytes | 901,668,864 (read-only, `r--r--r--`) |
| Manifest | `I7_V004_MANIFEST.json` (+ `.sha256`), overwrite-protected builder |
| Admissible | **61,335 ticker-days · 76 sessions (2026-04-28 → 2026-09-11) · 868 tickers · 19,793,865 bar rows** |
| Exclusions | X3 **7,038** (8 sessions) · E-PIT-2 2,044 · E-PIT-3 1,507 · E-PIT-4 10,890 |
| Reconciliation | 61,335 + 21,479 = **82,814** candidate cells — exact |

**X3 sessions (8) — broader than the review's three, and correctly so.** The review scanned v003's
*admitted* sessions and saw only `2026-07-09`. X3-as-specified also removes cells in sessions the
calendar never admitted: the three calendar-excluded dates (`2026-07-09`, `2026-07-24`, `2026-08-25`)
plus five sessions absent from the calendar entirely (`2026-05-01`, `05-14`, `05-15`, `05-28`, `06-16` —
vendor wrote rows on non-calendar dates) and the incomplete live session `2026-09-14`. All were already
non-admissible in v003; v004 re-labels them under the governing rule. **The admitted cohort changes by
exactly one session: 2026-07-09 (827 cells) — v003 62,162 − 827 = 61,335.**

**Verification (all performed on the frozen artifacts):**

| Required check | Result |
|---|---|
| 2026-07-09 handled per X3 | **958 cells, 100% X3, 0 admitted, 0 bars in `flow_bars_v004`** |
| Every session 2026-08-28→09-11 has an evaluable X3 status | **YES** — all 11 admitted by the extension (827–832 admissible cells each; 2026-09-02: 74; 2026-09-08: 1) |
| X1–X6 mechanically enforced | X1/X2 subsumed (asserted) · X3 gate in builder · X4 ≡ E-PIT-4 · X5/X6 estimation-layer, recorded in the manifest |
| Ledger reconciles | 61,335 + 7,038 + 2,044 + 1,507 + 10,890 = 82,814 ✓ |
| No pre-cutoff cells admitted | **0** (same-day writes before 16:15 WIB among admitted: 0) |
| Outcome blindness intact | `admissible()` signature unchanged and test-asserted (18/18 pass); builder reads only bar fields, `updated_at`, calendar membership; no close/return/outcome column |
| v003 immutable | store sha256 recomputed post-build: `a4a9f7f9…` byte-identical |

---

# HISTORICAL RECORD — V003 FREEZE (superseded by section 0; retained immutable)

> **I7 is NOT registered and NOT executed.** No return, IC, p-value, power, or profitability quantity was
> computed. No outcome column was read by any artifact built here. The I7 candidate specification
> (`BRANCH_A_NEW_MECHANISM_AUDIT_2026-09-14.md`) is **unchanged**. No hypothesis or family was created.
> `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md`, `EXPERIMENT_LEDGER.jsonl`, `DECISION_LOG.md`,
> `g1_config.json`, Dataset B and the v002 freeze are **untouched**. All production access was `mode=ro`.

---

## 1. What was built

| Artifact | Purpose |
|---|---|
| `i7_accrual/i7_admissibility.py` | The E-PIT gate — pure, importable, testable. Encodes E-PIT-1..4 and the 16:15 WIB cutoff |
| `i7_accrual/build_v003_freeze.py` | Read-only builder for the immutable admissible-cohort freeze |
| `i7_accrual/capture_guarded.py` | Pre-fetch operational guard wrapping the prospective service **without modifying it** |
| `i7_accrual/test_i7_admissibility.py` | 18 tests, **18/18 passing** |
| `i7_accrual/store/I7_V003_ADMISSIBLE_v1.sqlite` | **The freeze.** Read-only (`r--r--r--`) |
| `i7_accrual/store/I7_V003_MANIFEST.json` (+ `.sha256`) | Freeze manifest |

ZCode's `flow_capture_prospective/prospective_capture.py` was **not modified**. It already implements
immutable raw payloads (content-addressed, `O_EXCL`), retrieval timestamps (`captured_at_utc`), response
hashes, append-only manifest (`INSERT OR ABORT`) and run logs with `code_sha256`. What it lacked — and what
this package adds — is the **I7 admissibility concept and the post-session cutoff**.

## 2. Requirement-by-requirement status

| Req | Requirement | Status | Evidence |
|---|---|---|---|
| 1a | raw payloads immutable | **MET (pre-existing)** | content-addressed `raw/session=…/ticker=…/<sha256>.json.gz`, written `O_EXCL`; manifest `INSERT OR ABORT` |
| 1b | retrieval timestamps retained | **MET (pre-existing)** | `capture_manifest.captured_at_utc`, `tz_session` |
| 1c | session completeness explicit | **MET (added)** | `expected_bars()` — 335 Mon–Thu / 275 Fri; E-PIT-4 rejects any deviation; `expected_bars` stored per ledger row |
| 1d | capture cannot produce an admissible cell before the cutoff | **MET (added, two layers)** | §3 |
| 1e | 16:15 WIB requirement enforced **and tested** | **MET (added)** | `capture_permitted_now()`; 6 dedicated tests incl. exact boundary |
| 2 | immutable v003 freeze from provenance-valid capture | **MET** | §4 |
| 3 | E-PIT-1..4 encoded | **MET** | §5 |
| 6 | I7 spec preserved unchanged | **MET** | no edit to `BRANCH_A_NEW_MECHANISM_AUDIT_2026-09-14.md` |

## 3. The cutoff — enforced in two layers, deliberately

1. **Pre-fetch refusal** (`capture_guarded.py`). Refuses to launch a run against an incomplete session.
   Verified: a 13:00 WIB run against 2026-09-10 exits **3** with `REFUSED [E-PIT-3]`; an 18:30 run passes.
2. **Cohort gate** (`admissible()`, applied by the freeze builder). Even if a cell reaches the store by any
   other path — manual run, future scheduler, clock skew — it is classified **E-PIT-3** and never enters the
   frozen cohort.

> Layer 1 is operational hygiene. **Layer 2 is the guarantee**, because it judges each cell from its own
> recorded timestamp rather than from the honesty of whoever launched the run.

**Measured in the frozen cohort: same-day writes before 16:15 admitted = 0.**

## 4. The v003 freeze

| Field | Value |
|---|---|
| Store | `docs/research_programs/P-M/i7_accrual/store/I7_V003_ADMISSIBLE_v1.sqlite` |
| **sha256** | **`a4a9f7f90a8d3610d5f86163528f7f6fbde0994d8bb14651001bc16cd86ba0e0`** |
| Verification | recomputed via `sha256sum` CLI — a **separate code path** from the builder's `hashlib` — both agree |
| Bytes | 913,985,536 |
| Permissions | `r--r--r--` (store and manifest) |
| Manifest | `I7_V003_MANIFEST.json` + `.sha256` |
| Overwrite protection | the builder **refuses** to write over an existing freeze; a new version must be a new file |
| Provenance source | `stockbit_flow.updated_at` (pre-activation proxy — see §7) |

**Contents:**

| Table | Rows | Role |
|---|---:|---|
| `flow_bars_v003` | **20,070,910** | the admissible bars, copied out of the mutable production table |
| `admissibility_ledger` | **82,814** | **every candidate cell, admitted or not, with the rule that excluded it** |
| `freeze_manifest` | 21 | counts, hashes, rules, cutoff, module digests |

The ledger is the point: **exclusions are enumerated, never silent.** Anyone can re-derive the cohort from
it without trusting this document.

## 5. Exact counts

### Admissible cohort

| Quantity | Value |
|---|---:|
| **Admissible sessions** | **77** (2026-04-28 → 2026-09-11) |
| **Admissible ticker-days** | **62,162** |
| Admissible tickers | 868 |
| Admissible bar rows | 20,070,910 |
| Admissible cells per session | min 1 · p50 **829** · max 862 |

### Exclusions by rule

| Rule | Meaning | Excluded |
|---|---|---:|
| **E-PIT-1** | historical/backfilled v002 interval, wholesale | **239,695 ticker-days with bars** (session ≤ 2026-04-27) |
| **E-PIT-2** | no contemporaneous provenance (write lag outside 0–1 days) | **3,002** |
| **E-PIT-3** | same-day capture before the 16:15 WIB cutoff | **6,629** |
| **E-PIT-4** | bars absent, or `n_bars` ≠ weekday structural grid | **11,021** |

Rule precedence is deterministic and tested: E-PIT-1 is evaluated first, so a historical cell that also
violates 3 and 4 is counted **once**, under 1. Ledger arithmetic reconciles exactly:
62,162 + 3,002 + 6,629 + 11,021 = **82,814** candidate cells.

### Capture completeness

| Measure | Value |
|---|---:|
| Candidate cells in the contemporaneous window | 82,814 |
| **Admissible share** | **75.06%** |
| E-PIT-3 share of candidates | **8.00%** |
| Cells with bars vs admissible ledger rows | 62,162 = 62,162 ✓ |
| Cells violating the structural grid inside the freeze | **0** |
| Same-day pre-cutoff cells admitted | **0** |
| Earliest admitted session | 2026-04-28 (the E-PIT-1 boundary, exactly) |

> **E-PIT-3 removed 6,629 cells — 8% of all candidates.** The mid-session-capture trap identified by the
> PIT audit was real and material, not hypothetical. Without the gate those cells would have entered I7
> carrying structurally-zero late-session flow and been classified `EARLY_TILTED` by capture artifact.

## 6. Is capture operationally ready?

**The gate is ready. The service is built but NOT activated** — activation remains an Owner action and was
not performed.

| Component | State |
|---|---|
| Admissibility gate | **READY** — 18/18 tests pass |
| Pre-fetch guard | **READY** — verified refuse/permit |
| Freeze mechanism | **READY and exercised** — freeze built, hashed, immutable, overwrite-protected |
| Prospective capture service | **BUILT, NOT ACTIVATED** — no cron, no systemd, no scheduler entry |
| Raw-payload provenance for the *existing* 77 sessions | **NOT AVAILABLE** — see §7 |

### Activation requirements (stated, not performed)

1. Owner authorization.
2. Schedule **after 16:15 WIB** — `capture_guarded.py` enforces it, but scheduling it correctly is the
   operational half.
3. Run the service's own selftest plus `test_i7_admissibility.py`.
4. Isolated store only; never `data/walkforward.db`.

## 7. The honest residual limitation

The 77 admissible sessions predate the prospective service. Their provenance rests on
**`stockbit_flow.updated_at`** — a write-time stamp made by our own system in the same commit as the bars,
and never subsequently moved (the backfill *skips* complete cells rather than overwriting them).

That proves **we held this data on the session date, and it was never rewritten.** It is the PIT claim I7
needs, and it is why these cells are admissible.

It does **not** preserve the vendor's raw response, request parameters, or a response hash. So the cohort
supports *"we had it at formation time"* but not *"here is the vendor's original payload, re-verifiable by
a third party."* Once the service is activated, future sessions carry both.

**This limitation must be written into the I7 registration, not discovered afterwards.** It is a
verification weakness, not an availability weakness — a materially weaker defect than the one that
disqualified the v002 interval, and it is stated here so the distinction survives into the registration.

### One cohort characteristic to record

**2026-09-08 carries a single admissible cell.** It passes E-PIT-4 (that one ticker has a complete grid) but
the session is degenerate. **No minimum-cells rule was added** — that would modify the I7 specification,
which this task forbids. The spec already handles it: a one-cell session cannot contain both states, so it
is skipped and counted at estimation time.

## 8. Acceptance condition

> *"I7 must be ready for later registration without further provenance redesign, while remaining strictly
> outcome-blind during accrual."*

**Met.**

- **No further provenance redesign is required.** The E-PIT rules are frozen in code and tested; the freeze
  mechanism is exercised and repeatable; activation upgrades future cells without changing any rule. When
  the service is activated, `admissible()` is called with `capture_manifest.captured_at_utc` in place of the
  proxy — a **source substitution, not a rule change**.
- **Outcome-blindness is structural, not promised.** `admissible()`'s signature is
  `(session_date, captured_at_wib, n_bars)` — no price, return, or outcome can reach it, and a test asserts
  that signature. The builder reads only bar fields, `updated_at`, and the calendar.
- **Accrual is passive.** The cohort grows ~21 sessions/month with no decision required. Each new freeze is
  a new version; the existing freeze cannot be overwritten.

## 9. What remains for the Owner (unchanged by this task)

1. **Register now on 77 sessions, or wait for accrual?** 77 is ~23% of C3's 329 daily observations — a real
   risk of an indeterminate result, which is `RETIRED — UNPOWERED` rather than a failure, but spends a
   permanent family slot either way.
2. **Activate prospective capture?** Not performed here.
3. **Spend P-M slot #3**, and **accept the B4 (PPK/board) limitation.**

*No recommendation is offered on any of these.*

---

## PROVENANCE

| Item | Value |
|---|---|
| Freeze sha256 | `a4a9f7f90a8d3610d5f86163528f7f6fbde0994d8bb14651001bc16cd86ba0e0` (double-verified) |
| Source | `data/walkforward.db`, `mode=ro` |
| Tests | `test_i7_admissibility.py` — **18/18 pass** |
| Commands | `build_v003_freeze.py` (dry run, then `--write`); `test_i7_admissibility.py`; `capture_guarded.py --dry-run` |

**Note on the builder's query plan:** three iterations were needed. A grouped scan over
`stockbit_flow_bars` (~98M rows) ignores the date index because the `WHERE` sits on the second primary-key
column; a per-date query uses `idx_flow_bars_date` but is not covering and pays ~26M random row fetches. The
shipped form iterates **per ticker**, which is a covering range scan on the primary key
`(ticker, trade_date, bar_time)`. Read-only throughout; no data was affected.

# CONFIRMATIONS

- **I7 not registered · not executed · specification unchanged**
- **Zero returns / IC / p-values / power / backtests**
- **Zero registry mutations · zero family creation**
- **Zero writes to `data/walkforward.db`, Dataset B, or the v002 freeze**
- **Prospective capture NOT activated**
- Writes confined to `docs/research_programs/P-M/i7_accrual/`
