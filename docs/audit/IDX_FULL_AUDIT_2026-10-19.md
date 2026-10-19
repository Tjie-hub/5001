# IDX full audit — 5001 + jurnal26 (2026-10-19)

**Requested by:** owner, 2026-10-19 ("check all the repo focus on idx, full audit, test and debug").
**Scope:** `idx-walkforward-5001` (branch `ops/hardening-2026-07-10`) and `jurnal26` (branch `main`): tests, static
analysis, live runtime (services, timers, cron, logs, data), backups, security posture, last week's new features.
**Method:** full test suites; pyflakes on every tracked file; a Python audit hook that records every SQLite file a
test opens; read-only `--check` runs of the jurnal26 monitors against the live market; journal/cron log sweep since
2026-10-16; config-drift diff (crontab, systemd units); backup and restore-drill logs.
Done during market hours: read-only first; fixes test-first; restarts only via `scripts/safe_restart.sh`, after the
close.

## 1. Result

| | 5001 | jurnal26 |
|---|---|---|
| Test suite | At audit **3,722 passed, 5 skipped, 0 failed** (run alone, 6 min 35 s); after the fixes **3,728 passed, 5 skipped, 0 failed** (5 min 25 s) | At audit **164 passed, 1 xfailed** (the xfail documented F2); after the fixes **170 passed** |
| Hermetic (audit-hook probe) | conftest guard (Z1) already enforces it | **0 real-DB opens** after fixes (was 3) |
| pyflakes undefined names | 1 real (F9), 2 forward-ref annotations (fine) | 0 |
| Service health | `/health` ok, 52 jobs, scheduler running | 5003/5004 up, no errors today |
| Secrets | `.env`, `.stockbit_token`, telegram.env all 600; no token-shaped string in any log or the journal since 10-12 | |
| Config drift | crontab: only the owner's 3 personal entries; systemd units identical to `deploy/systemd` | |

