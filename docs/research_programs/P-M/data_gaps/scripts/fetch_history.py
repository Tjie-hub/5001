"""GAP 2: extend daily OHLCV back before the corpus start of 2021-07-05.

CRITICAL CAVEAT baked into the output: the source answers only for tickers
listed TODAY, so every pre-2021 bar collected here is a SURVIVOR's bar. The
script therefore also records, per year, how many tickers it can see, so the
survivorship rate can be measured against the known IDX listed-company counts
(2018:619 2019:668 2020:713 2021:766 2022:825 2023:903 2024:947 2025:956).
"""
import sys,os,time,json; sys.path.insert(0,".")
import yfinance as yf, pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/zoo.pkl"); tk=sorted(S.ticker.unique())
CUT=pd.Timestamp("2021-07-05")
out=[];meta=[];fails=[]
print(f"fetching full history for {len(tk)} tickers (keeping bars before {CUT.date()})",flush=True)
for i,t in enumerate(tk,1):
    try:
        h=yf.Ticker(f"{t}.JK").history(period="max",auto_adjust=False)
        if h is None or h.empty: fails.append((t,'empty')); continue
        h.index=pd.to_datetime(h.index).tz_localize(None)
        meta.append({'ticker':t,'first':h.index.min(),'last':h.index.max(),'n':len(h)})
        old=h[h.index<CUT]
        if len(old):
            d=pd.DataFrame({'ticker':t,'date':old.index,
                            'open':old['Open'].values,'high':old['High'].values,
                            'low':old['Low'].values,'close':old['Close'].values,
                            'volume':old['Volume'].values})
            out.append(d)
    except Exception as e: fails.append((t,type(e).__name__))
    if i%100==0: print(f"  {i}/{len(tk)} kept={sum(len(x) for x in out):,} fails={len(fails)}",flush=True)
    time.sleep(0.2)
H=pd.concat(out,ignore_index=True) if out else pd.DataFrame()
M=pd.DataFrame(meta)
H.to_pickle(f"{SP}/hist_pre2021.pkl"); M.to_pickle(f"{SP}/hist_meta.pkl")
json.dump([list(f) for f in fails],open(f"{SP}/hist_fails.json","w"))
print(f"\nDONE pre-2021 bars={len(H):,}  tickers={H.ticker.nunique() if len(H) else 0}  fails={len(fails)}")
if len(M):
    print("\n=== SURVIVORSHIP MEASUREMENT ===")
    known={2018:619,2019:668,2020:713,2021:766,2022:825,2023:903,2024:947,2025:956}
    print(f"{'year':>6} {'visible':>8} {'IDX listed':>11} {'survivorship':>13}")
    for y in range(2005,2026):
        vis=int((M['first']<=pd.Timestamp(f"{y}-12-31")).sum())
        k=known.get(y)
        s=f"{100*vis/k:11.1f}%" if k else "          -"
        print(f"{y:>6} {vis:8} {str(k) if k else '-':>11} {s:>13}")
    print("\n  'visible' = tickers alive TODAY that already had prices in that year.")
    print("  survivorship% below 100 is the share of that year's universe still listed now;")
    print("  the shortfall is exactly the bias a pre-2021 backfill would carry.")
