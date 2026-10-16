# ZCODE REPORT — Post-MSCI-shock hardening (brief of 2026-10-16)

**Executor:** ZCode · **Worked:** 2026-10-16 ~11:20–13:00 WIB · **Commits:** `ace1743`, `025cd2e`, `a8a07af` (+ this report) · **Not pushed** (per brief).
**Live deploys this session:** Z2 calendar via `scripts/safe_restart.sh` 11:45 WIB (preflight OK, 52 jobs registered; no scan/sweep active at restart).

---

## §0 — Corrections to my week review, checked

| Brief's correction | My verification |
|---|---|
| `_CONN_FACTORIES` already has `get_conn`/`_get_conn` | **Confirmed — I was wrong.** `tests/test_db_transaction.py:91-92` has both (plus `db.get_conn`). My claim came from a truncated `git show` diff window (the set literal wrapped onto a cut line). |
| Shock guard does not touch the forward tests | **Confirmed.** `grep` over `forward_testing/` and the P-M recorders: zero callers of `_event_guard_active`/`_macro_panic_state`/`_shock_guard_active`/`adaptive_strategy_selector`. All call sites are in `scheduler/scanner.py` (signal selection at :632/:1063/:1813, strategy weighting at :1546). Guard changes alter scanner output by design (that is what the forward-window frozen config exists to detect — see Z2 below), but the forward-test machinery itself never reads the guard. |
| 4/18 tape-vs-flow mismatches | Accepted (flow_filter keeps bars `<= "16:"` by string compare, dropping the 16:00 closing print; evening writer includes it). Not re-derived. |

## Z1 — Test-guard false positive on the live WAL

**Commits:** `ace1743` (round 1), `a8a07af` (round 2, after the first full run exposed the remaining gaps).

**Design.** Attribution moved from the filesystem to the test process:
- `sqlite3.connect` recorder (`_record_real_db_opens`, autouse): any in-process open of the real `data/` dir fails the test — `data.db.connect` routes through `sqlite3.connect`, the root conftest pins `DB_PATH` before `config` import, so a well-behaved test never lands there. **Exception (round 2):** `file:…?mode=ro` opens are exempt as *verified* read-only — SQLite refuses writes on them.
- The mtime sweep now flags **new files only**. Pre-existing DBs (main file and sidecars) are exempt outright: the live 5001 service writes `walkforward.db`/`-wal` continuously through short-lived connections, so there are instants where nobody holds them open and an mtime change is unattributable — that is what produced the historical `-wal` errors, and (round 2) the main-file teardown error.

**Round-2 evidence (the two errors in full run 1).** `3704 passed, 5 skipped, 2 errors` (`/tmp/z1_suite1.log`):
1. `ERROR at teardown of test_no_hardcoded_home_paths_in_production_code` — `changed: [('walkforward.db', size, mtime)]`; that test only greps source files, so this was the service's own write mid-test with the file momentarily unheld → fixed by the pre-existing-file exemption.
2. `ERROR at teardown of TestTFBContextFilterLive.test_tfb_context_on_real_brpt_daily` — `opened the real database file(s) ['data/walkforward.db', 'data/walkforward.db']` — a **true positive**: a deliberate read-only live-data test whose plain `sqlite3.connect('data/walkforward.db')` the old mtime guard never saw. Its intent is now declared machine-checkably (`file:…?mode=ro`, both in the test and in `_prod_db_has`).

**Done-when status:** (a) ✅ end-to-end negative test (`test_a_real_write_still_fails_the_guard` runs an offending test in a subprocess pytest and asserts the failure message). (b) ⚠️ **one** valid full run recorded during market hours with the service live (result above); the second consecutive run is scheduled **tonight 21:10 WIB** (automation `automation-85e0cc18`, appended to the evening section) — the daytime second run was skipped on the owner's instruction not to re-run. After `a8a07af`, targeted reruns of both errored tests + the guard tests: **47 passed** (`tests/test_db_isolation_guard.py tests/test_signal_checkers.py tests/test_config_hygiene.py`). (c) the two errors above are the full non-guard-error report; none other.

## Z2 — Event guard: dated calendar

