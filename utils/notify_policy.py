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
     the 17:45 WIB scheduler job flushes them as ONE message (and a 20:45
     late flush picks up items buffered after it, e.g. the 18:30 forward-test
     cycle and 20:15 broker flow).

Dedup records are written at decision time, not after successful delivery:
a lost send may swallow tomorrow's identical alert until the next day/state
change. Accepted trade-off — senders retry internally and every TIER_SEND
event is day-granular by design.

Dedup keys are "<event>|<subject>"; the subject (ticker, job, provider, ...)
partitions the day counter so one ticker's alert never mutes another's.

**Shared buffer contract (external writers, e.g. jurnal26).** External apps
append their tier-2 items into the same buffer so the owner gets one digest:

    file: logs/digest_buffer/<YYYY-MM-DD WIB>.jsonl
    line: one JSON object per line, appended with a single write() call
          {"event": str, "ts": float (epoch seconds), "text": str,
           "source": str (optional), "section": str (optional)}

The flush accepts lines with a `source` (e.g. "jurnal26") and events that are
NOT in EVENTS — the registry/classification gate applies to sends from this
codebase, not to lines already in the buffer. A malformed line is skipped and
logged, never fatal. Items are grouped by `section` when present, else by the
event prefix (market.* → Market, report.* → Reports, …).

