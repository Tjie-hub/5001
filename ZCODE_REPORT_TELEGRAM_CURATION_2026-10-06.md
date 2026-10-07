# ZCODE REPORT — Telegram curation: only important notifications, no duplicates

**Executed:** 2026-10-06 · **Branch:** `fix/telegram-curation` (off `research/new-order-2026-09-30` @ 062999d) ·
**Brief:** "ZCODE BRIEF — Telegram curation" (planner, owner-requested; committed 062999d)
**Blackout:** `logs/TELEGRAM_OFF` NOT deleted — nothing sends until the owner lifts it. All policy
code, tests, and the digest job are live on the branch, gated behind the kill file.

## 1. What was built

- **`utils/notify_policy.py`** — single policy gate `decide(event, subject, state, msg)` +
  registry `EVENTS: event_id -> (tier, dedup_rule)`. Order of enforcement: global
  `logs/TELEGRAM_OFF` → classification (unclassified = suppressed + WARNING, fail-closed) →
  dedup (`once_per_day` / `on_change` / `none`, persisted in `logs/notify_state.json`, atomic
  tmp+rename, shared across service + cron processes) → tier dispatch (send / digest-buffer /
  log-only). Dedup applies to BOTH tier-1 sends and tier-2 digest buffering (the latter is
  what actually fixes the IHSG refire: ten identical DOWNTREND scans → one buffer item).
- **`utils/telegram.py`** — `send_telegram(msg, event=…, subject=…, state=…)`; returns True
  only when a message actually went out. Legacy `category=`/TELEGRAM_MUTE still honored when
  passed alongside a registered event. Every sender in the repo now routes through the gate.
- **Evening digest** — tier-2 items append to `logs/digest_buffer/<date>.jsonl`; new scheduler
  job `notify_evening_digest` flushes ONE message at 17:45 WIB daily (empty buffer = silent;
  the flush itself is gated `report.evening_digest` once/day; buffer kept if OFF or send fails).
- **Standalone senders** — `stockbit_fetcher.py`, `auto_token.py`, `routes/telegram.py`
  (`bot.reply`), `scripts/cron_wrap.sh` (marker file once/job/day under `$LOG_DIR/notify_state`)
  all follow the same tiers through the same gate.
- **CI classification test** — `tests/test_notify_policy_classification.py`: AST-scans the
  deploy surface (excl. tests/, migrations/, scratchpad/, .worktrees/, docs/) and fails on any
  `send_telegram(` call without a registered `event=`; also asserts the four sender muscles
  route through the gate, cron_wrap honors OFF + daily dedup, and the 17:45 job is registered.

## 2. Debug finding fixed in passing

`scheduler/scanner.py` "IHSG Technical Alert" refired every intraday scan (~4×/day, every day
of the chronic downtrend — 50+ redundant sends over the replay window). Now
`market.ihsg_technical` = tier-2 digest, dedup `on_change(state=label)`: one digest line the
evening the label changes, silence while it persists, a new line on the next change.

## 3. Call-site classification (85 sites + 3 special paths)

Line numbers as of branch HEAD; `subject` shows the dedup partition where used.

