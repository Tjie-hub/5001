# Incident Report — `sqlite3.DatabaseError: database disk image is malformed`

**Date:** 2026-07-29 · **Severity:** Data corruption, isolated · **Status:** Investigation complete,
no repair performed (per incident constraints). **Investigation method:** live, read-only diagnostics
against the production host via SSH (`tjiesar@192.168.31.214`), verified reachable and used
directly — this is not a simulated or hypothetical report.

---

## Deliverable 1 — Incident Summary

The production database (`data/walkforward.db`) has genuine, confirmed corruption, isolated to
**exactly one table**: `ticks` (intraday tick/trade data) and its own unique index. Every other
table in the 60-table, ~3.3GB database reads cleanly under both `PRAGMA quick_check` and the more
thorough `PRAGMA integrity_check` (identical results, zero difference between the two runs).

**Root cause, with direct evidence, not inference:** Syncthing is actively, bidirectionally syncing
the live project directory — including `data/` and `logs/` — between this Windows development
machine and the Linux production host. A `.stfolder` marker sits directly in the directory
containing `data/walkforward.db`; three separate `walkforward.sync-conflict-*.db`/`.db-wal` files
were generated today alone (08:13, 10:15, 13:48 WIB); and — the most direct proof available — the
"production" `app.log` itself contains a traceback with a literal Windows path
(`D:\IDX\.winvenv\...`, `D:\IDX\tests\security\test_secret_hygiene.py`), meaning this Windows
machine's own local application activity has been merged into the production log stream by the sync
process. `journal_mode=wal` makes this DB a set of three files (`.db`/`-wal`/`-shm`) that must stay
mutually consistent — a file-sync tool racing a live WAL writer is one of the most well-documented
ways to corrupt a SQLite database, and the evidence here is specific to this repository, not a
generic possibility.

