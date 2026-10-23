# ZCODE BRIEF — Stockbit token refresh hardening (after the 2026-10-21 outage)

**Issued:** 2026-10-21, by Claude (planner role). Owner: "open new task for zcode", choosing token-refresh hardening.
**Repo:** `~/10 Projects/idx-walkforward-5001` (branch `ops/hardening-2026-07-10`). jurnal26 is not touched.
**Runs alongside** `ZCODE_BRIEF_FQ_FULL_PULL_AND_PIT_REVISION_2026-10-21.md`; it does not replace it. Tonight's 19:05
pilot and Sunday's full pull both depend on the token. **Nothing in this brief may leave the token or the saved
session unusable**; see the rules.

## 0. The incident (verified by Claude from logs and transcripts)

| When (WIB) | What happened |
|---|---|
| 10-20 08:41 | Refresh OK. The token expires 10-21 08:40. |
| 10-20 14:03 | A Claude cleanup deleted `.playwright_state/` (491 MB), listing it as "a browser profile, recreated on next run". It is `auto_token.py`'s saved Stockbit login. The owner approved on that description. |
| 10-21 08:40:02 | Cron run: `ERROR: No saved session`, twice. The `data.token_refresh_failed` alert passed dedup and is `BLACKOUT_EXEMPT`, so it was **probably** sent. `send_telegram` doesn't log a successful send, so nobody can confirm it. |
| 10-21 08:40:08 | Credential fallback (headless, `STATE_DIR` recreated empty): `Login redirect detected`, then no Bearer token captured → `REFRESH_FAILED`, rc=1. The second alert was suppressed `once_per_day`. No screenshot is taken on this path, so what Stockbit showed after the redirect is unknown. The guess is device verification on a fresh profile. |
| 08:40 → 09:10 | Token expired. 5001 intraday flow and the jurnal26 tape, broker and limit watchers ran with no Stockbit access through the open. |
| 09:08–09:10 | The owner ran `venv/bin/python3 auto_token.py --login`, logged in and pressed ENTER. Capture took ~20 s with **no output**, so it looked hung. Token saved, valid to 10-22 09:09. |