**Commit:** `025cd2e`. **Deployed** 11:45 WIB via `safe_restart.sh`.

- **Storage:** `paper_config` key `event_guard_windows` (JSON list of `{id,start,end,size_mult,source}`), seeded idempotently (`INSERT OR IGNORE` — an owner edit always wins) by `init_paper_table` from `paper_trade.DEFAULT_EVENT_GUARD_WINDOWS`. No new config system.
- **Migration:** the June window (`2026-06-15..24`, mult 0.5) migrated verbatim as `msci-2026-06-review`. The legacy keys stay in `paper_config` untouched (open forward windows froze them); the guard no longer reads them — `/health` shows the calendar instead.
- **Primary-source dates only** — MSCI press release *"MSCI Announces the Next Eight Index Review Dates"*, London, **2026-08-12** (`msci.com/eqb/pressreleases/archive/ir_dates.pdf`, downloaded and text-extracted 2026-10-16 11:32 WIB; quotes verbatim: "November 2026 Index Review / Announcement date: November 11, 2026 / Effective date: December 01, 2026", etc.). Window = announcement date through effective date, inclusive — the two published dates are the bounds, nothing padded. All **eight** reviews seeded (2026-11 through 2028-08): the release itself says MSCI "reserves the right to change these dates" and re-publishes the next eight at each review, so the whole published calendar is the durable form of this config. `tests/test_event_guard_windows.py::test_seeded_calendar_dates_match_the_msci_release` pins the bounds against fat-finger edits.
- **NOT seeded (open):** the consultation decision date — MSCI's 2026-10-15 release (per its own text, cross-checked via the Yahoo Finance republication of the release) gives only *"will announce its decision on or before June 30, 2027"*. A bound is not a date; per the brief, nothing was added. When MSCI publishes the actual date (or an interim-update date), add one row to `event_guard_windows` — the edit is exactly one UPDATE.
- **`/health`:** `event_guard` now carries `source`. Live at 11:46 WIB: `{"active": true, "size_mult": 0.5, "source": "shock rule: an IHSG session <= -5% within the last 5 sessions"}` — today's shock, correctly named.
- **Governance consequence (deliberate, disclosed):** the key is now in `engine/forward_window._paper_config`'s keep-set, so adding it changed the frozen config. At the **18:30 Forward-Test Cycle today**, `check_all` will close the three windows opened 2026-10-07 as `CLOSED_CONTAMINATED` with the recorded diff (`event_guard_windows: None -> <calendar>`), and successors open automatically with the calendar frozen in. This is the module's designed response ("a change … CLOSES the window as contaminated and opens a successor; results before and after are never pooled") — a guard-calendar change is a signal-generation regime change, and pooling across it silently would be worse. The windows were ~7 sessions into a 60-session minimum-read, so the cost is small. **Verify tonight** (evening automation item 5).
- Overlapping windows: most restrictive `size_mult` applies; bad JSON degrades to no windows (shock rule only), never fatal. Tests cover bounds, overlap, shock rule, seeding idempotence, owner-edit survival, the frozen-config keep-set, and `/health` degradation.

## Z3 — Adversarial review of the 10-15/10-16 changes

### Z3.1 Risk-score comparability — the old series was structurally understated

Recomputed the last 60 logged sessions both ways from stored components (`market_risk_log`, last row per date; old rule = INSUFFICIENT sensors scored 0 at full weight, no floor; new rule = missing excluded + rescaled + IHSG floor). Script: `/tmp/z31_recompute.py` (read-only).

