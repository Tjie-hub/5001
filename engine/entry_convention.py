"""engine/entry_convention.py — the single authority on when and at what price
a signal may be filled.

WHY THIS EXISTS (audit 2026-09-02, finding L-2)
------------------------------------------------
`check_nr7_signal` returned `details['price'] = df.iloc[-1]['open']` — the
session's opening print — and `scheduler/scanner.py` passed that straight into
`paper_trade.open_trade()`. The scan runs at 10:05 / 11:05 / 14:35 WIB. At 14:35
you cannot buy at 09:00's open. The bias was systematically favourable, because
the NR7 trigger condition *is* "the open gapped above the setup bar's high" —
so the only fills taken were the ones that had already gone the right way.

Every walk-forward strategy with an explicit fill uses the same convention:

    decide on completed bar data, fill at the NEXT bar's OPEN

(`strategy_nr7_breakout`, `strategy_trend_following_breakout`,
`strategy_inside_bar_breakout`, `strategy_orb`, `strategy_volume_profile_poc`,
`strategy_vwma_breakout_pullback`, `strategy_crash_recovery`,
`strategy_panic_rebound` — all read `row['open']` of the bar after the setup
bar). `forward_testing` already honours it via `resolver.next_open()`.

So the rule below is not new policy — it is the research convention, finally
enforced on the live path as well. A live scanner that observes the open cannot
fill at that open; it must STAGE the signal for the next session's open.

Contract
--------
`executable_entry()` returns an `EntryResolution`. `fill_price` is non-None ONLY
when a price is genuinely obtainable at or after the signal timestamp. Otherwise
`action == STAGE` and the caller must record the signal and wait — never
substitute a past price.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

# The one entry rule this repo's research validated. Stored on every signal so a
# forward-test row can prove which convention it was measured under.
ENTRY_RULE_NEXT_OPEN = "NEXT_SESSION_OPEN"

# Price-basis labels. A basis is retrospective when the price it names was
# printed before the signal timestamp and cannot be transacted at any more.
BASIS_LAST_CLOSE = "last_completed_close"   # reference/screening price
BASIS_SESSION_OPEN = "session_open"         # RETROSPECTIVE once the session is running
BASIS_NEXT_OPEN = "next_session_open"       # the executable basis — future at decision time

_RETROSPECTIVE_BASES = frozenset({BASIS_SESSION_OPEN})

ACTION_STAGE = "STAGE"
ACTION_FILL = "FILL"
ACTION_REJECT = "REJECT"


@dataclass(frozen=True)
class DecisionPrice:
    """The reference price a decision was taken at — never a fill."""
    price: Optional[float]
    basis: str
    bar_date: Optional[str]


@dataclass(frozen=True)
class EntryResolution:
    action: str                       # STAGE | FILL | REJECT
    fill_price: Optional[float]       # non-None only when action == FILL
    entry_rule: str
    decision: DecisionPrice
    reason: str

    @property
    def is_fill(self) -> bool:
        return self.action == ACTION_FILL


def decision_price(df, *, signal_bar_is_partial: bool = True) -> DecisionPrice:
    """Reference price for a decision taken now.

    The live scanner loads OHLCV with partial bars (`data/loaders.py` keeps
    `is_final=0` for live scans — they *are* the live signal input), so the last
    row is today's in-progress bar. Its close is the current traded price, which
    is the honest "what the market is at, at decision time" figure. It is a
    reference, never a fill: the fill is the next session's open.
    """
    if df is None or len(df) == 0:
        return DecisionPrice(None, BASIS_LAST_CLOSE, None)
    last = df.iloc[-1]
    try:
        price = float(last["close"])
    except (KeyError, TypeError, ValueError):
        return DecisionPrice(None, BASIS_LAST_CLOSE, None)
    bar_date = str(last["date"])[:10] if "date" in df.columns else None
    return DecisionPrice(price, BASIS_LAST_CLOSE, bar_date)


def is_retrospective(basis: str) -> bool:
    """True when a price on this basis was printed before the signal timestamp."""
    return basis in _RETROSPECTIVE_BASES


def executable_entry(details: dict[str, Any], df=None) -> EntryResolution:
    """Resolve how (and whether) a live signal may be filled.

    `details` is a checker result's `details` dict. A checker that names its
    price basis via `details['price_basis']` is taken at its word; one that does
    not is treated as `BASIS_LAST_CLOSE` (the historical default for every
    checker except NR7, which is now explicit).

    Live scans NEVER fill: the validated convention is next-session open, and
    that price does not exist yet. The resolution is therefore STAGE whenever a
    usable decision price exists, and REJECT when it does not.
    """
    details = details or {}
    basis = details.get("price_basis") or BASIS_LAST_CLOSE
    dp = decision_price(df)

    if dp.price is None:
        raw = details.get("price")
        if raw:
            dp = DecisionPrice(float(raw), basis, details.get("bar_date"))

    if dp.price is None:
        return EntryResolution(
            ACTION_REJECT, None, ENTRY_RULE_NEXT_OPEN, dp,
            "no decision price available",
        )

    if is_retrospective(basis):
        # The checker reported a price that had already printed. Do not fill it;
        # stage instead. This is the L-2 guard: it must be impossible to open a
        # trade at a price that predates the signal.
        return EntryResolution(
            ACTION_STAGE, None, ENTRY_RULE_NEXT_OPEN, dp,
            f"refused retrospective fill (basis={basis}); staged for next open",
        )

    return EntryResolution(
        ACTION_STAGE, None, ENTRY_RULE_NEXT_OPEN, dp,
        "staged for next session open (validated entry convention)",
    )