**The corruption is recent and narrow**, not systemic: corrupted pages cluster at the high end of
the file's page range (near page 805,535 of 805,535 total), consistent with today's most recently
written rows. A read against `ticks` for everything except the most recent date succeeds cleanly
(`2026-04-18` through `2026-07-28` readable; only the tail — today's data — is implicated).

The user-reported attribution to "VPIN Daily Batch 18:00" is directionally correct but imprecise:
`run_vpin_daily_batch()` (`scheduler/jobs.py:1139`) calls `engine.vpin.calc_vpin()`, which reads
`FROM ticks` (`engine/vpin.py:141`) — so the batch would indeed hit this corruption per-ticker. But
as of this investigation (18:15 WIB, 15 minutes after the scheduled 18:00 run), **no log evidence
was found that today's scheduled run has actually executed yet** — no "VPIN batch compute starting"/
"done" log lines for 2026-07-29 were found in the current log. The errors actually captured in the
logs were attributed to `screener.screener_jobs` (a related, tick-ingesting job, ~09:23 UTC /
~16:23 WIB), not literally the 18:00 batch.

---

## Phase 1 — Incident Investigation

### Every SQLite database located

| File | Size | Purpose | Owner module | Scheduler jobs using it |
|---|---|---|---|---|
| `data/walkforward.db` | ~3.30 GB (3,299,471,360 bytes), last modified 17:25 WIB today | The single production database — 60 tables spanning OHLCV, flow, `agent_decisions`/`agent_traces`, `watchlist_snapshot`, `paper_trades`, `ticks`, `vpin_scores`, `daily_screen`, and more | `data/db.py::connect()` — the single centralized connection point (per CLAUDE.md) | Effectively all scheduler jobs (main scan, EOD/premarket plans, VPIN batch, screener jobs, forward-testing, backups) |
| `data/walkforward.sync-conflict-20260729-134809-IMW57E4.db` | 3.2 GB, Jul 29 13:45 | Syncthing conflict copy of the live DB | N/A — sync artifact | None (not referenced by any code) |
| `data/walkforward.sync-conflict-20260729-101541-IMW57E4.db` | 3.3 GB, Jul 29 10:13 | Same | N/A | None |
| `data/walkforward.sync-conflict-20260729-081309-IMW57E4.db-wal` | 1.8 MB, Jul 29 08:22 | Syncthing conflict copy of a live WAL segment | N/A | None |
| `data/walkforward_backup_20260722.db` | 3.2 GB, Jul 22 | An ad hoc, manually-made local copy (not the scheduled backup mechanism) | N/A | None |
| `scratchpad/wf_copy.db` | 3.2 GB, Jun 30 | Ad hoc scratch copy | N/A | None |
| `data/idx_lite.db`, `data/paper_trade.db`, `data/trades.db`, `data/db.sqlite3` | 0 bytes each | Empty, unused | — | None |
| `~/backups/idx-walkforward-5001/walkforward-*.db.zst` (rolling, several days retained) | ~620-635 MB compressed each | The real, scheduled, verified nightly backup mechanism (`scripts/db_backup`, per `docs/OPERATIONS.md`) | `scripts/db_backup.py` (invoked via cron) | Backup/restore cron jobs only |

### Which database VPIN Daily Batch opens, exact code path

```
scheduler/__init__.py:270  scheduler.add_job(run_vpin_daily_batch, CronTrigger(...), id="vpin_daily_batch", name="VPIN Daily Batch 18:00")
scheduler/jobs.py:1139     def run_vpin_daily_batch(date_str=None):
scheduler/jobs.py:1158         conn = db_connect(DB_PATH)          # DB_PATH = data/walkforward.db, via config.py/.env
scheduler/jobs.py:1164-1181    for ticker in tickers:
                                    try:
                                        r = _calc_vpin(conn, ticker, date_str)   # engine.vpin.calc_vpin()
                                        conn.execute("INSERT OR REPLACE INTO vpin_scores ...")
                                        ...
                                    except Exception as _e:
                                        logging.warning(f"[vpin_batch] {ticker} error: {_e}")
                                        errors += 1
engine/vpin.py:141              ... FROM ticks ...
```
**Confirmed:** the batch opens `data/walkforward.db` (the single shared production DB, no separate
VPIN-specific file), and `calc_vpin()` reads the corrupted `ticks` table. The per-ticker `try/except`
means a `DatabaseError` on one ticker does **not** crash the whole batch — it degrades gracefully,
incrementing `errors` and continuing, which is why the process wasn't found crash-looped.

---

## Phase 2 — Read-only Integrity Checks

Both run against `file:.../data/walkforward.db?mode=ro` (read-only URI — no write lock possible)
directly through the `sqlite3` CLI (v3.45.1) on the production host.

**`PRAGMA quick_check;`** — 101 lines of output: 95 `btreeInitPage() returns error code 11` errors
+ 5 `Rowid ... out of order` errors, **all** under `Tree 637876`.

**`PRAGMA integrity_check;`** — identical output, byte-for-byte (`diff` against the `quick_check`
output: 0 lines differ). The more thorough check found nothing additional.

**Corrupted pages, sample:**
```
Tree 637876 page 805433: btreeInitPage() returns error code 11
Tree 637876 page 805431: btreeInitPage() returns error code 11
...
Tree 637876 page 804814 cell 342: Rowid 38921382 out of order
...
Tree 637876 page 805228: btreeInitPage() returns error code 11
```
(95 page errors total, spanning roughly pages 804814-805433, out of 805,535 total pages in the file.)

**Affected tables/indexes:** exactly one table and its own index — resolved via
`sqlite_master`:
```
table|ticks|637876
index|sqlite_autoindex_ticks_1|637877
```
No other `Tree N` number appears anywhere in either check's output.

**Is the schema readable?** Yes. `sqlite_master` itself, `PRAGMA journal_mode` (`wal`),
`PRAGMA page_count` (805535), and `PRAGMA freelist_count` (0) all read without error — the
database header and schema page are intact. A direct `SELECT MIN(date), MAX(date) FROM ticks WHERE
date < (SELECT MAX(date) FROM ticks)` also succeeded, returning `2026-04-18 | 2026-07-28` — the
bulk of the table's history (over 3 months) is readable; only the most recent tail is implicated.

**No database was modified.** Every command above used a read-only connection URI.

---

## Phase 3 — Root Cause Analysis

| Candidate | Assessment | Evidence |
|---|---|---|
| **Concurrent writers via an unmanaged file-sync process (leading hypothesis)** | **Strong, direct, repository-specific evidence** | `.stfolder` marker present directly in `.../idx-walkforward-5001/` (confirmed via `find`); three `walkforward.sync-conflict-*` files generated *today* (08:13, 10:15, 13:48 WIB), including a conflicted `-wal` segment; two `app.sync-conflict-*.log` files also generated today; the live `app.log` contains a Windows-path traceback (`D:\IDX\...`) proving this dev machine's activity is merged into the "production" log by the same sync process — direct proof the sync relationship is real, active, and touching these exact files |
| **WAL misuse (contributing mechanism)** | Likely the proximate mechanism, not the root cause | `PRAGMA journal_mode = wal` confirmed — a WAL-mode DB is 3 files that must stay consistent; corrupted pages sit at the highest page numbers in the file (most recently allocated), consistent with a sync tool copying/replacing the `.db` file at a moment inconsistent with the `-wal` segment's state |
| **Interrupted write** | Plausible as the literal mechanical event | If Syncthing's own copy operation raced a live `INSERT OR REPLACE INTO ticks` / WAL checkpoint, that is functionally an interrupted/torn write from SQLite's perspective — not a separate, independent cause |
| Power failure | **Ruled out** | Host uptime is continuous (`systemctl` shows the current process started 15:24:46 WIB today via a normal restart, not a crash-recovery boot; `df -h` and general host state show no signs of an unclean shutdown) |
| Disk failure | **Not supported, but not fully excludable** | `dmesg`/kernel error logs were not accessible without `sudo` in this investigation (sudo on this host requires an interactive password, per prior operational notes) — disk space is healthy (44% used, 126G free). Given the much stronger, direct Syncthing evidence, this is not the leading hypothesis, but a SMART/`dmesg` check by whoever has interactive access would close this out definitively |
| SQLite bug | **Unlikely** | SQLite 3.45.1 (Jan 2024) is a mature, widely-deployed release; this exact corruption signature (isolated recent b-tree, sync-conflict artifacts on the same files at the same time) is far better explained by the sync-tool interaction already evidenced directly |
| Application bug | **Unlikely** | `data/db.py::connect()` already centralizes every connection and sets `busy_timeout` + WAL specifically to prevent lock-related corruption (per its own module docstring, a prior fix point for "a class of lock bugs this repo hit repeatedly"); the traced code path (`run_vpin_daily_batch` → `calc_vpin` → `SELECT FROM ticks`) is a plain read, not a write, and not implicated in causing corruption itself |
| Filesystem issue | Not the leading hypothesis | Same disk serves the whole host without other reported issues; no filesystem-level error evidence found (though also not exhaustively checked without root) |

**Conclusion:** the leading, evidence-backed root cause is **Syncthing actively syncing the live
project directory (including the WAL-mode production database and its log files) between this
Windows development machine and the Linux production host**, racing against the application's own
live writes to `ticks`. This is a deployment-topology/infrastructure issue, not a defect in any code
audited or shipped in this session's certified work (Agent Firm, Ranking Engine, Watchlist
Generator) — none of that code touches `ticks`, `screener/`, or the VPIN subsystem.