An earlier full 5001 run showed 2 failed + 2 errors. They did not reproduce alone or in subsets: they came from
parallel pytest processes started during the audit sharing `/tmp/pytest-of-<user>` (cleanup of one run deleted the
other's temp dirs). Run the suite alone, or with `--basetemp` per run.

## 2. Findings

Severity: **H** = data or alert loss now; **M** = wrong data / silent failure / exposure; **L** = latent or hygiene.

| # | Sev | Finding | Status |
|---|---|---|---|
| F1 | H | **Weekly restore drill broken for 2 weeks.** 10-11: disk full; 10-18: "Disk quota exceeded". Since the Ubuntu 26.04 upgrade `/tmp` is a 3.6 GB tmpfs and the drill decompressed the ~15 GB DB there, leaving the partial file. Nightly backups themselves verified OK every night; the weekly off-SSD copy works. | **Fixed** `471fc72`: scratch in `/var/tmp` (`IDX_RESTORE_WORK_DIR`), free-space check before writing, scratch removed on success and failure. Live drill run after the close (§4). |
| F2 | H | **Frozen `bigplayer_watch.message()` crashes whenever a split-order algo is running**: the algo loop reuses `a`, which holds the absorption read → `KeyError 'sold'` (2026-10-16 15:00, ARNA ALGO). The event is logged, then the alert is lost, that ticker's state is not saved (re-logged next run) and every later ticker in the run is skipped. ALGO-start and absorption-with-algo alerts can never be delivered. | **Fixed** (owner "fix all"): jurnal26 `5fc8b93`, recorded as **D-103** (`039cb86`) — instrument correction, definitions and logged version unchanged, new hash `8618183215762237…`; 10-16 11:20/15:00 runs are gap windows. |
| F3 | H | **jurnal26's forward record had no backup**: `manage.py backup` copied only `jurnal*.db`; `tape_history.db` (120 MB) and the append-only `*.jsonl` event logs (D-098/D-099) were never copied. | **Fixed** `1df0091` (daily, online API + integrity check; logs as tar.gz). Off-SSD copy: F14. |
| F4 | M | **2026-10-12 stranded provisional bars**: VKTR stored close 595 vs settled 635 (**−6.3%**), AHAP provisional. Invisible to every `is_final=1` query; `data_heal` only looks for missing sessions. | **Fixed** `c42f6a0`: both are recorded rights issues (AHAP ex 10-09 7:5 @50, VKTR ex 10-07 35:12 @200) that put yfinance's earlier history on a TERP basis; the script now anchors on the nearest settled session each side. Applied: AHAP 76→70 (vol 11.4M→75.5M), VKTR 595→635 (vol 27.5M→177M); finalisation check OK. |
| F5 | M | **The 09:00 provisional-bars check failed daily and every alert was swallowed** by the Telegram blackout (not on the exempt list). | **Fixed** `739e110`: exempt, deduped daily. Since the F4 repair the check reports OK. |
| F6 | M | **Screener re-picked names the owner removed**: MSJA removed 10-16 ~16:30, re-picked as AUTO at 17:20. Deleting an AUTO pick in the app had the same effect. | **Fixed** `28374a6`: `dismissed by owner` for the 14-day AUTO life (OWNER log + AUTO picks gone without a system step). MSJA re-pick undone. |
| F7 | M | **Network exposure**: 5001, 5003, 5004 listen on `0.0.0.0` (home LAN 192.168.31.0/24). 5001 `AUTH_MODE` unset = off; admin routes are gated by the 2026-08-19 middleware stop-gap, viewer/operator routes are open to the LAN. jurnal26 has token auth (fail-closed). | **Fixed** `04893f3`: 5001 binds `127.0.0.1:5001` (its only client, the jurnal26 server, is on this host; one UI page load since 10-05); `GUNICORN_BIND` re-opens it deliberately. jurnal26 5003/5004 stay on the LAN/Twingate behind their token guard. |
| F8 | L | **Flow-fetch logs looked unfinished**: flow_filter's `\r` progress bar made journald store each run as "[17.8K blob data]", swallowing "Flow fetch selesai". Flow was fine (832 tickers 09:36). | **Fixed** `09481df`. |
| F9 | L | **Latent `NameError` in the momentum VPIN filter** (`_db_connect`, removed in Phase 3C `2c58bbf`): with `filter_vpin=1` the filter would silently pass every ticker. Default 0; never fired. | **Fixed** `b120685`. |
| F10 | L | **Dead duplicate router helpers**: `_parse_utc` / `_hydrate_quota_holds` defined twice; the later wins, 76 dead lines. | **Removed** `b120685` (agent_firm 351 passed). |
| F11 | L | jurnal26 `test_rules` "flake" was a real isolation bug (assumed one process per file); `test_chart_card` read 5001's production DB. | **Fixed** `9cda54e`. |
| F12 | L | `watch_void --live` (used 10-16) was uncommitted and untested. | **Fixed** `9cda54e`. |
| F13 | L | Backups leave a `-shm`/`-wal` pair per run (verify opens the WAL-mode snapshot): dozens of orphans. | **Fixed** `471fc72` (drop after verify; sweep orphans). |
| F14 | L | No off-SSD copy of jurnal26 data (pending owner item since 10-15). 5001 already copies weekly to `/mnt/storage2tb/idx-archive/backups_weekly`. | **Fixed** jurnal26 `8ecc954`: the daily backup set is copied to `/mnt/storage2tb/idx-archive/jurnal26`, sha256-verified, 14 days kept; refuses when the drive is not mounted. First copy verified. |
| F15 | L | `tape_backfill` loses weekend nights: the 24 h Stockbit token is refreshed weekdays 08:50 only → Sunday 22:00 "token rejected". | **Fixed** `739c8d6`: auto_token also 21:40 Sat/Sun (outside trading hours), installed crontab updated with the owner's personal entries kept. |
| F16 | L | Agent-firm kill switch is `/tmp/agent_firm.disable`; `/tmp` is now tmpfs → a set kill switch vanishes at reboot. | **Fixed** `032f058`: default `data/agent_firm.disable`; the legacy `/tmp` path is still honoured. |
| F17 | L | `limit_watch` / `insidebar_watch` crash with a bare `IndexError` when run without their positional arguments. | **Fixed** for `insidebar_watch` (jurnal26 `a59a56e`). `limit_watch` left as is: frozen (D-098), and a usage line is not worth a hash change. |

**Checked and healthy:** Stockbit trade-book endpoint (ZCode's 10-16 21:20 "update your app" rejection did not
persist: today's flow saved for 833 tickers); scheduler (no job exception since 10-16); Telegram delivery (one
transient reset, recovered by the retry); last week's new features on their first live Monday (pre-open breadth
08:56, open-void 09:00 — BRPT opened 1,130 < SL 1,140 and was voided —, Friday's void/refresh, halt watch idle on a
non-halt day); nightly backups (integrity ok, 86 tables, 137.6 M rows).

## 3. Owner decisions — resolved

The owner answered **"fix all"** (2026-10-19): F2 (D-103), F4 (repair applied), F7 (localhost bind), F14 (off-SSD
copy), F15 (weekend token) and the recommendations F16/F17 are done; see the table. Nothing is waiting.

## 4. Live verification after the close

Restart via `safe_restart.sh` at 17:52 (loads the in-process fixes F7–F10 and F16), then the real weekly drill
through `cron_wrap` on the latest backup. Result appended below.

Checked before the restart (F7): every 5001 client found uses loopback. jurnal26 calls `http://127.0.0.1:5001`
(`server.PROD_URL`, also used by `position_alerts`; `JURNAL_PROD_URL` unset), and no nginx, `/var/www` or crontab
entry addresses 5001 over the network.

## 5. Strategy logic check (owner question, 2026-10-19)

