"""
Signal Checker untuk Multi-Strategy Backtest
Tambahkan kode ini ke engine/strategies.py
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def check_current_entry_signal(ticker: str, strategy: str, df: pd.DataFrame = None) -> dict:
    """
    Cek apakah ticker memenuhi entry criteria dari strategy yang dipilih
    pada data terbaru (last bar)
    
    Args:
        ticker: Kode ticker (e.g., 'BBCA')
        strategy: Nama strategy ('vol_weighted', 'momentum', dll)
        df: DataFrame OHLCV ticker (optional, akan di-fetch jika None)
    
    Returns:
        dict: {
            'has_signal': bool,
            'reason': str (penjelasan kenapa pass/tidak pass),
            'details': dict (nilai-nilai metric untuk display)
        }
    """
    # Jika df tidak diberikan, fetch dari database
    if df is None:
        df = get_ticker_data(ticker)
    
    if df.empty or len(df) < 20:
        return {
            'has_signal': False,
            'reason': 'Data tidak cukup (minimum 20 bars)',
            'details': {}
        }
    
    # Route ke fungsi checker sesuai strategy
    if strategy == 'vol_weighted':
        return check_vol_weighted_signal(df)
    elif strategy == 'momentum':
        return check_momentum_signal(df)
    elif strategy == 'vwap_reversion':
        return check_vwap_reversion_signal(df)
    elif strategy == 'conservative':
        return check_conservative_signal(df)
    else:
        return {
            'has_signal': False,
            'reason': f'Strategy {strategy} belum didukung',
            'details': {}
        }


def check_vol_weighted_signal(df: pd.DataFrame) -> dict:
    """
    Vol-Weighted Entry Signal Checker
    
    Entry Criteria:
    - Volume Ratio (VR) > 1.8x
    - Price > VWAP (optional tapi recommended)
    """
    latest = df.iloc[-1]
    
    # Hitung Volume Ratio
    if 'avg_volume_20d' not in df.columns:
        df['avg_volume_20d'] = df['volume'].rolling(window=20).mean()
        latest = df.iloc[-1]
    
    current_volume = latest['volume']
    avg_volume = latest['avg_volume_20d']
    
    if pd.isna(avg_volume) or avg_volume == 0:
        return {
            'has_signal': False,
            'reason': 'Avg volume tidak tersedia',
            'details': {}
        }
    
    vr = current_volume / avg_volume
    
    # Hitung VWAP
    if 'vwap' not in df.columns:
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        latest = df.iloc[-1]
    
    current_price = latest['close']
    vwap = latest['vwap']
    price_vs_vwap = ((current_price - vwap) / vwap * 100) if vwap > 0 else 0
    
    # Check entry criteria
    vr_pass = vr > 1.8
    price_above_vwap = current_price > vwap
    
    has_signal = vr_pass
    
    if has_signal:
        vwap_status = "above VWAP ✓" if price_above_vwap else "below VWAP ⚠"
        reason = f"VR {vr:.2f}x > 1.8 ✓, Price {vwap_status}"
    else:
        reason = f"VR {vr:.2f}x ≤ 1.8 (butuh > 1.8)"
    
    return {
        'has_signal': has_signal,
        'reason': reason,
        'details': {
            'vr': round(vr, 2),
            'current_volume': int(current_volume),
            'avg_volume': int(avg_volume),
            'price': round(current_price, 2),
            'vwap': round(vwap, 2),
            'price_vs_vwap_pct': round(price_vs_vwap, 2),
            'price_above_vwap': price_above_vwap
        }
    }


def get_ticker_data(ticker: str) -> pd.DataFrame:
    """
    Fetch OHLCV data untuk ticker dari database
    """
    import sqlite3
    
    db_path = 'data/walkforward.db'
    
    try:
        conn = sqlite3.connect(db_path)
        query = f"""
            SELECT date, open, high, low, close, volume
            FROM ohlcv
            WHERE ticker = '{ticker}'
            ORDER BY date ASC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return pd.DataFrame()
