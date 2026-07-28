"""forward_testing/reporting.py — Telegram reporting layer over existing
forward-testing outputs (audit 2026-07-28 Phase 3).

Read-only: every function here either reads a stored ft_* column as-is or
computes a plain aggregate (COUNT/AVG/sort) over stored columns — same
discipline as engine.trade_plan's EOD/premarket reporting. Nothing here
writes to the database, opens a position, decides an exit, or changes a
lifecycle state; those stay owned by ShadowPositionManager/LifecycleManager.

Exit-reason vocabulary (SL/TP/TRAIL/TIME/STALE) is surfaced verbatim from
engine.exits.evaluator / shadow_manager rather than translated into an
invented "completed"/"stopped" taxonomy that doesn't exist in the code.
"""
import html
from typing import Any, Optional

from forward_testing.positions.shadow_manager import _excursions
from forward_testing.storage.db import ft_get_db

MAX_ROWS = 10
BEST_WORST_N = 3


# ── Read-only queries (new; no existing method covered these) ──────────────

def get_positions_opened_on(db_path: str, run_date: str) -> list[dict]:
    """ft_shadow_position rows whose entry (fill) date is run_date."""
    with ft_get_db(db_path) as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM ft_shadow_position WHERE entry_date=? ORDER BY ticker",
            (run_date,)).fetchall()]


def get_trades_closed_on(db_path: str, run_date: str) -> list[dict]:
    """ft_shadow_trade rows whose exit date is run_date."""
    with ft_get_db(db_path) as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM ft_shadow_trade WHERE exit_date=? ORDER BY ticker",
            (run_date,)).fetchall()]


def get_all_closed_trades(db_path: str) -> list[dict]:
    """Every ft_shadow_trade row to date, oldest first — the all-time scoreboard."""
    with ft_get_db(db_path) as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM ft_shadow_trade ORDER BY exit_date").fetchall()]


def get_active_candidate_count(repo, track: str = "SHADOW") -> int:
    """Signals still awaiting a fill (state=GENERATED, not yet opened) — reuses
    FTRepo.get_signals_by_state, the existing lookup method, unchanged."""
    return len(repo.get_signals_by_state("GENERATED", track=track))


# ── Pure aggregates over already-stored columns ─────────────────────────────

def win_loss_summary(trades: list[dict]) -> Optional[dict]:
    """Cumulative win/loss + average performance from ft_shadow_trade.pnl_pct/
    r_multiple/hold_days (all stored at close time — nothing recomputed here).
    None when there are no closed trades yet — never fabricate a 0% baseline
    for a strategy that hasn't closed a single round-trip."""
    if not trades:
        return None
    n = len(trades)
    wins = [t for t in trades if t["pnl_pct"] > 0]
    return {
        "n": n,
        "wins": len(wins),
        "losses": n - len(wins),
        "win_rate": len(wins) / n,
        "avg_pnl_pct": sum(t["pnl_pct"] for t in trades) / n,
        "avg_r_multiple": sum(t["r_multiple"] for t in trades) / n,
        "avg_hold_days": sum(t["hold_days"] for t in trades) / n,
    }


def best_worst_trades(trades: list[dict], n: int = BEST_WORST_N) -> tuple[list[dict], list[dict]]:
    """Top/bottom n closed trades by pnl_pct (already-stored column, just sorted).
    When there are 2n or fewer trades total, the two lists may overlap or one
    trade may appear in both — an honest reflection of a small sample, not a bug."""
    if not trades:
        return [], []
    ranked = sorted(trades, key=lambda t: t["pnl_pct"], reverse=True)
    best = ranked[:n]
    worst = list(reversed(ranked[-n:]))
    return best, worst


# ── Telegram message builder ────────────────────────────────────────────────

def _fmt_position(p: dict) -> str:
    entry = p.get("entry_price")
    sl = p.get("sl_price")
    tp = p.get("tp_price")
    sl_tp = ""
    if sl is not None or tp is not None:
        sl_txt = f"{sl:.2f}" if sl is not None else "—"
        tp_txt = f"{tp:.2f}" if tp is not None else "—"
        sl_tp = f"  SL {sl_txt} / TP {tp_txt}"
    entry_txt = f"{entry:.2f}" if entry is not None else "—"
    return (f"  <b>{html.escape(p['ticker'])}</b> {p['direction']} @ {entry_txt}{sl_tp}")


