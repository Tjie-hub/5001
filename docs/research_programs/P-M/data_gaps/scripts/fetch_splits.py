"""Split history back to inception. The pre-2021 fetch used auto_adjust=False,
so raw prices carry split discontinuities -- 227 moves beyond IDX auto-rejection
limits, concentrated 2007-09. Without back-adjustment these become spurious
volatility, which would corrupt the very factor under test."""
import sys,os,time,json; sys.path.insert(0,".")
import yfinance as yf, pandas as pd, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
tk=sorted(pd.read_pickle(f"{SP}/zoo.pkl").ticker.unique())
rows=[];fails=[]
print(f"fetching split history for {len(tk)} tickers",flush=True)
for i,t in enumerate(tk,1):
    try:
        s=yf.Ticker(f"{t}.JK").splits
        if s is not None and len(s):
            idx=pd.to_datetime(s.index).tz_localize(None)
            rows.append(pd.DataFrame({'ticker':t,'date':idx,'ratio':s.values}))
    except Exception as e: fails.append((t,type(e).__name__))
    if i%150==0: print(f"  {i}/{len(tk)} rows={sum(len(x) for x in rows):,}",flush=True)
    time.sleep(0.2)
S=pd.concat(rows,ignore_index=True) if rows else pd.DataFrame()
S.to_pickle(f"{SP}/split_hist.pkl")
print(f"\nDONE rows={len(S):,} tickers={S.ticker.nunique() if len(S) else 0} fails={len(fails)}")
if len(S): print("range:",S.date.min(),"->",S.date.max(),"| pre-2021:",int((S.date<pd.Timestamp('2021-07-05')).sum()))
