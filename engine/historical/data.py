"""engine/historical/data.py — raw vs adjusted data separation for historical systems.

Phase 9 §5:
  - Signal/setup geometry (H−L NR7 ranges, NR7 detection, Stretch, Opening
    Range, entry triggers, stop triggers) is computed on the RAW basis.
  - Adjusted prices are permitted for PnL accounting only.
  - Every signal/trade records which data basis produced it.
  - The existing adjusted-by-default research path
    (data/loaders.load_ohlcv_df / _load_ohlcv_bulk with adjusted defaulting to
    True) must NOT be used as a substitute for the signal basis.

BASIS HONESTY (Phase 9 retraction C-2): the stored corpus is already
split-adjusted at the source for splits known at rebuild time, so
`stored_raw` ("no adjustment applied at load") is exact raw only where the
corpus itself was raw. True unadjusted prices are not recoverable from
storage for pre-rebuild history; this limitation is recorded, not hidden.
`adjusted_gap_verified` applies data/adjustments gap-verified split factors —
for PnL accounting only.

Pure loader bridge: converts pandas frames into kernel Bar lists.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from engine.historical.base import SIGNAL_BASIS_STORED_RAW
from engine.historical.kernel import Bar

BASIS_STORED_RAW = SIGNAL_BASIS_STORED_RAW
BASIS_RAW_TICKS = "raw_ticks"
BASIS_ADJUSTED_GAP_VERIFIED = "adjusted_gap_verified"

_RAW_NOTE = ("no adjustment applied at load; corpus may be pre-adjusted at "
             "source for rebuild-time splits (Phase 9 C-2 retraction)")
_ADJ_NOTE = "gap-verified split adjustment applied; PnL accounting only"


@dataclass(frozen=True)
class BasisMetadata:
    basis: str
    note: str

    def to_dict(self) -> dict:
        return {"basis": self.basis, "note": self.note}


RAW_BASIS = BasisMetadata(BASIS_STORED_RAW, _RAW_NOTE)
ADJUSTED_BASIS = BasisMetadata(BASIS_ADJUSTED_GAP_VERIFIED, _ADJ_NOTE)


def load_signal_bars(conn, ticker: str, final_only: bool = True) -> tuple[list[Bar], BasisMetadata]:
    """Signal-basis bars: RAW. Uses the explicit adjusted=False path — never the
    adjusted research default. Returns kernel Bars in date order."""
    from data.loaders import load_ohlcv_raw
    df = load_ohlcv_raw(conn, ticker, final_only=final_only)
    bars = [Bar(date=str(d)[:10], open=float(o), high=float(h),
                low=float(l), close=float(c))
            for d, o, h, l, c in zip(df["date"], df["open"], df["high"],
                                     df["low"], df["close"])]
    return bars, RAW_BASIS


def load_pnl_closes(conn, ticker: str, final_only: bool = True):
    """PnL-basis frame (adjusted where appropriate) + its basis metadata.
    Returns (dates, closes, BasisMetadata)."""
    from data.loaders import load_ohlcv_df
    df = load_ohlcv_df(conn, ticker, final_only=final_only, adjusted=True)
    dates = [str(d)[:10] for d in df["date"]]
    return dates, [float(c) for c in df["close"]], ADJUSTED_BASIS


def raw_to_pnl_factor(pnl_dates, pnl_closes, raw_dates, raw_closes) -> dict:
    """Per-date raw→PnL-basis conversion factor: adjusted_close / raw_close.
    A factor of 1.0 means the two bases coincide on that date."""
    raw_by_date = dict(zip(raw_dates, raw_closes))
    factors = {}
    for d, adj in zip(pnl_dates, pnl_closes):
        raw = raw_by_date.get(d)
        factors[d] = (adj / raw) if (raw not in (None, 0.0) and raw == raw) else 1.0
    return factors


@dataclass(frozen=True)
class OpeningRangeUnavailable:
    """Why an Opening Range could not be built for one session.

    Distinct from `None` on purpose. `None` means "the data for this session did
    not yield an OR"; this object means "the OR the rule requires cannot be
    constructed from this source AT ALL". Conflating the two is how a
    30-second recovered rule silently becomes a 1-minute engine convention.
    """
    reason: str          # RejectionReason value
    details: dict

    def to_dict(self) -> dict:
        return {"reason": self.reason, "details": dict(self.details)}


def tick_opening_range_provider(db_path: str, ticker: str, session_start: str,
                                opening_range_seconds: int,
                                source_resolution_seconds: int,
                                min_ticks: int = 5):
    """Returns a provider callable(date) -> dict | OpeningRangeUnavailable | None.

    Session window: [session_start, session_start + opening_range_seconds).

    THE DURATION IS A RECOVERED RULE, NOT A KNOB (audit C-8). Crabel 1990's
    glossary defines the Opening Range as "the first thirty seconds of trade of
    each trading day". `source_resolution_seconds` states the finest interval
    the intraday source can actually distinguish (1 for traded prints stamped to
    the second, 60 for one-minute bars). When the requested window is finer than
    the source can resolve, every session is rejected with
    `insufficient_intraday_resolution` — the engine never widens the window to
    whatever the data happens to support.

    The session ANCHOR remains market/era-specific: PRIMARY SOURCE NOT
    RECOVERED, required configuration, never defaulted. Ticks are raw traded
    prints: basis `raw_ticks`.
    """
    if opening_range_seconds <= 0:
        raise ValueError("invalid_configuration: opening_range_seconds must be > 0")
    if source_resolution_seconds <= 0:
        raise ValueError("invalid_configuration: source_resolution_seconds must be > 0")

    unresolvable = opening_range_seconds < source_resolution_seconds
    start_t = datetime.strptime(session_start, "%H:%M:%S")
    end_t = (start_t + timedelta(seconds=opening_range_seconds)).strftime("%H:%M:%S")

    def provider(date: str):
        if unresolvable:
            return OpeningRangeUnavailable(
                reason="insufficient_intraday_resolution",
                details={"date": date, "ticker": ticker,
                         "opening_range_seconds": opening_range_seconds,
                         "source_resolution_seconds": source_resolution_seconds,
                         "session_start": session_start})
        from data.db import connect as db_connect
        try:
            conn = db_connect(db_path)
            rows = conn.execute(
                "SELECT price, volume FROM ticks "
                "WHERE ticker=? AND date=? AND time >= ? AND time < ? "
                "ORDER BY time ASC", (ticker, date, session_start, end_t)).fetchall()
            conn.close()
        except Exception:
            return None
        prices = [float(r[0]) for r in rows if r[0] is not None]
        if len(prices) < min_ticks:
            return None
        return {"or_high": max(prices), "or_low": min(prices),
                "n_ticks": len(prices), "basis": BASIS_RAW_TICKS,
                "session_start": session_start,
                "opening_range_seconds": opening_range_seconds,
                "source_resolution_seconds": source_resolution_seconds}

    return provider