def _fmt_closed(t: dict) -> str:
    return (f"  <b>{html.escape(t['ticker'])}</b> {t['direction']} {t['exit_reason']}  "
           f"pnl {t['pnl_pct'] * 100:+.2f}%  R {t['r_multiple']:+.2f}  {t['hold_days']}d")


def _fmt_active(p: dict) -> str:
    raw_entry = p.get("raw_entry_price") or p["entry_price"]
    mae, mfe = _excursions(p["direction"], raw_entry, p["highest_seen"], p["lowest_seen"])
    return (f"  <b>{html.escape(p['ticker'])}</b> {p['direction']} {p['hold_days']}d  "
           f"best {mfe * 100:+.2f}% / worst {mae * 100:+.2f}%")


def _fmt_scoreboard(t: dict) -> str:
    return (f"  <b>{html.escape(t['ticker'])}</b> {t['pnl_pct'] * 100:+.2f}% "
           f"({t['exit_reason']}, {t['hold_days']}d)")


def build_forward_test_message(
    date_str: str,
    new_positions: list[dict],
    closed_trades: list[dict],
    active_positions: list[dict],
    win_loss: Optional[dict],
    best_trades: list[dict],
    worst_trades: list[dict],
    active_candidates: Optional[int] = None,
    max_rows: int = MAX_ROWS,
) -> str:
    """Pure Telegram-message builder — no I/O, no langgraph import, unit-testable
    on the lean venv (same contract as engine.trade_plan.build_message and
    scheduler.jobs._build_premarket_firm_message)."""
    L: list[str] = [
        f"📊 <b>FORWARD TEST SUMMARY — {date_str}</b>",
        f"Active Positions: {len(active_positions)}",
        f"New: {len(new_positions)}",
        f"Closed: {len(closed_trades)}",
    ]
    if active_candidates is not None:
        L.append(f"Candidates awaiting fill: {active_candidates}")
    if win_loss:
        L.append(
            f"Avg Performance: {win_loss['avg_pnl_pct'] * 100:+.2f}% "
            f"({win_loss['wins']}/{win_loss['n']} win, {win_loss['win_rate'] * 100:.0f}% WR, "
            f"avg hold {win_loss['avg_hold_days']:.1f}d)"
        )
    else:
        L.append("Avg Performance: n/a (no closed trades yet)")

    if new_positions:
        L += ["", "<b>🟢 NEW</b>"]
        L += [_fmt_position(p) for p in new_positions[:max_rows]]
        if len(new_positions) > max_rows:
            L.append(f"  …+{len(new_positions) - max_rows} more")

    if closed_trades:
        L += ["", "<b>🔴 CLOSED</b>"]
        L += [_fmt_closed(t) for t in closed_trades[:max_rows]]
        if len(closed_trades) > max_rows:
            L.append(f"  …+{len(closed_trades) - max_rows} more")

    if active_positions:
        L += ["", f"<b>🟡 ACTIVE</b> ({len(active_positions)})"]
        L += [_fmt_active(p) for p in active_positions[:max_rows]]
        if len(active_positions) > max_rows:
            L.append(f"  …+{len(active_positions) - max_rows} more")

    if best_trades:
        L += ["", "<b>📈 BEST</b>"]
        L += [_fmt_scoreboard(t) for t in best_trades]

    if worst_trades:
        L += ["", "<b>📉 WORST</b>"]
        L += [_fmt_scoreboard(t) for t in worst_trades]

    return "\n".join(L)


def build_forward_test_report(db_path: str, run_date: str, repo: Any = None) -> str:
    """Assemble + render the full forward-test Telegram report for run_date.

    repo: inject an FTRepo for tests; defaults to a fresh FTRepo(db_path).
    """
    if repo is None:
        from forward_testing.storage.repo import FTRepo
        repo = FTRepo(db_path)

    new_positions = get_positions_opened_on(db_path, run_date)
    closed_trades = get_trades_closed_on(db_path, run_date)
    active_positions = repo.get_open_shadow_positions()
    active_candidates = get_active_candidate_count(repo)
    all_trades = get_all_closed_trades(db_path)
    win_loss = win_loss_summary(all_trades)
    best, worst = best_worst_trades(all_trades)

    return build_forward_test_message(
        run_date, new_positions, closed_trades, active_positions,
        win_loss, best, worst, active_candidates=active_candidates,
    )