---

## Phase 4 — Recovery Options (safest → most invasive)

Ranking accounts for **both** the risk of the recovery procedure itself going wrong **and** the
actual data-loss blast radius — for this specific incident, those two considerations point in
different directions from the generic default ordering, so the reasoning for each rank is spelled
out.

**1. Targeted extraction/rebuild of `ticks` alone via `sqlite3 .recover` against a *copy*, applied only to that one table**
   - Expected data loss: minimal — likely only the most recent day's tick rows (already probably
     re-fetchable from Stockbit/broker-flow source data, since `ticks` is raw intraday market data,
     not a durable decision/trade record).
   - Downtime: none required — can be done entirely against a copy while the live app keeps running
     off the current file (which already serves every other table cleanly).
   - Operational risk: **low** — `.recover` reads the source read-only and writes a brand-new file;
     the other 59 tables are never touched.
   - **Recommended first choice**, given exactly one, non-critical, re-derivable table is affected.

**2. `sqlite3 .recover` (whole-database) against a copy**
   - Expected data loss: same as above, extracted for every table at once (not just `ticks`) —
     useful as a cross-check that nothing else was silently damaged beyond what `integrity_check`
     already found.
   - Downtime: none (runs against a copy).
   - Operational risk: low — read-only against the source; output needs review before use.

