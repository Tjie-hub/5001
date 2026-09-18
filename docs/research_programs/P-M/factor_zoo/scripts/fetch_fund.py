"""Fetch IDX fundamentals from Yahoo for every ticker in the research panel.

Writes THREE raw artefacts to the scratch dir; nothing touches the production DB
(new production data needs its own table + fetcher + fence review, which this is
not). Everything is stored as-reported-by-the-source with its period-end date so
the point-in-time lag can be applied later, not baked in here.
"""
import sys,os,time,json; sys.path.insert(0,".")
import yfinance as yf, pandas as pd, numpy as np, warnings
warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/zoo.pkl")
tickers=sorted(S.ticker.unique())
print(f"fetching {len(tickers)} tickers",flush=True)
WANT_BS=['Stockholders Equity','Total Equity Gross Minority Interest','Total Assets',
         'Total Debt','Cash And Cash Equivalents','Common Stock Equity']
WANT_FI=['Net Income','Total Revenue','Operating Income','Gross Profit',
         'Net Income Common Stockholders','EBIT']
shares=[];fund=[];fails=[]
for i,t in enumerate(tickers,1):
    try:
        y=yf.Ticker(f"{t}.JK")
        sh=y.get_shares_full(start="2020-06-01")
        if sh is not None and len(sh):
            d=pd.DataFrame({'ticker':t,'date':pd.to_datetime(sh.index).tz_localize(None),'shares':sh.values})
            shares.append(d)
        bs=y.balance_sheet; fi=y.financials
        recs={}
        for src,want in ((bs,WANT_BS),(fi,WANT_FI)):
            if src is None or src.empty: continue
            for lbl in want:
                hit=[ix for ix in src.index if str(ix)==lbl]
                if not hit: continue
                for col in src.columns:
                    v=src.loc[hit[0],col]
                    if pd.isna(v): continue
                    recs.setdefault(pd.Timestamp(col).normalize(),{})[lbl]=float(v)
        for per,vals in recs.items():
            fund.append({'ticker':t,'period_end':per,**vals})
    except Exception as e:
        fails.append((t,type(e).__name__))
    if i%50==0: print(f"  {i}/{len(tickers)}  fails={len(fails)}",flush=True)
    time.sleep(0.25)
SH=pd.concat(shares,ignore_index=True) if shares else pd.DataFrame()
FU=pd.DataFrame(fund)
SH.to_pickle(f"{SP}/fund_shares.pkl"); FU.to_pickle(f"{SP}/fund_annual.pkl")
json.dump(fails,open(f"{SP}/fund_fails.json","w"))
print(f"\nDONE  shares rows={len(SH):,} tickers={SH.ticker.nunique() if len(SH) else 0}")
print(f"      annual rows={len(FU):,} tickers={FU.ticker.nunique() if len(FU) else 0}")
print(f"      failures={len(fails)}")
if len(FU): print("      period_end range:",FU.period_end.min(),"->",FU.period_end.max())
