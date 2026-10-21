# ZCODE Report — Stockbit token refresh hardening (brief 2026-10-21)

**Executed:** 2026-10-21, ~11:20–13:00 WIB, by ZCode on branch `ops/hardening-2026-07-10`.
**Commits (local only, NOT pushed — push approval was for the {FQ} brief only):**

| commit | item |
|---|---|
| `d904430` | T1 — failure alerts give working repair steps |
| `fc59c90` | T2 — failures diagnosable (send outcomes, fallback evidence, --login UX) |
| `21bdf34` | T3 — saved login moved out of the repo (code + docs; live migration scheduled, see §T3.6) |
| `a423c4c` | T4 — 07:40/08:10 refresh + 08:30 pre-open gate + crontab install |

**No service restart performed or needed:** only the cron script `auto_token.py`,
`deploy/crontab`, `scripts/cron_wrap.sh`, docs and tests were touched. No app code.
`utils/notify_policy.py` was **not** edited: no new events, no tier changes — the new
check reuses the already-registered, already-`BLACKOUT_EXEMPT` `data.token_expired`.

## Status

| item | status |
|---|---|
| T1 fix both failure alerts | **DONE** |
| T2 make failures diagnosable | **DONE** |
| T3 move saved login out of repo (code/docs/tests) | **DONE** |
| T3.6 live migration of `.playwright_state/` | **DONE — executed 2026-10-21 21:55 WIB** (automation `automation-c3dd2c60`; log below) |
| T4 pre-open slack + 08:30 gate + crontab | **DONE** (crontab installed) |

## T1 — both failure alerts now give steps that work — DONE

- New `_login_fix_command()` builds `cd "<BASE_DIR>" && venv/bin/python3 auto_token.py
  --login` from `BASE_DIR` (quoted — the repo path contains a space). Both alerts carry it.
- No-saved-session alert now says plainly that the saved-login folder is missing and names
  the **full `STATE_DIR` path**, that the folder IS the login, the DISPLAY :20 login flow,
  ENTER **in the terminal**, and that capture takes up to ~1 min after ENTER.
- Final-failure alert: `echo 'TOKEN' > ~/.stockbit_token` recipe removed. The manual paste
  path is now `install -m 600 /dev/stdin "<repo>/.stockbit_token"` (repo file, mode 600).
  Includes `_token_status_line()`: expiry wall-clock time + minutes left from the existing
  JWT decode.
- `auto_refresh()`'s STATE_DIR check moved above the playwright import (failure path needs
  no playwright).
- Tests: `test_no_saved_session_alert_gives_working_instructions`,
  `test_final_failure_alert_gives_working_instructions` — assert the venv command, the
  `cd "<BASE_DIR>"`, the token-file path/mode-600 recipe, minutes-left, and **no**
  `~/.stockbit_token` / `echo`.

## T2 — failures diagnosable — DONE

1. `send_telegram` logs the outcome of every real send: `[telegram] sent ok` /
   `HTTP <code>` (exception path unchanged). Nothing secret logged (asserted in test).
   This closes the §0 "probably sent" gap.
2. Credential fallback, redirect-but-no-token (the exact 08:40:08 incident path): logs
   `page.url` + `page.title()` after the BBCA navigation, saves
   `logs/login_debug_<YYYYmmdd_HHMMSS>.png` (mode 600, newest 5 kept — helper
   `_save_login_debug_screenshot`), and scans the login error texts **plus**
   OTP/device-verification words (`OTP`, `kode`, `verifikasi perangkat`, `device`) via
   `_log_login_error_texts`. The no-redirect path reuses the same helpers (was a fixed
   unpruned `login_debug.png` at default mode).
3. `--login` UX: the banner says ENTER must be pressed **in this terminal** after the
   browser shows logged-in; prints `Capturing token (up to 55 s)...` right after ENTER;
   prints the result with expiry.
4. **Bonus fix in the same function:** `initial_login` wrote the token with plain
   `write_text` — a fresh file would be mode 644, which startup validation rejects. Now
   `_write_token_atomic` (mode 600). See "findings that change §0".

## T3 — saved login out of the repo — DONE (code) / live migration scheduled

- New location: `~/.local/state/idx-walkforward/playwright_state` (`_resolve_state_dir()`,
  `XDG_STATE_HOME` respected), mode 700 on the repo-owned levels; `~/.local/state` itself
  is left at its own mode.
- `_migrate_legacy_state_dir()` runs at the start of **every** `auto_token.py` run:
  old exists + new missing → `os.rename` move (same filesystem; data never copied or
  deleted) + log line; both exist → use the new one, leave the old alone with a warning;
  rename failure → fall back to the legacy dir for that run and log loudly. **Never
  deletes either.**
- Pointer left behind: `.playwright_state.MOVED` (gitignored) beside the old path, saying
  where the login went and not to delete it.
- `.gitignore` updated (ignores + documents both paths), `docs/OPERATIONS.md` token
  section documents the new home + do-not-delete rule. The `repo-ops` skill does **not**
  name the state path (verified) → no edit needed there.
