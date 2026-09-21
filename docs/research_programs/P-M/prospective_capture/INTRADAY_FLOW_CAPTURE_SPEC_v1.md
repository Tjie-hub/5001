# PROSPECTIVE CAPTURE SPEC v1 — intraday flow + security classification

**Date:** 2026-09-14 · **Status:** DESIGN ONLY — nothing deployed, nothing scheduled, no capture started.
**Authority:** generated point-in-time record. **Companion:** `../DATA_GAP_CLOSURE_AUDIT_2026-09-14.md`

> **This spec introduces no hypothesis, no threshold, no feature, and no alpha construct.** It specifies
> provenance for data the estate already receives, plus forward capture of classification fields it
> currently discards on arrival.

---

## 1. Why this is not a novel design

`docs/research_programs/P-M/dataset_b/` **already implements the correct pattern**, and it was verified
working in this audit. Its store contains, alongside the data:

| Table | Rows | What it gives |
|---|---:|---|
| `raw_responses` | 30,880 | **gzipped immutable raw API payload** + `captured_at_utc` + `capture_version` |
| `capture_manifest` | 30,880 | per-cell `status`, `http_status`, `requested_from/to`, `returned_from/to`, `date_echo_match`, `n_buy`, `n_sell`, `truncated_buy/sell`, `latency_ms`, `retry_count`, `error`, `captured_at_utc` |
| `capture_run_log` | 3 | `run_id`, `code_sha256`, `roster_artifact_sha256`, `cells_intended/attempted/success/empty/failed`, `cadence_s`, `limit_param`, `host` |

That store's sha256 was re-verified during this audit as **`21661f033145ef90657f…`**, matching
`DATASET_B_FREEZE_MANIFEST_v1` exactly — the pattern demonstrably produces a reproducible, hash-pinnable
artifact.

**Production `stockbit_flow_bars` has none of this.** 98,454,570 rows, zero provenance columns, and both
writers use `INSERT OR REPLACE` (`stockbit_fetcher.py:789`, `tools/backfill_flow_bars.py:154`) — a re-fetch
overwrites history in place and leaves no trace. The content is excellent; it simply cannot be *proven*.

**So the recommendation is to port a proven in-repo pattern, not to design something new.**

---

## 2. Scope — two independent capture streams

### Stream A — intraday flow provenance (wraps existing collection)

Does **not** change what is fetched, when, or how often. It adds an immutable provenance sidecar so that
future intraday research is PIT-defensible.

### Stream B — security classification (new collection)

Captures the classification fields that are class **D** today and are the direct cause of HYP-PM-0008
blocker **B4**. IDX publishes all of them; the estate has simply never stored them.

---

## 3. Stream A — schema

Written to a **separate** store, never to `data/walkforward.db`:
`docs/research_programs/P-M/prospective_capture/store/INTRADAY_FLOW_CAPTURE_v1.sqlite`

```sql
-- immutable raw payload; one row per (ticker, session, attempt). NEVER updated, NEVER deleted.
CREATE TABLE IF NOT EXISTS raw_responses (
  capture_id        TEXT PRIMARY KEY,      -- uuid4
  ticker            TEXT NOT NULL,
  session_date      TEXT NOT NULL,         -- WIB calendar date, YYYY-MM-DD
  request_url       TEXT NOT NULL,
  request_params    TEXT NOT NULL,         -- exact JSON sent
  http_status       INTEGER,
  raw_json_gz       BLOB,                  -- gzip of the verbatim response body
  response_sha256   TEXT NOT NULL,         -- sha256 of the UNCOMPRESSED body
  retrieved_at_utc  TEXT NOT NULL,         -- ISO-8601 with offset
  market_tz         TEXT NOT NULL DEFAULT 'Asia/Jakarta',
  capture_version   TEXT NOT NULL
);

-- one row per (ticker, session) per run: what we intended, what we got.
CREATE TABLE IF NOT EXISTS capture_manifest (
  run_id            TEXT NOT NULL,
  ticker            TEXT NOT NULL,
  session_date      TEXT NOT NULL,
  capture_id        TEXT,                  -- -> raw_responses
  status            TEXT NOT NULL,         -- SUCCESS | EMPTY | FAILED | SKIPPED
  bars_returned     INTEGER,
  bars_expected     INTEGER,               -- from the session grid (section 5)
  completeness      REAL,                  -- bars_returned / bars_expected
  complete_flag     INTEGER,               -- 1 iff completeness = 1.0
  first_bar_time    TEXT,
  last_bar_time     TEXT,
  grid_gaps         TEXT,                  -- JSON list of missing bar_times
  latency_ms        INTEGER,
  retry_count       INTEGER NOT NULL DEFAULT 0,
  error             TEXT,
  PRIMARY KEY (run_id, ticker, session_date)
);

-- one row per run.
CREATE TABLE IF NOT EXISTS capture_run_log (
  run_id                 TEXT PRIMARY KEY,
  started_at_utc         TEXT NOT NULL,
  finished_at_utc        TEXT,
  code_sha256            TEXT NOT NULL,    -- sha256 of the capture script
  universe_artifact_sha  TEXT,             -- pinned roster
  calendar_artifact_sha  TEXT,
  cells_intended         INTEGER,
  cells_attempted        INTEGER,
  cells_success          INTEGER,
  cells_empty            INTEGER,
  cells_failed           INTEGER,
  cadence_s              REAL,
  host                   TEXT,
  note                   TEXT
);
```

