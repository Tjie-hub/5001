"""Fetch annual cash-flow statements: operating cash flow and capex, for
CF/P (the EM value measure) and RNOA-style profitability."""
import sys,os,time,json; sys.path.insert(0,".")
import yfinance as yf, pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/zoo.pkl"); tickers=sorted(S.ticker.unique())
WANT=['Operating Cash Flow','Capital Expenditure','Free Cash Flow',
      'Net Income From Continuing Operations','Depreciation And Amortization']
rows=[];fails=[]
print(f"fetching cashflow for {len(tickers)} tickers",flush=True)
for i,t in enumerate(tickers,1):
    try:
        cf=yf.Ticker(f"{t}.JK").cashflow
        if cf is not None and not cf.empty:
            for col in cf.columns:
                rec={'ticker':t,'period_end':pd.Timestamp(col).normalize()}
                got=False
                for lbl in WANT:
                    hit=[ix for ix in cf.index if str(ix)==lbl]
                    if hit and not pd.isna(cf.loc[hit[0],col]):
                        rec[lbl]=float(cf.loc[hit[0],col]); got=True
                if got: rows.append(rec)
    except Exception as e: fails.append((t,type(e).__name__))
    if i%100==0: print(f"  {i}/{len(tickers)} fails={len(fails)}",flush=True)
    time.sleep(0.25)
CF=pd.DataFrame(rows); CF.to_pickle(f"{SP}/fund_cashflow.pkl")
print(f"\nDONE rows={len(CF):,} tickers={CF.ticker.nunique() if len(CF) else 0} fails={len(fails)}")
if len(CF): print("period range:",CF.period_end.min(),"->",CF.period_end.max())