**Also found:** the final failure alert (`auto_token.py` ~line 661) gives instructions that **would fail**:
- `echo 'TOKEN' > ~/.stockbit_token` is the wrong path (the file is the repo's `.stockbit_token`), and `echo`
  creates it 664, which startup validation rejects (it needs mode 600);
- `python3 auto_token.py --login` lacks the venv and the `cd`.

The first alert (~line 351) has the same `python3` problem.

## Rules
- **Do not run a live refresh or a live login**, and do not overwrite `.stockbit_token`. The current token is valid
  to 10-22 09:09. Live calls allowed: `auto_token.py --check` (reads only), and the read-only Stockbit verify inside
  it.
- **Never delete, move or empty the live `.playwright_state/`, except under T3's migration rules.**
- Tests are hermetic: no network and no Playwright launch. Run `tests/test_auto_token.py`,
  `tests/test_cron_contract.py`, `tests/security/test_secret_hygiene.py` and every test file you touch.
- **Cron changes:** edit `deploy/crontab`, show a diff, and install it with `crontab -` only after a backup
  (`crontab -l > scratch`). The cron contract test must pass.
- **Do not edit `utils/notify_policy.py` event tiers** without saying so in the report. Adding a new event is fine,
  but register it in `EVENTS` and decide whether it is `BLACKOUT_EXEMPT`.
- **No restart needed:** `auto_token.py` is a cron script. If you touch app code, use `scripts/safe_restart.sh`
  outside market hours only.
- Commit locally. **Do not push**: the push approval was for the {FQ} brief only.

---

## T1. Fix both failure alerts so the steps they give work

1. **"No saved session" alert:**
   - Say plainly that the saved login folder (`STATE_DIR`, full path) is missing, so a headless refresh can't work.
   - Give the exact fix: `cd "<repo>" && venv/bin/python3 auto_token.py --login`, then log in in the browser on
     DISPLAY :20 and press ENTER.
   - Say the capture takes up to a minute after ENTER.
2. **Final failure alert:**
   - Same `--login` line.
   - Remove the `echo > ~/.stockbit_token` recipe. If a manual paste path is kept, it must write the repo's file
     with mode 600, e.g. `install -m 600 /dev/stdin "<repo>/.stockbit_token"`.
   - Include the token's expiry time and how many minutes are left, from the existing JWT decode.
3. Build the repo path from `BASE_DIR`, not a hard-coded string. Tests assert the text holds the venv command and no
   `~/.stockbit_token`.

## T2. Make failures diagnosable

1. **`send_telegram`:** log the outcome of every real send (`sent ok` / `HTTP <code>`). Never log the token or the
   chat id; redaction already exists.
2. **Credential fallback, redirect but no token:**
   - log `page.url` and `page.title()` after the BBCA navigation;
   - save a screenshot to `logs/login_debug_<YYYYmmdd_HHMMSS>.png` (mode 600) and keep the last 5;
   - check the same error texts the no-redirect path checks, plus OTP/verification words ("OTP", "kode", "verifikasi
     perangkat", "device").
3. **`--login` UX:** print `Capturing token (up to 55 s)...` right after ENTER, and the result with its expiry. Before
   ENTER, say ENTER must be pressed in this terminal after the browser shows you logged in.

## T3. Move the saved login out of the repo (the root cause)

`.playwright_state/` sits in the repo root, and repo cleanups will keep offering it.
1. **New location:** `~/.local/state/idx-walkforward/playwright_state` (respect `XDG_STATE_HOME`), mode 700.
2. **One-time migration at the start of any `auto_token.py` run:**
   - if the old dir exists and the new one doesn't, **move** it with `os.rename` (same filesystem), then log it;
   - if both exist, use the new one and leave the old one alone, with a warning in the log;
   - never delete either.
3. **Leave a pointer behind:** a small `README` at the old path, or a gitignored `.playwright_state.MOVED` note,
   saying where the login went and not to delete it.
4. Update the gitignore comment, `docs/OPERATIONS.md` (token section) and the `repo-ops` skill text if it names the
   path.
5. **Tests:** a temp-dir migration covering both cases above, plus `STATE_DIR` resolution with and without
   `XDG_STATE_HOME`.
6. **When to migrate the live directory:** run the migration once, live, **after 21:50 tonight or any time on a
   weekend**, never between 08:30 and 19:00 on a weekday. Then run `auto_token.py --check` and confirm the folder
   moved and the token is still valid.

## T4. Catch a failed refresh before the open, with time to fix it

**Today:** one attempt at 08:40, and the old token expires at 08:40 because each refresh is 24 h after the last. A
failure leaves zero slack.
1. **Proposed schedule:** move the weekday refresh to **07:40**, with a retry at **08:10**. `should_skip_refresh()`
   already skips when the token is fresh, so the retry is a no-op after a success. Check that 07:40 doesn't clash
   with anything in `deploy/crontab`.
2. **Add a light check at 08:30 weekdays** (an `auto_token.py --check`-style mode, or a small script). If the token
   expires within 3 h, or the API test fails, send `data.token_expired` (already `BLACKOUT_EXEMPT`) with the T1
   `--login` instructions.
3. **Weekend 21:40 Sat/Sun refresh:** keep it. Check that Sunday's {FQ} full pull (daytime) still has a valid token
   under the new weekday times.
4. **Write the drift in the report.** Each refresh resets the 24 h, so after this change the token will normally
   expire around 07:40 the next day. Confirm the first consumer after the refresh (08:15 research job? 08:50 OHLCV)
   is still covered.

## Deliverable

`docs/reports/ZCODE_TOKEN_REFRESH_HARDENING_2026-10-21.md` covering:
- T1–T4, each DONE, BLOCKED (why) or NOT RUN (why);
- the test result lines and the crontab diff;
- the live migration log line and the `--check` output after it;
- any finding that changes section 0.

Commit locally, with one commit per item where practical.
