Migrated from root `CLAUDE.md` (2026-08-27, /doctor lazy-loading migration) — content unchanged,
only relocated so it loads only when working under `scheduler/`. See root `CLAUDE.md`
"Scheduler (`scheduler/`)" for the short always-loaded overview this extends.

**Telegram operational reporting** (Production Engine Phases 1–3, 2026-07-28) — three daily reports,
all reporting-only (they consume already-decided engine outputs, never recompute a score/rank/exit):

- **EOD Trade Plan** (16:40 WIB, `run_eod_trade_plan`) — the consolidated agent-ranked long
  shortlist, plus a Watchlist Changes section (added/removed/upgraded/downgraded, rank + confidence
  deltas) computed by `engine/trade_plan.py`'s `diff_watchlist()`/`record_snapshot()` against a
  `watchlist_snapshot` table (`date, strategy, ticker, rank, confidence, conviction, confluence,
  sources`; keyed `(date, strategy, ticker)`).
- **Premarket Shortlist** (08:35 WIB, `run_premarket_firm_scan`) — reuses the same
  `watchlist_snapshot` diff infrastructure under `strategy='premarket'` (isolated from the EOD
  plan's `strategy='eod'` rows by the composite key), rendered as separate 📈 NEW / 📉 REMOVED /
  ⬆ UPGRADED / ⬇ DOWNGRADED / 🟢 STABLE sections plus a PREMARKET SUMMARY header (regime, risk
  tier, candidate counts, highest conviction).
- **Forward-Testing Summary** (18:30 WIB, `run_forward_test_cycle`) — `forward_testing/reporting.py`
  is a read-only layer over the existing `ft_shadow_position`/`ft_shadow_trade` tables: daily
  new/closed/active positions, a cumulative win/loss scoreboard, and best/worst closed trades.
  Exit reasons (SL/TP/TRAIL/TIME/STALE) are shown verbatim, never translated into an invented
  status taxonomy the underlying data doesn't support.

All three jobs share a `_job_sentinel` table (`job, run_date` primary key) as a dedup guard —
first `INSERT` wins, so a systemd-restart race never double-sends the same day's report.

**Scheduler crash alerting** — an `EVENT_JOB_ERROR` listener (`scheduler/__init__.py`,
`_make_job_error_listener`/`JobErrorRateLimiter`) sends one Telegram alert per uncaught in-process
job exception, closing the gap where only the heartbeat dead-man's-switch proved the *process* (not
any individual job) was alive. Rate-limited per `job_id` (`SCHEDULER_JOB_ERROR_COOLDOWN_S`, default
1h): the first failure for a job always alerts; repeats within the cooldown are logged only and
folded into the next alert as a "+N suppressed" count — this prevents a job stuck failing on every
tick from spamming Telegram.

All outbound Telegram text from every job above (and the pre-existing `send_telegram`/
`send_telegram_reply` call sites) is passed through `utils.logging_config.redact_secrets()` — the
same masking rule already applied to log lines — before sending, so an exception message that
happens to embed a configured secret value never ships to Telegram unmasked.