**Flush mechanics.** Claim-then-read: live `<day>.jsonl` files are atomically
renamed to `<day>.jsonl.sending` before reading, so an item appended during a
flush lands in a fresh `<day>.jsonl` and can never be archived unsent. On a
successful send the `.sending` files become `.sent`; on a failed/suppressed
send they stay `.sending` and are picked up by the next flush (never dropped).
The digest is split into consecutive parts under the same gated event at
Telegram's ~3800-char limit instead of being truncated, and the `.sent`
archive happens only after every part went out. At flush time items whose
file-day is more than 2 IDX trading days before today are NOT sent — they are
archived to `.stale` and the message ends with one "N older items skipped"
line. Trading days = weekends plus the IDX holiday list in
engine/calendar_filter.py; if the calendar can't be read, the rule falls back
to 2 calendar days. (D4, amended 2026-10-06: was 2 calendar days, which
dropped a Friday item whose flush failed on Monday.)
"""

import hashlib
import html
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
    "data.ohlcv_reconcile":               (TIER_SEND, RULE_DAILY),  # review after 1 week live; demote to digest if it fires most days
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
    "trade.paper_staged":                 (TIER_DIGEST, RULE_NONE),  # P3-2 staged summaries (consolidation 2026-10-07)
    # Ops owner-todo jobs (J1–J5, consolidation 2026-10-07): J1 is decision
    # support → digest; J3/J2 report-like → digest; J4/J5 send only on
    # failure/anomaly → alert tier.
    "ops.owner_reminders":                (TIER_DIGEST, RULE_NONE),  # J1
    "ops.p1_3_preflight":                 (TIER_DIGEST, RULE_NONE),  # J2 (one-shot)
    "ops.fq_snapshot":                    (TIER_DIGEST, RULE_NONE),  # J3
    "ops.ledger_push":                    (TIER_SEND, RULE_NONE),    # J4 — failures only
    "ops.health_daily":                   (TIER_SEND, RULE_NONE),    # J5 — anomalies only
    "screener.nr7_signal":                (TIER_DIGEST, RULE_DAILY),  # subject=ticker
    "report.evening_digest":              (TIER_SEND, RULE_DAILY),    # 17:45 main flush
    "report.late_digest":                 (TIER_SEND, RULE_DAILY),    # 20:45 late flush (D3)

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


# Section label for an item: explicit `section` wins, else derived from the
# event prefix. jurnal26 items carry their own sections (Positions, Patterns,
# Screener, Corporate actions, Weekly).
_SECTIONS_BY_PREFIX = (
    ("market", "Market"), ("report", "Reports"), ("screener", "Screener"),
    ("data", "Data"), ("risk", "Risk"), ("trade", "Trades"),
    ("llm", "LLM"), ("bot", "Bot"), ("system", "System"), ("ops", "Ops"),
)
_DEFAULT_SECTION = "Other"
_MAX_PART_CHARS = 3800  # Telegram's hard limit is 4096


def _section_for(event: Optional[str], explicit: Optional[str]) -> str:
    if explicit:
        return str(explicit)
    prefix = (event or "").split(".", 1)[0]
    for p, name in _SECTIONS_BY_PREFIX:
        if prefix == p:
            return name
    return _DEFAULT_SECTION


def _flush_title(event: str) -> str:
    base = ("🌙 <b>Late Digest</b>" if event == "report.late_digest"
            else "📋 <b>Evening Digest</b>")
    return base + " — " + wib_today()


# Stale-skip threshold in trading/calendar days (D4).
_STALE_DAYS = 2


def _idx_trading_days_between(start_day, end_day) -> Optional[int]:
    """Count IDX trading days d with start_day < d <= end_day — weekends plus
    the holiday list in engine/calendar_filter.py. Returns None when the
    calendar can't be read (import or computation failure), which switches the
    stale rule to its calendar-day fallback."""
    try:
        from engine.calendar_filter import is_trading_day

        gap = 0
        day = start_day
        while day < end_day:
            day += timedelta(days=1)
            if is_trading_day(day)[0]:
                gap += 1
        return gap
    except Exception:  # calendar unavailable — never fail a flush over this
        logger.warning("[notify_policy] IDX calendar unavailable; digest "
                       "stale rule falls back to calendar days", exc_info=True)
        return None


def _is_stale_day(file_day: str, today) -> bool:
    """True when the buffer file's day is more than _STALE_DAYS IDX trading
    days before `today` (D4, amended 2026-10-06 — was 2 calendar days, which
    dropped a Friday item whose flush failed on Monday; a Friday→Monday gap
    is only 1 trading day).

    `today` is whatever wib_today() returns — a 'YYYY-MM-DD' string — or a
    date, so tests can pin either shape. An unparsable or future file-day is
    never stale (keep and send, never drop). Calendar-day fallback when the
    holiday calendar can't be read.
    """
    try:
        day = datetime.strptime(file_day, "%Y-%m-%d").date()
    except ValueError:
        return False
    if isinstance(today, str):
        try:
            today = datetime.strptime(today, "%Y-%m-%d").date()
        except ValueError:
            return False
    if day >= today:
        return False
    gap = _idx_trading_days_between(day, today)
    if gap is None:
        gap = (today - day).days
    return gap > _STALE_DAYS


def _parse_buffer_line(ln: str) -> Optional[dict]:
    """Validate one shared-buffer line. Returns the item or None (malformed —
    skipped and logged, never fatal)."""
    try:
        it = json.loads(ln)
    except ValueError:
        return None
    if not isinstance(it, dict):
        return None
    text = it.get("text")
    if not isinstance(text, str) or not text.strip():
        return None
    return it


def flush_digest(event: str = "report.evening_digest") -> Optional[bool]:
    """Send buffered tier-2 items as ONE message (split into parts at the
    Telegram limit instead of truncated).

    Called by the 17:45 WIB main flush (event=report.evening_digest, the
    default) and the 20:45 WIB late flush (event=report.late_digest, D3 — a
    separate once_per_day event so the late flush isn't blocked by the main
    one). Returns True when the digest went out, False when suppressed or
    failed, None when there was nothing to send.

    Mechanics (see module docstring): claim-then-read (D1) — live
    `<day>.jsonl` files are atomically renamed to `.sending` before reading,
    so appends during the flush land in a fresh `<day>.jsonl`; the `.sending`
    files become `.sent` only after EVERY part went out, and stay `.sending`
    otherwise (picked up next flush, never dropped). Items whose file-day is
    more than 2 IDX trading days before today are archived to `.stale`, never
    sent (D4, amended 2026-10-06 — was 2 calendar days, which dropped a Friday
    item whose flush failed on Monday); calendar-day fallback when the holiday
    calendar can't be read. The message ends with one "N older items skipped"
    line when any were skipped. Item text is html.escape()d and grouped under
    section headers (D2/D3).
    """
    if not os.path.isdir(DIGEST_DIR):
        return None

    # D1: claim first, then read. Leftover `.sending` files from a previous
    # failed/suppressed flush are picked up here too.
    claimed: list = []
    for fname in sorted(os.listdir(DIGEST_DIR)):
        path = os.path.join(DIGEST_DIR, fname)
        if fname.endswith(".jsonl"):
            try:
                os.replace(path, path + ".sending")
                claimed.append(path + ".sending")
            except OSError as e:
                logger.warning("[notify_policy] digest claim failed for %s: %s", path, e)
        elif fname.endswith(".jsonl.sending"):
            claimed.append(path)
    if not claimed:
        return None

    today = wib_today()
    fresh: list = []        # (file_day, item)
    stale_paths: list = []  # .sending paths whose file-day is > 2 trading days old
    stale_count = 0
    malformed = 0
    for path in claimed:
        fname = os.path.basename(path)
        file_day = fname.split(".jsonl")[0]
        is_stale = _is_stale_day(file_day, today)
        try:
            with open(path) as fh:
                for ln in fh:
                    ln = ln.strip()
                    if not ln:
                        continue
                    it = _parse_buffer_line(ln)
                    if it is None:
                        malformed += 1
                        continue
                    if is_stale:
                        stale_count += 1
                    else:
                        fresh.append((file_day, it))
        except OSError as e:
            logger.warning("[notify_policy] digest read failed for %s: %s", path, e)
        if is_stale:
            stale_paths.append(path)

    if malformed:
        logger.warning("[notify_policy] digest flush skipped %d malformed "
                       "buffer line(s)", malformed)

    # D4: archive stale items immediately — they never ride in the message
    # and never depend on the send outcome.
    for path in stale_paths:
        try:
            os.replace(path, path[:-len(".sending")] + ".stale")
        except OSError as e:
            logger.warning("[notify_policy] stale archive failed for %s: %s", path, e)

    if not fresh:
        return None

    # D2: escape item text, drop the <event> token; group under section
    # headers in first-appearance order.
    grouped: dict = {}
    for file_day, it in fresh:
        text = it["text"].strip()
        first = text.splitlines()[0] if text else "(empty)"
        first = html.escape(first)
        if len(first) > 300:
            first = first[:297] + "..."
        src = it.get("source")
        if src and str(src) != "5001":
            first += " <i>(" + html.escape(str(src)) + ")</i>"
        day_prefix = "" if file_day == today else f"[{file_day}] "
        bullet = f"• {day_prefix}{first}"
        sec = _section_for(it.get("event"), it.get("section"))
        grouped.setdefault(sec, []).append(bullet)

    # Pack section blocks into parts at the ~3800-char limit; a section split
    # across parts re-emits its header at the start of the next part.
    chunks: list = []
    cur: list = []
    cur_len = 0
    for sec, bullets in grouped.items():
        need_header = True
        for b in bullets:
            piece = (f"<b>{sec}</b>\n" if need_header else "") + b
            if cur_len + len(piece) + 1 > _MAX_PART_CHARS and cur:
                chunks.append(cur)
                cur, cur_len = [], 0
                piece = f"<b>{sec}</b>\n" + b  # header repeats on the new part
            cur.append(piece)
            cur_len += len(piece) + 1
            need_header = False
    if cur:
        chunks.append(cur)

    n_parts = len(chunks)
    title = _flush_title(event)
    from utils.telegram import send_telegram
    sent_all = True
    for i, chunk in enumerate(chunks):
        msg = title if n_parts == 1 else f"{title} ({i + 1}/{n_parts})"
        msg += "\n\n" + "\n".join(chunk)
        if i == n_parts - 1 and stale_count:
            msg += (f"\n\n… {stale_count} older items skipped "
                    f"(see logs/digest_buffer)")
        # Same gated event for every part; the per-part subject keeps
        # once_per_day from swallowing parts 2..n.
        if not send_telegram(msg, event=event, subject=f"part{i + 1}"):
            sent_all = False
            break  # claimed .sending files stay for the next flush

    if sent_all:
        for path in claimed:
            if path.endswith(".jsonl.sending") and os.path.exists(path):
                try:
                    os.replace(path, path[:-len(".sending")] + ".sent")
                except OSError as e:
                    logger.warning("[notify_policy] digest archive failed for %s: %s", path, e)
    return sent_all


def flush_late_digest() -> Optional[bool]:
    """20:45 WIB late flush — same machinery, separate gated event (D3) so it
    runs after the 17:45 main flush on the same day."""
    return flush_digest(event="report.late_digest")


# ── The gate ─────────────────────────────────────────────────────────────────

def decide(event: Optional[str], subject: Optional[str] = None,
           state: Optional[str] = None, msg: str = "") -> Tuple[str, str]:
    """Single policy gate. Call BEFORE any network send.

    Returns (action, reason):
      ("send", reason)     — proceed with the actual delivery.
      ("digest", reason)   — item was buffered for the evening digest; do not
                             send now.
      ("suppress", reason) — do nothing (the gate already logged the line).

    Side effects: dedup record written when allowed; digest item appended for
    tier-2 events; every decision logged with the message head.

    The global OFF file blocks actual SENDS (tier-1) and the digest flush —
    but tier-2 items are still buffered under their dedup rules while it
    exists, so the digest resumes cleanly (≤2-day items) when the blackout is
    lifted; older backlog is archived stale at flush time (D4).
    """
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
        # Buffering continues while TELEGRAM_OFF exists (dedup already
        # applied above) — the digest resumes when the blackout is lifted.
        digest_append(event, str(msg))
        logger.info("[telegram] digest-buffered (event=%s, %s): %.80s",
                    event, reason, str(msg).replace("\n", " "))
        return _DECISION_DIGEST, "tier2 digest"

    if os.path.exists(OFF_FILE):
        logger.info("[telegram] suppressed (global OFF): %.80s",
                    str(msg).replace("\n", " "))
        return _DECISION_SUPPRESS, "global OFF"

    # TIER_SEND
    logger.info("[telegram] send allowed (event=%s, %s): %.80s",
                event, reason, str(msg).replace("\n", " "))
    return _DECISION_SEND, reason