- **54 sessions exist** (2026-06-05..2026-10-16; the log is younger than 60 sessions).
- **VPIN was INSUFFICIENT on 54 of 54 logged days** (`{'vpin': 54}`). The 10-16 morning incident was not an anomaly — the composite carried a 30%-weight "0 = safe" hole its entire logged history.
- **35 of 54 sessions change tier** under the new rules: 21 YELLOW→ORANGE, 12 ORANGE→RED, plus today's ORANGE→CRITICAL; e.g. 2026-10-13 57.2 ORANGE → 81.8 RED; 2026-10-08 55.8 → 79.6 RED; four June days also hit IHSG floors (−4.20%, −4.52%, −3.56%, −3.05%).
- **Consumers across the boundary:** none compares scores over time. `app.py:209` (latest row, dashboard card), `engine/trade_plan.get_regime` (latest same-day row, report header), `engine/risk_alert` (per-date unsent rows), `engine/veto` d4 (current tier), and `get_market_risk_for_circuit_breaker` **recomputes fresh** rather than reading the log. The daily 08:45 report will simply read new-rule scores from here on. Historical *alert* rows (ORANGE-only EOD summaries) stay as they were sent.

### Z3.2 Shock guard on provisional bars — fail-safe intraday, non-sticky after recovery

Historical IHSG final bars (1,270 sessions, 2021-07-05..2026-10-15; script `/tmp/z32_shockguard.py`):
- Final closes ≤ −5%: **2** in 5+ years (2025-04-08 −7.90%; 2026-01-28 −7.35%) — the 5-session persistence is rare by construction.
- Intraday low ≤ −5% with final close recovered above −5%: **6** (worst: 2026-01-29 low −10.08% → close −1.06%).
- Of those 6, **0** were followed by a ≤ −3% next session.

