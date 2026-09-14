#!/usr/bin/env python3
"""Dataset B feature-level fingerprint + semantic dependency register. READ-ONLY.

WHY FEATURE-LEVEL
-----------------
Dataset A's F-1 fingerprint pinned ticker, row count, date range, SUM(lot) and
SUM(lot_value) — two of broker_flow's eleven columns, and neither is one the
next study intends to use. Its own registration record says so: it "does NOT pin
broker_code/side granularity, freq, avg_price, investor_type, or row order".
Dataset A is therefore frozen for a claim nobody will make again.

This fingerprint pins every column any planned Dataset B feature touches, per
ticker, order-independently, and records the column list inside the receipt so
the scope is auditable rather than implicit.

ORDER INDEPENDENCE
------------------
Per (ticker, column) the values are folded with a commutative accumulator
(sum of per-row SHA-256 digests taken as integers, modulo 2^256), so row order
cannot affect the result while any single value change does. Text columns are
hashed as bytes, numerics as their exact repr, NULLs as a distinct sentinel —
so NULL and 0 are never confused.
"""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import foundation as F

HERE = Path(__file__).resolve().parent
MOD = 1 << 256

BROKER_FLOW_COLUMNS = ["broker_code", "side", "lot", "lot_value", "value",
                       "value_total", "avg_price", "freq", "investor_type"]
BANDAR_COLUMNS = ["total_buyer", "total_seller"]
OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]


def _cell(v) -> bytes:
    if v is None:
        return b"\x00NULL"
    if isinstance(v, float):
        return b"\x01" + repr(v).encode()
    if isinstance(v, int):
        return b"\x02" + str(v).encode()
    return b"\x03" + str(v).encode("utf-8")


def _fold(rows) -> str:
    """Commutative fold: order-independent, value-sensitive."""
    acc = 0
    for r in rows:
        h = hashlib.sha256(b"\x1f".join(_cell(v) for v in r)).digest()
        acc = (acc + int.from_bytes(h, "big")) % MOD
    return f"{acc:064x}"


