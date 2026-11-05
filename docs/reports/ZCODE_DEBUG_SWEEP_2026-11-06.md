# ZCode Debug Sweep — 2026-11-06 (05:33–06:4x WIB)

**Trigger:** Owner "Cek update. Many error. Debug" (05:33 WIB). **Box:** XPS-13 production.
**Method:** read-only sweep → root cause → fix per approved plan (TDD log filter + evidence-backed DB flag update).

---

## TL;DR

The "many error" = **~3,548 yfinance ERROR lines between 10-21 and 11-06**, one root cause:

**41 tickers that IDX delisted in the mid-July 2026 batch were never reconciled out of `idx_tickers`.**
All 41 still had `status='active'`, last OHLCV bar exactly 2026-07-17. Every daily fetch job re-probed
them and Yahoo refused each with "possibly delisted; no price data found".

Fixed now, two layers:

1. **DB flag update (root cause):** the 41 tickers flipped to `status='inactive'`. Active universe
   958 → 917. Live immediately — the fetcher reads the universe per call, no restart needed.
2. **Log noise filter (TDD):** new `YfinanceNoiseFilter` in `utils/logging_config.py` downgrades ONLY
   the per-symbol `$TICK.JK: possibly delisted...` lines to DEBUG. Batch summaries stay at ERROR so every
   run still shows which symbols failed. 7 new tests, 27 logging tests green. Arms at next restart.

Everything else swept was healthy. Open owner item: **the 2026-11-02 rebalance was never applied.**

---

## 1. Evidence table

| Surface | Result |
|---|---|
| app.log (11-03 14:38 → 11-06 05:30) | 817 ERROR, all yfinance delisted-class |
| app.log.1 (10-21 → 11-03) | 2,731 same-class errors; earliest 2026-10-21 16:25 WIB |
| Peak windows | 10:10 WIB staged-fill `fetch_all_incremental("ALL")`; scraper runs; 21:00 reconcile |
| Web/API 4xx/5xx since 10-21 | **0** |
| Crontab | `D=` symlink resolves to `10 Projects/...`; token preopen OK; reminders OK; fwd recorders OK; ops_health rc=0; heartbeat rc=0 |
| systemd --user timers | jurnal26-* fleet alive; no failed project units |
| fq_snapshot_monthend | idle by design ("not the last weekday"), rc=0 |
| Telegram | globally suppressed (notify_policy) — why the errors never reached the owner |
| Service | alive (heartbeat 05:30 WIB); NOT restarted |

## 2. Root cause detail

- **Class A — 41 delisted (permanent):** last bar exactly 2026-07-17; in the Yahoo-refusal set:
  WSKT, HOTL, CBMF, IIKP, PLAS, POOL, GOLL, ENVY, POSA, NUSA, TRIL, MAGP, SMRU, MABA, BTEL, TDPM,
  HOME, PURE, SCPI, UNIT, RIMO, LCGP, KBRI, HKMU, COWL, ARMY, SRIL, MTRA, GAMA, JSKY, SKYB, OCAP,
  SUGI, CPRI, SIMA, DUCK, TRIO, TECH, TRAM, CNTB, LMAS.
- **Class B — suspended-day noise (transient):** ~98 further tickers per day, single-day windows with
  no bar (suspensions/halts). Data gap is correct; only the log line is noise. Handled by the filter.
- Distinct tickers in the error log since 10-21: 139 (= 41 permanent + ~98 rolling suspended names).
- The fetcher honors `idx_tickers.status='active'` (`data/fetcher.py:70`), so the flag flip removes them
  from every fetch set. Zero open paper trades on the 41. CNTX (last bar 07-31) and META (08-13) are
  suspended but still Yahoo-served → deliberately left active.

## 3. Fixes applied ~06:2x WIB

### 3.1 DB flag update (root cause)

- Pre-state of all 41 rows saved to `~/scratch/idx_tickers_flip_prestate_2026-11-06.txt`
  (all `active`, updated_at 2026-04-27).
- Single transaction: `UPDATE idx_tickers SET status='inactive' ... WHERE ticker IN (41) AND status='active'`
  → `changes()=41`. Now **917 active / 55 inactive**; fetcher universe query returns 917.
- Reversal: restore `status='active'` + updated_at 2026-04-27 for any subset (pre-state file has exact values).

### 3.2 Log noise filter

- `utils/logging_config.py`: `YfinanceNoiseFilter` + attach in `setup_logging()`.
- `tests/test_yfinance_log_noise.py`: 7 tests (per-symbol downgraded, batch header kept, ticker-list kept,
  index form matched, unrelated untouched, counter).
- 27 passed (with existing logging tests). **Arms at next restart.**

## 4. Verification

- 27 logging tests green; production-line replay: 3,332 per-symbol lines would downgrade, 350 batch
  summaries kept at ERROR, 134 other yfinance errors untouched.
- Full suite (06:35-06:42): **1 failed, 3,918 passed, 5 skipped in 419s**
  (`logs/pytest_full_20261106_debugsweep.log`). The single failure
  (`test_fq_g1.py::test_main_refuses_until_registered`) is **pre-existing since 10-28**: it asserts
  `REG_SHA256 is None` while the {FQ} E/P registration (D-115, commit `ad05040`) pinned
  `7155e1c7...` the same day — no suite run happened on this box between 10-07 and today, so it went
  unnoticed. Unrelated to this sweep's changes (which touch logging + idx_tickers flags only).
  Owner call: update the test to assert the pinned-registered state, or file it.
- Today 09:10/10:10 WIB: staged-fill fetch runs on 917 tickers; the 41 no longer probed (DB flip live).
- After restart: ERROR/day should fall from ~340 to under 20 lines (batch summaries only).

## 5. Open owner items

1. **2026-11-02 rebalance never applied** — measured 06:3x WIB: ISAT/PTBA in_idx30=0, PGEO/UNVR in_idx30=1,
   SMGR lq45=0, SCMA lq45=1, AALI/TINS/TKIM in_idx80=0, 12 flags checked, all pre-rebalance.
   Runbook: ZCODE_TUESDAY_2026-10-27.md §J4.2 (safe_restart + jurnal26 restart + list tests → owner window).
2. **Service restart** to arm the log filter — same one-shot pattern as 10-29 17:35 (after the 17:00 news run).
   Until then, Class-B per-symbol errors continue (~100/day), harmless to data.
3. **ZCode harness:** the Agent tool default model `account:zai-individual-coding-plan/GLM-5-Turbo` no longer
   exists (ListModels shows 5 models / 4 plans). No local agent .md or settings.json references it —
   ZCode-internal; not fixable from this box. Workaround proven: main-session fallback.
4. **Push HOLD** maintained (49+ commits ahead, plus today's local commits).

## 6. Bookkeeping

- TODO.md: capture-verify item closed with measured numbers (958 rows × 5 days, captured 08:21-08:23);
  rebalance item updated with today's measured state.
- Memory updated (delisting reconciliation + sweep outcome).
- Local commits only. No push, no restart, no frozen study touched, J4 ledger.json appends untouched.
