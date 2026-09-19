"""Dividend history back to inception. corporate_actions only spans 2021-07+,
so the extended panel cannot compute yield without this."""
import sys,os,time,json; sys.path.insert(0,".")
import yfinance as yf, pandas as pd, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
tk=sorted(pd.read_pickle(f"{SP}/zoo.pkl").ticker.unique())
rows=[];fails=[]
print(f"fetching full dividend history for {len(tk)} tickers",flush=True)
for i,t in enumerate(tk,1):
    try:
        d=yf.Ticker(f"{t}.JK").dividends
        if d is not None and len(d):
            idx=pd.to_datetime(d.index).tz_localize(None)
            rows.append(pd.DataFrame({'ticker':t,'date':idx,'value':d.values}))
    except Exception as e: fails.append((t,type(e).__name__))
    if i%100==0: print(f"  {i}/{len(tk)} rows={sum(len(x) for x in rows):,} fails={len(fails)}",flush=True)
    time.sleep(0.2)
D=pd.concat(rows,ignore_index=True) if rows else pd.DataFrame()
D.to_pickle(f"{SP}/div_hist.pkl"); json.dump([list(f) for f in fails],open(f"{SP}/div_fails.json","w"))
print(f"\nDONE rows={len(D):,} tickers={D.ticker.nunique() if len(D) else 0} fails={len(fails)}")
if len(D):
    print("range:",D.date.min(),"->",D.date.max())
    print("pre-2021-07 dividends:",int((D.date<pd.Timestamp('2021-07-05')).sum()))
