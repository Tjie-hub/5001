# ZCODE BRIEF — Post-MSCI-shock hardening: verify today's hotfixes, fix the test-guard false positive, give the event guard a real calendar

**Issued:** 2026-10-16, by Claude (planner role, owner's request "next task for zcode") ·
**Repos:** `~/10 Projects/idx-walkforward-5001` (branch `ops/hardening-2026-07-10`), `~/jurnal26` (`master`) ·
**Follows:** your `week-review-2026-10-16` (findings verified: 6 confirmed, 3 wrong or out of date — see §0).

**Rules that apply to every item:**
- Production runs from the working tree. **Restart 5001 only with `scripts/safe_restart.sh`** (boot preflight;
  added today after the 10-15 NameError outage). Never a bare `systemctl --user restart`.
- Do not restart during an active sweep or scan (check `journalctl --user -u idx-walkforward -f` for 5 s first).
- jurnal26 tape monitor files are **frozen** (D-098/D-099): `bigplayer_watch.py`, `tape.py`, the event
  definitions in `limit_watch.py`. Do not edit them.
- Do not push. Do not touch `ZCODE_BRIEF_*`/`ZCODE_NOTE_*`, `forward_regime/ledger.json`, `HANDOFF.md`.
- No research reads, no new hypotheses. Nothing here touches `docs/research_programs/**`.

---

## 0. Your review, checked (so you do not re-chase these)

| Your finding | Status |
|---|---|
| d57e6f4 shipped unbootable, outage 17:52:15–17:54:47 | Confirmed → fixed: `scripts/preflight_boot.py` + `safe_restart.sh` (094276f). Proven on the 10-15 bug |
| accdist not excluded when it has no data | Confirmed → fixed (094276f): 0 classified tickers = missing |
| Sweep lock not on every sweep | Confirmed, but the gap was the screener-page run and the 17:30 retry, **not "another gunicorn worker"** (workers = 1, test-enforced) → fixed: `utils/stockbit_sweep.SWEEP_LOCK` |
| `_CONN_FACTORIES` omits get_conn/_get_conn | **Wrong** — both are in the set (`tests/test_db_transaction.py:91`) |
| Shock guard alters forward-test cohorts | **Wrong** — `forward_testing/` and the P-M recorders never call the guard/panic/selector; only the scanner strategy list and paper auto-trades change |
| 4 tape-vs-flow mismatches unexplained | **Out of date** — explained: flow_filter keeps bars `<= "16:"` (string compare), so it drops the 16:00 closing match + post-trading; the evening writer includes them and matches the tape |

New since your review (please include in Z3): **the 11:05 CRITICAL alert was logged but never sent** —
`engine/risk_alert.py` formatted `f"{None:.1f}"` for the missing VPIN; fixed in 094276f with a replay test.

---

## Z1. Test guard false positive on the live WAL (do first — it makes every suite run noisy)

**Symptom:** each full run has 1–8 setup ERRORs in different tests; each passes alone. Today's message:
`AssertionError: this test created/modified real database file(s) under .../data: ['walkforward.db-wal']`.
**Cause:** `tests/conftest.py` (`_isolate_db_path`, around line 150) compares mtimes of real files under `data/`;
the **running 5001 service** writes `walkforward.db-wal` itself, so whichever test is running gets blamed.

**Do:** make the guard attribute writes to the test process, not to the filesystem. Options, pick the simplest that
holds: ignore `-wal`/`-shm` siblings of a DB whose main file is unchanged; or record writes by patching
`data.db.connect`/`sqlite3.connect` for paths under `data/`. Keep the guard's purpose: a test that really writes
`data/walkforward.db` must still fail.

**Done when:** (a) a negative test proves a real write is still caught; (b) two consecutive full runs **during market
hours with the service live** show 0 guard errors; (c) report any remaining non-guard errors with their messages.

## Z2. Event guard: a dated calendar instead of one hardcoded window

**Today's lesson:** `scheduler/scanner._event_guard_active()` reads one window from `paper_config`
(`event_guard_start/end` = 2026-06-15..06-24, the June MSCI review). The October consultation shock passed with the
guard off; today's fix only added a reactive rule (`_shock_guard_active`: any IHSG session ≤ −5% → 5 sessions).

**Do:** support a list of dated windows (`id`, `start`, `end`, `size_mult`, `source`), stored the same way the repo
stores other operator config (follow the idempotent-migration pattern in CLAUDE.md "Coding Conventions"; do not
invent a new config system). Migrate the June window into it. Keep `_shock_guard_active` as-is.
Add the windows the owner needs **only from primary sources** — MSCI's published index-review calendar (November
2026 review announcement and effective dates) and the consultation decision date (on or before 2027-06-30, MSCI
release 2026-10-15). **Do not infer a date.** If a date is not published, add nothing and list it as open.
`/health` must show which window (or the shock rule) made the guard active.

**Done when:** tests for overlapping windows, the migrated June window, the shock rule, and the `/health` field;
preflight passes; deployed with `safe_restart.sh`.

## Z3. Adversarial review of the 10-15/10-16 changes (read-only except tests you add)

Commits — 5001: `b7ee9b5 ce79bba d57e6f4 020ab9b a1eef31 f56cdeb 7221abb 094276f ae42f44`;
jurnal26: `bf50036 a100237 f71b8d2 eada6b7 dbeb2de`. Questions to answer with evidence, not opinion:
1. **Risk score comparability.** Missing-sensor reweighting changes the meaning of `market_risk_log.score` from
   10-16 on. Quantify: recompute the last 60 sessions both ways; how many tier changes? Is any consumer comparing
   scores across that boundary?
2. **Shock floor / shock guard on provisional bars.** An intraday −5% that recovers to −1% still arms the 5-session
   guard. Intended (fail-safe) or a defect? Show what happened on past ≤ −5% intraday days if the bars allow it.
3. **Trade-book cache (`data/tradebook_cache.py`).** The 18:30 cron is retired; the 20:15 broker run now reuses
   payloads fetched at or after 16:15. Verify tonight (Z4 data) that 16:15+ payloads equal what an evening
   re-fetch returns for a sample of 20 tickers. Any difference = the 16:15 bound is wrong.
4. **macro_watch (jurnal26).** After the first days: false positives per topic from `data/macro_events.jsonl`,
   and any big-impact headline you can find that it missed. Report only; the topic filters are versioned, so a
   change is a new version with its reason in the docstring.
5. **Stop alerts (jurnal26 `watch_alert.quote`).** Stockbit-first quote: what does it return during the
   pre-opening, a trading halt, and a suspended ticker? Could it fire a STOP on a pre-open indicative print?

## Z4. Verify tonight's and Monday's first live runs (observation only)

- **16:15 post-close sweep:** start/end time; flow save time (expected ~16:24); the 16:00 Signal Report send time.
- **20:15 broker run:** trade-book requests should be ~0 (cache); count broker empties vs 10-15 (757 main / 533
  final) and untraded tickers skipped (~130).
- **22:00 tape backfill (jurnal26):** first full night; `python tape_backfill.py --status` in the morning.
- **Monday 08:56 pre-open breadth** (`jurnal26-macro-preopen`): output and whether it alerted.
- **First CRITICAL Telegram:** the 13:35 scan on 10-16 should have sent `risk.market_critical`; confirm the sent
  flag in `market_risk_log` and the message text.

---

## Deliverable

`ZCODE_REPORT_POST_MSCI_HARDENING_2026-10-1x.md` in the repo root: per item — what you changed (commit hashes),
the evidence (commands + output), and anything left open. Commit code with Conventional-Commit subjects; do not push.
