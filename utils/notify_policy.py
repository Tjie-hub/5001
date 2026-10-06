"""Notification policy — classification, dedup, and the shared evening digest.

Implements the owner-approved curation brief (2026-10-06): send only when the
owner must act or something relied on broke (TIER_SEND), fold the rest of the
day's decision-support into one evening digest (TIER_DIGEST), and log the
pure-noise class without sending (TIER_LOG).

Single gate, many muscles: every sender in the repo (utils.telegram,
stockbit_fetcher, auto_token, routes/telegram reply, cron_wrap.sh) calls
decide() before touching the network. The gate owns, in order:

  1. logs/TELEGRAM_OFF global blackout — suppress everything, buffer nothing
     (the suppressed-send log lines are the owner's curation record).
  2. Classification — an event id not in EVENTS suppresses (fail-closed to
     silence; the classification CI test makes this unreachable for static
     call sites, and it protects against future dynamic ones).
  3. Dedup — once_per_day / on_change / cooldown, persisted in
     logs/notify_state.json (atomic tmp+rename writes, survives restarts and
     is shared across the service and cron processes).
  4. Digest — TIER_DIGEST items append to logs/digest_buffer/<date>.jsonl;
     the 17:45 WIB scheduler job flushes them as ONE message.

Dedup records are written at decision time, not after successful delivery:
a lost send may swallow tomorrow's identical alert until the next day/state
change. Accepted trade-off — senders retry internally and every TIER_SEND
event is day-granular by design.

Dedup keys are "<event>|<subject>"; the subject (ticker, job, provider, ...)
partitions the day counter so one ticker's alert never mutes another's.
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

WIB = timezone(timedelta(hours=7))

TIER_SEND = "send"      # notify immediately
TIER_DIGEST = "digest"  # append to the evening digest buffer
TIER_LOG = "log"        # log line only, never sent

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG_DIR = os.path.join(_REPO_ROOT, "logs")
STATE_FILE = os.path.join(_LOG_DIR, "notify_state.json")
DIGEST_DIR = os.path.join(_LOG_DIR, "digest_buffer")

# Global kill switch (2026-10-05 blackout) — same file utils.telegram checks.
OFF_FILE = os.path.join(_LOG_DIR, "TELEGRAM_OFF")

# Dedup rules. ("none",) means the call site already guarantees singularity
# (state-transition guard, upstream rate limiter, or owner-initiated action).
RULE_NONE = ("none",)
RULE_DAILY = ("once_per_day",)
RULE_CHANGE = ("on_change",)


# ── Event registry ───────────────────────────────────────────────────────────
# event_id -> (tier, dedup_rule). The classification CI test
# (tests/test_notify_policy_classification.py) fails the build on any
# send_telegram() call site whose event id is not registered here.
EVENTS = {
    # ── TIER 1: send now (expected 0–3/day) ─────────────────────────────────
    # Scheduler / platform integrity
    "system.scheduler_job_error":         (TIER_SEND, RULE_NONE),  # 3600s limiter in scheduler/__init__
    "system.job_register_fail":           (TIER_SEND, RULE_NONE),  # once per process start
    "system.scheduler_dead":              (TIER_SEND, RULE_DAILY),
    "system.backup_dead":                 (TIER_SEND, RULE_DAILY),
    "system.fail_open":                   (TIER_SEND, RULE_DAILY),  # subject=source
    "system.report_build_error":          (TIER_SEND, RULE_DAILY),  # subject=report name
    "system.provisional_bars":            (TIER_SEND, RULE_DAILY),
    # Risk / circuit breakers / execution
    "risk.circuit_breaker":               (TIER_SEND, RULE_DAILY),
    "risk.market_critical":               (TIER_SEND, RULE_DAILY),  # DB sent-flag is the primary dedup
    "risk.dd_breaker_activated":          (TIER_SEND, RULE_NONE),   # fires on state transition only
    "trade.position_alert":               (TIER_SEND, RULE_DAILY),  # subject=ticker:alert_type
    "trade.monitor_error":                (TIER_SEND, RULE_DAILY),  # subject=ticker
    "trade.paper_closed":                 (TIER_SEND, RULE_NONE),   # one per real close (TP/SL/manual)
    # Data pipeline broken
    "data.token_expired":                 (TIER_SEND, RULE_DAILY),  # subject=job name
    "data.token_dead_pre_eod":            (TIER_SEND, RULE_DAILY),  # probe 401 AND refresh failed
    "data.token_refresh_failed":          (TIER_SEND, RULE_DAILY),  # auto_token hard failure
    "data.eod_degraded":                  (TIER_SEND, RULE_DAILY),
    "screener.eod_retry_recovered":       (TIER_DIGEST, RULE_DAILY),  # 🟢 success → digest
    "data.scraper_failed":                (TIER_SEND, RULE_DAILY),
    "data.ohlcv_fetch_failed":            (TIER_SEND, RULE_DAILY),
    "data.ohlcv_coverage":                (TIER_SEND, RULE_DAILY),
    "data.ohlcv_reconcile":               (TIER_SEND, RULE_DAILY),
    "data.pit_finality_violation":        (TIER_SEND, RULE_DAILY),
    "data.flow_fetch_failed":             (TIER_SEND, RULE_DAILY),
    "data.flow_zero_warning":             (TIER_SEND, RULE_DAILY),
    "data.flow_partial":                  (TIER_SEND, RULE_DAILY),
    "data.flow_coverage":                 (TIER_SEND, RULE_DAILY),
    "data.flow_gap":                      (TIER_SEND, RULE_DAILY),
    "data.broker_period_failed":          (TIER_SEND, RULE_DAILY),
    "data.corporate_actions_failed":      (TIER_SEND, RULE_DAILY),
    "data.ownership_failed":              (TIER_SEND, RULE_DAILY),
    "data.insider_failed":                (TIER_SEND, RULE_DAILY),
    "data.screener_fetch_failed":         (TIER_SEND, RULE_DAILY),
    "data.news_fetch_failed":             (TIER_SEND, RULE_DAILY),
    "data.premover_scan_failed":          (TIER_SEND, RULE_DAILY),
    "data.premarket_no_snapshot":         (TIER_SEND, RULE_DAILY),
    # LLM providers
    "llm.provider_quota":                 (TIER_SEND, RULE_DAILY),  # subject=provider
    # Owner-initiated (each reply is inherently singular)
    "bot.reply":                          (TIER_SEND, RULE_NONE),
    "bot.ui_scan_result":                 (TIER_SEND, RULE_NONE),
    # Test-only probe (registered so test suites can exercise the send path)
    "system.test_probe":                  (TIER_SEND, RULE_NONE),

    # ── TIER 2: evening digest, one combined message ~17:45 WIB ────────────
    "market.ihsg_technical":              (TIER_DIGEST, RULE_CHANGE),  # state=label; fixes refire bug
    "market.risk_red_bundle":             (TIER_DIGEST, RULE_NONE),
    "report.eod_risk_summary":            (TIER_DIGEST, RULE_NONE),
    "report.eod_trade_plan":              (TIER_DIGEST, RULE_NONE),
    "report.eod_trade_plan_empty":        (TIER_DIGEST, RULE_NONE),
    "report.forward_test":                (TIER_DIGEST, RULE_CHANGE),  # state=report hash
    "report.open_trades":                 (TIER_DIGEST, RULE_NONE),   # own change-detection upstream
    "risk.dd_breaker_reset":              (TIER_DIGEST, RULE_NONE),   # recovery is a state change
    "trade.paper_opened":                 (TIER_DIGEST, RULE_NONE),
    "screener.nr7_signal":                (TIER_DIGEST, RULE_DAILY),  # subject=ticker
    "report.evening_digest":              (TIER_SEND, RULE_DAILY),    # the flush itself

    # ── TIER 3: log only, never sent ────────────────────────────────────────
    "report.market_health":               (TIER_LOG, RULE_NONE),
    "report.premarket_summary":           (TIER_LOG, RULE_NONE),
    "report.daily_signal":                (TIER_LOG, RULE_NONE),
    "report.scan_summary":                (TIER_LOG, RULE_NONE),
    "report.watchlist_update":            (TIER_LOG, RULE_NONE),
    "report.reversal_watchlist":          (TIER_LOG, RULE_NONE),
    "report.flow_fetch_done":             (TIER_LOG, RULE_NONE),
    "report.fetch_status":                (TIER_LOG, RULE_NONE),
    "report.open_trades_empty":           (TIER_LOG, RULE_NONE),
    "report.flow_sentiment":              (TIER_LOG, RULE_NONE),
    "report.auto_trade_status":           (TIER_LOG, RULE_NONE),
    "report.bull_watch":                  (TIER_LOG, RULE_NONE),
    "report.admission_zero":              (TIER_LOG, RULE_NONE),
    "report.wf_revalidation":             (TIER_LOG, RULE_NONE),
    "data.token_health_warning":          (TIER_LOG, RULE_NONE),  # 08:20 pre-refresh warning
    "data.token_probe_inconclusive":      (TIER_LOG, RULE_NONE),
    "data.token_recovered":               (TIER_LOG, RULE_NONE),  # success message
    "data.token_refresh_progress":        (TIER_LOG, RULE_NONE),
    "data.token_refresh_ok":              (TIER_LOG, RULE_NONE),
    "system.polling_activated":           (TIER_LOG, RULE_NONE),
    "system.registry_announce":           (TIER_LOG, RULE_NONE),
}

_DECISION_SEND = "send"
_DECISION_DIGEST = "digest"
_DECISION_SUPPRESS = "suppress"


def wib_today() -> str:
    return datetime.now(WIB).strftime("%Y-%m-%d")


# ── Persistent dedup store ───────────────────────────────────────────────────

def _load_state() -> dict:
    try:
        with open(STATE_FILE) as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:
        logger.warning("[notify_policy] state file unreadable (%s) — resetting", e)
        return {}


def _save_state(state: dict) -> None:
    """Atomic write: tmp file + os.replace, so a crash mid-write can never
    leave a half-JSON state file behind."""
    os.makedirs(_LOG_DIR, exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    try:
        with open(tmp, "w") as fh:
            json.dump(state, fh)
        os.replace(tmp, STATE_FILE)
    except OSError as e:
        logger.warning("[notify_policy] state save failed: %s", e)


def _prune(state: dict) -> dict:
    """Drop stale records so the file stays tiny: day counters older than
    yesterday, cooldowns older than 7 days. State markers (on_change) stay —
    they must survive indefinitely to detect the next change."""
    today = wib_today()
    cutoff_ts = time.time() - 7 * 86400
    kept = {}
    for key, rec in state.items():
        if "d" in rec:
            if rec["d"] >= today:  # keep today's; yesterday's may re-fire
                kept[key] = rec
        elif "ts" in rec:
            if rec["ts"] >= cutoff_ts:
                kept[key] = rec
        else:  # {"s": state-marker}
            kept[key] = rec
    return kept


def _wib_date_of(ts: float) -> str:
    return datetime.fromtimestamp(ts, WIB).strftime("%Y-%m-%d")


def _dedup_allow(event: str, subject: str, state: Optional[str],
                 rule: tuple, msg: str, now: float) -> Tuple[bool, str, Optional[dict]]:
    """Returns (allowed, reason, record_to_store)."""
    kind = rule[0]
    key = f"{event}|{subject or ''}"
    if kind == "none":
        return True, "no-dedup", None
    state_all = _load_state()
    rec = state_all.get(key)
    if kind == "once_per_day":
        today = wib_today()
        if rec and rec.get("d") == today:
            return False, "once_per_day (already sent today)", None
        return True, "first today", {"d": today}
    if kind == "on_change":
        marker = state if state is not None else hashlib.sha1(
            msg.encode("utf-8", "replace")).hexdigest()[:12]
        if rec and rec.get("s") == marker:
            return False, f"on_change (state unchanged: {marker})", None
        return True, f"state changed → {marker}", {"s": marker}
    if kind == "cooldown":
        seconds = float(rule[1])
        if rec and now - float(rec.get("ts", 0)) < seconds:
            return False, f"cooldown {seconds:.0f}s", None
        return True, "cooldown elapsed", {"ts": now}
    return True, f"unknown rule {kind} — allowing", None


# ── Digest buffer ────────────────────────────────────────────────────────────

def _digest_path(day: Optional[str] = None) -> str:
    return os.path.join(DIGEST_DIR, (day or wib_today()) + ".jsonl")


def digest_append(event: str, text: str) -> None:
    """Append one tier-2 item to today's buffer. O_APPEND single write — safe
    across the service and cron processes. Never raises into the caller."""
    try:
        os.makedirs(DIGEST_DIR, exist_ok=True)
        line = json.dumps({"event": event, "ts": time.time(), "text": text},
                          ensure_ascii=False)
        with open(_digest_path(), "a") as fh:
            fh.write(line + "\n")
    except OSError as e:
        logger.warning("[notify_policy] digest append failed: %s", e)


def flush_digest() -> Optional[bool]:
    """Send today's (plus any unflushed older) digest items as ONE message.

    Called by the 17:45 WIB scheduler job. Returns True when a digest went
    out, False when suppressed/failed, None when there was nothing to send.
    The flush itself is a gated send (event=report.evening_digest,
    once_per_day) so the global OFF file and double-runs are both honored;
    the buffer is archived only after an actual send.
    """
    items = []
    day_files = sorted(os.listdir(DIGEST_DIR)) if os.path.isdir(DIGEST_DIR) else []
    for day_file in day_files:
        if not day_file.endswith(".jsonl"):
            continue
        path = os.path.join(DIGEST_DIR, day_file)
        try:
            with open(path) as fh:
                for ln in fh:
                    ln = ln.strip()
                    if not ln:
                        continue
                    try:
                        items.append((day_file[:-6], json.loads(ln)))
                    except ValueError:
                        continue
        except OSError as e:
            logger.warning("[notify_policy] digest read failed for %s: %s", path, e)
    if not items:
        return None

    lines = []
    total = 0
    truncated = 0
    for day, it in items:
        event = it.get("event", "?")
        text = (it.get("text") or "").strip()
        day_prefix = "" if day == wib_today() else f"[{day}] "
        one = f"• {day_prefix}<{event}> " + text.splitlines()[0] if text else f"• {day_prefix}<{event}> (empty)"
        # Keep each item to its first line, ~300 chars — the digest is a
        # headline list; full text lives in the logs.
        if len(one) > 300:
            one = one[:297] + "..."
        if total + len(one) + 1 > 3800:
            truncated += 1
            continue
        lines.append(one)
        total += len(one) + 1
    if truncated:
        lines.append(f"… +{truncated} more items (see logs)")
    msg = "📋 <b>Evening Digest</b> — " + wib_today() + "\n\n" + "\n".join(lines)

    from utils.telegram import send_telegram
    sent = send_telegram(msg, event="report.evening_digest")
    if sent:
        for day_file in os.listdir(DIGEST_DIR):
            if day_file.endswith(".jsonl"):
                try:
                    os.replace(os.path.join(DIGEST_DIR, day_file),
                               os.path.join(DIGEST_DIR, day_file + ".sent"))
                except OSError as e:
                    logger.warning("[notify_policy] digest archive failed: %s", e)
    return sent


# ── The gate ─────────────────────────────────────────────────────────────────

def decide(event: Optional[str], subject: Optional[str] = None,
           state: Optional[str] = None, msg: str = "") -> Tuple[str, str]:
    """Single policy gate. Call BEFORE any network send.

    Returns (action, reason):
      ("send", reason)     — proceed with the actual delivery.
      ("digest", reason)   — item was buffered for the evening digest; do not
                             send now.
      ("suppress", reason) — do nothing (the gate already logged the line).

    Side effects: dedup record written when a send is allowed; digest item
    appended for tier-2 events; every decision logged with the message head.
    """
    if os.path.exists(OFF_FILE):
        logger.info("[telegram] suppressed (global OFF): %.80s",
                    str(msg).replace("\n", " "))
        return _DECISION_SUPPRESS, "global OFF"

    if not event or event not in EVENTS:
        logger.warning("[notify_policy] UNCLASSIFIED send suppressed "
                       "(register it in utils/notify_policy.EVENTS): %.80s",
                       str(msg).replace("\n", " "))
        return _DECISION_SUPPRESS, "unclassified event"

    tier, rule = EVENTS[event]
    now = time.time()
    subj = subject or ""

    if tier == TIER_LOG:
        logger.info("[telegram] log-only (event=%s): %.80s",
                    event, str(msg).replace("\n", " "))
        return _DECISION_SUPPRESS, "tier3 log-only"

    # Both actionable tiers apply the dedup rule BEFORE acting: tier-send so a
    # repeat can't re-fire, tier-digest so the buffer isn't flooded by a
    # state that keeps being true (the scanner.py IHSG refire bug this policy
    # exists to fix).
    allowed, reason, record = _dedup_allow(event, subj, state, rule,
                                           str(msg), now)
    if not allowed:
        logger.info("[telegram] deduped (event=%s, %s): %.80s",
                    event, reason, str(msg).replace("\n", " "))
        return _DECISION_SUPPRESS, reason
    if record is not None:
        state_all = _load_state()
        state_all = _prune(state_all)
        state_all[f"{event}|{subj}"] = record
        _save_state(state_all)

    if tier == TIER_DIGEST:
        digest_append(event, str(msg))
        logger.info("[telegram] digest-buffered (event=%s, %s): %.80s",
                    event, reason, str(msg).replace("\n", " "))
        return _DECISION_DIGEST, "tier2 digest"

    # TIER_SEND
    logger.info("[telegram] send allowed (event=%s, %s): %.80s",
                event, reason, str(msg).replace("\n", " "))
    return _DECISION_SEND, reason