- Tests: XDG resolution with/without `XDG_STATE_HOME`; migration move / both-exist /
  no-legacy / rename-failure; `main()` runs migration first. New autouse fixture
  `isolated_state_dirs` pins `LEGACY_STATE_DIR`/`STATE_DIR` to tmp so the suite can never
  move the live login as a test side effect.
- `--login`/credential-login create the state dir via `_ensure_state_dir()` (700).

### T3.6 — live migration: SCHEDULED tonight 21:55 WIB (not yet run at report time)

The brief allows the live move only after 21:50 tonight or on a weekend; the brief was
executed 11:20–13:00 WIB Wednesday, inside the forbidden band, so the live move was
**not** performed in the main pass. A one-shot automation (`automation-c3dd2c60`,
created in this session, fires 2026-10-21 21:55 WIB) will: guard the window, record
pre-state (dir listing, token sha256 + mode), run only
`auto_token._migrate_legacy_state_dir()`, verify the move + `.MOVED` note, run
`auto_token.py --check` (read-only) to confirm the token still valid, then append the
migration log line + `--check` output to this report and commit it (docs only, no push).

**Fallback if that automation misses:** the migration is wired into `main()`, so the next
`auto_token.py` run performs it — the first is Thursday 07:40 (new schedule), which is
outside the 08:30–19:00 hard ban though not one of the two blessed windows. Until then the
repo-root dir stays exactly where it is (untouched; verified present during this work).

## T3.6 live migration (executed 2026-10-21 21:55 WIB)

Window guard passed (`date` → 2026-10-21 21:55:38 WIB, ≥ 21:50). Pre-state: `.playwright_state`
drwxrwxr-x (775) with 16 top-level entries; `.stockbit_token` sha256
`23c1b35c…368f`, mode 600. Migration returned **`migrated`**. Log lines
(logs/auto_token.log tail):

```
[2026-10-21 21:55:59] Browser-state login migrated: /home/tjiesar/10 Projects/idx-walkforward-5001/.playwright_state -> /home/tjiesar/.local/state/idx-walkforward/playwright_state
[2026-10-21 21:55:59] Left moved-note at /home/tjiesar/10 Projects/idx-walkforward-5001/.playwright_state.MOVED
```

Verification:
- old repo dir `.playwright_state` no longer exists; `.playwright_state.MOVED` note present and
  names the new path (full text: where the login went + do-not-delete warning);
- `~/.local/state/idx-walkforward` and `~/.local/state/idx-walkforward/playwright_state` both
  **mode 700**; all 16 top-level entries identical to the pre-state listing;
- token untouched: `auto_token.py --check` → issued 2026-10-21 09:09, expires 2026-10-22 09:09,
  **11.2 hours remaining, API test ✅ Valid**; sha256 and mode 600 re-verified identical.
- Nothing deleted anywhere (os.rename move only); no playwright, no refresh, no login run.

Tomorrow's 07:40 cron is the first run against the new location (migration is a no-op there).

## T4 — catch a failed refresh before the open — DONE

New weekday schedule (installed; weekend Sat/Sun 21:40 kept):

```
40 7  * * 1-5  auto_token venv/bin/python3 auto_token.py            # primary refresh
10 8  * * 1-5  auto_token venv/bin/python3 auto_token.py            # retry (no-op after success)
30 8  * * 1-5  token_preopen_check venv/bin/python3 auto_token.py --preopen-check
```

- **07:40 clash check:** nothing else fires at 07:40 (nearest: Mon 07:30
  `research_fwd_volex`, daily 07:00 `backup_heartbeat_check`). 08:10 is clear (nearest
  08:15 `research_backtest_cache`). 08:30 shares the minute with the daily
  `owner_reminders` job — different job, both lightweight; noted, harmless.
- **Retry semantics:** `should_skip_refresh()` (14 h margin) makes 08:10 a no-op after a
  07:40 success; after a hard 07:40 failure (rc=1) the 08:10 run is a genuine retry.
- **`--preopen-check` mode:** read-only (at most one keystats GET — same class as
  `--check`). Alerts `data.token_expired` (BLACKOUT_EXEMPT, subject `preopen_check`) with
  the T1 `--login` instructions when the token is missing, unreadable, expires within 3 h,
  or fails the live verify (server-side revocation with a valid exp claim — 2026-09-21/22).
  Exit 0 when fine or alert delivered; exit 1 only when a problem exists AND the alert
  could not be sent (cron_wrap's generic alert then fires as the fallback —
  `token_preopen_check` was added to cron_wrap's BLACKOUT_EXEMPT job list so that
  fallback, too, punches through the blackout). The mode was validated by unit tests only
  — a live invocation before the 21:55 migration would have triggered the live migration
  mid-weekday, which the rules forbid.
