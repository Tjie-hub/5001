import yfinance as yf
from data.db import get_db

TICKERS = ['AALI', 'ACES', 'ADRO', 'AGII', 'AKRA', 'AMMN', 'AMPG', 'AMRT', 'ANJT', 'ANTM', 'ARTO', 'ASII', 'BANK', 'BBCA', 'BBNI', 'BBRI', 'BBTN', 'BFIN', 'BMKI', 'BMRI', 'BNGA', 'BORN', 'BRIS', 'BRPT', 'BSDE', 'BTPS', 'BUKA', 'CMRY', 'CPIN', 'CTRA', 'DNET', 'DSNG', 'EMTK', 'ERAA', 'ESSA', 'EXCL', 'FAST', 'GGRM', 'GOTO', 'HEAL', 'HERO', 'HMSP', 'HOKI', 'HRUM', 'ICBP', 'INCO', 'INDF', 'INKP', 'INPC', 'INTP', 'ISAT', 'ISSP', 'ITMG', 'JPFA', 'JSMR', 'KIJA', 'KLBF', 'LINK', 'LPPF', 'LSIP', 'MAPI', 'MBMA', 'MDKA', 'MEDC', 'MFIN', 'MIKA', 'MLPL', 'MTEL', 'MYOR', 'NCKL', 'NISP', 'PANI', 'PGAS', 'PGEO', 'PNBN', 'PTBA', 'PTPP', 'PWON', 'SCMA', 'SIDO', 'SMCB', 'SMGR', 'SMRA', 'TBIG', 'TKIM', 'TLKM', 'TOWR', 'TPIA', 'UNTR', 'UNVR', 'WIFI']

def fetch_ticker(ticker, period="2y"):
    symbol = ticker + ".JK"
    print(f"Fetching {symbol}...")
    df = yf.download(symbol, period=period, auto_adjust=True, progress=False)
    if df.empty:
        print(f"  WARNING: no data for {symbol}")
        return 0
    df = df.reset_index()
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df.rename(columns={"Date":"date","Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
    df["date"] = df["date"].astype(str).str[:10]
    conn = get_db()
    saved = 0
    for _, row in df.iterrows():
        try:
            conn.execute("INSERT OR IGNORE INTO ohlcv (ticker,date,open,high,low,close,volume) VALUES (?,?,?,?,?,?,?)",
                (ticker, row["date"], row["open"], row["high"], row["low"], row["close"], row["volume"]))
            saved += 1
        except: pass
    conn.commit()
    conn.close()
    print(f"  {saved} bars saved")
    return saved

def fetch_all(period="2y"):
    for t in TICKERS:
        fetch_ticker(t, period)