| Site | Event | Tier | Dedup |
|---|---|---|---|
| engine/agent_firm/providers/alerts.py:46 | `llm.provider_quota` | send | once_per_day (key) |
| engine/fail_open_alarm.py:33 | `system.fail_open` | send | once_per_day (source) |
| engine/risk_alert.py:81 | `risk.market_critical` | send | once_per_day |
| engine/risk_alert.py:130 | `market.risk_red_bundle` | digest | none |
| engine/risk_alert.py:146 | `report.eod_risk_summary` | digest | none |
| monitor.py:587 | `trade.position_alert` | send | once_per_day (ticker) |
| monitor.py:634 | `trade.position_alert` | send | once_per_day (ticker:alert_type) |
| monitor.py:648 | `trade.monitor_error` | send | once_per_day (ticker) |
| paper_trade.py:457 | `trade.paper_opened` | digest | none (ticker) |
| paper_trade.py:522 | `trade.paper_closed` | send | none (ticker) |
| paper_trade.py:652 | `risk.dd_breaker_activated` | send | none |
| paper_trade.py:669 | `risk.dd_breaker_reset` | digest | none |
| research/jobs.py:172 | `report.wf_revalidation` | log | none |
| routes/backtest.py:922 | `trade.paper_closed` | send | none (ticker) |
| routes/backtest.py:1106 | `bot.ui_scan_result` | send | none |
| routes/telegram.py:241 | `system.polling_activated` | log | none |
| scheduler/__init__.py:188 | `system.job_register_fail` | send | none |
| scheduler/__init__.py:218 | `system.scheduler_job_error` | send | none (upstream 3600s limiter) |
| scheduler/jobs.py:100 | `data.pit_finality_violation` | send | once_per_day |
| scheduler/jobs.py:108 | `data.flow_zero_warning` | send | once_per_day |
| scheduler/jobs.py:117 | `data.flow_fetch_failed` | send | once_per_day |
| scheduler/jobs.py:236 | `data.token_expired` | send | once_per_day (broker_flow) |
| scheduler/jobs.py:264 | `data.flow_coverage` | send | once_per_day |
| scheduler/jobs.py:281 | `data.flow_gap` | send | once_per_day |
| scheduler/jobs.py:291 | `data.flow_fetch_failed` | send | once_per_day |
| scheduler/jobs.py:326 | `data.token_expired` | send | once_per_day (broker_period) |
| scheduler/jobs.py:347 | `data.broker_period_failed` | send | once_per_day |
| scheduler/jobs.py:394 | `data.token_expired` | send | once_per_day (corporate_actions) |
| scheduler/jobs.py:413 | `data.corporate_actions_failed` | send | once_per_day |
| scheduler/jobs.py:456 | `data.token_expired` | send | once_per_day (ownership) |
| scheduler/jobs.py:475 | `data.ownership_failed` | send | once_per_day |
| scheduler/jobs.py:517 | `data.token_expired` | send | once_per_day (insider) |
| scheduler/jobs.py:536 | `data.insider_failed` | send | once_per_day |
| scheduler/jobs.py:578 | `data.screener_fetch_failed` | send | once_per_day |
| scheduler/jobs.py:604 | `data.ohlcv_reconcile` | send | once_per_day |
| scheduler/jobs.py:636 | `data.token_health_warning` | log | none |
| scheduler/jobs.py:685 | `data.token_probe_inconclusive` | log | none |
| scheduler/jobs.py:701 | `data.token_recovered` | log | none |
| scheduler/jobs.py:706 | `data.token_dead_pre_eod` | send | once_per_day |
| scheduler/jobs.py:739 | `data.ohlcv_coverage` | send | once_per_day |
| scheduler/jobs.py:807 | `data.news_fetch_failed` | send | once_per_day |
| scheduler/jobs.py:930 | `risk.circuit_breaker` | send | once_per_day |
| scheduler/jobs.py:940 | `data.premover_scan_failed` | send | once_per_day |
| scheduler/jobs.py:1057 | `report.market_health` | log | none |
| scheduler/jobs.py:1375 | `data.premarket_no_snapshot` | send | once_per_day |
| scheduler/jobs.py:1591 | `report.premarket_summary` | log | none |
| scheduler/jobs.py:1705 | `report.watchlist_update` | log | none |
| scheduler/jobs.py:1740 | `report.eod_trade_plan_empty` | digest | none |
| scheduler/jobs.py:1871 | `report.eod_trade_plan` | digest | none |
| scheduler/jobs.py:2106 | `report.forward_test` | digest | on_change (report fingerprint) |
| scheduler/jobs.py:2160 | `report.bull_watch` | log | none |
| scheduler/reports.py:125 | `report.fetch_status` | log | none |
| scheduler/reports.py:130 | `system.report_build_error` | send | once_per_day (fetch) |
| scheduler/reports.py:156 | `report.open_trades_empty` | log | none |
| scheduler/reports.py:295 | `report.open_trades` | digest | none (own change-detection) |
| scheduler/reports.py:301 | `system.report_build_error` | send | once_per_day (open_trades) |
| scheduler/reports.py:329 | `report.flow_sentiment` | log | none |
| scheduler/reports.py:338 | `system.report_build_error` | send | once_per_day (flow_sentiment) |
| scheduler/reports.py:457 | `report.flow_sentiment` | log | none |
| scheduler/reports.py:464 | `system.report_build_error` | send | once_per_day (flow) |
| scheduler/reports.py:509 | `report.auto_trade_status` | log | none |
| scheduler/reports.py:513 | `system.report_build_error` | send | once_per_day (auto_trade_status) |
| scheduler/scanner.py:582 | `report.daily_signal` | log | none |
| scheduler/scanner.py:641 | `trade.paper_opened` | digest | none (ticker) |
| scheduler/scanner.py:1034 | `report.admission_zero` | log | none |
| scheduler/scanner.py:1352 | `market.ihsg_technical` | digest | on_change (label) |
| scheduler/scanner.py:1571 | `screener.nr7_signal` | digest | once_per_day (ticker) |
| scheduler/scanner.py:1826 | `report.scan_summary` | log | none |
| scheduler/utils.py:94 | `data.ohlcv_fetch_failed` | send | once_per_day |
| screener/screener_jobs.py:109 | *(helper pass-through)* | — | via `event=` argument |
| screener/screener_jobs.py:146 | `data.token_expired` | send | once_per_day (screener_intraday) |
| screener/screener_jobs.py:198 | `data.scraper_failed` | send | once_per_day |
| screener/screener_jobs.py:273 | `data.eod_degraded` | send | once_per_day |
| screener/screener_jobs.py:338 | `screener.eod_retry_recovered` (🟢) / `data.eod_degraded` (🔴) | digest / send | once_per_day (eod_retry) |
| screener/screener_jobs.py:478 | `report.reversal_watchlist` | log | none |
| auto_token.py:341 | `data.token_refresh_failed` | send | once_per_day |
| auto_token.py:637 | `data.token_refresh_progress` | log | none |
| auto_token.py:643 | `data.token_refresh_ok` | log | none |
| auto_token.py:651 | `data.token_refresh_failed` | send | once_per_day |
| stockbit_fetcher.py:941 | `report.flow_fetch_done` | log | none |
| stockbit_fetcher.py:948 | `data.flow_partial` | send | once_per_day |
| stockbit_fetcher.py:985 | `data.token_expired` | send | once_per_day (flow_cron) |
| scripts/check_provisional_bars.py:100 | `system.provisional_bars` | send | once_per_day |
| scripts/check_scheduler_heartbeat.py:34 | `system.scheduler_dead` | send | once_per_day |
| scripts/check_backup_heartbeat.py:80 | `system.backup_dead` | send | once_per_day |

