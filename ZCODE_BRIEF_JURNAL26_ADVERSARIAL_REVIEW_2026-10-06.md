# ZCode brief — adversarial review of jurnal26 (2026-10-06)

**Category:** Review / audit. **Owner-requested.** The job is to **challenge**, not to approve.
**Deliverable:** one report, `ZCODE_REPORT_JURNAL26_REVIEW_2026-10-06.md`. Write it into this repo
(idx-walkforward-5001) at the repo root, on branch `fix/telegram-curation`.
**This is review only.** Do not edit any file under `~/jurnal26`. Claude owns that code and will
apply the fixes you justify.

## What jurnal26 is

The owner's personal investment journal. It is a separate repo from this one, built and maintained
by Claude.

- **Path:** `/home/tjiesar/jurnal26` (git: `github.com/Tjie-hub/jurnal26`, branch `main`, HEAD `36abec3`)
- **Stack:** Flask + stdlib `sqlite3` (WAL), single-file UI, no build step.
- **Venv:** `/home/tjiesar/jurnal26/.venv`.
- **Live instances:**
  - `jurnal26.service` on port **5004**: owner's real data, `data/jurnal.db`.
  - `jurnal26-5003.service` on port **5003**: a second user, `data/jurnal-5003.db`.
  - Both use `EnvironmentFile` under `~/.config/jurnal26/` (holds the X-Token; **never print it**).
- **Reads from this repo's production, read-only:**
  - the DB `data/walkforward.db` (`mode=ro` URI): `ohlcv`, `stockbit_flow`, `broker_flow`,
    `insider_transactions`, `corporate_action_events`, `trading_calendar`, `ticker_sector`
  - the 5001 API: `/api/ticker/X/full`, `/api/broker-flow`, `/api/liquidity`, `/api/market/risk`

### Files (≈2,900 lines)