def fingerprint(conn, roster, cal, quarantined=()) -> dict:
    q = set(quarantined)
    cells = {(t, d) for d, m in roster.session_members.items() for t in m if t not in q}
    tickers = sorted({t for t, _ in cells})
    ph = ",".join("?" * len(tickers))
    lo, hi = cal.sessions[0], cal.sessions[-1]

    per_ticker = {}

    bf = {}
    for row in conn.execute(
            f"SELECT ticker, trade_date, {', '.join(BROKER_FLOW_COLUMNS)} FROM broker_flow "
            f"WHERE ticker IN ({ph}) AND trade_date >= ? AND trade_date <= ?",
            tickers + [lo, hi]):
        if (row[0], row[1]) in cells:
            bf.setdefault(row[0], []).append(row[1:])
    bd = {}
    for row in conn.execute(
            f"SELECT ticker, trade_date, {', '.join(BANDAR_COLUMNS)} FROM bandar_detector "
            f"WHERE ticker IN ({ph}) AND trade_date >= ? AND trade_date <= ?",
            tickers + [lo, hi]):
        if (row[0], row[1]) in cells:
            bd.setdefault(row[0], []).append(row[1:])
    px = {}
    for row in conn.execute(
            f"SELECT ticker, date, {', '.join(OHLCV_COLUMNS)} FROM ohlcv "
            f"WHERE ticker IN ({ph}) AND date >= ? AND date <= ?", tickers + [lo, hi]):
        if (row[0], row[1]) in cells:
            px.setdefault(row[0], []).append(row[1:])

    for t in tickers:
        per_ticker[t] = {
            "broker_flow": {"rows": len(bf.get(t, [])), "fold": _fold(bf.get(t, []))},
            "bandar_detector": {"rows": len(bd.get(t, [])), "fold": _fold(bd.get(t, []))},
            "ohlcv": {"rows": len(px.get(t, [])), "fold": _fold(px.get(t, []))},
        }

    body = {
        "artifact": "DATASET_B_FINGERPRINT", "version": "v1",
        "method": "per-ticker commutative SHA-256 fold; order-independent, value-sensitive",
        "columns": {"broker_flow": BROKER_FLOW_COLUMNS, "bandar_detector": BANDAR_COLUMNS,
                    "ohlcv": OHLCV_COLUMNS},
        "roster_artifact_sha256": roster.sha256,
        "calendar_artifact_sha256": cal.sha256,
        "window": {"start": lo, "end": hi},
        "cells_in_scope": len(cells), "tickers": len(tickers),
        "quarantined": sorted(q),
        "per_ticker": per_ticker,
    }
    body["dataset_fingerprint"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return body


SEMANTIC_REGISTER = {
    "broker_flow.lot": {
        "meaning": "NET lots for that broker on that ticker-session (buy minus sell), SIGNED",
        "status": "VERIFIED",
        "evidence": "a broker appears exactly once per ticker-session (3,026,786/3,026,786 rows "
                    "have a single side); vendor request carries transaction_type="
                    "TRANSACTION_TYPE_NET; live probe at full limit nets to exactly 0",
        "research_use": "SUM(lot) for a net. NEVER BUY_lot - SELL_lot (double-applies the sign).",
    },
    "broker_flow.value": {
        "meaning": "NET rupiah value for that broker on that ticker-session, SIGNED",
        "status": "VERIFIED",
        "evidence": "SUM(value) = 0 on 70,424/70,424 complete-disclosure ticker-days; "
                    "= 0 exactly on all three full-limit probe responses",
        "research_use": "the accounting identity makes aggregate net UNINFORMATIVE. Do not "
                        "resurrect aggregate net-flow as a directional variable.",
    },
    "broker_flow.lot_value": {
        "meaning": "GROSS shares transacted on the broker's dominant side; non-negative",
        "status": "PARTIALLY VERIFIED",
        "evidence": "lot_value >= |lot|*100 in 3,026,786/3,026,786 rows; avg_price = "
                    "value_total/lot_value in 3,015,371/3,026,786; the identity "
                    "buy_gross + sell_gross - ohlcv_volume = bandar.volume*100 closes exactly "
                    "on 74.8% of complete-disclosure days and within 1% on 87.0%",
        "research_use": "usable as gross-on-dominant-side. blotv/slotv field-level semantics "
                        "are NOT independently confirmed against vendor documentation.",
    },
    "broker_flow.value_total": {
        "meaning": "GROSS rupiah on the broker's dominant side; non-negative",
        "status": "PARTIALLY VERIFIED", "evidence": "as lot_value; avg_price reconciles",
        "research_use": "gross exposure only",
    },
    "broker_flow.freq": {
        "meaning": "UNKNOWN",
        "status": "UNKNOWN",
        "evidence": "the fetcher maps ONE vendor field onto both buy and sell rows "
                    "(stockbit_fetcher.py:719,731). Tested against the independent "
                    "stockbit_flow daily summary over 34,017 ticker-days: SUM(freq) / "
                    "(flow.buy_freq+flow.sell_freq) has median 0.0080, and no variant "
                    "reaches 2% agreement on any day. A ~100x shortfall is far beyond what "
                    "top-25 truncation can explain (the top 25 carry ~75% of value).",
        "research_use": "FORBIDDEN as a transaction count or ticket-size denominator until a "
                        "vendor probe establishes its unit.",
    },
    "broker_flow.investor_type": {
        "meaning": "Ownership category of the BROKERAGE HOUSE: foreign-owned / local / "
                   "government-state-owned brokerage",
        "status": "VERIFIED",
        "evidence": "95 broker codes, exactly one investor_type each, invariant across "
                    "3,026,786 rows, 397 sessions, both sides, both calendar years. The third "
                    "class has exactly four constant members (CC, NI, OD, DX). IDX investor "
                    "reporting has two classes, not three.",
        "research_use": "say 'foreign-owned brokerage flow'. NEVER 'foreign investor flow', "
                        "'retail investor flow' or 'institutional investor flow'.",
    },
    "broker_flow.side": {
        "meaning": "the sign of the broker's net, not a raw buy/sell split",
        "status": "VERIFIED WITH DEFECT",
        "evidence": "757 BUY rows carry lot<0 and 1,822 SELL rows carry lot>0 in the Dataset A "
                    "window — vendor rounding where net lots and net value disagree in sign",
        "research_use": "derive direction from sign(value), never from the side column",
    },
    "bandar_detector.total_buyer / total_seller": {
        "meaning": "UNCENSORED count of brokers net-buying / net-selling that ticker-session",
        "status": "VERIFIED",
        "evidence": "disclosed_rows == min(total, 25) in 30,626/30,626 ticker-days on both "
                    "sides, zero mismatches; parsed from the same API response as broker_flow "
                    "yet reaching 79 where broker rows cap at 25; live probe at full limit "
                    "returned exactly total_buyer / total_seller rows",
        "research_use": "the only uncensored participation measure available",
    },
    "bandar_detector.value / volume": {
        "meaning": "NET CROSSED volume and its rupiah value — NOT market traded totals",
        "status": "VERIFIED",
        "evidence": "value = volume*100*avg_price with standard deviation 0.0000 across 30,468 "
                    "rows; live probe: bandar.volume equals the sum of positive net lots at "
                    "ratio 1.0000",
        "research_use": "NEVER a denominator for concentration or market volume. Use "
                        "ohlcv.volume for traded volume.",
    },
    "ohlcv.close / volume": {
        "meaning": "traded price and volume, regular board; adjustment basis MIXED",
        "status": "VERIFIED WITH DEFECT",
        "evidence": "already split-adjusted for PTRO, CUAN and DSSA; NOT adjusted for RAJA "
                    "(close/broker-VWAP 4.946 before the ex-date, 0.993 after)",
        "research_use": "run the residual detector at build time; quarantine basis mismatches "
                        "rather than applying a blanket adjustment (which would double-adjust "
                        "the three already-correct tickers)",
    },
    "idx_tickers.in_idx80": {
        "meaning": "a stale single snapshot written 2026-04-27; NOT historical membership",
        "status": "REJECTED FOR RESEARCH USE",
        "evidence": "matches no reconstitution period (best 64/80 at P2, 57/80 at P7); contains "
                    "the 692nd most liquid stock on the exchange; no writer exists in the "
                    "codebase, only readers",
        "research_use": "FORBIDDEN. Use the frozen PIT roster artifact.",
    },
    "IDX auto-rejection bands": {
        "meaning": "regime-dependent daily price limits; the Dataset B window STRADDLES a boundary",
        "status": "VERIFIED",
        "evidence": "LC-PM-0009: R3 symmetric to 2025-04-07, R4 ARB -15% from 2025-04-08 "
                    "(SK Kep-00003/BEI/04-2025). Dataset B: 58 R3 sessions, 328 R4 sessions.",
        "research_use": "each session carries a band_regime label. LC-PM-0009 states pooling "
                        "across regimes without conditioning is void under B8.",
    },
}


def main(write=False):
    conn = F.ro_connect()
    cal = F.SessionCalendar.load("v2"); ros = F.PitRoster.load("v1")
    rep = F.vwap_ratio_report(conn, ros.universe, cal.sessions)
    fp = fingerprint(conn, ros, cal, quarantined=rep["flagged"])
    print("=== Dataset B fingerprint ===")
    print(f"  columns pinned : broker_flow {len(BROKER_FLOW_COLUMNS)}, "
          f"bandar {len(BANDAR_COLUMNS)}, ohlcv {len(OHLCV_COLUMNS)}")
    print(f"  cells in scope : {fp['cells_in_scope']:,} over {fp['tickers']} tickers")
    print(f"  quarantined    : {fp['quarantined']}")
    print(f"  roster sha256  : {fp['roster_artifact_sha256'][:32]}…")
    print(f"  calendar sha256: {fp['calendar_artifact_sha256'][:32]}…")
    print(f"  DATASET FINGERPRINT: {fp['dataset_fingerprint']}")
    print(f"\n=== semantic register: {len(SEMANTIC_REGISTER)} entries ===")
    for k, v in SEMANTIC_REGISTER.items():
        print(f"  {v['status']:24s} {k}")
    if write:
        p = HERE / "artifacts" / "DATASET_B_FINGERPRINT_v1.json"
        p.write_text(json.dumps(fp, indent=1, sort_keys=True) + "\n")
        (HERE / "artifacts" / f"{p.name}.sha256").write_text(
            f"{fp['dataset_fingerprint']}  {p.name}\n")
        q = HERE / "artifacts" / "DATASET_B_SEMANTIC_REGISTER_v1.json"
        q.write_text(json.dumps(SEMANTIC_REGISTER, indent=1, sort_keys=True) + "\n")
        print(f"\nwrote {p.name} and {q.name}")
    conn.close(); return fp


if __name__ == "__main__":
    main(write="--write" in sys.argv)
