# Production signal audit — 5001 and jurnal26 (2026-10-26)

**Scope:** every live source that produces a buy/sell idea or alert, matched against the research record. Read-only:
config, schedules, table counts and logs. **No trade outcome or forward-test P&L was read.** Nothing was changed;
recommendations in §4 wait for the owner.

## 1. What actually reaches the owner

- **5001:** `logs/TELEGRAM_OFF` has stood since **2026-10-13**. Only `BLACKOUT_EXEMPT` events send (ops/data
  failures, backups, disk, scheduler, net outage, and `risk.market_critical`). Every trading report is either
  log-only (daily signal, premarket summary, scan summary, watchlists, bull watch) or tier-2 digest
  (EOD trade plan, paper opens/stages, forward-test report), and the digest flush is blocked by the same OFF file.
  **No 5001 trading signal reaches Telegram.** They are visible only on the dashboard.
- **jurnal26** shares that OFF file but exempts seven kinds: `position`, `sniper`, `bank`, `bigplayer`, `insidebar`,
  `limit`, `macro` (`notify.BLACKOUT_EXEMPT`). **These are the alerts the owner receives.**

## 2. 5001 sources

| Source (schedule) | What it emits | Research basis | Observed state |
|---|---|---|---|
| Multi-strategy scan (09:05–14:35, 5×) + daily signal scan (16:00) | Strategy signals from the live checkers: NR7 Breakout, Trend Following Breakout, Crash Recovery, Panic Rebound, Liquidity Sweep, vol_weighted, momentum, vwap_reversion, conservative | **No validated edge.** NR7_BULL RETIRED (D-066); daily price-pattern search closed (D-070). Earlier notes (not re-run today): TFB net −0.59%/trade (adversarial review 2026-09-16); flow-confirmed Liquidity Sweep failed validation; pooled walk-forward OOS negative for all but NR7 (July) | October `scheduled_signals`: 3,826 rows, **all `distribution`** — no long strategy signal logged this month |
| Paper trading (staged fills 09:10/10:10; monitor hourly) | Auto paper entries | — | **Idle**: `paper_trades` empty, `staged_entries` empty; 8 strategies in `disabled_strategies`; `auto_trade_from_premover=off` |
| EOD trade plan (16:40) + premarket firm scan (08:35) | Top-3 longs from the reversal watchlist, bullish/volume screen and prior approvals, vetted by the Agent Firm | Inputs have no tested edge: flow edge study closed (no edge); OIB continuation FAILED (D-091); short-horizon reversal FAILED→INVALID (D-089); volume/price screens fall under D-070. The firm's approvals have never been evaluated | Since 2026-09-16: 25 sessions, 75 evaluations — **15 approve, 50 veto, 10 degraded**. Never delivered (digest blocked). Each run makes ~20 Claude Sonnet calls (10-23: 16:40:01–16:42:13), drawing on the 5-hour subscription window shared with interactive Claude Code |
| Pre-mover EOD (16:30) | Pre-mover candidates, a plan source | Not tested as a mechanism | Feeds the plan; auto-trade off |
| Phase-5 BULL watch (17:10) | NR7 band-transition note | **NR7_BULL RETIRED** (D-066) | Log-only; watches a retired strategy — dead job |
| Forward-test cycle (18:30) | Shadow positions (`ft_*`) | Research tooling | Fine as is |
| `risk.market_critical` (exempt) | Market-wide CRITICAL tier | Descriptive risk read, not an edge claim | Today's risk endpoint reads CRITICAL (96.1); sends at most once a day |

## 3. jurnal26 alerts (these reach the owner)

| Kind | What it is | Research basis | Read |
|---|---|---|---|
| `position` | Stop/target/ARB/suspension on held stocks | Risk management, no edge claim | Keep |
| `sniper` | Price enters an owner sniper zone or hits its SL | Owner's discretionary system. Research: sniper support-zone entry since 2021 NULL (D-070 list); setup filter HYP-PM-0016 FAILED (D-072); exit study: no arm recommended | Keep as order management (the limit orders need action). **No tested edge** |
| `bank` | Big-4 bank 2-ATR climax low | **HYP-PM-0014**, registered, forward test FWD-PM-BANK-001 (2 trades since 10-05); passed a pre-2021 holdout | Keep — the only alert backed by a registered rule. Frozen protocol: no changes |
| `bigplayer` | Big-player side flip / split-order algo at a key level | Forward tape record **frozen** (D-098/099/103/108); recorded, not read; no tested edge | Keep (owner asked). Descriptive only. File is frozen — no edits |
| `insidebar` | Inside-bar mother-bar break | Price pattern (D-070 class); NR7/inside-bar family has no edge | Keep (owner asked by name). **No tested edge** |
| `limit` | ARB/ARA lock, unlock, queue drain | Descriptive market state | Keep. File is frozen |
| `macro` | Big-impact news, pre-open breadth, halt watch | Descriptive | Keep |

## 4. Recommendations (owner decides; nothing applied)

1. **Remove the Phase-5 BULL watch job** (17:10). It watches NR7_BULL, which D-066 retired; it can only produce log
   lines about a strategy production may not trade.
2. **Agent Firm daily runs (EOD 16:40, premarket 08:35): stop spending the shared Claude quota on output nobody
   receives.** Options: (a) `AGENT_FIRM_ENABLED=false` — the plan falls back to deterministic confluence ranking
   ("⚠️ Firm offline"); (b) keep the firm but route it to the GLM fallback only (`AGENT_FIRM_PROVIDER_ORDER=zai`);
   (c) keep as is if the dashboard plan is used. Note: the intraday exit veto in `monitor.py` shares the router;
   with no open paper trades it is idle. Needs a 5001 restart via `scripts/safe_restart.sh`, outside market hours.
3. **Label, don't trade, the 5001 strategy signals.** Add an "unvalidated — no tested edge" tag to the dashboard's
   signal and plan views, citing D-070 / D-066. Small UI change, separate approval.
4. **jurnal26: no code change.** Keep all seven kinds. The owner should read `sniper`, `insidebar` and `bigplayer` as
   descriptive or discretionary, not as tested edges; `bank` is the only one under a registered forward test.

## 5. Sources

`utils/notify_policy.py` (EVENTS, BLACKOUT_EXEMPT, OFF_FILE); `~/jurnal26/notify.py` (BLACKOUT_EXEMPT, OFF_FILE);
`scheduler/__init__.py` (job schedule); `engine/strategy_specs.py`; `registry/edge_registry.yaml` (NR7_BULL v2
RETIRED); `paper_config`, `paper_trades`, `staged_entries`, `scheduled_signals`, `agent_firm_daily_plan`,
`agent_firm_daily_run` (counts only); service journal 2026-10-23 16:40–16:42; DECISION_LOG D-066, D-070, D-072,
D-089, D-091, D-098; HYPOTHESIS_REGISTRY (HYP-PM-0014, -0016).