| File | Role |
|---|---|
| `server.py` | API: `/api/state` (versioned optimistic concurrency: `version`/`baseVersion` → 409, `BEGIN IMMEDIATE`), `/api/prices`, `/api/analysis`, `/api/watchlist`, `/api/candidates`, `/api/review`, `/api/review/refresh` (background thread). X-Token auth. `_prod()` 30 s timeout with stale-cache fallback. |
| `index.html` | Whole UI (tabs: Summary, Stocks, Research, Funds, Journal, Metrics). Net-cost average; swing lots (`lot:'swing'`, sells carry `closes:[{id,qty}]`); reverse swing (`lot:'rswing'`, buy-back BUY with `closes`, `rsKept`); concentration warning; per-tranche P/L; plans (stop/target/thesis). |
| `review.py` | Builds `data/<dbstem>-review.json` for the Research tab; uses Claude's written reads (`<dbstem>-review-reads.json`) if ≤ 2 days old, else `auto_read()`. |
| `notify.py` | Tier 1 immediate / tier 2 spool `data/digest_spool.jsonl` → `--send-digest`. Honors 5001 `logs/TELEGRAM_OFF`. |
| `position_alerts.py` | Stop/target/suspension/ARB/stale/swing/reverse/insider alerts; `--digest` weekly. Insider = KSEI stake before→after. |
| `bank_alert.py` | Big-4 bank 2-ATR climax low (HYP-PM-0014 context). |
| `watch_alert.py` | Sniper buy-zone intraday alerts from yfinance 5-min bars (today's bar required). |
| `three_push.py`, `climax_alert.py` | Pattern notices; both labelled as tested null (watch only). |
| `screener.py`, `watchlist.py` | Composite screen; auto-adds ≤ 3 sniper picks/day (`auto` flag, `until` expiry). |
| `manage.py` | Admin CLI. |

### systemd user timers (`~/.config/systemd/user/jurnal26-*.timer`)

| Timer | Schedule (WIB) |
|---|---|
| `pos-intraday`, `watch-alert` | intraday |
| `bank-alert`, `three-push`, `climax`, `pos-eod`, `screener` | after the close |
| `review` | 17:25 and 19:25 |
| `notify-digest` | Mon–Fri 17:45 and 19:50 |
| `digest` (weekly) | Fri 17:40 |

Read the `.timer` files for exact times.

## Hard constraints

- **Do not touch the live instances:**
  - no writes to `data/*.db`, `data/*.json` or the spool
  - no restart or stop of any `jurnal26*` unit, nor of `idx-walkforward`, crypto 5002 or idx_screener
  - no `POST /api/state` against 5003 or 5004
- **No Telegram sends.** `logs/TELEGRAM_OFF` stays in place. Never call `notify.now()` or
  `notify.send_digest()` for real.
- **Never print or log a token:** X-Token, Telegram, Stockbit, `~/.config/jurnal26/env*`. If a
  finding involves a secret, describe the class, not the value.
- **Dynamic tests go on a throwaway copy only.**
  - Copy `data/jurnal.db` to a temp dir and run `server.py` on port **5099** with
    `JURNAL_DB=<copy>` and a test-only token.
  - Delete the copy afterwards.
  - If you use a browser, clear its localStorage for that origin afterwards.
- Read-only queries against `walkforward.db` must use `mode=ro`.

## What to challenge (do every section; findings need evidence)

1. **Money math.** These numbers drive real decisions:
   - Net-cost average, per-tranche P/L and realized P/L.
   - Fees: buy 0.15%, sell 0.25%, used in both `review.py` and `index.html`. Do the two agree?
   - Swing-lot and reverse-swing accounting: partial `closes`, closes that exceed the lot, deleted or
     edited transactions referenced by `closes`, buy-backs, `rsKept`.
   - Rounding and lot size (100 shares).
   - Construct **adversarial transaction sequences** and show where `calc()` and `review.build()` disagree or go wrong.
2. **Concurrency and data loss.**
   - `/api/state` versioning: two tabs, phone + desktop, a stale `baseVersion`, an offline edit
     replayed later. Is there any path that silently overwrites newer data? Check the 409 handling.
   - WAL and cache invalidation: the `-wal` mtime trick in the watchlist cache.
   - The `/api/review/refresh` background thread: double-click, a thread still running at the 17:25
     timer, a crash midway (partial JSON?).
   - Atomic writes of every JSON state file (review, alert states, spool).
3. **Isolation between 5003 and 5004.** They share `data/`. Find **any** file, cache, spool or state
   that is not per-DB:
   - `digest_spool.jsonl`
   - `*_alert_state.json`
   - screener picks
   - which DB the timers run against

   Can user B's positions or alerts leak into user A's Telegram or UI?
4. **Security.**
   - Auth on every route, including the GETs.
   - Token comparison: constant-time?
   - Token in localStorage or URL?
   - XSS in `index.html`: ticker names, thesis text, notes and Claude's reads are rendered into
     innerHTML. Is anything unescaped?
   - CSRF, CORS headers, the bind address (0.0.0.0?) and exposure via Twingate/LAN.
   - Path or SQL injection through ticker params into the 5001 DB queries.
5. **Alert correctness.** For each alert script:
   - Can it fire falsely? Check provisional (`is_final=0`) bars, holidays (`trading_calendar`),
     suspensions, splits and rights issues (`corporate_action_events`), pre-open yfinance data, and
     a stale 5001 DB.
   - Can it miss a real event?
   - Can it fire twice? Check the dedup keys in `*_state.json` and the reruns at 19:xx.
   - Tier choice: anything tier 1 that should not wake the owner, or the reverse?
   - The timer failure mode: a script crashing silently with no alert.
6. **Honesty of the labels.**
   - The Research tab, the alerts and the screener show "R:R", targets, stops, "IN ZONE", verdicts
     and auto reads. Does any wording imply a tested edge where the 5001 research says null? The
     relevant 5001 records:
     - exhaustion/climax null
     - three-push null
     - double bottom null
     - insider buys null
     - FWD-PM-BANK-001 still in forward test, not validated
   - Is the bank alert presented consistently with HYP-PM-0014's frozen protocol
     (`docs/research_programs/P-M/forward_bank/PROTOCOL.md`)?
   - Do auto-added snipers look like recommendations?
7. **Coupling to 5001.**
   - What breaks in jurnal26 when 5001 is down, slow, mid-08:50-fetch, or changes a column or route?
   - Does any jurnal26 path open `walkforward.db` without `mode=ro`, or hold a long read transaction
     that blocks WAL checkpoints for the production writer?
8. **The planned digest merge.**
   - Claude will point `notify.digest()` at 5001's `logs/digest_buffer/<date>.jsonl`, per
     `ZCODE_BRIEF_DIGEST_FOLLOWUP_2026-10-06.md` §3, and retire jurnal's 17:45/19:50 timers.
   - Challenge that plan: file permissions, two writers, the timezone of `<date>` (WIB vs the jurnal
     host clock), what 5003's items do in the owner's digest (they must not appear), and the failure
     mode when 5001's flush is down.
9. **Operational.**
   - Reboot behaviour (linger, `After=` ordering).
   - Backups of `data/jurnal*.db`: do they exist, are they WAL-safe, and has a restore been tested?
   - Log growth, and timers that `OnCalendar` misparses (`systemd-analyze calendar`).
   - Python version and dependencies, and what pins them.
10. **Code quality.** Only where it causes a real bug risk: dead code, duplicated logic between
   `review.py` and `index.html`, and silent `except Exception: pass` hiding failures.

## Report format

- Findings ranked by severity: **Critical** (money or data loss, cross-user leak, security),
  **High**, **Medium**, **Low**.
- Each finding gives:
  - `file:line`
  - a concrete failure scenario (inputs or state, then the wrong result)
  - the evidence: command or test you ran, output trimmed, no secrets
  - a suggested fix
- Mark each one **CONFIRMED** (reproduced on the 5099 copy or by reading the code with a concrete
  trace) or **PLAUSIBLE** (reasoned but not reproduced). Do not inflate PLAUSIBLE to CONFIRMED.
- A short "challenged and held up" section: things you tried to break that were correct. This
  counts as evidence too.
- No praise, no summary of what the app does beyond what a finding needs.
- Commit the report. Conventional-Commits subject: `docs(review): jurnal26 adversarial review`.
  Push to `fix/telegram-curation`.
- Clean up the 5099 instance and the DB copy, and say in the report that you did.