Special paths (not `send_telegram(` literals, verified by test):

| Path | Event | Tier | Dedup |
|---|---|---|---|
| `engine/registry_loader.py` announce (dynamic `telegram_fn`) | `system.registry_announce` | log | none |
| `scripts/cron_wrap.sh` failure alert | (bash; OFF + once/job/day marker) | send | once_per_day |
| `routes/telegram.send_telegram_reply` (all bot commands) | `bot.reply` | send | none (owner-initiated) |

## 4. Replay: last 14 days through the new policy

Journal coverage 2026-09-22 → 2026-10-05 (market days; Sep 26-27 / Oct 3-4 weekends had none).
"Before (sent)" = messages that actually went out; "Before (muted)" = the 09-16 TELEGRAM_MUTE
block. After-policy = what the same day would produce under the new tiers + dedup
(tier-1s that genuinely fired, plus 1 digest when the buffer was non-empty).

| Day | Before sent | Before muted | After (est.) |
|---|---|---|---|
| Sep 22 | 16 | 4 | 2 |
| Sep 23 | 13 | 4 | 1 |
| Sep 24 | 12 | 5 | 2 |
| Sep 25 | 9 | 6 | 1 |
| Sep 28 | 16 | 6 | 2 |
| Sep 29 | 12 | 5 | 1 |
| Sep 30 | 10 | 6 | 1 |
| Oct 01 | 10 | 6 | 1 |
| Oct 02 | 10 | 6 | 1 |
| Oct 05 | 14 | 4 | 3 |
| **Total** | **122** | **51** | **15** |

Attribution of the recurring sends (per day): 08:20 token warning → log-only; 08:35 premarket
→ log-only; 08:45 market health → log-only; 09:05/10:05/11:05/13:35/14:35 intraday IHSG
technical alerts (136 chars each) → digest, on_change ≈ 0; 16:00 daily signal report →
log-only (was muted); 16:40 watchlist update → log-only (was muted); 17:30 EOD-retry 🟢
recovered → digest; 18:30 flow/forward-test reports → log-only/digest; restart registry
announces → log-only. Kept as tier-1: the Oct-05 provider-quota pair (→ 1 after once/day),
the Sep-22 job-error and 21:00 reconcile one-offs, ownership 09:03 monthly completion →
log-only. Digest ≈ 1/day because on a typical day the buffer holds the EOD trade plan
(+ occasionally an IHSG label change or a recovered retry).

## 5. Could not classify cleanly / flagged for owner (asked, not guessed)

All sites are classified (CI-enforced); these four assignments are judgment calls the owner
may want to move:

1. **`report.market_health` (08:45 premarket briefing) → log-only.** It reports level, not
   change; tier-2 keeps "market risk label CHANGE". If you want it back as a digest item, say so.
2. **`report.admission_zero` ("no strategy is admissible", once/day by sentinel) → log-only.**
   Informational by its own text ("zero signals is the correct output"), but it is the only
   signal that the whole pipeline produced nothing today — borderline.
3. **`report.wf_revalidation` (research job: live strategies with negative avg return) →
   log-only.** Advisory; fires from the weekly research cron.
4. **`data.ohlcv_reconcile` (close-value mismatches vs yfinance, 21:00) → tier 1 once/day.**
   Research-data integrity = "something you rely on broke"; if it fires chronically it will
   ping daily — demote to digest on your say-so.

Also noted: tier-2 items landing AFTER 17:45 (forward-test cycle 18:30, broker flow 20:15)
sit in the buffer and appear in the NEXT day's digest (per the brief's fixed 17:45). If you
want the forward-test summary same-evening, either move the digest to ~20:45 or promote
forward-test trade events to tier 1.

## 6. State, verification, and what was NOT done

- Tests: `tests/test_notify_policy.py` (20: registry integrity, OFF, unclassified fail-closed,
  once_per_day incl. subject partitioning + persistence + atomic write, on_change incl. the
  10-identical-scans case, digest buffer/flush/archive/empty/OFF/failure),
  `tests/test_notify_policy_classification.py` (5 CI gates). Existing suites updated to the
  gated API (`event=` probe; hermetic fixtures against the live kill file; `**kw` on injected
  sender fakes). Full `pytest -q` result recorded in the commit message.
- **Not done:** blackout NOT lifted (`logs/TELEGRAM_OFF` untouched); branch NOT merged; the
  service has NOT been restarted onto this branch — production still runs the 2026-10-05
  blackout build until the owner deploys.