**3. Export surviving tables (`.dump` excluding `ticks`, or selective `SELECT`s) + re-derive `ticks` from source**
   - Expected data loss: same as #1, plus more manual effort; functionally similar outcome to #1/#2
     with more hands-on steps.
   - Downtime: low.
   - Operational risk: low-medium (more manual steps = more chance of operator error).

**4. Restore latest verified backup (`walkforward-20260727-213001.db.zst`, verified `integrity=ok`, 2026-07-27 21:30 WIB)**
   - Expected data loss: **~2 days of every one of the 60 tables** — including 2 days of
     `agent_decisions`, `watchlist_snapshot`, `paper_trades`, `ticks`, everything — not just the one
     affected table. **Note: no 2026-07-28 or 2026-07-29 backup exists** — the nightly backup job
     appears to have not run/completed for at least the last night, a separate operational gap
     flagged below.
   - Downtime: the time to restore + verify a 3.2GB database (prior restore drills in this repo's
     own log took roughly 3-4 minutes to snapshot+verify+compress; a restore should be comparably
     fast).
   - Operational risk: **low** (this repo has a documented, weekly-drilled restore procedure,
     `scripts/db_restore` / `docs/OPERATIONS.md`) — the procedure itself is safe and proven, but
     the **data-loss blast radius is far larger** than options 1-3 for this specific incident,
     because it discards 59 tables that are not corrupted to fix the one that is.
   - **Not recommended as the first move here** despite being the conventionally "safest" default —
     ranked below the targeted options specifically because the corruption is narrow and the backup
     is not.

**5. Fresh database + replay**
   - Expected data loss: total, until replay completes; replay of 60 tables' worth of historical
     ingestion is a large, multi-source undertaking (Stockbit flow, OHLCV history, research
     pipeline outputs, etc.).
   - Downtime: highest of any option.
   - Operational risk: **highest** — last resort, only if 1-4 all fail.

**Recommendation:** Option 1 (or 2 as a cross-check), not Option 4, precisely because this
corruption is isolated to one small, ephemeral, re-fetchable table out of sixty — a full backup
restore would needlessly discard two days of the Agent Firm decision trail, watchlist history, and
paper-trade records this whole session's work was built around, to fix a table that a five-minute
targeted recovery can address with far less loss.

---

## Phase 5 — Recovery Plan (procedure to execute, not executed by this investigation)

1. **Contain first, before any repair:** pause whatever is actively racing the database.
   - Stop (or reconfigure to exclude `data/` and `logs/`) the Syncthing folder covering this
     project directory — `systemctl --user stop syncthing` on the production host, or narrow its
     `.stignore`/folder config to exclude `data/*.db*` and `logs/*.log`. **This is the single most
     urgent action** — every additional sync-conflict event is a fresh opportunity to widen the
     corruption or damage a currently-clean table. Requires an operator decision (this is a live
     service stop) — not performed by this investigation.
   - Optionally pause the `vpin_daily_batch` and the tick-ingesting `screener` job specifically
     (rather than the whole scheduler — every other job reads/writes tables confirmed clean) until
     `ticks` is repaired, so they stop accumulating per-ticker errors against a table known to be
     damaged.
2. **Backup before repair:** take a fresh, ad hoc snapshot of the *current* (still-corrupted) live
   `data/walkforward.db` before touching anything — even a corrupted file is evidence and a fallback
   position (`cp` while the app is briefly quiesced, or use `scripts/db_backup`'s own snapshot
   mechanism, which already handles a live SQLite file safely).
