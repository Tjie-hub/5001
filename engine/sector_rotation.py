"""
sector_rotation.py — IDX Sector Momentum Scoring & Rotation Logic
=================================================================
Scores each IDX sector based on average price momentum of member tickers.
Top sectors = OVERWEIGHT (trade freely), bottom = UNDERWEIGHT (avoid entries).
"""

import sqlite3
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

from config import DB_PATH
from data.db import connect as db_connect

# IDX Sector → Ticker mapping (based on tickers in DB)
IDX_SECTOR_MAP: Dict[str, List[str]] = {
    "Financials":        ["BBCA","BBRI","BMRI","BBNI","BNGA","NISP","BRIS","BTPS","BBTN","BANK","BFIN","ARTO","PNBN"],
    "Energy":            ["ADRO","PTBA","ITMG","HRUM","ESSA","MEDC","PGAS","PGEO"],
    "BasicMaterials":    ["ANTM","INCO","MDKA","NCKL","AMMN","MBMA","BRPT","TPIA","ISSP","SMGR","INTP","SMCB","INKP","TKIM"],
    "ConsumerNCyclical": ["UNVR","ICBP","INDF","MYOR","KLBF","SIDO","GGRM","HMSP"],
    "ConsumerCyclical":  ["ACES","MAPI","AMRT","ERAA","LPPF","HERO","CPIN","JPFA","FAST","HOKI"],
    "Technology":        ["EMTK","DNET","WIFI","LINK","SCMA","BUKA","GOTO"],
    "Telecom":           ["TLKM","EXCL","ISAT","TBIG","TOWR","MTEL"],
    "Property":          ["BSDE","CTRA","PWON","SMRA","KIJA"],
    "Industrials":       ["ASII","UNTR","JSMR","PTPP","LSIP","AALI","DSNG"],
    "Healthcare":        ["MIKA","HEAL","CMRY"],
    "Infrastructure":    ["AKRA"],
}

# Reverse map: ticker → sector (uppercase)
TICKER_SECTOR_MAP: Dict[str, str] = {
    t: s for s, tickers in IDX_SECTOR_MAP.items() for t in tickers
}


def get_ticker_sector(ticker: str) -> str:
    return TICKER_SECTOR_MAP.get(ticker.upper(), "Unknown")


def _calc_return(closes: pd.Series, lookback: int) -> float:
    if len(closes) < lookback + 1:
        return 0.0
    v0 = closes.iloc[-(lookback + 1)]
    v1 = closes.iloc[-1]
    return float((v1 / v0 - 1) * 100) if v0 > 0 else 0.0


def score_sectors(db_path: str = None) -> List[Dict]:
    """
    Calculate weighted momentum score per IDX sector.
    Score = 0.5 * ret5D + 0.3 * ret10D + 0.2 * ret20D (avg across members in DB).
    Returns list sorted descending, tagged OVERWEIGHT / NEUTRAL / UNDERWEIGHT.
    """
    db_path = db_path or DB_PATH
    conn = db_connect(db_path)
    try:
        tickers_in_db = {r[0] for r in conn.execute(
            "SELECT DISTINCT ticker FROM ohlcv"
        ).fetchall()}
    except Exception:
        conn.close()
        return []

    sector_scores = []

    for sector, members in IDX_SECTOR_MAP.items():
        available = [t for t in members if t in tickers_in_db]
        if not available:
            continue

        ret5_list, ret10_list, ret20_list = [], [], []

        for ticker in available:
            try:
                df = pd.read_sql(
                    "SELECT close FROM ohlcv WHERE ticker=? ORDER BY date DESC LIMIT 22",
                    conn, params=(ticker,)
                )
                closes = df["close"].astype(float).dropna().iloc[::-1].reset_index(drop=True)
                if len(closes) < 6:
                    continue
                ret5_list.append(_calc_return(closes, 5))
                if len(closes) >= 11:
                    ret10_list.append(_calc_return(closes, 10))
                if len(closes) >= 21:
                    ret20_list.append(_calc_return(closes, 20))
            except Exception:
                continue

        if not ret5_list:
            continue

        avg5  = float(np.mean(ret5_list))
        avg10 = float(np.mean(ret10_list)) if ret10_list else avg5
        avg20 = float(np.mean(ret20_list)) if ret20_list else avg10
        score = round(0.5 * avg5 + 0.3 * avg10 + 0.2 * avg20, 3)

        sector_scores.append({
            "sector":    sector,
            "score":     score,
            "ret_5d":    round(avg5, 2),
            "ret_10d":   round(avg10, 2),
            "ret_20d":   round(avg20, 2),
            "n_tickers": len(ret5_list),
            "members":   available,
            "weight":    "NEUTRAL",  # filled below
        })

    conn.close()

    sector_scores.sort(key=lambda x: x["score"], reverse=True)
    n = len(sector_scores)
    for i, s in enumerate(sector_scores):
        if i < 3:
            s["weight"] = "OVERWEIGHT"
        elif i >= n - 3:
            s["weight"] = "UNDERWEIGHT"

    return sector_scores


def is_sector_tradeable(ticker: str, scored: List[Dict] = None) -> Tuple[bool, str]:
    """
    Returns (tradeable, reason).
    UNDERWEIGHT sectors block new entries.
    """
    sector = get_ticker_sector(ticker)
    if sector == "Unknown":
        return True, "sector unknown"

    if scored is None:
        scored = score_sectors()

    entry = next((s for s in scored if s["sector"] == sector), None)
    if entry is None:
        return True, "sector not ranked"

    weight = entry["weight"]
    score  = entry["score"]
    if weight == "UNDERWEIGHT":
        return False, f"{sector} UNDERWEIGHT (score {score:+.2f}%)"
    return True, f"{sector} {weight} (score {score:+.2f}%)"