**Invariants (each enforced by a test in §6):**

| # | Invariant |
|---|---|
| A1 | `raw_responses` is **append-only** — no `UPDATE`, no `DELETE`, no `INSERT OR REPLACE` anywhere in the writer |
| A2 | Every `capture_manifest` row with `status='SUCCESS'` has a resolvable `capture_id` |
| A3 | `response_sha256` recomputed from `gunzip(raw_json_gz)` equals the stored value, for every row |
| A4 | A re-run produces a **new** `run_id` and **new** `capture_id`s; prior rows are untouched |
| A5 | Every timestamp carries an explicit offset; `session_date` is WIB, `retrieved_at_utc` is UTC — never mixed |
| A6 | The parsed bar table is **derivable** from `raw_responses` alone (deterministic reconstruction, §6) |

## 4. Stream B — security classification schema

```sql
-- PIT classification. Modelled directly on data/walkforward.db::idx80_membership_history,
-- which is this repository's exemplar of a correct PIT reference table.
CREATE TABLE IF NOT EXISTS security_classification (
  ticker            TEXT NOT NULL,
  effective_from    TEXT NOT NULL,
  effective_to      TEXT,                  -- NULL = still in force
  board             TEXT,                  -- UTAMA | PENGEMBANGAN | EKONOMI_BARU | PEMANTAUAN_KHUSUS
  special_monitor   INTEGER,               -- 1 if on Papan Pemantauan Khusus that day
  instrument_type   TEXT,                  -- SAHAM | ETF | DIRE | WARRANT | OTHER
  listing_date      TEXT,
  suspension_flag   INTEGER,
  confidence        TEXT NOT NULL,         -- PRIMARY_VERIFIED | CROSS_VALIDATED | BRACKETED_RECONSTRUCTED
  source            TEXT NOT NULL,         -- exact document / announcement identifier
  source_url        TEXT,
  source_sha256     TEXT,
  retrieved_at_utc  TEXT NOT NULL,
  PRIMARY KEY (ticker, effective_from)
);
```

**The `confidence` vocabulary is adopted verbatim from `idx80_reconstitution_periods`** so that every PIT
reference table in the estate grades evidence on one scale.

> **Rule B1 — no silent fill.** A field that is unknown for a period is `NULL` with **no row asserting a
> value**. Absence is never encoded as a default. Forward-filling a classification across an unobserved
> interval is prohibited; if an interval is inferred, it is marked `BRACKETED_RECONSTRUCTED` and its
> bracketing evidence is named in `source`.

> **Rule B2 — historical reconstruction is out of scope for this stream.** Stream B is **class C,
> prospective-only**, by construction. It fixes the gap from its start date forward. It does **not**
> retroactively make 2023 classifiable, and must never be presented as doing so.

## 5. Session grid (shared)

Derived in this audit from `stockbit_flow_bars` on 2026-03-10 (859 tickers, 100% grid completeness):

```
09:00 .. 11:59   180 bars
[12:00 .. 13:29] lunch break — structurally absent, NOT missing data
13:30 .. 15:49   140 bars
[15:50 .. 15:59] pre-closing / closing auction — structurally absent
16:00 .. 16:14    15 bars
                 --------
                 335 bars per ticker-session
```

`bars_expected = 335` for a full session. Any deviation is recorded in `grid_gaps`, never silently
tolerated. **The grid must be re-derived, not assumed, if IDX changes session hours** — trading hours
already changed once inside the corpus window (2023-04-03, per LC-PM-0009).

## 6. Validation harness (to build alongside, before any capture runs)

| Test | Asserts |
|---|---|
| `test_raw_responses_append_only` | writer source contains no `UPDATE`/`DELETE`/`INSERT OR REPLACE` against `raw_responses` (source-scan, in the style of `tests/test_architecture_boundary.py`) |
| `test_response_hash_roundtrip` | for a sample, `sha256(gunzip(raw_json_gz)) == response_sha256` |
| `test_deterministic_reconstruction` | re-parsing `raw_responses` reproduces the parsed bar table **byte-identically** — the load-bearing test; without it "immutable raw" is decorative |
| `test_manifest_completeness_accounting` | `cells_intended == success + empty + failed + skipped` for every `run_id` |
| `test_timezone_explicit` | every timestamp column parses with an explicit offset; no naive datetimes |
| `test_no_silent_fill` | no `security_classification` row asserts a value for a period whose `source` is empty |
| `test_isolated_store` | the capture writer never opens `data/walkforward.db` in write mode |

## 7. What this spec deliberately does NOT do

- Does not modify `stockbit_flow_bars`, `data/walkforward.db`, or the frozen Dataset B store.
- Does not backfill, re-fetch, or alter any existing row.
- Does not schedule anything, deploy anything, or start any capture.
- Does not define a feature, threshold, state, or signal.
- Does not make 2023 classifiable (§B2) — it cannot, and claiming otherwise would be the silent-fill
  failure this spec exists to prevent.
- Does not close HYP-PM-0008 blocker **B4** for the R3 window. B4 is retrospective; this stream is
  prospective. **A hypothesis whose population is dated before the capture start date remains
  unclassifiable.**