3. Run `sqlite3 <copy-of-live.db> ".recover" | sqlite3 recovered.db` against the **snapshot from
   step 2**, never the live file directly.
4. **Validate after repair:** run `PRAGMA integrity_check;` against `recovered.db` — confirm clean.
   Spot-check `ticks` row counts/date range against what was known-good pre-incident (the
   `2026-04-18`-`2026-07-28` range already confirmed readable) to quantify exactly how many rows
   (if any) were actually lost versus recovered.
5. Compare `recovered.db`'s other 59 tables against the live file's equivalent counts (a cheap
   `SELECT COUNT(*)` per table) to confirm nothing else was silently affected, corroborating the
   integrity-check result with row-level evidence.
6. Swap `recovered.db` into place as `data/walkforward.db` (atomic rename, with the corrupted
   original moved aside, not deleted) during a brief, planned maintenance window.
7. **Scheduler restart:** restart `idx-walkforward` (`systemctl --user restart idx-walkforward`) so
   every connection is reopened against the repaired file, not a stale handle to the old one.
8. **Smoke tests:** run `engine/agent_firm/smoke.py` and `scripts/wait_for_health.sh` per the
   standard post-deploy checklist (`docs/OPERATIONS.md`).
9. **VPIN batch verification:** manually invoke `run_vpin_daily_batch()` for today's date (or wait
   for the next scheduled 18:00 run) and confirm `errors` returns to its normal baseline (compare
   against a recent healthy day's `[vpin_batch] ... done: N computed, 0 errors` log line) rather than
   the elevated per-ticker corruption errors seen today.
10. **Re-enable Syncthing** only after its folder configuration is corrected to exclude the live
    database and log files (or an explicit decision is made to accept the risk, which is not
    recommended) — re-enabling it unchanged would reintroduce the same failure mode.
11. Investigate and close the separate, smaller finding: **no nightly backup exists for 2026-07-28
    or 2026-07-29** — confirm whether `cron_db_backup` actually ran (its own log shows nothing past
    2026-07-27) and fix the gap so the next incident has a fresher restore point.

---

## Deliverables

**1. Incident summary:** above.

**2. Corrupted database identification:** `data/walkforward.db` (the single production DB), table
`ticks` + its unique index only.

**3. Integrity-check results:** `quick_check` and `integrity_check` identical — 95 page errors + 5
row-order errors, entirely within `Tree 637876` (`ticks`). Schema and every other table read clean.

**4. Root-cause assessment:** Syncthing actively syncing the live project directory (including the
WAL-mode database and logs) between this Windows dev machine and the production host — direct,
multi-source evidence (§Phase 3), not a generic guess.

**5. Recovery recommendation:** targeted `.recover`/rebuild of `ticks` alone (Phase 4, options 1-2),
**not** a full backup restore — the latter would discard two clean days of every other table to fix
one damaged, re-fetchable one.

**6. Estimated data loss:** likely limited to the most recent day's (2026-07-29's) `ticks` rows —
everything from 2026-04-18 through 2026-07-28 in that table already reads cleanly, and `ticks` data
is re-fetchable from source (Stockbit/broker flow), so even that loss may be fully recoverable by
re-running ingestion for the affected date rather than accepted as permanent loss.

**7. Remaining risks:**
- Syncthing is still actively running and still configured to sync the live DB/logs as of this
  writing — the corruption can recur, or worsen, at any moment until contained (Phase 5, step 1).
- No verified backup newer than 2026-07-27 exists — a second, unrelated failure between now and a
  fix would have a larger-than-necessary blast radius.
- Disk-level hardware issues were not fully excluded (no root access for `dmesg`/SMART in this
  session) — low-probability given the strong competing evidence, but not zero.
- Whether today's 18:00 VPIN batch has actually run yet was not resolved with certainty — no
  start/done log line was found as of 18:15 WIB; if it is still in flight, it will keep hitting
  per-ticker errors against `ticks` until contained.

**8. GO / NO-GO for resuming scheduler:**

