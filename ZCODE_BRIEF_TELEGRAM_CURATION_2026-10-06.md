# ZCODE BRIEF — Telegram curation: only important notifications, no duplicates

**Issued:** 2026-10-06, by Claude (planner), Owner's request ("I want only important notif, don't
duplicate") · **Repo:** idx-walkforward-5001 (`D:\IDX` WSL mirror) · **Branch:** off current HEAD of
`research/new-order-2026-09-30`, as `fix/telegram-curation` · **Scope:** the notification layer only.
Do NOT touch `docs/research_programs/**`, DECISION_LOG / HYPOTHESIS_REGISTRY / FAILURE_REGISTRY, any
`forward_*` PROTOCOL.md / ledger, or research-table schemas. Mimosa gates every commit.
**Do NOT delete `logs/TELEGRAM_OFF`.** The Owner lifts the blackout after reviewing your report.

---

## 0. Context (verified 2026-10-05/06; commits `12e8978`, `73c187a`)
- ~110 `send_telegram(` call sites: 33 `scheduler/jobs.py`, 11 `scheduler/reports.py`, 6 `scheduler/scanner.py`,
  5 `screener/screener_jobs.py`, 4 `paper_trade.py`, 3 `monitor.py`, 3 `engine/risk_alert.py`, plus
  `scheduler/__init__.py`, `scheduler/utils.py`, `routes/backtest.py`, `research/jobs.py`,
  `engine/fail_open_alarm.py`, `engine/agent_firm/providers/alerts.py`, `utils/logging_config.py`, and
  `scripts/check_{scheduler_heartbeat,provisional_bars,backup_heartbeat}.py`. Four standalone senders:
  `stockbit_fetcher.py`, `auto_token.py`, `routes/telegram.send_telegram_reply`, `scripts/cron_wrap.sh`.
- Almost every site uses the default category `"alert"`, which `TELEGRAM_MUTE` can never silence.
  Pre-blackout volume: 10–16 messages/day.
- Known noise bug: `scheduler/scanner.py:1352` "IHSG Technical Alert" re-sends on every intraday scan
  (~30 min) during a chronic DOWNTREND/death-cross. No dedup, no sentinel.
- Suppressed sends are logged while the kill file exists:
  `journalctl --user -u idx-walkforward | grep 'global OFF'` and
  `grep 'suppressed (global OFF)' logs/cron_*.log`. Use these to replay volume (§5).

## 1. Goal
Only important notifications, each sent once. Target: **0–3 individual messages on a normal day + one
evening digest** across BOTH systems (this repo and the Owner's jurnal26 on the same Dell, same bot).

## 2. Policy (implement exactly; changes need Owner OK)
**TIER 1 SEND (immediate, once per event):**
- risk / circuit-breaker / execution failures (`paper_trade`, `monitor`, `engine/risk_alert`, `fail_open_alarm`)
- Stockbit token expired **and** the auto-refresh failed. Not the pre-refresh 08:20 warning when the
  08:40 refresh then succeeds.
- stranded/provisional bars found by `check_provisional_bars` (next morning); backup / heartbeat dead-man failures
- scheduler job crash (keep the existing `EVENT_JOB_ERROR` cooldown)
- LLM provider quota exhausted (max once per provider per day)
- `cron_wrap.sh` nonzero exit (max once per job per day)

**TIER 2 DIGEST (one evening message, see §2b):**
- EOD trade plan + agent decisions (one line per ticker)
- forward-test summary only when something changed (new position/close/verdict)
- premover / screener highlights (top 5, one line each)

**TIER 3 LOG ONLY (never sent):**
- scan summaries
- flow / ownership / OHLCV "done" and "retry OK" successes
- the startup registry announce
- watchlist / reversal updates
- the daily WF signal report (0 BUY by design)
- heartbeat-OK messages
- the IHSG technical alert, at any level (see §2a)

### 2a. Owned by jurnal26: do NOT re-implement here (one owner per event)
jurnal26 (`~/jurnal26/notify.py`, commit `4a56aab`) already sends these:
- stop hit / target reached on positions; sniper zone entered / SL hit
- bank 2-ATR climax signal
- ARB / suspension on a position
- **market risk label change** (on change only)
- EOD-bars-not-final watchdog at 19:15
- volume climax, trend break, breakout-with-distribution, climax top, three-pushes, climax low
- corporate actions (14 days ahead)
- screener AUTO picks

So the IHSG/market alert here becomes **log only**. That also fixes the scanner.py:1352 refire. Keep
`check_provisional_bars` (next-morning stranded sessions): it is a different check from jurnal's 19:15
watchdog.

### 2b. One evening digest for both systems
jurnal26 owns the single evening sender: timer 17:45 (late items 19:50). Its spool is a JSON-lines file,
one object per item: `{"ts": ISO, "section": str, "text": str}`.
- Add `NOTIFY_DIGEST_SPOOL` to config. On the Dell it is `/home/tjiesar/jurnal26/data/digest_spool.jsonl`.
- When it is set, tier-2 items **append** to that file (atomic line append) and this repo schedules **no**
  digest of its own.
- When it is unset (CI, the Windows mirror), buffer to `logs/notify_digest.jsonl` and send one 17:45
  digest yourself, so tests stay hermetic.
- Use these sections: `"EOD plan"`, `"Forward test"`, `"Screener"`.

## 3. Implementation
1. `utils/notify_policy.py`: a registry `EVENT_ID -> (tier, dedup_rule)`. `dedup_rule` is one of
   `once_per_day(subject)`, `on_change(state)` or `cooldown(seconds)`. Every call site passes an explicit
   `event=` id; stop relying on the default `"alert"` category.
2. Persistent dedup store (small table in the production DB, or `logs/notify_state.json` with atomic
   writes). Key = event + subject (ticker / job / provider) + day or state. It must survive restarts.
3. Tier-2 calls go to the digest (§2b). Tier-3 calls write the log line only.
4. The standalone senders follow the same tiers (`cron_wrap`: once per job per day).
5. Keep `logs/TELEGRAM_OFF` (global) and `logs/TELEGRAM_MUTE` working as today. While OFF exists, the
   dedup store still records events as handled, so lifting the blackout does not replay a backlog.

## 4. Tests (CI)
- A classification test like `tests/security/test_route_policy.py`: a source scan fails on any
  `send_telegram(` without an `event=` registered in `notify_policy`.
- Dedup tests: once_per_day; on_change; cooldown; persistence across a process restart.
- Digest tests: spool append when `NOTIFY_DIGEST_SPOOL` is set (exact JSON shape); own digest when it is
  unset; nothing is sent when empty.
- Full `pytest -q` green **with the live kill file present**.

## 5. Report back
- A table of every call site: `file:line`, event id, tier, dedup rule.
- A replay of the last 14 days of logged sends through the new policy: messages/day before vs after,
  both systems combined (jurnal26 adds ~0–2 tier-1 per day plus its share of the digest).
- Anything you could not classify. Ask; don't guess.
- Do not lift the blackout. Do not merge to the deploy branch without Owner review.