The owner asked whether the logic of the tested strategies was checked. Sections 1–2 did not: passing tests show
the code does what its tests expect, not that a rule matches its spec. This section checks each forward-tested
rule against its frozen protocol and reference script, and each live rule the owner acts on. **No forward-test
outcome was read:** only formation lists, row counts, metadata and pre-forward history were used.

### 5.1 Live rules the owner acts on

| # | Finding | Status |
|---|---|---|
| L1 | **The held-position ARB alert could never fire.** One symmetric 2023 table (20/25/35% by price) served both bands, but ARB has been a flat 15% since 2025-04-08, so the alert needed a one-day fall of 19.5% or more, which the floor rules out. BMTR (held) closed on its 63 floor on 2026-10-16 with no alert. | **Fixed** jurnal26 `37f443e`: floor = previous close × 0.85 rounded up to the tick, tested as a price (BMTR's floor is −13.7% after rounding). |
| L2 | **The screener's "close not at the ARA/ARB band" rule let ARB closes through** (same table). | **Fixed** `37f443e`: the rule as written, not a tuning. |
| L3 | 5001 `engine/exits/price_limits.py` (paper trades and backtests) still uses the symmetric table; the research foundation (`dataset_b/foundation.py`) already models the 15% ARB from 2025-04-08. Effect: a paper-trade stop between −15% and the stale floor is not capped. | **Owner decision** (production behaviour). |
| L4 | Sniper zones use 250 raw bars. After a split, the target and 52-week high come from pre-split prices (RAJA window max 8,100 vs 490 now; MLPT 225,700 vs 740), inflating R:R. No current pick is affected: those names have no support zone. | **Recommended:** cut the window at the last price step. |

### 5.2 Forward-tested rules against their frozen protocols

| # | Test | Finding | Recorded rows affected | Next step |
|---|---|---|---|---|
| T1 | REGIME-002 (HYP-PM-0010) | **The recorder lacks the §2 contamination guard** ("exclude any trade whose window contains a split or a ±35% session") that its reference backtest applies (`scripts/ref002.py` line 26). A split trips the 3×ATR stop and would record a fake −80% trade; trend names are the ones that split (RAJA, RMKE, MLPT in July). | 0 of 105 (checked without reading returns) | **Owner:** add the guard (conformance to the frozen §2, deviation entry). Rights issues in November (MGLV, CBRE, BMAS) and splits listed to December. |
| T2 | FADE-001 (HYP-PM-0012) | **The guard window is backward:** `s.shift(-1).rolling(h)` covers sessions t−18 … t+1, not the protocol's t+1 … t+20. The same line is in the frozen script and in `forward_regime/scripts/panel.py` (about 15 research scripts). Re-run on the registered in-sample data: −1.46%, t −8.16 becomes −1.49%, t −8.35 (immaterial; the bug was slightly conservative). | none yet; the first rows land 2026-10-20 09:35 | **Owner:** fix the recorder to the protocol's window (deviation entry), or apply it at read time. Voided rows are not stored, so either route recovers them. |
| T3 | BANK-001 (HYP-PM-0014) | The bank leg is voided on splits, rights, bonus and reverse splits; **the equal-weight book is not.** Over 2021–26, 41% of windows hold a contaminated member. Mean effect −0.001 pp, worst −1.85 pp (July 2026: RAJA, RMKE, MLPT splits; COCO, BNBR, PADI rights). A contaminated book biases the excess upward. | none yet; the first row lands 2026-10-23 09:40 | **Owner:** screen book members with the protocol's own void rule, or accept it (mean ≈ 0). |
| T4 | VOLEX-001 | Rupiah traded value = split-adjusted close × raw volume, so a recent split understates liquidity by the split factor for the top-200 ranking. | neither formation (09-15, 10-01) changes | **Owner:** fix before the 2026-11-02 formation. |
| T5 | HALTARB-001 | IHSG's t+1/t+5 benchmark legs are not stored. | none | None: recomputable from settled bars at read time. |
| T6 | all recorders | Sessions are counted by rows, so a missing bar stretches a window by one session (BNBR, COCO, PADI and SPMA have no 2026-07-09 row). The finalisation check cannot see per-ticker gaps. | not measured | Recommended: a per-ticker gap check. |

**Checked and consistent:**
- **BANK:** rule, de-dup and entry/exit match the protocol and jurnal26's live bank alert. Void labels match the database (`stocksplit`, `stock_reverse`, `rightissue`, `bonus`, keyed by ex-date).
- **FADE:** signal, universe, fills, costs and benchmarks match the protocol. The frozen script reproduces the registered numbers.
- **REGIME:** features (EMA20 slope, ER, participation, ATR as the mean of high−low) match the reference script.
- **VOLEX:** the DEV-002 completeness wait is applied, and a split inside the holding window is back-adjusted.
- **HALTARB:** the floor reproduces BBCA 5,175 and BBRI 2,640 on 10-16.
- **5001 exit evaluator:** stop before target on a conflict bar, gap fills at the open, trail anchored to the prior high.