- **Sunday {FQ} full pull coverage:** Saturday 21:40 refresh → token valid until Sunday
  21:40 → at the Sunday ~09:05 pull start ~12.6 h remain. Covered. (Pre-existing
  exposure, unchanged by this brief: if the *Saturday* 21:40 refresh fails, Sunday
  daytime inherits Friday-07:40's dead token — the weekend line has no retry; flagged as
  a possible future addition, not added here.)
- **Drift (required by the brief):** each refresh resets the 24 h TTL, so the token now
  normally **expires ~07:40 the next weekday**. First consumers after the 07:40 refresh:
  app `token_health_0820` (exp claim only) at 08:20, `token_preopen_check` 08:30, first
  Stockbit-API consumer `stockbit_ohlcv` 08:50 — all ~1–2 h inside the window. Last
  consumer 20:15 `run_broker_flow_fetch` sits 12 h 35 m after the refresh, inside the
  24 h TTL and under the 14 h skip-margin (margin comment updated in code). Monday:
  Sunday-21:40 token has exactly 14.0 h left at Monday 07:40 → not > margin → refresh
  proceeds normally (no gap).

### Crontab install + a live-vs-file drift closed

Backup first: `crontab -l > ~/scratch/crontab_backup_2026-10-21_T4.txt` (131 lines).
Diffing it against the edited `deploy/crontab` revealed the installed crontab had
**drifted ahead of the repo file**: three owner-installed entries — `@reboot nohup
~/watch.sh`, the `*/10` mtr sampler (`~/mtr-log.txt`), and the 22:00
`idx_external/status/snap_status.py` job — plus the 2026-10-07 J-section state (J2
deliberately omitted) existed only live. Installing the repo file verbatim (as its own
header instructs) would have **deleted three live production jobs**.

Resolution: `deploy/crontab` was rebuilt as *installed truth + the token change only*,
with the three live entries recorded verbatim under a clearly-marked
`LIVE HOST ENTRIES` marker, and `tests/test_cron_contract.py` now scopes its
wrapped-job/script-existence contracts to the section above the marker (plus a pin test
so those entries cannot silently disappear from the file again). Active job-line diff
vs the backup is exactly the token change (08:40 → 07:40 + 08:10 + 08:30) plus one
no-op position move of `fwd_halt_arb_recorder` above the marker. Installed with
`crontab -` and verified `crontab -l` ≡ `deploy/crontab` byte-identical.

## Test results (hermetic: no network, no Playwright launch)

```
tests/test_auto_token.py:                 57 passed   (35 pre-existing + 22 new)
tests/test_cron_contract.py:              13 passed   (10 pre-existing + 3 new/adjusted)
tests/security/test_secret_hygiene.py:    5 passed    (mandated, unmodified)
tests/test_notify_policy_classification.py: 5 passed  (classification gate over the new send sites)
combined: 80 passed
```

## Crontab diff (active job lines; comments omitted here, full diff in backup vs file)

```diff
-40 8 * * 1-5 cd $D && $W auto_token venv/bin/python3 auto_token.py
+40 7 * * 1-5 cd $D && $W auto_token venv/bin/python3 auto_token.py
+10 8 * * 1-5 cd $D && $W auto_token venv/bin/python3 auto_token.py
+30 8 * * 1-5 cd $D && $W token_preopen_check venv/bin/python3 auto_token.py --preopen-check
 (fwd_halt_arb line moved above the LIVE HOST marker; all 23 other job lines byte-identical)
```

## Findings that change or extend §0 of the brief

1. **`initial_login` could recreate the token file mode 644** (`TOKEN_FILE.write_text`),
   which startup validation rejects — the manual `--login` fix the owner performed at
   09:08 would have left a rejected token file on a fresh file. Only the fact that the
   file already existed (mode 600) saved the morning. Fixed in T2 (`_write_token_atomic`).
2. **The "No saved session" error fires twice per cron run** — `_retry_with_backoff`
   retries `auto_refresh`'s falsy return, so the 08:40:02 double ERROR in the log is one
   cron run, not two; the second alert was swallowed by `once_per_day` dedup, not sent.
   Left as-is (harmless with dedup); explaining it corrects §0's "twice" reading.
3. **Installed-vs-deploy crontab drift** (three live owner jobs live-only in the
   installed crontab) — discovered during T4; closed as described above. This is the
   same drift class the repo already burned itself on once (`fwd_fade_recorder`).
4. **The app-side 08:20/12:00 `token_health_*` checks are TIER_LOG (log-only)** — during
   the incident they could not have alerted by design. The 08:30 cron gate now covers the
   pre-open window with a BLACKOUT_EXEMPT alert. (Adjacent, not changed: that job's own
   alert text still suggests bare `python3 auto_token.py` — it never sends, tier-3.)
5. The `repo-ops` skill lists manual ops commands (`python3 auto_token.py ...`) with the
   same missing-venv shape T1 fixed in the alerts; it does not name the state-dir path,
   so per the brief it was not edited. Flagged for a future pass.

## Not done / out of scope

- No push (per rules). No `safe_restart.sh` (no app code touched).
- Weekend refresh has no retry (pre-existing; flagged above).
- `utils/notify_policy.py` untouched.
