"""GAP 4: quarterly fundamentals. The annual fetch gave ~4-5 observations per
ticker with a median staleness of 363 days, so factors barely moved within a
year and power against them was weak. Quarterly gives ~4x the observations and
cuts staleness to ~1 quarter."""
import sys,os,time,json; sys.path.insert(0,".")
import yfinance as yf, pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/zoo.pkl"); tk=sorted(S.ticker.unique())
WANT_BS=['Stockholders Equity','Total Assets','Total Debt','Cash And Cash Equivalents']
WANT_IS=['Net Income','Total Revenue','Operating Income','Gross Profit','EBIT']
WANT_CF=['Operating Cash Flow','Free Cash Flow','Capital Expenditure']
rows=[];fails=[]
print(f"fetching QUARTERLY fundamentals for {len(tk)} tickers",flush=True)
for i,t in enumerate(tk,1):
    try:
        y=yf.Ticker(f"{t}.JK")
        recs={}
        for src,want in ((y.quarterly_balance_sheet,WANT_BS),
                         (y.quarterly_financials,WANT_IS),
                         (y.quarterly_cashflow,WANT_CF)):
            if src is None or src.empty: continue
            for lbl in want:
                hit=[ix for ix in src.index if str(ix)==lbl]
                if not hit: continue
                for col in src.columns:
                    v=src.loc[hit[0],col]
                    if pd.isna(v): continue
                    recs.setdefault(pd.Timestamp(col).normalize(),{})[lbl]=float(v)
        for per,vals in recs.items():
            rows.append({'ticker':t,'period_end':per,**vals})
    except Exception as e: fails.append((t,type(e).__name__))
    if i%100==0: print(f"  {i}/{len(tk)} rows={len(rows):,} fails={len(fails)}",flush=True)
    time.sleep(0.25)
Q=pd.DataFrame(rows); Q.to_pickle(f"{SP}/fund_quarterly.pkl")
json.dump([list(f) for f in fails],open(f"{SP}/quarterly_fails.json","w"))
print(f"\nDONE rows={len(Q):,} tickers={Q.ticker.nunique() if len(Q) else 0} fails={len(fails)}")
if len(Q):
    print("period range:",Q.period_end.min(),"->",Q.period_end.max())
    print(f"obs per ticker: median {Q.groupby('ticker').size().median():.0f}  max {Q.groupby('ticker').size().max()}")
    for c in Q.columns:
        if c in ('ticker','period_end'): continue
        print(f"  {c:36} {100*Q[c].notna().mean():5.1f}%")
