# PROSPECTIVE 1-MINUTE FLOW CAPTURE — DESIGN (2026-09-14)

**Status: BUILT, NOT ACTIVATED.** Nothing here is wired into cron, systemd, or any
scheduler. Activation is an owner action (see §7). Nothing here writes to
production `walkforward.db`, `research.db`, Dataset B, or any frozen store.

## 1. Why this exists (audit findings it addresses)

* 1-minute Stockbit flow bars are historically **near-complete** for the frozen
  v002 window (99.70% complete incl. confirmed-empties), but the frozen window
  ends 2026-04-27, and the live production table has **post-freeze defects**:
  4,311 true-gap ticker-days on 7 dates plus 6 full capture-outage sessions.
* The vendor's history for a given (ticker, date) is **not stable across fetch
  cohorts**: the 2025-08-05..2025-09-17 stretch was re-fetched in 2026-09 with
  5–26% nonzero daily summaries (vs a ~86% healthy baseline), while IHSG volume
  was flat across the stretch — i.e. what the vendor returns for a past date
  decays/changes. **The only durable research asset is the raw response captured
  close to the session.**
* Production's daily 18:30 WIB job persists **parsed rows only** — no raw
  response, no response hash, no per-request audit trail. If the parser or the
  vendor semantics are ever questioned, there is nothing to go back to.

This module therefore captures and retains **raw responses, content-addressed,
append-only**, with a complete request/response audit trail.

## 2. Store layout (separate isolated store — never touches Dataset B)

```
flow_capture_prospective/
  prospective_capture.py     service (this package)
  DESIGN.md                  this file
  store/                     created on first run
    raw/
      session=YYYY-MM-DD/
        ticker=<TICKER>/
          <response_sha256>.json.gz      # content-addressed, written once (O_EXCL)
    manifest.sqlite                      # capture_manifest + run_log (schema below)
    runs/
      RUN-<utc>-<digest>/run_manifest.json
      RUN-<utc>-<digest>/run_manifest.json.sha256
```

* **Immutable raw**: object name = sha256 of the exact response body bytes
  (decompressed identity preserved via gzip of the exact bytes received). A
  second capture of the same cell writes a NEW object if bytes differ; the
  manifest records the full object set per cell. Nothing is ever overwritten
  or deleted.
* **PIT-safe partitioning**: `session=` and `ticker=` partitions only — no
  capture-time data is mixed into session partitions, so "all responses for
  session S" is reconstructable exactly.

## 3. Manifest schema (manifest.sqlite)

```sql
CREATE TABLE capture_manifest (
  ticker TEXT NOT NULL, session_date TEXT NOT NULL,
  status TEXT NOT NULL,                -- SUCCESS / EMPTY / FAILED (terminal)
  attempt INTEGER NOT NULL,
  http_status INTEGER,
  url_host TEXT, url_path TEXT,        -- request metadata (no credentials)
  requested_from TEXT, requested_to TEXT,
  returned_from TEXT, returned_to TEXT,
  date_echo_match INTEGER,             -- vendor echoed the requested window
  n_rows INTEGER, truncation_suspected INTEGER,
  response_sha256 TEXT NOT NULL,
  response_bytes INTEGER NOT NULL,
  raw_object TEXT NOT NULL,            -- relative path under raw/
  captured_at_utc TEXT NOT NULL,
  tz_session TEXT NOT NULL,            -- 'Asia/Jakarta'
  error TEXT,
  PRIMARY KEY (ticker, session_date, attempt)
);
CREATE TABLE run_log ( ... run_id, started/finished_utc, code_sha256,
  config_digest, cells_intended/attempted/success/empty/failed, host, note ...);
```

## 4. Requirements coverage (mission §4 checklist)

| Requirement | Implementation |
|---|---|
| immutable raw response | content-addressed objects, O_EXCL write-once, never deleted |
| timestamp | `captured_at_utc` + session tz recorded per row |
| ticker / session / source | manifest columns incl. `url_host`/`url_path` |
| request metadata | requested window, attempt index, code_sha256, config digest |
| response hash | `response_sha256` (of exact body bytes); object named by it |
| completeness marker | `date_echo_match`, `truncation_suspected` (rows == limit), EMPTY classification |
| retry / checkpoint | manifest is the checkpoint: non-terminal cells are retried, terminal cells skipped; idempotent resume |
| no overwrite | `INSERT OR ABORT` on manifest PK; raw objects O_EXCL |
| PIT-safe partitioning | `session=`/`ticker=` partitions; session partition content fixed at capture |
| deterministic reconstruction | `rebuild_rows()` = pure function of raw bytes; same bytes ⇒ same rows (tested) |
| explicit timezone/session calendar | `tz_session='Asia/Jakarta'`; sessions validated against the admitted session calendar before capture |
| audit manifest | per-run `run_manifest.json` + sha sidecar; append-only `runs/` |

## 5. Vendor adapter

`vendor_fetch` mirrors the **validated Dataset B capture request verbatim**:
`GET https://exodus.stockbit.com/marketdetectors/{ticker}` with
`transaction_type=TRANSACTION_TYPE_NET`, `market_board=MARKET_BOARD_REGULER`,
`investor_type=INVESTOR_TYPE_ALL`, `limit=150`, `from=to=<session>`, bearer
auth from the repo-root `.stockbit_token` file, and it retains the **exact
response body bytes** (production `stockbit_fetcher.fetch_flow` parses and
discards them — that is the loss this service exists to prevent). Security
hardening: https-only, exact host pin, DNS resolution validated against
private/loopback/link-local/reserved/non-global addresses AND pinned for the
connection itself (`pin_validated_resolution` closes the TOCTOU rebinding
window between validation and connect; TLS/SNI still use the hostname so
certificate verification is unaffected), redirects disabled, ticker charset
restricted to A–Z/0–9, 15 s timeout. The offline selftest never imports the
adapter (fake fetcher), and the module loads without any network library.

## 6. Validation (offline, no network)

`python3 prospective_capture.py selftest` runs the built-in suite:
fake-fetcher run over 3 cells incl. one empty and one failing cell →
manifest accounting reconciles; second run is a no-op (checkpoint);
immutability violation (overwrite attempt) raises; rebuild determinism
(same raw ⇒ same rows, twice).

## 7. Activation (owner action, deliberately not automated)

1. Decide capture cadence (recommended: EOD 18:40 WIB after the production
   cron, or a shadow hook next to `stockbit_fetcher.py run_flow`).
2. `python3 prospective_capture.py capture --session <YYYY-MM-DD>` (or
   `--watch` loop) with the vendor adapter enabled.
3. Coverage reconciliation: compare `capture_manifest` against the session
   calendar; publish a weekly coverage report.
4. NEVER point this store at Dataset B or walkforward.db; the only writes are
   under `flow_capture_prospective/store/`.
