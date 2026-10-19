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
| Test suite | **3,722 passed, 5 skipped, 0 failed** (run alone, 6 min 35 s) | **164 passed, 1 xfailed** (the xfail documents F2) |
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
| F2 | H | **Frozen `bigplayer_watch.message()` crashes whenever a split-order algo is running**: the algo loop reuses `a`, which holds the absorption read → `KeyError 'sold'` (2026-10-16 15:00, ARNA ALGO). The event is logged, then the alert is lost, that ticker's state is not saved (re-logged next run) and every later ticker in the run is skipped. ALGO-start and absorption-with-algo alerts can never be delivered. | **Owner decision:** one-line rename in a D-098/D-099-frozen file = instrument fix (precedent D-099) → needs a D-entry. Patch prepared and proven; strict-xfail test `74cbb3e`. |
| F3 | H | **jurnal26's forward record had no backup**: `manage.py backup` copied only `jurnal*.db`; `tape_history.db` (120 MB) and the append-only `*.jsonl` event logs (D-098/D-099) were never copied. | **Fixed** `1df0091` (daily, online API + integrity check; logs as tar.gz). Off-SSD copy still owner item (F14). |
| F4 | M | **2026-10-12 stranded provisional bars**: VKTR stored close 595 vs settled 635 (**−6.3%**), AHAP provisional. Invisible to every `is_final=1` query; `data_heal` only looks for missing sessions. | **Owner decision:** `scripts/repair_provisional_bars.py --apply` repairs VKTR (dry run done); AHAP needs a split-basis check. |
| F5 | M | **The 09:00 provisional-bars check failed daily and every alert was swallowed** by the Telegram blackout (not on the exempt list). | **Fixed** `739e110`: exempt, deduped daily. It will alert tomorrow 09:00 until F4 is repaired. |
| F6 | M | **Screener re-picked names the owner removed**: MSJA removed 10-16 ~16:30, re-picked as AUTO at 17:20. Deleting an AUTO pick in the app had the same effect. | **Fixed** `28374a6`: `dismissed by owner` for the 14-day AUTO life (OWNER log + AUTO picks gone without a system step). MSJA re-pick undone. |
| F7 | M | **Network exposure**: 5001, 5003, 5004 listen on `0.0.0.0` (home LAN 192.168.31.0/24). 5001 `AUTH_MODE` unset = off; admin routes are gated by the 2026-08-19 middleware stop-gap, viewer/operator routes are open to the LAN. jurnal26 has token auth (fail-closed). | **Owner decision:** keep (phone access) / bind 127.0.0.1 + VPN / `AUTH_MODE=shadow → enforce`. |
| F8 | L | **Flow-fetch logs looked unfinished**: flow_filter's `\r` progress bar made journald store each run as "[17.8K blob data]", swallowing "Flow fetch selesai". Flow was fine (832 tickers 09:36). | **Fixed** `09481df`. |
| F9 | L | **Latent `NameError` in the momentum VPIN filter** (`_db_connect`, removed in Phase 3C `2c58bbf`): with `filter_vpin=1` the filter would silently pass every ticker. Default 0; never fired. | **Fixed** `b120685`. |
| F10 | L | **Dead duplicate router helpers**: `_parse_utc` / `_hydrate_quota_holds` defined twice; the later wins, 76 dead lines. | **Removed** `b120685` (agent_firm 351 passed). |
| F11 | L | jurnal26 `test_rules` "flake" was a real isolation bug (assumed one process per file); `test_chart_card` read 5001's production DB. | **Fixed** `9cda54e`. |
| F12 | L | `watch_void --live` (used 10-16) was uncommitted and untested. | **Fixed** `9cda54e`. |
| F13 | L | Backups leave a `-shm`/`-wal` pair per run (verify opens the WAL-mode snapshot): dozens of orphans. | **Fixed** `471fc72` (drop after verify; sweep orphans). |
| F14 | L | No off-SSD copy of jurnal26 data (pending owner item since 10-15). 5001 already copies weekly to `/mnt/storage2tb/idx-archive/backups_weekly`. | **Owner decision** (same pattern, new target dir). |
| F15 | L | `tape_backfill` loses weekend nights: the 24 h Stockbit token is refreshed weekdays 08:50 only → Sunday 22:00 "token rejected". | **Owner decision** (weekend token refresh vs skip weekends). |
| F16 | L | Agent-firm kill switch is `/tmp/agent_firm.disable`; `/tmp` is now tmpfs → a set kill switch vanishes at reboot. | Recommendation: move to `data/`. |
| F17 | L | `limit_watch` / `insidebar_watch` crash with a bare `IndexError` when run without their positional arguments. | Cosmetic; recommendation. |

**Checked and healthy:** Stockbit trade-book endpoint (ZCode's 10-16 21:20 "update your app" rejection did not
persist: today's flow saved for 833 tickers); scheduler (no job exception since 10-16); Telegram delivery (one
transient reset, recovered by the retry); last week's new features on their first live Monday (pre-open breadth
08:56, open-void 09:00 — BRPT opened 1,130 < SL 1,140 and was voided —, Friday's void/refresh, halt watch idle on a
non-halt day); nightly backups (integrity ok, 86 tables, 137.6 M rows).

## 3. Owner decisions waiting

1. **F2:** approve the one-line instrument fix to the frozen `bigplayer_watch.py` (→ D-103, definitions unchanged).
2. **F4:** run `scripts/repair_provisional_bars.py --apply` (repairs VKTR 2026-10-12; AHAP stays for a manual check).
3. **F7:** network/auth posture for 5001/5003/5004.
4. **F14 / F15:** off-SSD copy target for jurnal26; weekend token refresh for the tape backfill.

## 4. Live verification after the close

Restart via `safe_restart.sh` at 17:52 (loads F8–F10), then the real weekly drill through `cron_wrap` on the
latest backup. Result appended below.
