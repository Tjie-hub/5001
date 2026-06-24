"""External macro snapshot for the premarket briefing (08:45 WIB).

Pulls overnight global + regional + FX levels via yfinance so the morning report
shows the world IDX is waking up into: KOSPI (user-requested), Nikkei, Hang Seng,
S&P 500, Nasdaq, DXY, USD/IDR.

A sanity guard flags glitch bars (yfinance occasionally returns a partial/erroneous
last bar — e.g. KOSPI printed exactly -9.99% on 2026-06-23, round-tripping a week of
gains). Suspect bars are marked ⚠ rather than silently trusted or silently dropped.
"""
from __future__ import annotations

from typing import Any, Optional

try:
    import yfinance as yf
    _YF = True
except ImportError:  # pragma: no cover
    _YF = False

# Ordered: Asia peers → US overnight → FX
SYMBOLS: list[tuple[str, str]] = [
    ("KOSPI", "^KS11"),
    ("Nikkei", "^N225"),
    ("HangSeng", "^HSI"),
    ("S&P500", "^GSPC"),
    ("Nasdaq", "^IXIC"),
    ("DXY", "DX-Y.NYB"),
    ("USD/IDR", "USDIDR=X"),
]

# A 1-day move at/above this magnitude is treated as a likely data glitch, not a real
# move (Asian indices hit circuit breakers around 8-10%; FX never moves this much/day).
GLITCH_THRESHOLD = 0.085


def compute_changes(closes: list[float]) -> Optional[dict[str, Any]]:
    """Pure: from a list of daily closes (oldest→newest) return last/d1/d5/suspect.
    Returns None if there isn't enough data for a 1-day change."""
    vals = [float(c) for c in closes if c is not None]
    if len(vals) < 2:
        return None
    last, prev = vals[-1], vals[-2]
    d1 = (last - prev) / prev if prev else 0.0
    d5 = (last - vals[-6]) / vals[-6] if len(vals) >= 6 and vals[-6] else None
    return {"last": last, "d1": d1, "d5": d5, "suspect": abs(d1) >= GLITCH_THRESHOLD}


def fetch_external_macro() -> list[dict[str, Any]]:
    """Fetch each symbol; resilient per-symbol (network/parse errors → ok=False)."""
    out: list[dict[str, Any]] = []
    for name, sym in SYMBOLS:
        row: dict[str, Any] = {"name": name, "symbol": sym, "ok": False}
        if not _YF:
            out.append(row)
            continue
        try:
            df = yf.download(sym, period="10d", auto_adjust=True, progress=False)
            closes = df["Close"].squeeze().tolist() if df is not None and len(df) else []
            ch = compute_changes(closes)
            if ch:
                row.update(ch)
                row["ok"] = True
        except Exception as e:  # pragma: no cover - network
            row["error"] = str(e)
        out.append(row)
    return out


def _arrow(d1: float) -> str:
    return "▲" if d1 > 0 else ("▼" if d1 < 0 else "▬")


def build_external_macro_block(data: list[dict[str, Any]]) -> str:
    """Pure: render the external-macro lines for the Telegram briefing."""
    lines = ["🌐 <b>External Macro</b> (overnight)"]
    for r in data:
        if not r.get("ok"):
            lines.append(f"  {r['name']}: N/A")
            continue
        last, d1 = r["last"], r["d1"]
        d5 = r.get("d5")
        d5txt = f" · 5d {d5 * 100:+.1f}%" if d5 is not None else ""
        warn = " ⚠verify" if r.get("suspect") else ""
        lines.append(
            f"  {r['name']}: {last:,.2f}  {_arrow(d1)}{d1 * 100:+.2f}%{d5txt}{warn}"
        )
    return "\n".join(lines)


def macro_bias(data: list[dict[str, Any]]) -> str:
    """One-word risk read from non-suspect equity indices (FX excluded)."""
    eq = [r for r in data if r.get("ok") and not r.get("suspect")
          and r["name"] in {"KOSPI", "Nikkei", "HangSeng", "S&P500", "Nasdaq"}]
    if not eq:
        return "n/a"
    up_ratio = sum(1 for r in eq if r["d1"] > 0) / len(eq)
    if up_ratio >= 0.6:
        return "risk-on 🟢"
    if up_ratio <= 0.4:
        return "risk-off 🔴"
    return "mixed/soft 🟡"