Semantics (from `_shock_guard_active`, which reads the last 5 IHSG closes whatever their finality): a provisional −5% bar arms the guard **for the remainder of that session** (fail-safe: 2026-01-29's −10% intraday is exactly when momentum entries should be blocked); once the recovered **final** bar lands, the next call sees it and the guard disarms. The 5-session persistence keys off final closes only — the brief's "recovers to −1% but still arms for 5 sessions" case does not occur. Residual edge (fail-safe direction): if the final bar never lands (data outage), a provisional −5% bar lingers and keeps the guard on. **Today's live case is pending the evening check:** if IHSG closed ≤ −5% the guard persists 5 sessions; if it recovered, `/health`'s source should drop back to `null` after the final bar.

### Z3.3 Trade-book cache vs evening re-fetch — **deferred to tonight** (needs the 20:15 run's data). Evening automation item 3 re-fetches 20 tickers bypassing the cache and diffs against the 16:15+ payloads.

### Z3.4 macro_watch (jurnal26) — live for ~1.5 h at review time

- Deployed ~09:42 WIB today; `data/macro_state.json` shows the whole overnight MSCI flood (156 index_status, 102 halt, 47 crash matches) was **seed-suppressed by design** ("a first run does not replay a story the owner already knows") — every `seen` key is stamped `2026-10-16T02:42:59Z`. Those rows are `alerted:false` because of the seed, not a miss.
- Live alerting so far: **2 bundles, 6 headlines, all regulation topics** (reg_finance ×4: OJK POJK bank business plans; reg_tax ×2: vehicle-tax opsen in 37 provinces, crypto-asset tax priorities). Assessment: reg_finance borderline-relevant; **reg_tax opsen/crypto-tax look like noise for an IDX equity book** — candidate filter tightening (topic filters are versioned; a change is a new version with its reason in the docstring — left untouched here, report-only per the brief).
- Missed big-impact headlines: none observable in-window (the only giant story of the night was the seed-suppressed MSCI flood, which the owner knew first). A true miss-audit needs a longer window and a source beyond the match log (the log only records matches by construction) — listed under open items.

### Z3.5 Stop alerts (jurnal26 `watch_alert.quote`) — guarded on all three states

Code (`watch_alert.py:25-52`, commit `dbeb2de`): Stockbit order-book header first — **requires today `volume` AND `lastprice`**, else raises "no trade today yet"; yfinance fallback requires a **today-dated** 5-minute bar. The docstring records the fixed 09:00 false-alert path ("yesterday's last/low before the open fired false alerts at 09:00") and the 10-16 failure it fixes (yfinance "possibly delisted" on the shock morning).
- **Pre-opening:** no volume/no today-bar → raises → no quote → **cannot fire on an indicative print** (pre-open is a call market; Stockbit's volume stays 0. The 09:00 opening-auction print has volume, but that is a real trade — acting on it is correct).
- **Trading halt:** returns the last real pre-halt print (legitimate — it traded there); no synthetic quotes.
- **Suspended ticker:** both sources raise (no today data) → no stop fire. Correct: suspension is not a stop breach.
- **Live probe** 11:50 WIB on the halt day: `quote('BBCA')` → `(5225.0, 5175.0)` — primary path healthy post-halt.

jurnal26 commits reviewed (`bf50036 a100237 f71b8d2 eada6b7 dbeb2de`): coherent with the above; tape_backfill's 22:00–06:30 window deliberately serialises after 5001's 20:15 broker run on the shared token, 5xx retried then the night ends (the 10-15 21:08 crash class). No findings beyond the reg-topic noise note.

## Z4 — Tonight / Saturday / Monday first live runs

- **Tonight 21:10 WIB — scheduled** (automation `automation-85e0cc18`): 16:15 sweep + flow-save times; 16:00 report send time; 20:15 broker run (trade-book requests ≈ 0 via cache, broker empties vs 757/533, untraded skipped ~130); Z3.3 20-ticker cache re-fetch diff; CRITICAL `sent` flag for today's scans; the 18:30 forward-window roll; IHSG final close vs the shock guard's persistence; **second full-suite run** (Z1 done-when (b)). Appends an "Evening verification" section here and commits the report only.
- **Saturday 08:30 / Monday 09:05 — NOT scheduled (platform limit: one automation per session).** Run manually or from a fresh session:
  - Sat: `cd ~/jurnal26 && .venv/bin/python tape_backfill.py --status` (first full night: sessions backfilled, request budget, 5xx retries); overnight macro tally from `data/macro_events.jsonl` (per topic, alerted vs logged).
  - Mon 09:05: `jurnal26-macro-preopen` timer output (~08:56) — did the pre-open breadth alert, and with what reading on a post-shock market; macro_watch market-topic behavior during pre-open hours; `watch_alert` state — confirm **no** stop alert fired on pre-open indicative data (expected: none before 09:00 volume exists).

## Open items

1. **MSCI consultation decision date** — no published date ("on or before 2027-06-30", release 2026-10-15); add a window when MSCI publishes it. Feedback deadline 2027-04-30 is published but is not a market-moving gate; deliberately not windowed.
2. **Z3.3 cache-bound verification + Z1 second full-suite run** — tonight's 21:10 automation.
3. **Forward-window roll verification** — tonight (expected: 3× CLOSED_CONTAMINATED, `event_guard_windows` diff).
4. **IHSG final close today** — decides whether the shock guard persists 5 sessions (evening check).
5. **macro_watch reg-topic noise** (opsen/crypto-tax) — candidate version bump, owner's call; miss-audit needs a longer window.
6. **Saturday / Monday checks** — commands above; need manual runs or a new-session schedule.
7. My week-review recommendation to give `accdist` the missing-sensor exclusion was already fixed by the planner in `094276f` (0 classified tickers = missing) — verified in `engine/risk_score.py`; nothing left.

---

## Evening verification 2026-10-16 21:10 WIB (scheduled run)

**1. Post-close sweep + 16:00 report.** Journal: job "Post-close sweep 16:15 (screener EOD + flow)" ran **16:15:00 → 16:29:50** ("[screener] Fetching Stockbit tradebook for 958 tickers…" at 16:15:00, "executed successfully" 16:29:50). The flow save completed ≤ 16:30:12 — the 16:00 Signal Report job (fired 16:00:00) **waited for it exactly as designed** (`b7ee9b5` gate) and ran its scan at 16:30:12, sending at 16:30:36 ("Tidak ada sinyal Momentum hari ini" — log-only under TELEGRAM_OFF). Also at 16:30:00: **"[16:30] Circuit breaker OPEN: Market risk CRITICAL (score=86.0) — auto-trading paused"** — the shock floor closing the session at CRITICAL, as intended. (The table's `updated_at` for today's `stockbit_flow` now shows only the 20:15 run's writes, 958 rows 20:15:00–20:38:18; the 16:15 save stamp was overwritten.)

**2. 20:15 broker run (one-run evening, cache-only).** 20:15:00 → **21:08:27** ("[21:08] Broker flow selesai. 632 tickers untuk 2026-10-16", incl. retry passes). Journal counts 20:15–21:00: **541** "✓ Broker:" summaries, **225** "broker summary empty (traded ticker) — queued for retry" (vs **757** on 10-15), **121** "no trades, broker summary skipped" (expected ~130), **0** trade-book fetch lines — the trade-book side came entirely from the 16:15 cache (`a1eef31` working as designed; retries recovered ~91 of the empties: 632 saved).

**3. Z3.3 cache-bound verification — BLOCKED, stays OPEN (new vendor finding).** Between the broker run's end (21:08, endpoint working) and ~21:20, **Stockbit began rejecting the trade-book chart endpoint**: a direct probe (`api.stockbit.com/v2.1/order-trade/trade-book/chart`, symbol BBCA) returns HTTP **200 with body `{"error":"InvalidParameter","message":"Silahkan update aplikasi kamu ke versi terbaru…"}`**, and all 20 module-path re-fetches came back non-200. 828 tickers have cached payloads fetched ≥16:15 today, so the cached tape is intact — but the fresh comparison could not be made. Consequences to watch: **tomorrow's 16:15 sweep fetches this endpoint for all 958 names** (if the rejection persists it fails wholesale — the screener EOD and the flow table lose their source); jurnal26's 22:00 tape backfill uses a **different** endpoint (`exodus.stockbit.com/order-trade/running-trade`) and is not automatically affected. Re-try the 20-ticker diff when the endpoint recovers; if "update your app" is a persistent client-version gate, the endpoint's params/headers need a vendor-side refresh (owner call).

**4. CRITICAL delivery.** `SELECT … FROM market_risk_log WHERE date='2026-10-16'`:
```
11:05 | CRITICAL | 86.0 | sent=0   (pre-fix: the None-format crash, fixed 094276f, live 11:45)
13:35 | CRITICAL | 98.5 | sent=1
14:35 | CRITICAL | 98.5 | sent=1
```
Log: `[telegram] send allowed (event=risk.market_critical, first today): 🚨 Market Risk: CRITICAL — Score 98.5/100  IHSG today: -8.01% — floor CRITICAL` (13:35), then `deduped … once_per_day (already sent today)` (14:35). One Telegram delivered, both rows marked sent — the policy's documented DB-sent-flag dedup.

**5. Forward-window roll.** Exactly as predicted in the Z2 section: at 18:30:00 all three windows opened 2026-10-07 closed and successors opened:
```
38b08ac3|scanner    | CLOSE_CONTAMINATED | changes: ["paper_config.event_guard_windows: None -> '[{"id": …'"]
76b32312|scanner    | OPEN (successor)
62035b3c|eod        | CLOSE_CONTAMINATED | (same diff)   → 0105567b OPEN
a24b1636|premarket  | CLOSE_CONTAMINATED | (same diff)   → 05c50f1e OPEN
```
The Forward-Test Cycle itself ran clean at 18:30:38 (`ingested=0 opened=2 closed=89 open_now=490`).

**6. IHSG close + guard state.** 2026-10-16 close **5393.92 = −8.01%** vs 5863.78 (still `is_final=0` at 21:15). At ≤ −5% the **shock guard persists 5 sessions**; `/health`: `{"active": true, "size_mult": 0.5, "source": "shock rule: an IHSG session <= -5% within the last 5 sessions"}`.

**7. Second full-suite run (Z1 done-when (b)).** `venv/bin/python -m pytest tests/ -q -p no:cacheprovider` → **`3716 passed, 4 skipped in 393.71s`, `PYTEST_EXIT:0`, zero DB-isolation-guard errors** (run during the live service, market closed). With run 1's two errors diagnosed and fixed in `a8a07af`, **Z1 is now fully done-when-met**. (3,716 vs 3,704 tests: the parallel session added tests during the afternoon.)

**Evening additions to open items:** (8) the trade-book endpoint rejection of item 3 — retry the 20-ticker diff when it recovers and watch Monday's 16:15 sweep; (9) nothing else outstanding from tonight.