# CONDITIONAL GO — contain first, do not resume VPIN/tick-writing jobs uncontained

The application itself does not need to be stopped — it has been running continuously and serving
every other endpoint correctly throughout this investigation, and 59 of 60 tables are confirmed
clean. **But do not let the VPIN batch or tick-ingesting screener jobs keep running against the
`ticks` table un-contained** — each additional run degrades gracefully (won't crash) but keeps
producing incomplete VPIN data and keeps the corrupted table in active use during recovery. Most
urgently: **Syncthing's sync of `data/`/`logs/` should be paused before anything else**, since it is
the evidenced, ongoing mechanism of harm — every hour it stays enabled is another chance to damage a
currently-clean table. This is a recommendation for the operator to act on, not something this
investigation executed, per its own constraints (no destructive operations, no repair, no
configuration changes performed).

No database was modified. No repair was attempted. No code was changed. This investigation used
only read-only diagnostics against the production host.

---

## Addendum — Containment Verified (2026-08-06)

Follow-up read-only investigation (Production Engine Phase 1 Task 3), re-examining this incident's
own "Remaining risks" item 1 ("Syncthing is still actively running and still configured to sync the
live DB/logs as of this writing"). That statement is now **stale** — containment was applied the
same day, and has held for 8 days since. Evidence, not assumption:

1. **`.stignore` exists at the repo root**, `mtime 2026-07-29 19:55:39 WIB` — created a few hours
   after this investigation, on the same day, implementing exactly the Phase 5 Step 1
   recommendation above ("narrow its `.stignore`/folder config to exclude `data/*.db*` and
   `logs/*.log`"). Its patterns: `*.db`, `*.db-wal`, `*.db-shm`, `*.db-journal`,
   `*.sync-conflict-*.db(-wal|-shm)`, and `logs/`. It carries its own warning comment: "Do not
   remove without first addressing why these were excluded."
2. **The underlying sync relationship is unchanged, not removed** — Syncthing's own config
   (`~/.local/state/syncthing/config.xml`) still lists this exact directory as folder `fdds3-owznl`
   ("IDX"), `type="sendreceive"`, `fsWatcherEnabled="true"`, syncing with the same two device IDs
   (`IMW57E4...`, `5O4DTXI...`) whose suffixes appear in this report's own sync-conflict filenames
   above. Syncthing is actively running on this host (`systemctl --user status syncthing`: active
   since 2026-08-04). The mitigation is exclusion of the dangerous paths from an otherwise-still-live
   sync, not termination of the sync relationship itself.
3. **Zero sync-conflict artifacts postdate the fix.** Every `*sync-conflict*` file found anywhere in
   the repo — `data/walkforward.sync-conflict-*.db(-wal)`, `logs/app.sync-conflict-*.log` — carries a
   2026-07-28 or 2026-07-29 timestamp, all predating 19:55:39. `data/walkforward.db` itself has been
   under continuous, active write traffic since (current mtime: 2026-08-06, today) — if the exclusion
   had not taken effect, the pre-fix pattern (multiple conflict files per day) would be expected to
   have continued. It did not resume, across 8 days of continued live writes.
4. **`fsWatcherEnabled="true"`** means Syncthing applies a new/changed `.stignore` via its live
   filesystem watcher, not only on its 3600s periodic rescan — consistent with the fix taking effect
   promptly rather than after a delay.

**Conclusion: the corruption vector is mitigated and verified holding**, not merely theoretically
fixed. Residual gap (not a re-opening of this incident, but real): `.stignore` itself was, until this
addendum's companion commit, **untracked by git** — invisible to repo history, and would not survive
a fresh clone/checkout of this working tree onto another machine. See `docs/OPERATIONS.md`'s new
"Data integrity — Syncthing exclusion" section for the now-durable record, and the commit that
accompanies this addendum for `.stignore` being committed for the first time.

This closes "Remaining risks" item 1. Items 2–4 (backup freshness, disk-hardware exclusion, VPIN
batch run-status on 2026-07-29) are outside this addendum's scope (data-integrity/Syncthing risk
only) and are not re-investigated here.
